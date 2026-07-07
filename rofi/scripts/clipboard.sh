#!/usr/bin/env bash
THEME="$HOME/.config/rofi/clipboard.rasi"

selected=$(cliphist list | rofi -dmenu -p " " -theme "$THEME" \
    -kb-custom-1 "Control+Delete" \
    -kb-custom-2 "Alt+Delete")

exit_code=$?

case "$exit_code" in
    10)
        [ -n "$selected" ] && echo "$selected" | cliphist delete
        ;;
    11)
        cliphist wipe
        ;;
    0)
        [ -n "$selected" ] && echo "$selected" | cliphist decode | wl-copy
        ;;
esac
