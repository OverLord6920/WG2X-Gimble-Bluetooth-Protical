# FeiyuTech WG2X — BLE control

Reverse-engineered controller for the WG2X 3-axis gimbal over Bluetooth LE.

## Status
- ✅ GATT mapped: service `0xFFFF`, write `ff01`, notify `ff02`
- ✅ Frame format decoded: `A5 5A | cmd | id | len | payload | crc16-le`
- ✅ Checksum cracked: **CRC16/XMODEM** over `cmd..payload` (verified vs 275 frames)
- ✅ `protocol.py` builds byte-exact frames (round-trips real captures)
- ✅ Telemetry id `0x10` decodes (angle fields + sequence counter)
- ✅ **Motion command decoded** (from HCI snoop, 46/46 frames CRC-valid):
      `A5 5A 00 11 05 | FF | pan(i16le) | tilt(i16le) | crc` — pan/tilt ∈ [-200,200],
      streamed ~20 Hz; `build_move()` reproduces the app's frames exactly
- ✅ **Init/handshake decoded** — 4 frames sent on connect to arm manual control
      (id 06 hello ×2, cmd10/id00, cmd04/id01 = arm); `INIT_FRAMES` in protocol.py
- ✅ **DIY USB BLE dongle** — Seeed XIAO nRF52840 flashed with Zephyr `hci_usb`
      shows up as `hci0` (see `dongle-fw/`)
- ✅ **CONFIRMED WORKING** — gimbal physically pans/tilts under server control 🎉

## Files
- `protocol.py` — frame build/parse, CRC16/XMODEM, telemetry decode (self-tests on run)
- `gimbal.py`   — `bleak` BLE client: `scan` / `listen` / `send`

## Run
```bash
python3 -m venv .venv && ./.venv/bin/pip install bleak
./.venv/bin/python gimbal.py scan              # confirm FY_WG2X is seen
./.venv/bin/python gimbal.py listen            # live decoded telemetry
./.venv/bin/python gimbal.py move 120 0 1.5    # pan right at speed 120 for 1.5s
./.venv/bin/python gimbal.py move 0 -200 1     # tilt down full speed for 1s
./.venv/bin/python gimbal.py send 03 <id> <hex>   # raw frame escape hatch
```

> BLE allows one central at a time. If a run is killed mid-connect, the next
> connect hangs until supervision timeout — clear it with:
> `bluetoothctl disconnect 24:0A:C4:9B:61:EE`

## The DIY dongle (`dongle-fw/`)
The home server has no Bluetooth radio, so a **Seeed XIAO nRF52840** is flashed
with Zephyr's `hci_usb` sample to become a standard USB BT controller (`hci0`).
- `dongle-fw/build.sh` — builds the firmware in the official Zephyr Docker image
- `dongle-fw/out/hci_usb_xiao_ble.uf2` — prebuilt firmware (drag onto the
  `XIAO-BLE` UF2 drive after double-tapping reset)
- Enumerates as `2fe3:000b NordicSemiconductor Zephyr USBD BT HCI`

## Other command ids (provisional, seen in capture)
- `cmd=02 id=0e len=1` — button/mode codes (0x07..0x12)
- `cmd=00 id=10 len=5` — second 5-byte control (roll/speed?)
- `cmd=00 id=06`, `cmd=02 id=40`, `cmd=04 id=01` — handshake/config

## Device
`FY_WG2X_ed` @ `24:0A:C4:9B:61:EE`
