from core.lhm_loader import get_types, LHMLoadError
import os
from pathlib import Path
import statistics
from core.cap_policy import evaluate_legacy_cap_change
from collections import deque

def evaluate_librehm_decision(has_enabled_sensors, decrease_checks, increase_checks, has_missing_enabled_data):
    """
    Pure decision helper for LibreHM monitoring method.
    Returns (should_decrease, should_increase).
    - If no sensors are enabled, returns (False, False).
    - Decrease: True if any enabled sensor with valid data exceeds upper threshold.
    - Increase: True only if all enabled sensors have valid data and all meet lower threshold.
                If any enabled sensor is missing data (None value or empty history), increase is non-qualifying (False).
    """
    if not has_enabled_sensors:
        return (False, False)
    should_decrease = any(decrease_checks) if decrease_checks else False
    if has_missing_enabled_data:
        should_increase = False
    else:
        should_increase = all(increase_checks) if increase_checks else False
    return (should_decrease, should_increase)

class FPSUtils:
    def __init__(self, cm, lhm_sensor, logger=None, dpg=None, viewport_width=610, base_dir=None):
        self.cm = cm
        self.lhm_sensor = lhm_sensor
        self.logger = logger
        self.dpg = dpg
        self.viewport_width = viewport_width
        self.last_fps_limits = []

        self.reset_summary_statistics()

        # Ensure LHM assembly loaded and get types (pass Base_dir from caller)
        try:
            Computer, SensorType, HardwareType = get_types(base_dir)
        except LHMLoadError as exc:
            if self.logger is not None:
                self.logger.add_log(f"LibreHardwareMonitor unavailable ({exc}); LibreHM monitoring disabled.")
            SensorType, HardwareType = None, None
        self.SensorType = SensorType
        self.HardwareType = HardwareType

    def current_stepped_limits(self):
        maximum = int(self.dpg.get_value("input_maxcap"))
        minimum = int(self.dpg.get_value("input_mincap"))
        step = int(self.dpg.get_value("input_capstep"))
        ratio = int(self.dpg.get_value("input_capratio"))
        use_custom = self.dpg.get_value("input_capmethod").lower()

        if use_custom == "custom":
            custom_limits = self.dpg.get_value("input_customfpslimits")
            if custom_limits and self.cm:
                try:
                    custom_limits = self.cm.parse_and_normalize_string_to_decimal_set(custom_limits)
                    if custom_limits:
                        return custom_limits
                except Exception as e:
                    if self.logger:
                        self.logger.add_log(f"Error parsing custom FPS limits: {e}")
            if self.logger:
                self.logger.add_log("Custom FPS limits unavailable; falling back to stepped limits.")
            return self.make_stepped_values(maximum, minimum, step)
        elif use_custom == "step":
            return self.make_stepped_values(maximum, minimum, step)
        elif use_custom == "ratio":
            return self.make_ratioed_values(maximum, minimum, ratio)
        else:
            if self.logger:
                self.logger.add_log(f"Unknown FPS cap method '{use_custom}'; falling back to stepped limits.")
            return self.make_stepped_values(maximum, minimum, step)

    def make_stepped_values(self, maximum, minimum, step):
        values = list(range(maximum, minimum - 1, -step))
        if minimum not in values:
            values.append(minimum)
        return sorted(set(values))

    def make_ratioed_values(self, maximum, minimum, ratio):
        values = []
        current = maximum
        ratio_factor = 1 - (ratio / 100.0)
        if ratio_factor <= 0 or ratio_factor >= 1:
            return sorted(set([maximum, minimum]))
        prev_diff = None
        values.append(int(round(current)))

        while current >= minimum:
            current = current * ratio_factor
            rounded_current = int(round(current))
            if len(values) >= 3:
                prev_diff = abs(values[-1] - values[-2])
            if prev_diff is not None and abs(rounded_current - values[-1]) > prev_diff:
                rounded_current = values[-1] - prev_diff

            # Duplicate detection and correction
            while rounded_current in values and rounded_current > minimum:
                rounded_current -= 1

            values.append(rounded_current)
            current = rounded_current

            if rounded_current <= minimum:
                break
        if minimum not in values:
            values.append(minimum)
        custom_limits = sorted(x for x in set(values) if x >= minimum)
        return custom_limits

    def update_fps_cap_visualization(self, active_applied_cap=None):
        dpg = self.dpg

        fps_limits = self.current_stepped_limits()
        if not fps_limits:
            if dpg.does_item_exist("Foreground"):
                dpg.delete_item("Foreground")
            self.last_fps_limits = []
            self._last_ladder_geometry = None
            return

        scale = getattr(dpg, "scale", 1)
        if not isinstance(scale, (int, float)) or scale <= 0:
            scale = 1
        # ScaledDPG getters return physical pixels; drawing takes logical pixels.
        # Configuration also works before an item has a rendered rectangle.
        configuration = dpg.get_item_configuration("fps_cap_drawlist")
        panel_width = configuration["width"] / scale
        panel_height = configuration["height"] / scale
        labels = []
        metrics = []
        if len(fps_limits) < 20:
            for cap in fps_limits:
                label = str(cap)
                extent = dpg.get_text_size(label)
                # DPG documents text measurement as available after the first
                # frame. Retry next refresh rather than caching guessed metrics.
                if not extent or extent[1] <= 0:
                    return
                labels.append(label)
                # Normalize the current font's advance to draw_text's explicit
                # size. Both measurements are physical, so their ratio is unitless;
                # neither is sent through the pixel adapter a second time.
                metrics.append(extent[0] / extent[1])
        geometry = (panel_width, scale, active_applied_cap, panel_height, tuple(metrics))
        if (fps_limits == self.last_fps_limits
                and geometry == getattr(self, "_last_ladder_geometry", None)
                and dpg.does_item_exist("Foreground")):
            return

        self.last_fps_limits = fps_limits.copy()
        self._last_ladder_geometry = geometry
        dpg.delete_item("Foreground")
        with dpg.draw_layer(tag="Foreground", parent="fps_cap_drawlist"):
            draw_width = panel_width
            margin = 5
            usable_width = draw_width - 2 * margin
            y_center = 15
            tick_half_h = 6
            highlight_half_h = 10

            min_fps = min(fps_limits)
            max_fps = max(fps_limits)
            fps_range = max_fps - min_fps

            positions = [margin + usable_width // 2 if fps_range == 0 else
                         margin + int(float((cap - min_fps) / fps_range) * usable_width)
                         for cap in fps_limits]
            label_positions = {}
            text_size = 14
            if labels:
                # Pack complete glyph bounds, including two pixels of bearing/
                # rounding slack. Close fractional caps can share nearly the same
                # tick; move their labels apart, or use the second reserved row.
                gap = 4
                rows = 1
                if sum(m * text_size + 2 for m in metrics) + gap * (len(labels) - 1) > draw_width:
                    rows = 2 if panel_height >= 57 else 1
                lanes = [list(range(row, len(labels), rows)) for row in range(rows)]
                for lane in lanes:
                    available = draw_width - 2 * len(lane) - gap * (len(lane) - 1)
                    text_size = min(text_size, available / sum(metrics[i] for i in lane))
                for row, lane in enumerate(lanes):
                    right = -gap
                    for index in lane:
                        width = metrics[index] * text_size + 2
                        left = max(right + gap, min(draw_width - width, positions[index] - width / 2))
                        label_positions[index] = [left, y_center + 8 + row * (text_size + gap)]
                        right = left + width
                    # Backward packing keeps the final glyph inside the container,
                    # without losing any labels or changing their Decimal strings.
                    left = draw_width + gap
                    for index in reversed(lane):
                        width = metrics[index] * text_size + 2
                        label_positions[index][0] = min(label_positions[index][0], left - gap - width)
                        left = label_positions[index][0]

            for index, cap in enumerate(fps_limits):
                x_pos = positions[index]

                is_highlighted = False
                if active_applied_cap is not None:
                    try:
                        from decimal import Decimal
                        is_highlighted = (Decimal(str(cap)) == Decimal(str(active_applied_cap)))
                    except Exception:
                        is_highlighted = (cap == active_applied_cap)

                if is_highlighted:
                    # Highlight current active cap with prominent yellow/gold line & thickness
                    dpg.draw_line(
                        (x_pos, y_center - highlight_half_h),
                        (x_pos, y_center + highlight_half_h),
                        color=(255, 215, 0),
                        thickness=3,
                        parent="Foreground"
                    )
                else:
                    dpg.draw_line(
                        (x_pos, y_center - tick_half_h),
                        (x_pos, y_center + tick_half_h),
                        color=(200, 200, 200),
                        thickness=1,
                        parent="Foreground"
                    )

                if len(fps_limits) < 20:
                    dpg.draw_text(
                        tuple(label_positions[index]),
                        labels[index],
                        color=(255, 215, 0) if is_highlighted else (200, 200, 200),
                        size=text_size,
                        parent="Foreground"
                    )

    def copy_from_plot(self):
        fps_limits = sorted(set(self.current_stepped_limits()))
        fps_limits_str = ", ".join(str(x) for x in fps_limits)
        self.dpg.set_value("input_customfpslimits", fps_limits_str)

    def reset_custom_limits(self):
        lowerlimit = self.dpg.get_value("input_mincap")
        upperlimit = self.dpg.get_value("input_maxcap")
        self.dpg.set_value("input_customfpslimits", f"{lowerlimit}, {upperlimit}")
        
    def evaluate_cap_change(self, gpu_values, cpu_values, monitoring_method):
        """
        Returns a tuple (should_decrease, should_increase).
        Preserves existing semantics:
          - Legacy: decrease = (gpu_decrease OR cpu_decrease), increase = (gpu_increase AND cpu_increase)
          - LibreHM: decrease = any(enabled sensor value >= upper), increase = all(enabled sensor value <= lower)
        """
        cm = self.cm
        lhm_sensor = self.lhm_sensor

        # Legacy behavior: GPU/CPU thresholds and delays
        if monitoring_method == "Legacy":
            return evaluate_legacy_cap_change(
                gpu_values, cpu_values, cm.delaybeforedecrease, cm.delaybeforeincrease,
                cm.gpucutofffordecrease, cm.cpucutofffordecrease,
                cm.gpucutoffforincrease, cm.cpucutoffforincrease)

        # LibreHM behavior: evaluate enabled sensors once and derive decrease/increase
        elif monitoring_method == "LibreHM":
            decrease_checks = []
            increase_checks = []
            groups = {}
            sensor_infos = getattr(cm, "sensor_infos", []) or []

            if not sensor_infos:
                return (False, False)

            # Snapshot relevant dictionaries and deques under lhm_sensor._lock
            lock = getattr(lhm_sensor, "_lock", None)
            if lock is not None:
                with lock:
                    cpu_perc_snap = dict(getattr(lhm_sensor, "cpu_percentiles", {}))
                    gpu_perc_snap = dict(getattr(lhm_sensor, "gpu_percentiles", {}))
                    cpu_hist_snap = {k: list(v) for k, v in getattr(lhm_sensor, "cpu_history_long", {}).items()}
                    gpu_hist_snap = {k: list(v) for k, v in getattr(lhm_sensor, "gpu_history_long", {}).items()}
                    gpu_hw_names_snap = list(getattr(lhm_sensor, "gpu_hw_names", [])) if hasattr(lhm_sensor, "gpu_hw_names") else []
            else:
                cpu_perc_snap = dict(getattr(lhm_sensor, "cpu_percentiles", {}))
                gpu_perc_snap = dict(getattr(lhm_sensor, "gpu_percentiles", {}))
                cpu_hist_snap = {k: list(v) for k, v in getattr(lhm_sensor, "cpu_history_long", {}).items()}
                gpu_hist_snap = {k: list(v) for k, v in getattr(lhm_sensor, "gpu_history_long", {}).items()}
                gpu_hw_names_snap = list(getattr(lhm_sensor, "gpu_hw_names", [])) if hasattr(lhm_sensor, "gpu_hw_names") else []

            has_enabled_sensors = False
            has_missing_enabled_data = False

            for sensor in sensor_infos:
                param_id = sensor.get("parameter_id")
                enable_tag = f"input_{param_id}_enable"
                upper_tag = f"input_{param_id}_upper"
                lower_tag = f"input_{param_id}_lower"

                if not param_id or not self.dpg.does_item_exist(enable_tag):
                    continue

                try:
                    if not self.dpg.get_value(enable_tag):
                        continue
                except Exception:
                    continue

                has_enabled_sensors = True

                # read thresholds; if invalid, skip corresponding check
                upper = None
                lower = None
                try:
                    upper = float(self.dpg.get_value(upper_tag))
                except Exception:
                    pass
                try:
                    lower = float(self.dpg.get_value(lower_tag))
                except Exception:
                    pass

                sensor_type = sensor.get("sensor_type")
                sensor_name = sensor.get("sensor_name")
                hw_name = sensor.get("hw_name")
                hw_type = sensor.get("hw_type")
                identifier = sensor.get("identifier")
                value = None

                perc_snap = cpu_perc_snap if hw_type == self.HardwareType.Cpu else gpu_perc_snap
                hist_snap = cpu_hist_snap if hw_type == self.HardwareType.Cpu else gpu_hist_snap

                if identifier:
                    # Metadata has identifier: resolve ONLY that identity even if missing (None)
                    value = perc_snap.get(identifier)
                    values_long = hist_snap.get(identifier, [])
                elif hw_type == self.HardwareType.Cpu:
                    sensor_name_indexed = sensor.get("sensor_name_indexed") or sensor_name
                    key = (sensor_type, sensor_name_indexed)
                    value = perc_snap.get(key)
                    values_long = hist_snap.get(key, [])
                    if value is None and key != (sensor_type, sensor_name):
                        key_raw = (sensor_type, sensor_name)
                        value = perc_snap.get(key_raw)
                        values_long = hist_snap.get(key_raw, [])
                else:
                    sensor_name_indexed = sensor.get("sensor_name_indexed") or sensor_name
                    key = (sensor_type, sensor_name_indexed)
                    value = perc_snap.get(key)
                    values_long = hist_snap.get(key, [])
                    if value is None:
                        if gpu_hw_names_snap:
                            try:
                                idx = gpu_hw_names_snap.index(hw_name) + 1
                                key2 = (sensor_type, f"{idx} {sensor_name}")
                                value = perc_snap.get(key2)
                                values_long = hist_snap.get(key2, [])
                            except ValueError:
                                value = None
                                values_long = []
                        if value is None:
                            for k, v in perc_snap.items():
                                if isinstance(k, tuple) and len(k) == 2 and k[0] == sensor_type and k[1].endswith(sensor_name):
                                    value = v
                                    break
                        
                        if not values_long:
                            for k, v in hist_snap.items():
                                if isinstance(k, tuple) and len(k) == 2 and k[0] == sensor_type and k[1].endswith(sensor_name):
                                    values_long = v
                                    break

                # compute avg/std/median for this sensor
                try:
                    avg = statistics.mean(values_long)
                    std = statistics.stdev(values_long) if len(values_long) > 1 else 0.0
                    med = statistics.median(values_long)
                    display_name = sensor_name
                    sensor_type_str = getattr(sensor_type, "name", str(sensor_type))
                    hw_display = hw_name or "Unknown"
                    groups.setdefault(hw_display, {}).setdefault(sensor_type_str, []).append(
                        (display_name, avg, std, med)
                    )
                except Exception:
                    # skip sensors that fail stats computation
                    pass

                # Log once per sensor
                self.logger.add_log(f"LibreHM check {hw_name}/{sensor_type}/{sensor_name}: value={value} lower={lower} upper={upper}")

                if value is None or not values_long:
                    has_missing_enabled_data = True
                else:
                    if upper is not None:
                        decrease_checks.append(value >= upper)
                    if lower is not None:
                        increase_checks.append(value <= lower)

            should_decrease, should_increase = evaluate_librehm_decision(
                has_enabled_sensors, decrease_checks, increase_checks, has_missing_enabled_data
            )

            # Sort sensor summary lines alphabetically (case-insensitive) before showing
            if groups:
                out_lines = []
                name_w = 26
                for hw in sorted(groups.keys(), key=lambda s: s.casefold()):
                    out_lines.append(f"{hw}")
                    for st in sorted(groups[hw].keys(), key=lambda s: s.casefold()):
                        out_lines.append(f"{st}:")
                        for sn, avg, std, med in sorted(groups[hw][st], key=lambda x: x[0].casefold()):
                            sn_col = f"{sn}:"
                            if len(sn_col) > name_w:
                                sn_col = sn_col[: max(0, name_w - 3)] + "..."
                            out_lines.append(f"  {sn_col:<{name_w}} avg={avg:6.2f} | std={std:6.2f} | med={med:6.2f}")
                    out_lines.append("")  # blank line between hardware blocks
                summary_text = "\n".join(out_lines).rstrip()
            else:
                summary_text = "No enabled LibreHM sensors with data."
            try:
                self.dpg.set_value("SummaryText", summary_text)
            except Exception:
                pass

            return (should_decrease, should_increase)

    def update_summary_statistics(self):
        dpg = self.dpg
        lhm_sensor = self.lhm_sensor

        # Update duration. Format elapsed_time (seconds) as HH:MM:SS
        total_seconds = int(self.elapsed_time)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        dpg.set_value("summary_duration", f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        def compute_stats(values):
            if not values:
                return ("--", "--", "--", "--")

            avg = statistics.mean(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
            median = statistics.median(values)
            try:
                mode = statistics.mode(values)
            except statistics.StatisticsError:
                mode = "--"
            return (f"{avg:.2f}", f"{std_dev:.2f}", f"{median:.2f}", f"{mode:.2f}")

        # Compute for FPS and cap summaries
        fps_avg, fps_std, fps_med, fps_mode = compute_stats(self.summary_fps)
        cap_avg, cap_std, cap_med, cap_mode = compute_stats(self.summary_cap)

        # Write to DPG fields (tags defined in app.py)
        try:
            dpg.set_value("summary_fps_avg", fps_avg)
            dpg.set_value("summary_fps_std", fps_std)
            dpg.set_value("summary_fps_median", fps_med)
            dpg.set_value("summary_fps_mode", fps_mode)

            dpg.set_value("summary_cap_avg", cap_avg)
            dpg.set_value("summary_cap_std", cap_std)
            dpg.set_value("summary_cap_median", cap_med)
            dpg.set_value("summary_cap_mode", cap_mode)

        except Exception:
            # silently ignore any GUI update errors
            pass

    def reset_summary_statistics(self):
        self.elapsed_time = 0.0
        self.summary_fps = []
        self.summary_cap = []

        lhm_sensor = getattr(self, "lhm_sensor", None)
        if lhm_sensor is not None:
            lock = getattr(lhm_sensor, "_lock", None)
            if lock is not None:
                with lock:
                    if hasattr(lhm_sensor, "cpu_history_long"):
                        lhm_sensor.cpu_history_long.clear()
                    if hasattr(lhm_sensor, "gpu_history_long"):
                        lhm_sensor.gpu_history_long.clear()
            else:
                if hasattr(lhm_sensor, "cpu_history_long"):
                    lhm_sensor.cpu_history_long.clear()
                if hasattr(lhm_sensor, "gpu_history_long"):
                    lhm_sensor.gpu_history_long.clear()
