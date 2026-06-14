#!/usr/bin/env bash
# Capture a FULL-RESOLUTION 4056x3040 still from the IMX477.
#
# The Pi camera allows only one user at a time, so this briefly stops the
# MediaMTX stream, grabs the photo at full sensor resolution (which bypasses
# the 1080p H.264 encoder limit), then restarts the stream. Expect a ~2-3s
# gap in the live feed.
#
# Usage:  rpi/snapshot.sh [output.jpg]
set -euo pipefail
OUT="${1:-$HOME/snapshots/imx477_$(date +%Y%m%d_%H%M%S).jpg}"
mkdir -p "$(dirname "$OUT")"

echo ">> pausing stream"
sudo systemctl stop mediamtx
# small settle so libcamera fully releases the device
sleep 1

echo ">> capturing full-res 4056x3040 -> $OUT"
# --immediate skips the long preview; bump --denoise for low light if needed.
rpicam-still --width 4056 --height 3040 --quality 95 --immediate -o "$OUT"

echo ">> resuming stream"
sudo systemctl start mediamtx
echo ">> done: $OUT"
