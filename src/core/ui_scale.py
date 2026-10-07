"""Logical UI pixels → native pixels. No DPG import or Windows import side effects."""
import configparser
import ctypes
from ctypes import wintypes

UI_SCALE_CHOICES = ("Auto", "100%", "125%", "150%", "175%", "200%", "250%", "300%")


def normalize_preference(value):
    value = value.replace("%%", "%") if isinstance(value, str) else value
    return value if value in UI_SCALE_CHOICES else "Auto"


def resolve_scale(preference="Auto", dpi=96):
    preference = normalize_preference(preference)
    return (max(96, dpi or 96) / 96 if preference == "Auto"
            else int(preference[:-1]) / 100)


def pixels(value, scale, sentinel=True):
    """Preserve DPG's zero/negative auto-size values only for dimensions."""
    return value if sentinel and value <= 0 else round(value * scale)


def point(value, scale):
    return tuple(pixels(v, scale, sentinel=False) for v in value)


def titlebar_hit(point_xy, width, scale):
    x, y = point_xy
    return 0 <= y < pixels(40, scale) and 0 <= x < width - pixels(75, scale)


def read_preference(path):
    cfg = configparser.ConfigParser()
    cfg.read(path)
    return normalize_preference(cfg.get("Preferences", "ui_scale", raw=True, fallback="Auto"))


def _prototype(function, args, result):
    function.argtypes = args
    function.restype = result
    return function


def enable_native_dpi(loader=None):
    """Enable awareness before any HWND; no OS bitmap enlargement is used."""
    loader = loader if loader is not None else getattr(ctypes, "windll", None)
    if loader is None:
        return False
    try:
        fn = _prototype(loader.user32.SetProcessDpiAwarenessContext,
                        [ctypes.c_void_p], wintypes.BOOL)
        if fn(ctypes.c_void_p(-4)):  # PER_MONITOR_AWARE_V2, pointer-sized pseudo handle
            return True
    except (AttributeError, OSError):
        pass
    try:
        fn = _prototype(loader.shcore.SetProcessDpiAwareness, [ctypes.c_int], ctypes.c_long)
        if fn(2) == 0:
            return True
    except (AttributeError, OSError):
        pass
    try:
        return bool(_prototype(loader.user32.SetProcessDPIAware, [], wintypes.BOOL)())
    except (AttributeError, OSError):
        return False


def primary_monitor_dpi(loader=None):
    """The application launches centered on primary, so query that monitor."""
    loader = loader if loader is not None else getattr(ctypes, "windll", None)
    if loader is None:
        return 96
    try:
        monitor = _prototype(loader.user32.MonitorFromPoint,
                             [wintypes.POINT, wintypes.DWORD], ctypes.c_void_p)(wintypes.POINT(0, 0), 1)
        x, y = wintypes.UINT(), wintypes.UINT()
        fn = _prototype(loader.shcore.GetDpiForMonitor,
                        [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(wintypes.UINT),
                         ctypes.POINTER(wintypes.UINT)], ctypes.c_long)
        if fn(monitor, 0, ctypes.byref(x), ctypes.byref(y)) == 0 and x.value:
            return x.value
    except (AttributeError, OSError):
        pass
    try:
        dpi = _prototype(loader.user32.GetDpiForSystem, [], wintypes.UINT)()
        return dpi or 96
    except (AttributeError, OSError):
        return 96


# Only these APIs accept logical pixel dimensions. Texture allocation, plot
# data, event thresholds, IDs, colors and all other APIs pass through untouched.
_LAYOUT = frozenset(("window", "child_window", "plot", "drawlist", "tooltip",
                     "add_button", "add_image", "add_image_button", "add_input_int",
                     "add_input_text", "add_combo", "add_text", "add_spacer",
                     "add_checkbox", "add_radio_button", "configure_item", "create_viewport"))
_STYLES = ("FrameRounding", "WindowBorderSize", "ChildBorderSize", "FrameBorderSize",
           "WindowPadding", "WindowRounding", "ItemSpacing", "TabBarBorderSize", "TabRounding",
           "ChildRounding", "FramePadding", "ItemInnerSpacing", "ScrollbarSize",
           "ScrollbarRounding", "GrabMinSize", "GrabRounding", "IndentSpacing",
           "CellPadding", "WindowMinSize", "PopupRounding", "PopupBorderSize")
_PLOT_STYLES = ("LineWeight", "MarkerSize", "MarkerWeight", "ErrorBarSize",
                "ErrorBarWeight", "DigitalBitHeight", "DigitalBitGap", "PlotBorderSize", "MajorTickLen", "MinorTickLen", "MajorTickSize",
                "MinorTickSize", "MajorGridSize", "MinorGridSize", "MousePosPadding",
                "PlotDefaultSize", "PlotMinSize", "LabelPadding", "PlotPadding", "LegendPadding",
                "LegendInnerPadding", "LegendSpacing", "AnnotationPadding")


class ScaledDPG:
    """Explicit pixel-call adapter. Inputs remain logical; getters stay physical."""
    def __init__(self, dpg, scale=1):
        self.raw = dpg.raw if isinstance(dpg, ScaledDPG) else dpg
        self.scale = scale

    def __getattr__(self, name):
        original = getattr(self.raw, name)
        if name not in _LAYOUT and name not in (
                "add_font", "add_theme_style", "add_table_column", "draw_line",
                "draw_circle", "draw_text", "set_viewport_max_width", "set_viewport_max_height"):
            return original

        def call(*args, **kwargs):
            args = list(args)
            kwargs = dict(kwargs)
            if name in _LAYOUT:
                for key in ("width", "height", "wrap", "min_width", "min_height", "max_width", "max_height"):
                    if key in kwargs:
                        kwargs[key] = pixels(kwargs[key], self.scale)
                if "pos" in kwargs:
                    kwargs["pos"] = point(kwargs["pos"], self.scale)
                # x_pos/y_pos are physical screen coordinates, deliberately untouched.
            elif name == "add_font":
                if len(args) > 1:
                    args[1] = pixels(args[1], self.scale)
                elif "size" in kwargs:
                    kwargs["size"] = pixels(kwargs["size"], self.scale)
            elif name == "add_table_column":
                # DPG's default sizing policy is fixed; explicit stretch is a weight.
                if not kwargs.get("width_stretch", False) and "init_width_or_weight" in kwargs:
                    kwargs["init_width_or_weight"] = pixels(kwargs["init_width_or_weight"], self.scale)
            elif name == "add_theme_style":
                style = args[0] if args else kwargs.get("target")
                category = kwargs.get("category", getattr(self.raw, "mvThemeCat_Core", 0))
                if category == getattr(self.raw, "mvThemeCat_Core", 0):
                    keys = ["mvStyleVar_" + s for s in _STYLES]
                elif category == getattr(self.raw, "mvThemeCat_Plots", 1):
                    keys = ["mvPlotStyleVar_" + s for s in _PLOT_STYLES]
                else:
                    keys = []
                pixel_ids = {getattr(self.raw, key, None) for key in keys}
                pixel_ids.discard(None)
                if style in pixel_ids:
                    # DPG target/x/y may be positional; category is keyword-only.
                    # Negative y retains DPG's unspecified/default sentinel.
                    for index, key in ((1, "x"), (2, "y")):
                        if len(args) > index:
                            if key != "y" or args[index] >= 0:
                                args[index] *= self.scale
                        elif key in kwargs and (key != "y" or kwargs[key] >= 0):
                            kwargs[key] *= self.scale
            elif name.startswith("set_viewport_max_"):
                args[0] = pixels(args[0], self.scale)
            else:
                count = 2 if name == "draw_line" else 1
                for i in range(min(count, len(args))):
                    args[i] = point(args[i], self.scale)
                for key in ("p1", "p2", "center", "pos"):
                    if key in kwargs:
                        kwargs[key] = point(kwargs[key], self.scale)
                if name == "draw_circle" and len(args) > 1:
                    args[1] *= self.scale
                for key in ("radius", "size", "thickness"):
                    if key in kwargs:
                        kwargs[key] *= self.scale
                if name in ("draw_line", "draw_circle") and "thickness" not in kwargs:
                    kwargs["thickness"] = self.scale
            return original(*args, **kwargs)
        return call
