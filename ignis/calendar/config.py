import gi
gi.require_version('NM', '1.0')
from ignis.widgets import Widget
from ignis.app import IgnisApp
import calendar
import datetime


today = datetime.date.today()


def shifted(n):
    m = (today.month - 1 + n) % 12 + 1
    y = today.year + ((today.month - 1 + n) // 12)
    return y, m


def month_grid(year, month):
    name = datetime.date(year, month, 1).strftime("%B %Y")

    dow = Widget.Box(
        child=[
            Widget.Label(label=d, css_classes=["cal-dow"], hexpand=True, halign="center")
            for d in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        ],
    )

    weeks = []
    for week in calendar.monthcalendar(year, month):
        cells = []
        for day in week:
            is_today = day != 0 and datetime.date(year, month, day) == today
            cells.append(Widget.Label(
                label=str(day) if day else "",
                css_classes=["cal-today" if is_today else "cal-day"],
                hexpand=True,
                halign="center",
            ))
        weeks.append(Widget.Box(child=cells))

    return Widget.Box(
        vertical=True,
        spacing=4,
        css_classes=["cal-month-box"],
        child=[
            Widget.Label(label=name, css_classes=["cal-month"], halign="center"),
            dow,
        ] + weeks,
    )


def main():
    app = IgnisApp.get_default()
    app.apply_css(f"{__file__.replace('config.py', 'style.css')}")

    state = {"offset": 0}
    months_box = Widget.Box(spacing=8)

    def refresh():
        o = state["offset"]
        y0, m0 = shifted(o)
        y1, m1 = shifted(o + 1)
        while True:
            child = months_box.get_first_child()
            if child is None:
                break
            months_box.remove(child)
        months_box.append(month_grid(y0, m0))
        months_box.append(month_grid(y1, m1))

    def go(delta):
        state["offset"] += delta
        refresh()

    nav = Widget.Box(
        halign="center",
        spacing=6,
        child=[
            Widget.Button(
                css_classes=["cal-nav"],
                child=Widget.Label(label=""),
                on_click=lambda *_: go(-1),
            ),
            Widget.Button(
                css_classes=["cal-nav"],
                child=Widget.Label(label=""),
                on_click=lambda *_: go(1),
            ),
        ],
    )

    refresh()

    Widget.Window(
        namespace="cal-island",
        anchor=["top", "right"],
        margin_top=2,
        margin_right=5,
        layer="overlay",
        kb_mode="none",
        css_classes=["cal-window"],
        child=Widget.Box(
            vertical=True,
            spacing=6,
            css_classes=["cal-island"],
            child=[nav, months_box],
        ),
    )

    app.hold()
    app.run()


main()
