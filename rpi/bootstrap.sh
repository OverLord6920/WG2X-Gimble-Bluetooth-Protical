#!/usr/bin/env bash
# One-command bootstrap for a fresh Raspberry Pi: installs git, clones this
# repo (rpi branch), and runs the full installer.
#
#   curl -fsSL https://raw.githubusercontent.com/OverLord6920/WG2X-Gimble-Bluetooth-Protical/rpi/rpi/bootstrap.sh | bash
#
# Optional first arg = clone destination (default ~/feiyu-gimbal).
set -euo pipefail
REPO_URL="https://github.com/OverLord6920/WG2X-Gimble-Bluetooth-Protical.git"
BRANCH="rpi"
DEST="${1:-$HOME/feiyu-gimbal}"

echo ">> installing git"
sudo apt-get update
sudo apt-get install -y git

if [ -d "$DEST/.git" ]; then
  echo ">> updating existing clone at $DEST"
  git -C "$DEST" fetch origin "$BRANCH"
  git -C "$DEST" checkout "$BRANCH"
  git -C "$DEST" pull --ff-only origin "$BRANCH"
else
  echo ">> cloning $REPO_URL ($BRANCH) -> $DEST"
  git clone --branch "$BRANCH" "$REPO_URL" "$DEST"
fi

echo ">> running installer"
cd "$DEST"
bash rpi/install.sh
