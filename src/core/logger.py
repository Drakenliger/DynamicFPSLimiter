import logging
import sys # Import sys module
import threading
import os
import faulthandler

log_messages = []

# GuiQueue (injected at startup via set_gui_queue) so DPG log-widget updates are
# deferred to the main DPG thread. add_log may be called from any background thread,
# and DearPyGui is only safe on the thread that owns the render context.
_gui_queue = None
_log_lock = threading.Lock()
_dpg = None
_fatal_sink_file = None
_fatal_sink_owned = False


def set_gui_queue(queue):
    """Inject the GuiQueue so DPG log-widget updates run on the main thread."""
    global _gui_queue
    _gui_queue = queue


def set_dpg(dpg_instance):
    """Inject the dearpygui module instance used for log-widget updates."""
    global _dpg
    _dpg = dpg_instance


def close_fatal_sink():
    """Close and disable the fatal crash sink if owned, or reset reference."""
    global _fatal_sink_file, _fatal_sink_owned
    try:
        faulthandler.disable()
    except Exception:
        pass
    if _fatal_sink_owned and _fatal_sink_file is not None:
        try:
            if not getattr(_fatal_sink_file, "closed", True):
                _fatal_sink_file.close()
        except Exception:
            pass
    _fatal_sink_file = None
    _fatal_sink_owned = False


def _enable_fatal_sink(log_file_path):
    global _fatal_sink_file, _fatal_sink_owned
    root = logging.getLogger()

    matching_handler = None
    if log_file_path:
        abs_path = os.path.abspath(log_file_path)
        for h in root.handlers:
            if isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None):
                if os.path.abspath(h.baseFilename) == abs_path:
                    matching_handler = h
                    break

    if matching_handler is None:
        for h in root.handlers:
            if isinstance(h, logging.FileHandler) and getattr(h, "stream", None):
                matching_handler = h
                break

    if matching_handler is not None and getattr(matching_handler, "stream", None):
        stream = matching_handler.stream
        if stream and not getattr(stream, "closed", True):
            if _fatal_sink_file is stream and faulthandler.is_enabled():
                return
            try:
                faulthandler.enable(file=stream)
                _fatal_sink_file = stream
                _fatal_sink_owned = False
                return
            except Exception:
                pass

    if not log_file_path:
        return
    abs_path = os.path.abspath(log_file_path)
    if _fatal_sink_file is not None and not getattr(_fatal_sink_file, "closed", True):
        if getattr(_fatal_sink_file, "name", None) == abs_path and faulthandler.is_enabled():
            return

    try:
        log_dir = os.path.dirname(abs_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        close_fatal_sink()
        sink = open(abs_path, "a", encoding="utf-8", buffering=1)
        faulthandler.enable(file=sink)
        _fatal_sink_file = sink
        _fatal_sink_owned = True
    except Exception:
        pass


# Function to initialize logging configuration and set the exception hook
def init_logging(log_file_path):
    """Configure error logging and uncaught main/thread exception hooks."""
    if log_file_path:
        abs_path = os.path.abspath(log_file_path)
        log_dir = os.path.dirname(abs_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception:
                pass

        root = logging.getLogger()
        has_matching_file_handler = any(
            isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None)
            and os.path.abspath(h.baseFilename) == abs_path
            for h in root.handlers
        )
        if not has_matching_file_handler:
            handler = logging.FileHandler(abs_path, encoding='utf-8')
            handler.setLevel(logging.ERROR)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            root.addHandler(handler)
            if root.level > logging.ERROR or root.level == logging.NOTSET:
                root.setLevel(logging.ERROR)

    _enable_fatal_sink(log_file_path)

    # Redirect uncaught exceptions to the error_log_exception function
    if not getattr(sys.excepthook, "_dfl_error_log_hook", False):
        def main_error_log(exc_type, exc_value, exc_traceback):
            error_log_exception(exc_type, exc_value, exc_traceback)
        main_error_log._dfl_error_log_hook = True
        sys.excepthook = main_error_log

    current_thread_hook = threading.excepthook
    if not getattr(current_thread_hook, "_dfl_error_log_hook", False):
        previous = current_thread_hook
        def thread_error_log(args):
            try:
                if args.exc_type is not SystemExit:
                    logging.error("Uncaught thread exception (%s)", args.thread.name if args.thread else "unknown",
                                  exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
                    for h in logging.root.handlers:
                        try:
                            h.flush()
                        except Exception:
                            pass
            finally:
                previous(args)
        thread_error_log._dfl_error_log_hook = True
        threading.excepthook = thread_error_log

# Error logging function - now just logs the error
def error_log_exception(exc_type, exc_value, exc_traceback):
    """Logs uncaught exceptions using the configured logger."""
    if exc_type is not SystemExit:
        logging.error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        for h in logging.root.handlers:
            try:
                h.flush()
            except Exception:
                pass

def _apply_log_text_to_widget():
    """Read the current log snapshot and update the LogText widget.

    Runs on the main DPG thread (via the GuiQueue) when a queue is configured, so
    ``dpg.*`` is only ever touched where it is safe.
    """
    with _log_lock:
        text = "\n".join(log_messages)
    global _dpg
    if _dpg is None:
        return
    try:
        if _dpg.does_item_exist("LogText"):
            _dpg.set_value("LogText", text)
    except Exception:
        # If there's any issue with the GUI update, just continue silently.
        # The log messages are still stored in the log_messages list.
        pass


def add_log(message):
    with _log_lock:
        log_messages.insert(0, message)  # Add message at the top
        log_messages[:] = log_messages[:50]  # Keep only the latest 50 messages
    if _gui_queue is not None:
        _gui_queue.submit(_apply_log_text_to_widget)
    else:
        _apply_log_text_to_widget()


def refresh_log_display():
    """Refresh the log display widget with current messages."""
    if _gui_queue is not None:
        _gui_queue.submit(_apply_log_text_to_widget)
    else:
        _apply_log_text_to_widget()
