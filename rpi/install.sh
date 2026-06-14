#!/usr/bin/env bash
# One-shot setup: IMX477 stream + WG2X gimbal web control.
# Run on the Pi (Raspberry Pi OS Trixie) from the cloned repo root:
#   bash rpi/install.sh
# (Fresh Pi with nothing cloned yet? use rpi/bootstrap.sh instead.)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
echo ">> repo at $REPO"

echo ">> [1/6] apt deps"
sudo apt-get update
# ffmpeg = quick 1080p photo grabs from the live stream (/api/photo)
sudo apt-get install -y git python3-venv python3-pip rpicam-apps bluez tar ffmpeg

echo ">> [2/6] MediaMTX (arch-matched release)"
case "$(uname -m)" in
  aarch64) MARCH=arm64v8 ;;
  armv7l)  MARCH=armv7   ;;
  *) echo "unexpected arch $(uname -m)"; exit 1 ;;
esac
VER=$(curl -fsSL https://api.github.com/repos/bluenviron/mediamtx/releases/latest \
      | grep -oP '"tag_name": "\K[^"]+')
echo "   installing MediaMTX $VER ($MARCH)"
curl -fsSL -o /tmp/mediamtx.tar.gz \
  "https://github.com/bluenviron/mediamtx/releases/download/${VER}/mediamtx_${VER}_linux_${MARCH}.tar.gz"
sudo tar -xzf /tmp/mediamtx.tar.gz -C /usr/local/bin mediamtx
sudo chmod +x /usr/local/bin/mediamtx

echo ">> [3/6] python venv + bleak/aiohttp"
python3 -m venv "$REPO/.venv"
"$REPO/.venv/bin/pip" install --upgrade pip bleak aiohttp
chmod +x "$REPO"/rpi/*.sh

echo ">> [4/6] systemd services"
# patch the unit paths to the actual repo/user, then install
sed "s#/home/pi/feiyu-gimbal#${REPO}#g" "$REPO/rpi/mediamtx.service"   | sudo tee /etc/systemd/system/mediamtx.service   >/dev/null
sed "s#/home/pi/feiyu-gimbal#${REPO}#g; s/^User=pi/User=$(whoami)/" \
    "$REPO/rpi/gimbal-web.service" | sudo tee /etc/systemd/system/gimbal-web.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now mediamtx gimbal-web

echo ">> [5/6] sudoers for full-res snapshot (stop/start mediamtx, no password)"
echo "$(whoami) ALL=(root) NOPASSWD: /usr/bin/systemctl stop mediamtx, /usr/bin/systemctl start mediamtx" \
  | sudo tee /etc/sudoers.d/gimbal-snapshot >/dev/null
sudo chmod 440 /etc/sudoers.d/gimbal-snapshot

echo ">> [6/6] done"
echo "   stream:  http://$(hostname -I | awk '{print $1}'):8889/cam"
echo "   control: http://$(hostname -I | awk '{print $1}'):8095/"
echo "   check:   systemctl status mediamtx gimbal-web --no-pager"
