#!/usr/bin/env bash
set -euxo pipefail
export HOME=/root
git config --global --add safe.directory '*'
mkdir -p /ws && cd /ws
west init -m https://github.com/zephyrproject-rtos/zephyr --mr main /ws
west update
west zephyr-export
west build -b xiao_ble /ws/zephyr/samples/bluetooth/hci_usb -d /ws/build
ls -la /ws/build/zephyr/zephyr.uf2
cp /ws/build/zephyr/zephyr.uf2 /out/hci_usb_xiao_ble.uf2
echo "DONE: /out/hci_usb_xiao_ble.uf2"
