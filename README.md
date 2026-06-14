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
- ⬜ **Host BT radio** — the home server has no Bluetooth; needs a USB BLE dongle
      (this is now the ONLY thing between us and driving the gimbal from the server)

## Files
- `protocol.py` — frame build/parse, CRC16/XMODEM, telemetry decode (self-tests on run)
- `gimbal.py`   — `bleak` BLE client: `scan` / `listen` / `send`

## Run (once a BT dongle is attached + `pip install bleak`)
```bash
python3 gimbal.py scan              # confirm FY_WG2X is seen
python3 gimbal.py listen           # live decoded telemetry
python3 gimbal.py move 120 0 1.5   # pan right at speed 120 for 1.5s
python3 gimbal.py move 0 -200 1    # tilt down full speed for 1s
python3 gimbal.py send 03 <id> <hex>   # raw frame escape hatch
```

## Other command ids (provisional, seen in capture)
- `cmd=02 id=0e len=1` — button/mode codes (0x07..0x12)
- `cmd=00 id=10 len=5` — second 5-byte control (roll/speed?)
- `cmd=00 id=06`, `cmd=02 id=40`, `cmd=04 id=01` — handshake/config

## Device
`FY_WG2X_ed` @ `24:0A:C4:9B:61:EE`
