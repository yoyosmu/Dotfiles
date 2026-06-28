import gi
gi.require_version('NM', '1.0')
from gi.repository import GLib
from ignis.widgets import Widget
from ignis.app import IgnisApp
import subprocess
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.expanduser("~/Pictures")


def timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def flash_label(lbl, text, duration=1200):
    lbl.set_label(text)
    lbl.set_visible(True)
    GLib.timeout_add(duration, lambda: (lbl.set_label(""), lbl.set_visible(False)) or False)


def shot_monitor(status_lbl):
    try:
        raw = subprocess.check_output(["hyprctl", "monitors", "-j"])
        monitors = json.loads(raw)
        regions = "\n".join(
            f"{m['x']},{m['y']} {m['width']}x{m['height']} {m['name']}"
            for m in monitors
        )
        selected = subprocess.check_output(
            ["slurp", "-r"],
            input=regions.encode(),
        ).decode().strip()
        geo_part = selected.split(" ")[0] + " " + selected.split(" ")[1]
        name = next(
            (m["name"] for m in monitors
             if f"{m['x']},{m['y']} {m['width']}x{m['height']}" == geo_part),
            None,
        )
    except Exception:
        flash_label(status_lbl, "✗ cancelled")
        return
    out = os.path.join(SAVE_DIR, f"monitor_{timestamp()}.png")
    r = subprocess.run(["grim", "-o", name, out] if name else ["grim", "-g", selected, out])
    flash_label(status_lbl, "✓ monitor" if r.returncode == 0 else "✗ failed")


def shot_window(status_lbl):
    try:
        raw = subprocess.check_output(["hyprctl", "clients", "-j"])
        clients = json.loads(raw)
        visible = [c for c in clients if c.get("mapped") and c["at"][0] >= 0]
        if not visible:
            flash_label(status_lbl, "✗ no windows")
            return
        regions = "\n".join(
            f"{c['at'][0]},{c['at'][1]} {c['size'][0]}x{c['size'][1]} {c.get('title','')[:30]}"
            for c in visible
        )
        geo = subprocess.check_output(
            ["slurp", "-r"],
            input=regions.encode(),
        ).decode().strip()
    except Exception:
        flash_label(status_lbl, "✗ cancelled")
        return
    out = os.path.join(SAVE_DIR, f"window_{timestamp()}.png")
    r = subprocess.run(["grim", "-g", geo, out])
    flash_label(status_lbl, "✓ window" if r.returncode == 0 else "✗ failed")


def shot_region(status_lbl):
    try:
        geo = subprocess.check_output(["slurp"]).decode().strip()
    except Exception:
        flash_label(status_lbl, "✗ cancelled")
        return
    out = os.path.join(SAVE_DIR, f"region_{timestamp()}.png")
    r = subprocess.run(["grim", "-g", geo, out])
    flash_label(status_lbl, "✓ region" if r.returncode == 0 else "✗ failed")


def main():
    app = IgnisApp.get_default()
    app.apply_css(os.path.join(SCRIPT_DIR, "style.css"))

    status_lbl = Widget.Label(label="", css_classes=["ss-status"], visible=False)

    buttons = Widget.Box(
        spacing=4,
        halign="center",
        child=[
            Widget.Button(
                css_classes=["ss-btn"],
                child=Widget.Box(
                    spacing=6,
                    child=[
                        Widget.Label(label="󱂬", css_classes=["ss-icon"]),
                        Widget.Label(label="Window", css_classes=["ss-label"]),
                    ],
                ),
                on_click=lambda *_: shot_window(status_lbl),
            ),
            Widget.Label(label="│", css_classes=["ss-divider"]),
            Widget.Button(
                css_classes=["ss-btn"],
                child=Widget.Box(
                    spacing=6,
                    child=[
                        Widget.Label(label="󰍹", css_classes=["ss-icon"]),
                        Widget.Label(label="Monitor", css_classes=["ss-label"]),
                    ],
                ),
                on_click=lambda *_: shot_monitor(status_lbl),
            ),
            Widget.Label(label="│", css_classes=["ss-divider"]),
            Widget.Button(
                css_classes=["ss-btn"],
                child=Widget.Box(
                    spacing=6,
                    child=[
                        Widget.Label(label="󰩭", css_classes=["ss-icon"]),
                        Widget.Label(label="Region", css_classes=["ss-label"]),
                    ],
                ),
                on_click=lambda *_: shot_region(status_lbl),
            ),
        ],
    )

    Widget.Window(
        namespace="ss-island",
        anchor=["bottom"],
        margin_bottom=5,
        layer="overlay",
        kb_mode="none",
        css_classes=["ss-window"],
        child=Widget.Box(
            vertical=True,
            spacing=0,
            css_classes=["ss-island"],
            child=[buttons, status_lbl],
        ),
    )

    app.hold()
    app.run()


main()
