import gi
gi.require_version('NM', '1.0')
from ignis.widgets import Widget
from ignis.app import IgnisApp
from gi.repository import Gtk
import subprocess
import re
import json
import datetime
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GLOBAL_MIN, GLOBAL_MAX = -10, 45


def fetch_days():
    try:
        raw = subprocess.check_output(
            ["wttrbar", "--date-format", "%d.%m.%Y", "-l", "en"],
            stderr=subprocess.DEVNULL,
        ).decode()
    except Exception:
        return []

    tooltip = json.loads(raw).get("tooltip", "")
    days = []
    blocks = re.split(r'\n(?=<b>)', tooltip)

    for block in blocks:
        if not block.strip() or "Feels Like" in block:
            continue
        title_match = re.search(r'<b>(.*?)</b>', block)
        if not title_match:
            continue
        title = title_match.group(1).split(",")[0]

        hours = re.findall(r'(\d{2})\s+(\S+)\s+(\d+)°\s+([^\n]+)', block)
        if not hours:
            continue

        slots = []
        for h in hours:
            condition = h[3].split(",")[0].strip()
            slots.append({
                "hour": int(h[0]),
                "emoji": h[1],
                "temp": int(h[2]),
                "condition": condition,
            })

        days.append({"title": title, "slots": slots})

    return days


def temp_color(temp):
    if temp <= 0:
        return (0.1, 0.4, 1.0, 1.0)       # vivid blue
    elif temp <= 15:
        return (0.2, 0.8, 1.0, 1.0)       # cyan
    elif temp <= 28:
        return (1.0, 0.5, 0.2, 1.0)       # orange
    else:
        return (1.0, 0.15, 0.15, 1.0)     # vivid red


def make_hbar(temp, bar_width=60, height=5):
    fill = max(0.0, min(1.0, (temp - GLOBAL_MIN) / (GLOBAL_MAX - GLOBAL_MIN)))
    r, g, b, a = temp_color(temp)

    da = Gtk.DrawingArea()
    da.set_size_request(bar_width, height)
    da.set_valign(Gtk.Align.CENTER)

    def draw(widget, cr, w, h):
        import math
        rad = h / 2

        def pill(width):
            cr.new_path()
            cr.arc(rad, rad, rad, math.pi / 2, 3 * math.pi / 2)
            cr.arc(max(width - rad, rad + 0.01), rad, rad, -math.pi / 2, math.pi / 2)
            cr.close_path()

        cr.set_source_rgba(1, 1, 1, 0.12)
        pill(w)
        cr.fill()

        cr.set_source_rgba(r, g, b, a)
        pill(max(h, w * fill))
        cr.fill()

    da.set_draw_func(draw)
    return da


def hour_row(slot):
    bar = make_hbar(slot["temp"])

    return Widget.Box(
        spacing=8,
        halign="fill",
        child=[
            Widget.Label(
                label=f"{slot['hour']:02d}:00",
                css_classes=["wx-hour"],
                halign="start",
            ),
            bar,
            Widget.Label(label=slot["emoji"], css_classes=["wx-emoji"]),
            Widget.Label(
                label=f"{slot['temp']}°",
                css_classes=["wx-temp-inline"],
                halign="start",
            ),
            Widget.Label(
                label=slot["condition"],
                css_classes=["wx-condition"],
                halign="start",
                hexpand=True,
                ellipsize="end",
                max_width_chars=14,
            ),
        ],
    )


def day_view(day):
    rows = [hour_row(s) for s in day["slots"]]
    return Widget.Box(
        vertical=True,
        spacing=4,
        child=[
            Widget.Label(label=day["title"], css_classes=["wx-title"], halign="center"),
        ] + rows,
    )


def main():
    app = IgnisApp.get_default()
    app.apply_css(os.path.join(SCRIPT_DIR, "style.css"))

    days = fetch_days()
    if not days:
        days = [{"title": "No data", "slots": [{"hour": 0, "emoji": "❓", "temp": 0, "condition": "Unknown"}]}]

    state = {"idx": 0}
    content = Widget.Box(vertical=True)

    def refresh():
        child = content.get_first_child()
        while child:
            content.remove(child)
            child = content.get_first_child()
        content.append(day_view(days[state["idx"]]))

    def go(delta):
        state["idx"] = (state["idx"] + delta) % len(days)
        refresh()

    nav = Widget.Box(
        halign="center",
        spacing=6,
        child=[
            Widget.Button(css_classes=["wx-nav"], child=Widget.Label(label="←"), on_click=lambda *_: go(-1)),
            Widget.Button(css_classes=["wx-nav"], child=Widget.Label(label="→"), on_click=lambda *_: go(1)),
        ],
    )

    refresh()

    Widget.Window(
        namespace="wx-island",
        anchor=["top", "right"],
        margin_top=2,
        margin_right=5,
        layer="overlay",
        kb_mode="none",
        css_classes=["wx-window"],
        child=Widget.Box(
            vertical=True,
            spacing=6,
            css_classes=["wx-island"],
            child=[nav, content],
        ),
    )

    app.hold()
    app.run()


main()
