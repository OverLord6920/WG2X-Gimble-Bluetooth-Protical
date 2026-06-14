#!/usr/bin/env bash
# One-shot setup for the Pi Zero 2 W: IMX477 stream + WG2X gimbal web control.
# Run on the Pi (Raspberry Pi OS Bookworm) from the cloned repo root:
#   bash rpi/install.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
echo ">> repo at $REPO"

echo ">> [1/5] apt deps"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip rpicam-apps bluez tar

echo ">> [2/5] MediaMTX (arch-matched release)"
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

echo ">> [3/5] python venv + bleak/aiohttp"
python3 -m venv "$REPO/.venv"
"$REPO/.venv/bin/pip" install --upgrade pip bleak aiohttp

echo ">> [4/5] systemd services"
# patch the unit paths to the actual repo/user, then install
sed "s#/home/pi/feiyu-gimbal#${REPO}#g" "$REPO/rpi/mediamtx.service"   | sudo tee /etc/systemd/system/mediamtx.service   >/dev/null
sed "s#/home/pi/feiyu-gimbal#${REPO}#g; s/^User=pi/User=$(whoami)/" \
    "$REPO/rpi/gimbal-web.service" | sudo tee /etc/systemd/system/gimbal-web.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now mediamtx gimbal-web

echo ">> [5/5] done"
echo "   stream:  http://$(hostname -I | awk '{print $1}'):8889/cam"
echo "   control: http://$(hostname -I | awk '{print $1}'):8095/"
echo "   check:   systemctl status mediamtx gimbal-web --no-pager"
