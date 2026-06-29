import gi
gi.require_version('NM', '1.0')
gi.require_version('Gtk', '4.0')
from gi.repository import GLib
from ignis.widgets import Widget
from ignis.app import IgnisApp
from ignis.services.network import NetworkService
import subprocess
import time


DOUBLE_CLICK_MS = 400


def get_networks():
    network = NetworkService.get_default()
    seen, known, unknown = set(), [], []

    for dev in network.wifi.devices:
        for ap in dev.access_points:
            ssid = ap.ssid
            if not ssid or ssid in seen:
                continue
            seen.add(ssid)
            entry = {
                "ssid": ssid,
                "signal": ap.strength,
                "active": ap.is_connected,
                "ap": ap,
            }
            if ap.psk is not None or ap.is_connected:
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


def make_rows(networks, on_click_fn):
    rows, state_refs = [], []

    for net in networks:
        last_click = [0.0]

        icon_lbl = Widget.Label(label=signal_icon(net["signal"]), css_classes=["wifi-icon"])
        ssid_lbl = Widget.Label(label=net["ssid"], css_classes=["wifi-ssid"],
                                ellipsize="end", max_width_chars=18, hexpand=True, halign="start")
        dot_lbl = Widget.Label(label="●" if net["active"] else "", css_classes=["wifi-active-dot"])

        classes = ["wifi-row"] + (["wifi-row--active"] if net["active"] else [])

        def make_click(ssid, lc):
            def handler(*_):
                now = time.monotonic() * 1000
                if now - lc[0] < DOUBLE_CLICK_MS:
                    subprocess.Popen(
                        ["nmcli", "device", "wifi", "connect", ssid],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    lc[0] = 0
                else:
                    lc[0] = now
            return handler

        btn = Widget.Button(
            css_classes=classes,
            child=Widget.Box(spacing=8, child=[icon_lbl, ssid_lbl, dot_lbl]),
            on_click=make_click(net["ssid"], last_click),
        )

        state_refs.append({"ssid": net["ssid"], "icon": icon_lbl, "dot": dot_lbl, "btn": btn})
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

        rows, refs = make_rows(networks, None)
        state_refs[0] = refs
        for row in rows:
            container.append(row)

    def update(*_):
        networks = get_networks()
        refs = state_refs[0]

        if not refs or len(networks) != len(refs):
            build()
            return

        for i, net in enumerate(networks):
            ref = refs[i]
            if net["ssid"] != ref["ssid"]:
                build()
                return
            ref["icon"].set_label(signal_icon(net["signal"]))
            new_dot = "●" if net["active"] else ""
            if ref["dot"].get_label() != new_dot:
                ref["dot"].set_label(new_dot)
                classes = ["wifi-row"] + (["wifi-row--active"] if net["active"] else [])
                ref["btn"].set_css_classes(classes)

    build()

    network = NetworkService.get_default()
    for dev in network.wifi.devices:
        dev.connect("notify::access-points", update)
        for ap in dev.access_points:
            ap.connect("notify::strength", update)
            ap.connect("notify::is-connected", update)

    network.wifi.connect("notify::devices", lambda *_: build())

    Widget.Window(
        namespace="wifi-island",
        anchor=["top", "right"],
        margin_top=2,
        margin_right=220,
        layer="overlay",
        kb_mode="none",
        css_classes=["wifi-island-window"],
        child=container,
    )

    app.hold()
    app.run()


main()
