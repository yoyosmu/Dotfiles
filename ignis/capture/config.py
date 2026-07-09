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
import shlex


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.expanduser("~/Pictures")
VIDEO_DIR = os.path.expanduser("~/Videos")
STATE_FILE = "/tmp/ignis-recorder-state"
GSR = "gpu-screen-recorder"


def timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def flash_label(lbl, text, duration=1200):
    lbl.set_label(text)
    lbl.set_visible(True)
    GLib.timeout_add(duration, lambda: (lbl.set_label(""), lbl.set_visible(False)) or False)


def spawn_delayed(cmd_list, delay=3):
    """Run cmd_list after `delay` seconds in a fully detached process
    (new session, no ties to this app), so it still fires even if this
    widget/app is closed or killed before the delay elapses."""
    quoted = " ".join(shlex.quote(c) for c in cmd_list)
    shell_cmd = f"sleep {delay} && exec {quoted}"
    return subprocess.Popen(
        ["bash", "-c", shell_cmd],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def gsr_running():
    try:
        return bool(subprocess.check_output(["pgrep", "-f", f"^{GSR}"], stderr=subprocess.DEVNULL).strip())
    except Exception:
        return False


def gsr_stop():
    subprocess.run(["pkill", "-SIGINT", "-f", f"^{GSR}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def save_rec_state(kind):
    with open(STATE_FILE, "w") as f:
        f.write(kind)


def load_rec_state():
    try:
        if gsr_running():
            with open(STATE_FILE) as f:
                return f.read().strip()
    except Exception:
        pass
    return None


def clear_rec_state():
    try:
        os.remove(STATE_FILE)
    except Exception:
        pass


def get_active_workspace():
    try:
        raw = subprocess.check_output(["hyprctl", "activeworkspace", "-j"])
        return json.loads(raw)["id"]
    except Exception:
        return None


def pick_window():
    raw = subprocess.check_output(["hyprctl", "clients", "-j"])
    clients = json.loads(raw)
    ws = get_active_workspace()
    visible = [
        c for c in clients
        if c.get("mapped") and c["at"][0] >= 0
        and (ws is None or c.get("workspace", {}).get("id") == ws)
    ]
    if not visible:
        return None, None
    regions = "\n".join(
        f"{c['at'][0]},{c['at'][1]} {c['size'][0]}x{c['size'][1]} {c.get('title','')[:30]}"
        for c in visible
    )
    geo = subprocess.check_output(["slurp", "-r"], input=regions.encode()).decode().strip()
    xy = geo.split(" ")[0]
    x, y = map(int, xy.split(","))
    matched = next(
        (c for c in visible if c["at"][0] == x and c["at"][1] == y),
        None,
    )
    return geo, matched


def slurp_to_gsr(geo):
    xy, wh = geo.strip().split(" ")
    x, y = xy.split(",")
    return wh + f"+{x}+{y}"


def pick_monitor():
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
    return name, selected


def pick_region():
    return subprocess.check_output(["slurp"]).decode().strip()


def main():
    app = IgnisApp.get_default()
    app.apply_css(os.path.join(SCRIPT_DIR, "style.css"))

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)

    rec_state = load_rec_state()
    mode = {"current": "recorder" if rec_state else "screenshot"}
    recording = {"kind": rec_state}

    status_lbl = Widget.Label(label="", css_classes=["ss-status"], visible=False)

    win_lbl = Widget.Label(label="", css_classes=["ss-label"])
    mon_lbl = Widget.Label(label="", css_classes=["ss-label"])
    reg_lbl = Widget.Label(label="", css_classes=["ss-label"])
    mode_lbl = Widget.Label(label="Screenshot", css_classes=["cap-mode-lbl"])

    def refresh_labels():
        kind = recording["kind"]
        is_rec = mode["current"] == "recorder"
        win_lbl.set_label("■ Stop" if is_rec and kind == "window" else "Window")
        mon_lbl.set_label("■ Stop" if is_rec and kind == "monitor" else "Monitor")
        reg_lbl.set_label("■ Stop" if is_rec and kind == "region" else "Region")
        mode_lbl.set_label("Recorder" if is_rec else "Screenshot")

    refresh_labels()

    def start_countdown(on_done, seconds=3):
        # Cosmetic on-screen 3..2..1 tick. The real action is already
        # guaranteed to fire via spawn_delayed(), independent of this UI.
        status_lbl.set_visible(True)
        count = {"n": seconds}

        def tick():
            if count["n"] > 0:
                status_lbl.set_label(str(count["n"]))
                count["n"] -= 1
                return True
            status_lbl.set_label("")
            status_lbl.set_visible(False)
            on_done()
            return False

        tick()
        GLib.timeout_add(1000, tick)

    def toggle_mode(*_):
        mode["current"] = "recorder" if mode["current"] == "screenshot" else "screenshot"
        refresh_labels()

    def on_window(*_):
        if mode["current"] == "screenshot":
            try:
                geo, _ = pick_window()
                if not geo:
                    flash_label(status_lbl, "✗ no windows")
                    return
            except Exception:
                flash_label(status_lbl, "✗ cancelled")
                return

            out = os.path.join(SCREENSHOT_DIR, f"window_{timestamp()}.png")
            spawn_delayed(["grim", "-g", geo, out], delay=0)
            app.quit()
        else:
            if recording["kind"]:
                gsr_stop()
                clear_rec_state()
                recording["kind"] = None
                refresh_labels()
                flash_label(status_lbl, "✓ saved")
                return
            try:
                geo, matched = pick_window()
                if not geo:
                    flash_label(status_lbl, "✗ no windows")
                    return
            except Exception:
                flash_label(status_lbl, "✗ cancelled")
                return

            if matched and matched.get("address"):
                subprocess.run(
                    ["hyprctl", "dispatch", "focuswindow", f"address:0x{matched['address']}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            out = os.path.join(VIDEO_DIR, f"window_{timestamp()}.mp4")
            spawn_delayed([GSR, "-w", "region", "-region", slurp_to_gsr(geo),
                           "-f", "60", "-a", "default_output", "-o", out])
            save_rec_state("window")
            recording["kind"] = "window"
            refresh_labels()
            start_countdown(lambda: flash_label(status_lbl, "● recording"))

    def on_monitor(*_):
        if mode["current"] == "screenshot":
            try:
                name, selected = pick_monitor()
            except Exception:
                flash_label(status_lbl, "✗ cancelled")
                return

            out = os.path.join(SCREENSHOT_DIR, f"monitor_{timestamp()}.png")
            if name:
                spawn_delayed(["grim", "-o", name, out], delay=0)
            else:
                spawn_delayed(["grim", "-g", selected, out], delay=0)
            app.quit()
        else:
            if recording["kind"]:
                gsr_stop()
                clear_rec_state()
                recording["kind"] = None
                refresh_labels()
                flash_label(status_lbl, "✓ saved")
                return
            try:
                name, selected = pick_monitor()
            except Exception:
                flash_label(status_lbl, "✗ cancelled")
                return

            out = os.path.join(VIDEO_DIR, f"monitor_{timestamp()}.mp4")
            spawn_delayed([GSR, "-w", name if name else "screen", "-f", "60",
                           "-a", "default_output", "-o", out])
            save_rec_state("monitor")
            recording["kind"] = "monitor"
            refresh_labels()
            start_countdown(lambda: flash_label(status_lbl, "● recording"))

    def on_region(*_):
        if mode["current"] == "screenshot":
            try:
                geo = pick_region()
            except Exception:
                flash_label(status_lbl, "✗ cancelled")
                return

            out = os.path.join(SCREENSHOT_DIR, f"region_{timestamp()}.png")
            spawn_delayed(["grim", "-g", geo, out], delay=0)
            app.quit()
        else:
            if recording["kind"]:
                gsr_stop()
                clear_rec_state()
                recording["kind"] = None
                refresh_labels()
                flash_label(status_lbl, "✓ saved")
                return
            try:
                geo = pick_region()
            except Exception:
                flash_label(status_lbl, "✗ cancelled")
                return

            out = os.path.join(VIDEO_DIR, f"region_{timestamp()}.mp4")
            spawn_delayed([GSR, "-w", "region", "-region", slurp_to_gsr(geo),
                           "-f", "60", "-a", "default_output", "-o", out])
            save_rec_state("region")
            recording["kind"] = "region"
            refresh_labels()
            start_countdown(lambda: flash_label(status_lbl, "● recording"))

    mode_btn = Widget.Button(
        css_classes=["cap-mode-btn"],
        child=Widget.Box(
            spacing=6,
            child=[
                Widget.Label(label="⇄", css_classes=["cap-mode-arrow"]),
                mode_lbl,
            ],
        ),
        on_click=toggle_mode,
    )

    buttons = Widget.Box(
        spacing=4,
        halign="center",
        child=[
            mode_btn,
            Widget.Label(label="│", css_classes=["ss-divider"]),
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
        namespace="capture-island",
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
