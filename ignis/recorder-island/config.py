import gi
gi.require_version('NM', '1.0')
gi.require_version('Gtk', '4.0')
from gi.repository import GLib
from ignis.widgets import Widget
from ignis.app import IgnisApp
import subprocess
import datetime
import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.expanduser("~/Videos")
STATE_FILE = "/tmp/ignis-recorder-state"
GSR = "gpu-screen-recorder"


def timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def flash_label(lbl, text, duration=1200):
    lbl.set_label(text)
    lbl.set_visible(True)
    GLib.timeout_add(duration, lambda: (lbl.set_label(""), lbl.set_visible(False)) or False)


def gsr_running():
    try:
        out = subprocess.check_output(["pgrep", "-f", f"^{GSR}"], stderr=subprocess.DEVNULL)
        return bool(out.strip())
    except Exception:
        return False


def gsr_stop():
    subprocess.run(["pkill", "-SIGINT", "-f", f"^{GSR}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def save_state(kind):
    with open(STATE_FILE, "w") as f:
        f.write(kind)


def load_state():
    try:
        if gsr_running():
            with open(STATE_FILE) as f:
                return f.read().strip()
    except Exception:
        pass
    return None


def clear_state():
    try:
        os.remove(STATE_FILE)
    except Exception:
        pass


def start_gsr(target, out):
    subprocess.Popen(
        [GSR, "-w", target, "-f", "60", "-a", "default_output", "-o", out],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def main():
    app = IgnisApp.get_default()
    app.apply_css(os.path.join(SCRIPT_DIR, "style.css"))

    os.makedirs(SAVE_DIR, exist_ok=True)

    recording_kind = load_state()
    state = {"recording": recording_kind is not None, "kind": recording_kind}

    status_lbl = Widget.Label(label="", css_classes=["ss-status"], visible=False)

    win_lbl = Widget.Label(label="", css_classes=["ss-label"])
    mon_lbl = Widget.Label(label="", css_classes=["ss-label"])
    reg_lbl = Widget.Label(label="", css_classes=["ss-label"])

    def refresh_labels():
        kind = state["kind"]
        win_lbl.set_label("■ Stop" if kind == "window" else "Window")
        mon_lbl.set_label("■ Stop" if kind == "monitor" else "Monitor")
        reg_lbl.set_label("■ Stop" if kind == "region" else "Region")

    refresh_labels()

    def stop_recording(status_lbl):
        gsr_stop()
        clear_state()
        state["recording"] = False
        state["kind"] = None
        refresh_labels()
        flash_label(status_lbl, "✓ saved")

    def on_window(*_):
        if state["recording"]:
            stop_recording(status_lbl)
            return
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
            geo = subprocess.check_output(["slurp", "-r"], input=regions.encode()).decode().strip()
        except Exception:
            flash_label(status_lbl, "✗ cancelled")
            return
        out = os.path.join(SAVE_DIR, f"window_{timestamp()}.mp4")
        start_gsr(geo, out)
        save_state("window")
        state["recording"] = True
        state["kind"] = "window"
        refresh_labels()
        flash_label(status_lbl, "● recording")

    def on_monitor(*_):
        if state["recording"]:
            stop_recording(status_lbl)
            return
        try:
            raw = subprocess.check_output(["hyprctl", "monitors", "-j"])
            monitors = json.loads(raw)
            regions = "\n".join(
                f"{m['x']},{m['y']} {m['width']}x{m['height']} {m['name']}"
                for m in monitors
            )
            selected = subprocess.check_output(["slurp", "-r"], input=regions.encode()).decode().strip()
            geo_part = selected.split(" ")[0] + " " + selected.split(" ")[1]
            name = next(
                (m["name"] for m in monitors
                 if f"{m['x']},{m['y']} {m['width']}x{m['height']}" == geo_part),
                None,
            )
        except Exception:
            flash_label(status_lbl, "✗ cancelled")
            return
        out = os.path.join(SAVE_DIR, f"monitor_{timestamp()}.mp4")
        start_gsr(name if name else "screen", out)
        save_state("monitor")
        state["recording"] = True
        state["kind"] = "monitor"
        refresh_labels()
        flash_label(status_lbl, "● recording")

    def on_region(*_):
        if state["recording"]:
            stop_recording(status_lbl)
            return
        try:
            geo = subprocess.check_output(["slurp"]).decode().strip()
        except Exception:
            flash_label(status_lbl, "✗ cancelled")
            return
        out = os.path.join(SAVE_DIR, f"region_{timestamp()}.mp4")
        start_gsr(geo, out)
        save_state("region")
        state["recording"] = True
        state["kind"] = "region"
        refresh_labels()
        flash_label(status_lbl, "● recording")

    buttons = Widget.Box(
        spacing=4,
        halign="center",
        child=[
            Widget.Button(
                css_classes=["ss-btn"],
                child=Widget.Box(spacing=6, child=[
                    Widget.Label(label="󱂬", css_classes=["ss-icon"]),
                    win_lbl,
                ]),
                on_click=on_window,
            ),
            Widget.Label(label="│", css_classes=["ss-divider"]),
            Widget.Button(
                css_classes=["ss-btn"],
                child=Widget.Box(spacing=6, child=[
                    Widget.Label(label="󰍹", css_classes=["ss-icon"]),
                    mon_lbl,
                ]),
                on_click=on_monitor,
            ),
            Widget.Label(label="│", css_classes=["ss-divider"]),
            Widget.Button(
                css_classes=["ss-btn"],
                child=Widget.Box(spacing=6, child=[
                    Widget.Label(label="󰩭", css_classes=["ss-icon"]),
                    reg_lbl,
                ]),
                on_click=on_region,
            ),
        ],
    )

    Widget.Window(
        namespace="recorder-island",
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
