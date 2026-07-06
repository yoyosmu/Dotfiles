import gi
gi.require_version('NM', '1.0')
gi.require_version('Gtk', '4.0')
from gi.repository import GLib, Gtk
from ignis.widgets import Widget
from ignis.app import IgnisApp
from ignis.services.audio import AudioService
import math
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HIDE_DELAY = 1600


def make_hpill(height=6):
    da = Gtk.DrawingArea()
    da.set_size_request(-1, height)
    da.set_hexpand(True)
    da.set_valign(Gtk.Align.CENTER)
    state = {"fill": 0.0, "r": 0.65, "g": 0.89, "b": 0.63}
    rad = height / 2

    def draw(widget, cr, w, h):
        def pill(width):
            cr.new_path()
            cr.arc(rad, rad, rad, math.pi / 2, 3 * math.pi / 2)
            cr.arc(max(width - rad, rad + 0.01), rad, rad, -math.pi / 2, math.pi / 2)
            cr.close_path()
        cr.set_source_rgba(1, 1, 1, 0.12)
        pill(w)
        cr.fill()
        cr.set_source_rgba(state["r"], state["g"], state["b"], 0.9)
        pill(max(h, w * state["fill"]))
        cr.fill()

    da.set_draw_func(draw)

    def update(fill, r=0.65, g=0.89, b=0.63):
        state["fill"] = max(0.0, min(1.0, fill))
        state["r"] = r
        state["g"] = g
        state["b"] = b
        da.queue_draw()

    return da, update


def volume_icon(vol, muted):
    if muted or vol == 0: return "󰝟"
    if vol < 33: return "󰕿"
    if vol < 66: return "󰖀"
    return "󰕾"


def main():
    app = IgnisApp.get_default()
    app.apply_css(os.path.join(SCRIPT_DIR, "style.css"))

    icon_lbl = Widget.Label(label="󰕾", css_classes=["osd-icon"])
    pct_lbl = Widget.Label(label="", css_classes=["osd-pct"])
    pill, pill_update = make_hpill(height=6)

    win = Widget.Window(
        namespace="osd-bar",
        anchor=["top"],
        margin_top=10,
        layer="overlay",
        kb_mode="none",
        css_classes=["osd-window"],
        visible=False,
        child=Widget.Box(
            spacing=10,
            css_classes=["osd-island"],
            child=[icon_lbl, pill, pct_lbl],
        ),
    )

    hide_timer = [None]

    def show():
        if hide_timer[0] is not None:
            GLib.source_remove(hide_timer[0])
            hide_timer[0] = None
        win.set_visible(True)

        def hide():
            win.set_visible(False)
            hide_timer[0] = None
            return False

        hide_timer[0] = GLib.timeout_add(HIDE_DELAY, hide)

    def on_volume(*_):
        audio = AudioService.get_default()
        speaker = audio.speaker
        if speaker is None:
            return
        vol = speaker.volume
        muted = speaker.is_muted
        fill = 0.0 if muted else min(vol / 100.0, 1.0)
        over = vol > 100
        r, g, b = (1.0, 0.4, 0.4) if over else (0.65, 0.89, 0.63)
        pill_update(fill, r, g, b)
        icon_lbl.set_label(volume_icon(vol, muted))
        pct_lbl.set_label("muted" if muted else f"{vol}%")
        show()

    audio = AudioService.get_default()

    def connect_speaker(*_):
        speaker = audio.speaker
        if speaker is not None:
            speaker.connect("notify::volume", on_volume)
            speaker.connect("notify::is-muted", on_volume)

    audio.connect("notify::speaker", connect_speaker)
    connect_speaker()

    app.hold()
    app.run()


main()
