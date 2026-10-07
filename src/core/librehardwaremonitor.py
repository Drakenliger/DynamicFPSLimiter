from core.lhm_loader import ensure_loaded, get_types, LHMLoadError
from pathlib import Path
from collections import deque, defaultdict
import time
import threading
try:
    import numpy as np
except ModuleNotFoundError:
    np = None

def _percentile(data, percentile):
    if not data:
        return None
    if np is not None:
        return float(np.percentile(data, percentile))
    # Pure Python percentile fallback when numpy is not installed
    s = sorted(data)
    k = (len(s) - 1) * (percentile / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(s):
        return float(s[f])
    return float(s[f] + (s[c] - s[f]) * (k - f))
import os
import sys

def get_selected_sensor_details(hardware, sensor_map):
    """Return a list of dicts for selected sensors: [{'sensor_type': ..., 'name': ..., 'value': ..., 'identifier': ...}]"""
    details = []
    name_counts = defaultdict(int)

    for sensor in hardware.Sensors:
        if sensor.SensorType not in sensor_map:
            continue

        wanted_names = sensor_map.get(sensor.SensorType)
        if wanted_names is not None and sensor.Name not in wanted_names:
            continue

        base_name = sensor.Name
        stype = sensor.SensorType
        count = name_counts[(stype, base_name)]
        if count == 0:
            name = base_name
        else:
            name = f"{base_name} ({count})"
        name_counts[(stype, base_name)] += 1

        identifier = str(sensor.Identifier) if hasattr(sensor, "Identifier") and sensor.Identifier is not None else None
        details.append({
            "sensor_type": sensor.SensorType,
            "name": name,
            "value": sensor.Value,
            "identifier": identifier,
        })
    return details

def get_selected_sensor_values(hardware, sensor_map):
    """Return a dict of selected sensor values for the given hardware, only for specified sensor types."""
    result = {}
    for d in get_selected_sensor_details(hardware, sensor_map):
        if d["value"] is not None:
            result.setdefault(d["sensor_type"], {})[d["name"]] = d["value"]
    return result

def get_all_sensor_infos(base_dir, logger=None):

    try:
        Computer, SensorType, HardwareType = get_types(base_dir)
    except LHMLoadError as exc:
        if logger is not None and hasattr(logger, "add_log"):
            logger.add_log(f"LibreHardwareMonitor unavailable ({exc}); no LibreHM sensors will be listed.")
        return []

    sensors = []
    cpu_count = 0
    gpu_count = 0

    try:
        computer = Computer()

        computer.IsGpuEnabled = True
        computer.IsCpuEnabled = True
        computer.Open()
    except Exception as exc:
        if logger is not None and hasattr(logger, "add_log"):
            logger.add_log(f"LibreHardwareMonitor unavailable ({exc}); no LibreHM sensors will be listed.")
        return []

    try:
        for hw in computer.Hardware:
            hw.Update()
            if hw.HardwareType == HardwareType.Cpu:
                cpu_count += 1
                param_indices = {"Load": 0, "Power": 0, "Temperature": 0}
                name_counts = defaultdict(int)  # track duplicate sensor names per sensor type
                for sensor in hw.Sensors:
                    if sensor.SensorType in [SensorType.Load, SensorType.Power, SensorType.Temperature]:
                        sensor_type_str = sensor.SensorType.ToString() if hasattr(sensor.SensorType, "ToString") else str(sensor.SensorType)
                        param_indices[sensor_type_str] += 1

                        # Handle duplicate sensor names per sensor type
                        base_name = sensor.Name
                        count = name_counts[(sensor.SensorType, base_name)]
                        if count == 0:
                            indexed_name = base_name
                        else:
                            indexed_name = f"{base_name} ({count})"
                        name_counts[(sensor.SensorType, base_name)] = count + 1

                        parameter_id = f"cpu{cpu_count}_{sensor_type_str.lower()}_{param_indices[sensor_type_str]:02d}"
                        hw_id = f"cpu{cpu_count}"
                        identifier = str(sensor.Identifier) if hasattr(sensor, "Identifier") and sensor.Identifier is not None else None
                        sensors.append({
                            "hw_type": hw.HardwareType,
                            "hw_name": hw.Name,
                            "sensor_type": sensor.SensorType,
                            "sensor_name": sensor.Name,
                            "sensor_name_indexed": indexed_name,   # match LHMSensor naming for duplicates
                            "parameter_id": parameter_id,
                            "hw_id": hw_id,
                            "identifier": identifier,
                        })
            elif hw.HardwareType in (HardwareType.GpuAmd, HardwareType.GpuNvidia):
                gpu_count += 1
                param_indices = {"Load": 0, "Power": 0, "Temperature": 0}
                name_counts = defaultdict(int)  # track duplicate sensor names per sensor type
                for sensor in hw.Sensors:
                    if sensor.SensorType in [SensorType.Load, SensorType.Power, SensorType.Temperature]:
                        sensor_type_str = sensor.SensorType.ToString() if hasattr(sensor.SensorType, "ToString") else str(sensor.SensorType)
                        param_indices[sensor_type_str] += 1

                        # Handle duplicate sensor names per sensor type
                        base_name = sensor.Name
                        count = name_counts[(sensor.SensorType, base_name)]
                        if count == 0:
                            indexed_name_only = base_name
                        else:
                            indexed_name_only = f"{base_name} ({count})"
                        name_counts[(sensor.SensorType, base_name)] = count + 1

                        parameter_id = f"gpu{gpu_count}_{sensor_type_str.lower()}_{param_indices[sensor_type_str]:02d}"
                        hw_id = f"gpu{gpu_count}"
                        # Build the indexed sensor name exactly as LHMSensor._poll_loop uses for gpu_percentiles keys
                        sensor_name_indexed = f"{gpu_count} {indexed_name_only}"
                        identifier = str(sensor.Identifier) if hasattr(sensor, "Identifier") and sensor.Identifier is not None else None
                        sensors.append({
                            "hw_type": hw.HardwareType,
                            "hw_name": hw.Name,
                            "sensor_type": sensor.SensorType,
                            "sensor_name": sensor.Name,
                            "sensor_name_indexed": sensor_name_indexed,
                            "parameter_id": parameter_id,
                            "hw_id": hw_id,
                            "identifier": identifier,
                        })
    finally:
        computer.Close()
    return sensors

class LHMSensor:
    def __init__(self, get_running, logger_instance, dpg_instance, themes_instance, interval=0.1, max_samples=20, percentile=70, base_dir=None, gui_queue=None):
        self._running = get_running  # This should be a callable, e.g. lambda: running
        self.logger = logger_instance
        self.dpg = dpg_instance
        self.gui_queue = gui_queue
        self.themes = themes_instance
        self.interval = interval
        self.max_samples = max_samples
        self.percentile = percentile
        self.cpu_history = defaultdict(lambda: deque(maxlen=max_samples))
        self.gpu_history = defaultdict(lambda: deque(maxlen=max_samples))
        self.cpu_history_long = defaultdict(lambda: deque(maxlen=600))
        self.gpu_history_long = defaultdict(lambda: deque(maxlen=600))
        self.cpu_percentiles = defaultdict(float)
        self.gpu_percentiles = defaultdict(float)
        self._thread = None
        self._lock = threading.Lock()
        self._should_stop = threading.Event()
        self.disabled = False

        # Ensure assembly loaded and types available
        try:
            Computer, SensorType, HardwareType = ensure_loaded(base_dir, self.logger)
        except LHMLoadError as exc:
            self.disabled = True
            self.logger.add_log(f"LibreHardwareMonitor unavailable ({exc}); LibreHM monitoring disabled.")
            self.Computer = None
            self.SensorType = None
            self.HardwareType = None
            self.computer = None
            self.cpu_name = None
            self.gpu_name = None
            return
        self.Computer = Computer
        self.SensorType = SensorType
        self.HardwareType = HardwareType

        # Initialize computer
        self._computer_open = False
        self._create_and_open_computer()


        # Define which sensors to extract for each hardware type and sensor type
        self.CPU_SENSORS = {
            SensorType.Load: None, #['CPU Total', 'CPU Core Max'],
            SensorType.Temperature: None, #['CPU Package'],
            SensorType.Power: None,  #['CPU Package'],
        }

        self.GPU_SENSORS = {
            SensorType.Load: None,  # None means all available
            SensorType.Temperature: None, #['GPU Core', 'GPU Hot Spot'],
            SensorType.Power: None, #['GPU Package'],
        }

        self.cpu_name = self.get_cpu_name()
        self.gpu_name = self.get_gpu_name()

    def set_gui_queue(self, gui_queue):
        """Attach the GuiQueue used to defer dpg.* calls from the poll thread."""
        self.gui_queue = gui_queue

    def _submit_dpg(self, fn, *args, **kwargs):
        """Run a dpg.* call on the main render thread when a GuiQueue is attached.

        Called from the LHM poll thread; without a queue the call runs directly
        (used by tests and legacy single-threaded callers).
        """
        if self.gui_queue is not None:
            self.gui_queue.submit(fn, *args, **kwargs)
        else:
            fn(*args, **kwargs)

    def get_cpu_name(self):
        for hw in self.computer.Hardware:
            if hw.HardwareType == self.HardwareType.Cpu:
                return hw.Name
        return None

    def get_gpu_name(self): #TODO Remove this if unused
        for hw in self.computer.Hardware:
            if hw.HardwareType in (self.HardwareType.GpuAmd, self.HardwareType.GpuNvidia):
                return hw.Name
        return None

    def get_gpu_names(self):
        """Return a list of all detected GPU names."""
        names = []
        for hw in self.computer.Hardware:
            if hw.HardwareType in (self.HardwareType.GpuAmd, self.HardwareType.GpuNvidia):
                names.append(hw.Name)
        return names

    def _create_and_open_computer(self):
        """Create a fresh Computer, enable CPU/GPU, and open it.

        Idempotent with respect to a prior close: always builds a new instance
        so a Stop -> Start cycle re-opens clean hardware rather than iterating
        a Computer that has already been Closed.
        """
        self.computer = self.Computer()
        self.computer.IsGpuEnabled = True
        self.computer.IsCpuEnabled = True
        self.computer.Open()
        self._computer_open = True

    def start(self):
        if self.disabled:
            return
    # Reset histories and percentiles
        with self._lock:
            self.cpu_history.clear()
            self.gpu_history.clear()
            self.cpu_history_long.clear()
            self.gpu_history_long.clear()
            self.cpu_percentiles.clear()
            self.gpu_percentiles.clear()
        if self._thread and self._thread.is_alive():
            return  # Already running
        if self.computer is None or not self._computer_open:
            self._create_and_open_computer()
            self.cpu_name = self.get_cpu_name()
        self._should_stop.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._should_stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self.computer is not None and self._computer_open:
            self.computer.Close()
            self._computer_open = False
        self.logger.add_log("Stopped LibreHardwareMonitor polling.")

    def _poll_loop(self):
        calculate_percentile = _percentile

        self.cpu_percentiles = defaultdict(float)
        self.gpu_percentiles = defaultdict(float)

        while not self._should_stop.is_set() and self._running():
            gpu_index = 1
            refreshed_cpu_keys = set()
            refreshed_gpu_keys = set()
            cpu_hw_name = None

            for hw in self.computer.Hardware:
                if hw.HardwareType == self.HardwareType.Cpu:
                    hw.Update()
                    details = get_selected_sensor_details(hw, self.CPU_SENSORS)
                    with self._lock:
                        for d in details:
                            if d["value"] is None:
                                continue
                            sensor_type = d["sensor_type"]
                            name = d["name"]
                            val = round(d["value"], 2)
                            key = (sensor_type, name)
                            identifier = d["identifier"]
                            canon_key = identifier if identifier else key

                            self.cpu_history[canon_key].append(val)
                            self.cpu_history_long[canon_key].append(val)
                            p = round(calculate_percentile(self.cpu_history[canon_key], self.percentile), 2)
                            self.cpu_percentiles[canon_key] = p
                            refreshed_cpu_keys.add(canon_key)

                            # Mirror to display key and identifier for display / backward compatibility without mixing histories
                            if canon_key != key:
                                self.cpu_history[key] = self.cpu_history[canon_key]
                                self.cpu_history_long[key] = self.cpu_history_long[canon_key]
                                self.cpu_percentiles[key] = p
                                refreshed_cpu_keys.add(key)
                            if canon_key != identifier and identifier:
                                self.cpu_history[identifier] = self.cpu_history[canon_key]
                                self.cpu_history_long[identifier] = self.cpu_history_long[canon_key]
                                self.cpu_percentiles[identifier] = p
                                refreshed_cpu_keys.add(identifier)

                    cpu_hw_name = hw.Name
                elif hw.HardwareType in (self.HardwareType.GpuAmd, self.HardwareType.GpuNvidia):
                    hw.Update()
                    details = get_selected_sensor_details(hw, self.GPU_SENSORS)
                    with self._lock:
                        for d in details:
                            if d["value"] is None:
                                continue
                            sensor_type = d["sensor_type"]
                            name = f"{gpu_index} {d['name']}"
                            val = round(d["value"], 2)
                            key = (sensor_type, name)
                            identifier = d["identifier"]
                            canon_key = identifier if identifier else key

                            self.gpu_history[canon_key].append(val)
                            self.gpu_history_long[canon_key].append(val)
                            p = round(calculate_percentile(self.gpu_history[canon_key], self.percentile), 2)
                            self.gpu_percentiles[canon_key] = p
                            refreshed_gpu_keys.add(canon_key)

                            # Mirror to display key and identifier for display / backward compatibility without mixing histories
                            if canon_key != key:
                                self.gpu_history[key] = self.gpu_history[canon_key]
                                self.gpu_history_long[key] = self.gpu_history_long[canon_key]
                                self.gpu_percentiles[key] = p
                                refreshed_gpu_keys.add(key)
                            if canon_key != identifier and identifier:
                                self.gpu_history[identifier] = self.gpu_history[canon_key]
                                self.gpu_history_long[identifier] = self.gpu_history_long[canon_key]
                                self.gpu_percentiles[identifier] = p
                                refreshed_gpu_keys.add(identifier)

                    if not hasattr(self, 'gpu_hw_names'):
                        self.gpu_hw_names = []
                    if hw.Name not in self.gpu_hw_names:
                        self.gpu_hw_names.append(hw.Name)
                    gpu_index += 1

            # Mark unrefreshed sensors missing (None) each tick
            with self._lock:
                for k in list(self.cpu_percentiles.keys()):
                    if k not in refreshed_cpu_keys:
                        self.cpu_percentiles[k] = None
                for k in list(self.gpu_percentiles.keys()):
                    if k not in refreshed_gpu_keys:
                        self.gpu_percentiles[k] = None

            # Update ReadingsText in the GUI
            cpu_str = self.format_history(self.cpu_history, self.cpu_percentiles, cpu_hw_name if 'cpu_hw_name' in locals() else "CPU")
            gpu_titles = self.gpu_hw_names if hasattr(self, 'gpu_hw_names') else ["GPU"]
            gpu_str = ""
            # Split GPU history by index for display
            for idx, gpu_name in enumerate(gpu_titles, start=1):
                gpu_str += self.format_history(
                    {k: v for k, v in self.gpu_history.items() if k[1].startswith(f"{idx} ")},
                    self.gpu_percentiles,
                    gpu_name
                ) + "\n\n"
            readings = cpu_str + "\n\n" + gpu_str
            try:
                self._submit_dpg(self.dpg.set_value, "ReadingsText", readings)
            except Exception as e:
                self.logger.add_log(f"Failed to update ReadingsText: {e}")
            time.sleep(self.interval)

    def format_history(self, hist, percentiles, title):
        # Define column widths
        type_w = 12
        name_w = 26
        last_w = 8
        perc_w = 10
        header = f"{'Type':<{type_w}}| {'Name':<{name_w}}| {'Current':>{last_w}}| {'70th %ile':>{perc_w}}"
        lines = [f"{title}:"]
        lines.append(header)
        lines.append("-" * len(header))
        for key, values in hist.items():
            if not isinstance(key, tuple) or len(key) != 2:
                continue
            sensor_type, name = key
            sensor_type_str = getattr(sensor_type, 'name', str(sensor_type))
            last_val = values[-1] if values else 'N/A'
            percentile_val = percentiles.get(key, 'N/A')
            lines.append(
                f"{sensor_type_str:<{type_w}}| {name:<{name_w}}| {str(last_val):>{last_w}}| {str(percentile_val):>{perc_w}}"
            )
        return "\n".join(lines)

    def get_cpu_history(self):
        with self._lock:
            return dict(self.cpu_history)

    def get_gpu_history(self):
        with self._lock:
            return dict(self.gpu_history)

