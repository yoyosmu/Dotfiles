import gi
gi.require_version('Gtk', '4.0')
from ignis.widgets import Widget
from ignis.app import IgnisApp
from gi.repository import GLib, Gtk
import subprocess
import json
import os
import math


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.expanduser("~/.config/ignis/eq/state.json")
HOOK_SCRIPT = os.path.expanduser("~/.config/ignis/eq/apply.sh")
POLL_MS = 400

FREQS = ["60", "170", "310", "600", "1K", "3K", "6K", "12K"]
N_BANDS = len(FREQS)

PRESETS = {
    "Flat":  [0.42, 0.42, 0.46, 0.50, 0.54, 0.58, 0.54, 0.46],
    "Bass":  [0.80, 0.70, 0.62, 0.55, 0.52, 0.52, 0.46, 0.38],
    "Rock":  [0.62, 0.54, 0.42, 0.40, 0.52, 0.68, 0.74, 0.70],
    "Pop":   [0.40, 0.46, 0.60, 0.70, 0.68, 0.62, 0.54, 0.42],
    "Vocal": [0.30, 0.36, 0.52, 0.72, 0.78, 0.72, 0.54, 0.36],
    "Jazz":  [0.48, 0.52, 0.46, 0.46, 0.54, 0.68, 0.68, 0.54],
}

PAD_X = 20
PAD_TOP = 14
PAD_BOTTOM = 14
HIT_RADIUS = 22

ACCENT = (0.65, 0.89, 0.63)
TRACK = (1, 1, 1, 0.12)


def load_state():
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
            vals = data.get("values")
            if isinstance(vals, list) and len(vals) == N_BANDS:
                return vals
    except Exception:
        pass
    return list(PRESETS["Flat"])


def state_mtime():
    try:
        return os.path.getmtime(STATE_FILE)
    except Exception:
        return 0.0


def save_state(values):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump({"values": values}, f)
    except Exception:
        pass


def apply_eq(values):
    db = [round((v - 0.5) * 24, 1) for v in values]
    save_state(values)
    if os.path.isfile(HOOK_SCRIPT) and os.access(HOOK_SCRIPT, os.X_OK):
        subprocess.Popen(
            [HOOK_SCRIPT] + [str(x) for x in db],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def matching_preset(values, tolerance=0.015):
    for name, preset in PRESETS.items():
        if all(abs(a - b) <= tolerance for a, b in zip(values, preset)):
            return name
    return None


def main():
    app = IgnisApp.get_default()
    app.apply_css(os.path.join(SCRIPT_DIR, "style.css"))

    state = {
        "values": load_state(),
        "active_band": None,
        "drag_start_y": 0.0,
        "last_mtime": state_mtime(),
    }
    hover_state = {"active": False}

    profile_text_lbl = Widget.Label(label="Flat", css_classes=["eq-profile-text"])

    chart_slot = Widget.Box(css_classes=["eq-chart-slot"])

    freq_labels = Widget.Box(
        spacing=0,
        homogeneous=True,
        css_classes=["eq-freq-row"],
        child=[Widget.Label(label=f, css_classes=["eq-freq-lbl"]) for f in FREQS],
    )

    def band_x(i, width):
        usable = width - 2 * PAD_X
        if N_BANDS == 1:
            return PAD_X
        return PAD_X + usable * (i / (N_BANDS - 1))

    def value_to_y(v, height):
        usable = height - PAD_TOP - PAD_BOTTOM
        return PAD_TOP + usable * (1 - v)

    def y_to_value(y, height):
        usable = height - PAD_TOP - PAD_BOTTOM
        v = 1 - (y - PAD_TOP) / usable
        return max(0.0, min(1.0, v))

    def sync_profile_label():
        if hover_state["active"]:
            return
        match = matching_preset(state["values"])
        profile_text_lbl.set_label(match if match else "Custom")

    def reset_all(*_):
        state["values"] = [0.5] * N_BANDS
        area.queue_draw()
        apply_eq(state["values"])
        state["last_mtime"] = state_mtime()
        refresh_preset_buttons()
        sync_profile_label()

    profile_btn = Widget.Button(
        css_classes=["eq-profile-btn"],
        child=profile_text_lbl,
        on_click=reset_all,
    )

    profile_hover = Gtk.EventControllerMotion()

    def on_profile_hover_enter(controller, x, y):
        hover_state["active"] = True
        profile_text_lbl.set_label("Reset")
        profile_btn.set_css_classes(["eq-profile-btn", "eq-profile-btn--reset"])

    def on_profile_hover_leave(controller):
        hover_state["active"] = False
        profile_btn.set_css_classes(["eq-profile-btn"])
        sync_profile_label()

    profile_hover.connect("enter", on_profile_hover_enter)
    profile_hover.connect("leave", on_profile_hover_leave)
    profile_btn.add_controller(profile_hover)

    def select_preset(name):
        state["values"] = list(PRESETS[name])
        area.queue_draw()
        apply_eq(state["values"])
        state["last_mtime"] = state_mtime()
        refresh_preset_buttons()
        sync_profile_label()

    preset_buttons = {}

    def make_preset_button(name):
        btn = Widget.Button(
            css_classes=["eq-preset-btn"],
            child=Widget.Label(label=name, css_classes=["eq-preset-lbl"]),
            on_click=lambda *_: select_preset(name),
        )
        preset_buttons[name] = btn
        return btn

    def refresh_preset_buttons():
        match = matching_preset(state["values"])
        for name, btn in preset_buttons.items():
            classes = ["eq-preset-btn"] + (["eq-preset-btn--active"] if name == match else [])
            btn.set_css_classes(classes)

    names = list(PRESETS.keys())
    row1 = Widget.Box(spacing=4, homogeneous=True, child=[make_preset_button(n) for n in names[:3]])
    row2 = Widget.Box(spacing=4, homogeneous=True, child=[make_preset_button(n) for n in names[3:]])

    header = Widget.Box(
        spacing=6,
        css_classes=["eq-header"],
        child=[
            Widget.Label(label="Equalizer", css_classes=["eq-title"], hexpand=True, halign="start"),
            profile_btn,
        ],
    )

    container = Widget.Box(
        vertical=True,
        spacing=8,
        css_classes=["eq-island"],
        child=[
            header,
            chart_slot,
            freq_labels,
            Widget.Box(vertical=True, spacing=4, child=[row1, row2]),
        ],
    )

    Widget.Window(
        namespace="eq-island",
        anchor=["bottom"],
        margin_bottom=10,
        layer="overlay",
        kb_mode="none",
        css_classes=["eq-island-window"],
        child=container,
    )

    area = Gtk.DrawingArea()
    area.set_content_width(360)
    area.set_content_height(140)
    area.set_hexpand(True)

    def nearest_band(x, width):
        best_i, best_d = None, HIT_RADIUS
        for i in range(N_BANDS):
            d = abs(band_x(i, width) - x)
            if d < best_d:
                best_i, best_d = i, d
        return best_i

    def draw(area, cr, width, height):
        values = state["values"]
        points = [(band_x(i, width), value_to_y(values[i], height)) for i in range(N_BANDS)]

        cr.set_line_width(1)
        cr.set_source_rgba(1, 1, 1, 0.08)
        for frac in (0.25, 0.5, 0.75):
            y = PAD_TOP + (height - PAD_TOP - PAD_BOTTOM) * frac
            cr.move_to(PAD_X, y)
            cr.line_to(width - PAD_X, y)
            cr.stroke()

        for x, y in points:
            cr.set_line_width(2.5)
            cr.set_source_rgba(*TRACK)
            cr.move_to(x, PAD_TOP)
            cr.line_to(x, height - PAD_BOTTOM)
            cr.stroke()

        def curve_path():
            cr.move_to(*points[0])
            for i in range(len(points) - 1):
                x0, y0 = points[i]
                x1, y1 = points[i + 1]
                mx = (x0 + x1) / 2
                cr.curve_to(mx, y0, mx, y1, x1, y1)

        curve_path()
        cr.line_to(points[-1][0], height - PAD_BOTTOM)
        cr.line_to(points[0][0], height - PAD_BOTTOM)
        cr.close_path()
        cr.set_source_rgba(ACCENT[0], ACCENT[1], ACCENT[2], 0.12)
        cr.fill()

        curve_path()
        cr.set_line_width(2)
        cr.set_source_rgba(*ACCENT, 0.9)
        cr.stroke()

        for i, (x, y) in enumerate(points):
            active = state["active_band"] == i
            r = 6 if active else 4.5
            cr.set_source_rgba(*ACCENT, 0.25)
            cr.arc(x, y, r + 4, 0, 2 * math.pi)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, 0.95)
            cr.arc(x, y, r, 0, 2 * math.pi)
            cr.fill()
            cr.set_source_rgba(*ACCENT, 1)
            cr.arc(x, y, r, 0, 2 * math.pi)
            cr.set_line_width(1.5)
            cr.stroke()

    area.set_draw_func(draw)

    drag = Gtk.GestureDrag()

    def on_drag_begin(gesture, start_x, start_y):
        width = area.get_width()
        height = area.get_height()
        i = nearest_band(start_x, width)
        state["active_band"] = i
        state["drag_start_y"] = start_y
        if i is not None:
            state["values"][i] = y_to_value(start_y, height)
            sync_profile_label()
            area.queue_draw()

    def on_drag_update(gesture, offset_x, offset_y):
        i = state["active_band"]
        if i is None:
            return
        height = area.get_height()
        y = state["drag_start_y"] + offset_y
        state["values"][i] = y_to_value(y, height)
        sync_profile_label()
        area.queue_draw()

    def on_drag_end(gesture, offset_x, offset_y):
        if state["active_band"] is not None:
            apply_eq(state["values"])
            state["last_mtime"] = state_mtime()
        state["active_band"] = None
        area.queue_draw()

    drag.connect("drag-begin", on_drag_begin)
    drag.connect("drag-update", on_drag_update)
    drag.connect("drag-end", on_drag_end)
    area.add_controller(drag)

    chart_slot.append(area)

    def poll_external_changes():
        if state["active_band"] is not None:
            return True
        mtime = state_mtime()
        if mtime != state["last_mtime"]:
            state["last_mtime"] = mtime
            state["values"] = load_state()
            sync_profile_label()
            refresh_preset_buttons()
            area.queue_draw()
        return True

    GLib.timeout_add(POLL_MS, poll_external_changes)

    sync_profile_label()
    refresh_preset_buttons()

    app.hold()
    app.run()


main()
