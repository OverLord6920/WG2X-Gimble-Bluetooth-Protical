#!/usr/bin/env bash
# Launch the local touchscreen kiosk on the Pi's DSI display.
# Run inside the Pi's graphical session (see README for autostart).
set -euo pipefail

URL="http://localhost:8095/web/kiosk.html"

# keep the screen awake (X11; harmless/no-op under Wayland)
xset s off -dpms 2>/dev/null || true

# Chromium binary differs by distro: RPi OS = chromium-browser, Debian = chromium
CHROME="$(command -v chromium-browser || command -v chromium || true)"
if [ -z "$CHROME" ]; then echo "chromium not found (apt install chromium-browser)"; exit 1; fi

# --autoplay-policy lets the WebRTC video start without a tap;
# --app gives a chromeless window; --kiosk makes it fullscreen.
exec "$CHROME" \
  --kiosk --app="$URL" \
  --ozone-platform-hint=auto \
  --noerrdialogs --disable-infobars --disable-session-crashed-bubble \
  --autoplay-policy=no-user-gesture-required \
  --check-for-update-interval=31536000 \
  --overscroll-history-navigation=0
