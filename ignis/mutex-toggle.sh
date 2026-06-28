#!/usr/bin/env bash
MUTEX_FILE="/tmp/ignis-mutex"

resolve_dir() {
    case "$1" in
        screenshot) echo "screenshot-island" ;;
        recorder)   echo "recorder-island" ;;
        wifi)       echo "wifi-island" ;;
        *)          echo "$1" ;;
    esac
}

WIDGET_FOLDER="$(resolve_dir "$1")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIDGET_DIR="$SCRIPT_DIR/$WIDGET_FOLDER"
PID_FILE="/tmp/ignis-${1}.pid"

kill_current() {
    if [ -f "$MUTEX_FILE" ]; then
        CURRENT=$(cat "$MUTEX_FILE")
        CURRENT_PID="/tmp/ignis-${CURRENT}.pid"
        if [ -f "$CURRENT_PID" ] && kill -0 "$(cat "$CURRENT_PID")" 2>/dev/null; then
            kill "$(cat "$CURRENT_PID")"
            rm -f "$CURRENT_PID"
        fi
        rm -f "$MUTEX_FILE"
    fi
}

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    kill "$(cat "$PID_FILE")"
    rm -f "$PID_FILE"
    rm -f "$MUTEX_FILE"
else
    kill_current
    python "$WIDGET_DIR/config.py" &
    echo $! > "$PID_FILE"
    echo "$1" > "$MUTEX_FILE"
fi
