"""Fake 3D game: a minimal DearPyGui window that renders continuously via D3D11.

The app's GPU monitoring reads the PDH "GPU Engine" (``engtype_3D``) counter and
RTSS limits frame rate by hooking a D3D swap chain's ``Present``. A real commercial
game is the natural workload for both, but it is not scriptable. DearPyGui is a
D3D11 application, so a DPG window that renders every frame:

  * drives the GPU 3D engine (shows up in PDH ``engtype_3D``), and
  * is detected by RTSS as a DirectX app whose FPS can be limited.

This makes it a controllable stand-in for the "fake 3D game" in automated testing.
It is launched as a *separate process* so it has its own PID, a real window, and its
own D3D device -- exactly what PDH and RTSS observe for a game.

``--frametime-file`` writes buffered CSV timestamp (wall epoch seconds, matching
cap logs) and frame_time_ms per completed presentation. First frame timing starts
just before first render; later intervals span completed presentations. Motion,
intervals and duration use perf_counter, independent of wall-clock changes.
CSV closes and flushes on normal, interrupted and error exits.

Run:
    python tests/fake_game.py --title "DFL Fake Game" --ready-file <path>
        [--width 1024] [--height 768] [--load 8] [--fps-file <path>] [--duration 0]

The process writes ``--ready-file`` (JSON) once the first frame has been presented,
then keeps rendering until the window is closed, ``--duration`` elapses, or it is
killed. It is intentionally not a pytest module (no ``test_`` prefix).
"""
import csv
import math
from collections import deque
import argparse
import json
import os
import time


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Fake 3D game (DearPyGui D3D11 render loop)")
    ap.add_argument("--title", default="DFL Fake Game", help="window title (identifies the process)")
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=768)
    ap.add_argument("--load", type=int, default=8,
                    help="number of full-screen filled quads drawn per frame (3D engine load)")
    ap.add_argument("--ready-file", default=None, help="write JSON readiness signal here after first frame")
    ap.add_argument("--fps-file", default=None, help="write measured FPS here every ~0.5s")
    ap.add_argument("--frametime-file", help="per-present CSV: timestamp epoch seconds and frame_time_ms; first interval starts before first render")
    ap.add_argument("--duration", type=float, default=0.0,
                    help="auto-exit after N seconds (0 = run until window closed/killed)")
    ap.add_argument("--no-vsync", action="store_true", help="disable vsync (uncapped, heavier load)")
    return ap



def motion(elapsed, width):
    """Absolute elapsed seconds: two-second sweep, one-second rotation."""
    return elapsed % 2 / 2 * width, elapsed % 1 * math.tau


def graph_points(history, width, height):
    """Fixed 100ms vertical scale, newest sample at right."""
    return [(width * (history.maxlen - len(history) + i) / (history.maxlen - 1),
             height * (1 - min(max(ms, 0), 100) / 100))
            for i, ms in enumerate(history)]


class FrameTiming:
    def __init__(self, start, history_size=180):
        self.start = self.previous = self.fps_start = start
        self.history = deque(maxlen=history_size)
        self.frames = 0
        self.fps = self.last_ms = 0.0
        self.last_write = None

    def completed(self, now, wall):
        self.last_ms = (now - self.previous) * 1000
        self.previous = now
        self.history.append(self.last_ms)
        self.frames += 1
        span = now - self.fps_start
        self.fps = self.frames / span if span > 0 else 0.0
        if self.last_write is None or now - self.last_write >= 0.5:
            payload = {"fps": round(self.fps, 2), "frames": self.frames, "t": wall}
            self.frames = 0
            self.fps_start = self.last_write = now
            return payload
        return None


def main() -> int:
    args = build_arg_parser().parse_args()
    import dearpygui.dearpygui as dpg

    frame_file = None
    context_created = False
    try:
        if args.frametime_file:
            # File failures propagate, including buffered writes on close.
            frame_file = open(args.frametime_file, "w", newline="", encoding="utf-8")
            writer = csv.writer(frame_file)
            writer.writerow(("timestamp", "frame_time_ms"))
        dpg.create_context()
        context_created = True
        dpg.create_viewport(title=args.title, width=args.width, height=args.height,
                            resizable=True, decorated=True)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_viewport_vsync(not args.no_vsync)
        with dpg.window(label="FakeGame", tag="fg_window", no_scrollbar=True):
            metrics = dpg.add_text("FPS: warming up | Frame: warming up")
            dl = dpg.add_drawlist(width=args.width, height=args.height)
        dpg.set_primary_window("fg_window", True)
        timing = FrameTiming(time.perf_counter())
        first_frame = True
        while dpg.is_dearpygui_running():
            now = time.perf_counter()
            width = max(1, dpg.get_viewport_client_width() - 32)
            height = max(1, dpg.get_viewport_client_height() - 64)
            dpg.configure_item(dl, width=width, height=height)
            dpg.delete_item(dl, children_only=True)
            for i in range(max(1, args.load)):
                inset = (i % 5) * 8
                tint = (40 + i * 12) % 200
                dpg.draw_rectangle((inset, inset), (width - inset, height - inset),
                                   fill=(tint, 60, 90, 255), parent=dl)
            x, angle = motion(now - timing.start, width)
            dpg.draw_rectangle((x, 0), (x + 8, height),
                               color=(255, 255, 0, 255), fill=(255, 255, 0, 255), parent=dl)
            center = (width / 2, height / 3)
            tip = (center[0] + 35 * math.cos(angle), center[1] + 35 * math.sin(angle))
            dpg.draw_line(center, tip, color=(0, 255, 255, 255), thickness=6, parent=dl)
            graph_height = min(100, height)
            points = [(px, height - graph_height + py) for px, py in
                      graph_points(timing.history, width, graph_height)]
            dpg.draw_rectangle((0, height - graph_height), (width, height),
                               fill=(0, 0, 0, 230), parent=dl)
            if len(points) > 1:
                dpg.draw_polyline(points, color=(0, 255, 0, 255), thickness=2, parent=dl)
            dpg.set_value(metrics, f"FPS: {timing.fps:.1f} | Frame: {timing.last_ms:.2f} ms | Graph: 0–100 ms")
            dpg.render_dearpygui_frame()
            completed = time.perf_counter()
            wall = time.time()
            payload = timing.completed(completed, wall)
            if frame_file is not None:
                writer.writerow((wall, timing.last_ms))
            if payload is not None and args.fps_file:
                try:
                    with open(args.fps_file, "w", encoding="utf-8") as f:
                        json.dump(payload, f)
                except OSError:
                    pass
            if first_frame:
                first_frame = False
                if args.ready_file:
                    try:
                        with open(args.ready_file, "w", encoding="utf-8") as f:
                            json.dump({"ready": True, "pid": os.getpid(), "title": args.title,
                                       "width": args.width, "height": args.height,
                                       "load": args.load, "started": wall}, f)
                    except OSError as e:
                        print(f"[fake_game] failed to write ready-file: {e}", flush=True)
            if args.duration and completed - timing.start >= args.duration:
                dpg.stop_dearpygui()
                break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if frame_file is not None:
                frame_file.close()
        finally:
            if context_created:
                dpg.destroy_context()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
