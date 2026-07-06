#!/usr/bin/env bash
set -e

PRESET_FILE="$HOME/.local/share/easyeffects/output/eq-island.json"
STATE_FILE="$HOME/.config/ignis/eq/state.json"
PRESET_NAME="eq-island"

if [ ! -f "$PRESET_FILE" ]; then
    echo "eq-island: ERROR preset file not found at $PRESET_FILE" >> /tmp/eq-island.log
    exit 1
fi

G1="${1:-0.0}"
G2="${2:-0.0}"
G3="${3:-0.0}"
G4="${4:-0.0}"
G5="${5:-0.0}"
G6="${6:-0.0}"
G7="${7:-0.0}"
G8="${8:-0.0}"

python3 - "$PRESET_FILE" "$STATE_FILE" "$G1" "$G2" "$G3" "$G4" "$G5" "$G6" "$G7" "$G8" <<'PYEOF'
import json
import sys
import os

preset_path = sys.argv[1]
state_path = sys.argv[2]
gains = [float(x) for x in sys.argv[3:11]]
Q_LIST = [1.3, 1.1, 0.9, 0.8, 0.8, 0.9, 1.0, 1.2]

with open(preset_path) as f:
    data = json.load(f)

eq = data["output"]["equalizer#0"]

for channel in ("left", "right"):
    for i, gain in enumerate(gains):
        eq[channel][f"band{i}"]["gain"] = gain
        eq[channel][f"band{i}"]["q"] = Q_LIST[i]

with open(preset_path, "w") as f:
    json.dump(data, f, indent=4)

values = [max(0.0, min(1.0, (g / 24.0) + 0.5)) for g in gains]
os.makedirs(os.path.dirname(state_path), exist_ok=True)
with open(state_path, "w") as f:
    json.dump({"values": values}, f)
PYEOF

easyeffects --load-preset "$PRESET_NAME" >/dev/null 2>&1

echo "eq-island: applied gains $G1 $G2 $G3 $G4 $G5 $G6 $G7 $G8 via $PRESET_NAME" >> /tmp/eq-island.log
