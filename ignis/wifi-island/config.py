import gi
gi.require_version('NM', '1.0')
from gi.repository import NM, GLib
from ignis.widgets import Widget
from ignis.app import IgnisApp
import subprocess
import time

DOUBLE_CLICK_MS = 400
_last_click: dict[str, float] = {}
_nm_client = NM.Client.new(None)


def get_networks():
    seen, known, unknown = set(), [], []
    active_ssids = set()

    for ac in _nm_client.get_active_connections():
        for dev in ac.get_devices():
            if dev.get_device_type() == NM.DeviceType.WIFI:
                ap = dev.get_active_access_point()
                if ap and ap.get_ssid():
                    active_ssids.add(ap.get_ssid().get_data().decode(errors="replace"))

    saved = set()
    for c in _nm_client.get_connections():
        s_wifi = c.get_setting_wireless()
        if s_wifi and s_wifi.get_ssid():
            saved.add(s_wifi.get_ssid().get_data().decode(errors="replace"))

    for dev in _nm_client.get_devices():
        if dev.get_device_type() != NM.DeviceType.WIFI:
            continue
        for ap in dev.get_access_points():
            raw = ap.get_ssid()
            if not raw:
                continue
            ssid = raw.get_data().decode(errors="replace")
            if not ssid or ssid in seen:
                continue
            seen.add(ssid)
            entry = {"ssid": ssid, "signal": ap.get_strength(), "active": ssid in active_ssids}
            if ssid in saved:
                known.append(entry)
            else:
                unknown.append(entry)

    known.sort(key=lambda x: x["signal"], reverse=True)
    unknown.sort(key=lambda x: x["signal"], reverse=True)
    return known[:2] + unknown[:1]


def signal_icon(s):
    if s > 80: return "󰤨"
    if s > 60: return "󰤥"
    if s > 40: return "󰤢"
    if s > 20: return "󰤟"
    return "󰤫"


def connect(ssid):
    subprocess.Popen(
        ["nmcli", "device", "wifi", "connect", ssid],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def on_click(ssid, refresh_fn):
    now = time.monotonic() * 1000
    last = _last_click.get(ssid, 0)
    if now - last < DOUBLE_CLICK_MS:
        connect(ssid)
        _last_click[ssid] = 0
    else:
        _last_click[ssid] = now


def make_rows(networks, refresh_fn):
    rows = []
    state_refs = []

    for net in networks:
        icon_lbl = Widget.Label(label=signal_icon(net["signal"]), css_classes=["wifi-icon"])
        ssid_lbl = Widget.Label(label=net["ssid"], css_classes=["wifi-ssid"],
                                ellipsize="end", max_width_chars=18, hexpand=True, halign="start")
        dot_lbl = Widget.Label(label="●" if net["active"] else "", css_classes=["wifi-active-dot"])

        classes = ["wifi-row"] + (["wifi-row--active"] if net["active"] else [])
        btn = Widget.Button(
            css_classes=classes,
            child=Widget.Box(spacing=8, child=[icon_lbl, ssid_lbl, dot_lbl]),
            on_click=lambda *_, s=net["ssid"]: on_click(s, refresh_fn),
        )

        state_refs.append({
            "ssid": net["ssid"],
            "icon": icon_lbl,
            "dot": dot_lbl,
            "btn": btn,
        })
        rows.append(btn)

    return rows, state_refs


def main():
    app = IgnisApp.get_default()
    app.apply_css(f"{__file__.replace('config.py', 'style.css')}")

    container = Widget.Box(vertical=True, spacing=2, css_classes=["wifi-island"])
    state_refs = [None]

    def build():
        child = container.get_first_child()
        while child:
            container.remove(child)
            child = container.get_first_child()

        networks = get_networks()
        if not networks:
            container.append(Widget.Label(label="No networks", css_classes=["wifi-empty"]))
            state_refs[0] = []
            return

        rows, refs = make_rows(networks, update)
        state_refs[0] = refs
        for row in rows:
            container.append(row)

    def update():
        networks = get_networks()
        refs = state_refs[0]

        if not refs or len(networks) != len(refs):
            build()
            return False

        for i, net in enumerate(networks):
            ref = refs[i]
            if net["ssid"] != ref["ssid"]:
                build()
                return False
            ref["icon"].set_label(signal_icon(net["signal"]))
            new_dot = "●" if net["active"] else ""
            if ref["dot"].get_label() != new_dot:
                ref["dot"].set_label(new_dot)
                classes = ["wifi-row"] + (["wifi-row--active"] if net["active"] else [])
                ref["btn"].set_css_classes(classes)

        return False

    build()

    win = Widget.Window(
        namespace="wifi-island",
        anchor=["top", "right"],
        margin_top=2,
        margin_right=220,
        layer="overlay",
        kb_mode="none",
        css_classes=["wifi-island-window"],
        child=container,
    )

    timer_id = [None]

    def start_timer():
        if timer_id[0] is None:
            def tick():
                update()
                return True
            timer_id[0] = GLib.timeout_add(500, tick)

    def stop_timer():
        if timer_id[0] is not None:
            GLib.source_remove(timer_id[0])
            timer_id[0] = None

    win.connect("map", lambda *_: start_timer())
    win.connect("unmap", lambda *_: stop_timer())
    start_timer()

    app.hold()
    app.run()


main()
