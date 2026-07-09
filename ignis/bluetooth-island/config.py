import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib
from ignis.widgets import Widget
from ignis.app import IgnisApp
import subprocess
import time
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOUBLE_CLICK_MS = 400
POLL_MS = 3000


def bt_info(mac):
    try:
        return subprocess.check_output(
            ["bluetoothctl", "info", mac], stderr=subprocess.DEVNULL
        ).decode()
    except Exception:
        return ""


def parse_device_list(args):
    try:
        raw = subprocess.check_output(
            ["bluetoothctl"] + args, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return []

    devices = []
    for line in raw.splitlines():
        parts = line.split(" ", 2)
        if len(parts) < 3:
            continue
        devices.append({"mac": parts[1], "name": parts[2]})
    return devices


def start_background_scan():
    subprocess.Popen(
        ["timeout", "4", "bluetoothctl", "scan", "on"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def get_devices():
    paired = parse_device_list(["devices", "Paired"])
    for d in paired:
        d["connected"] = "Connected: yes" in bt_info(d["mac"])
    paired.sort(key=lambda d: d["name"])
    known = paired[:2]

    known_macs = {d["mac"] for d in paired}
    all_devices = parse_device_list(["devices"])
    unknown = [d for d in all_devices if d["mac"] not in known_macs]
    for d in unknown:
        d["connected"] = False
    unknown.sort(key=lambda d: d["name"])
    unknown = unknown[:1]

    return known + unknown


def make_rows(devices):
    rows, state_refs = [], []

    for dev in devices:
        last_click = [0.0]
        mac = dev["mac"]

        icon_lbl = Widget.Label(label="󰂯", css_classes=["bt-icon"])
        name_lbl = Widget.Label(label=dev["name"], css_classes=["bt-name"],
                                ellipsize="end", max_width_chars=18, hexpand=True, halign="start")
        dot_lbl = Widget.Label(label="●" if dev["connected"] else "", css_classes=["bt-active-dot"])

        classes = ["bt-row"] + (["bt-row--active"] if dev["connected"] else [])

        def make_click(mac=mac, lc=last_click):
            def handler(*_):
                now = time.monotonic() * 1000
                if now - lc[0] < DOUBLE_CLICK_MS:
                    lc[0] = 0
                    currently_connected = "Connected: yes" in bt_info(mac)
                    if currently_connected:
                        subprocess.Popen(["bluetoothctl", "disconnect", mac],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.Popen(["bluetoothctl", "pair", mac],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        subprocess.Popen(["bluetoothctl", "connect", mac],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    lc[0] = now
            return handler

        btn = Widget.Button(
            css_classes=classes,
            child=Widget.Box(spacing=8, child=[icon_lbl, name_lbl, dot_lbl]),
            on_click=make_click(),
        )

        state_refs.append({"mac": mac, "dot": dot_lbl, "btn": btn})
        rows.append(btn)

    return rows, state_refs


def main():
    app = IgnisApp.get_default()
    app.apply_css(os.path.join(SCRIPT_DIR, "style.css"))

    container = Widget.Box(vertical=True, spacing=2, css_classes=["bt-island"])
    state_refs = [None]

    def build():
        child = container.get_first_child()
        while child:
            container.remove(child)
            child = container.get_first_child()

        devices = get_devices()
        if not devices:
            container.append(Widget.Label(label="No devices found", css_classes=["bt-empty"]))
            state_refs[0] = []
            return

        rows, refs = make_rows(devices)
        state_refs[0] = refs
        for row in rows:
            container.append(row)

    def poll(*_):
        devices = get_devices()
        refs = state_refs[0]

        if not refs or len(devices) != len(refs):
            build()
            return True

        for i, dev in enumerate(devices):
            ref = refs[i]
            if dev["mac"] != ref["mac"]:
                build()
                return True
            new_dot = "●" if dev["connected"] else ""
            if ref["dot"].get_label() != new_dot:
                ref["dot"].set_label(new_dot)
                classes = ["bt-row"] + (["bt-row--active"] if dev["connected"] else [])
                ref["btn"].set_css_classes(classes)

        return True

    start_background_scan()
    build()
    GLib.timeout_add(POLL_MS, poll)

    Widget.Window(
        namespace="bluetooth-island",
        anchor=["top", "right"],
        margin_top=2,
        margin_right=220,
        layer="overlay",
        kb_mode="none",
        css_classes=["bt-island-window"],
        child=container,
    )

    app.hold()
    app.run()


main()
