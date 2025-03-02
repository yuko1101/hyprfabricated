#!/bin/bash

# Directory to save recordings
SAVE_DIR="$XDG_VIDEOS_DIR/Screenrecords"
SAVE_FILE="$SAVE_DIR/record_$(date +'%y%m%d_%H%M%S').mp4"
random_string=$(LC_ALL=C tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 7)
audiodev="alsa_output.pci-0000_00_1b.0.analog-stereo.monitor"
focused_window=$(hyprctl activewindow)
app_name=$(echo "$focused_window" | grep "class:" | awk '{print $2}')
file="${random_string}-${app_name}"
output_file=$HOME/Videos/Recordings/"${file}-tmp.mp4"

# Create directory if it doesn't exist
mkdir -p $HOME/Videos/Recordings

# Check if wl-screenrec is already running
if pgrep -x "wl-screenrec" >/dev/null; then
    pkill wl-screenrec
    notify-send -a "Fabric" "Screen Recording" "Recording stopped ✅"
    exit 0
fi

# Start Recording
notify-send -a "Fabric" "Screen Recording" "Recording started 🎥"
wl-screenrec --audio --audio-device "$audiodev" -f "$output_file" -g "$(slurp -d)" 2>/dev/null

notify-send -a "Fabric" "Recording saved to:" "$output_file"

