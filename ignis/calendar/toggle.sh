#!/usr/bin/env bash
PID_FILE="/tmp/ignis-cal-island.pid"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    kill "$(cat "$PID_FILE")"
    rm -f "$PID_FILE"
else
    python "$SCRIPT_DIR/config.py" &
    echo $! > "$PID_FILE"
fi
