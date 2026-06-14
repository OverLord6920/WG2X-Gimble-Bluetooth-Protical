#!/usr/bin/env python3
"""
Minimal BLE controller for the FeiyuTech WG2X.

Requires a Bluetooth LE adapter on the host (the home server currently has
none — plug in a USB BT4.0+ dongle first) and `pip install bleak`.

Usage:
    python3 gimbal.py scan                 # find the gimbal
    python3 gimbal.py listen               # connect + print decoded telemetry
    python3 gimbal.py move <pan> <tilt> <seconds>   # joystick drive, -200..200
    python3 gimbal.py send 03 10 1122...    # send a raw frame (cmd id payload-hex)
"""

import asyncio
import sys

from bleak import BleakClient, BleakScanner

import protocol as p

ADDRESS = "24:0A:C4:9B:61:EE"   # FY_WG2X_ed (from your capture)
NAME    = "FY_WG2X"


async def scan():
    print("Scanning 8s for BLE devices...")
    for d in await BleakScanner.discover(timeout=8.0):
        tag = "  <-- gimbal" if (d.name or "").startswith(NAME) else ""
        print(f"  {d.address}  {d.name or '(unknown)'}{tag}")


async def listen():
    def on_notify(_handle, data: bytes):
        try:
            f = p.parse_frame(bytes(data))
            extra = p.decode_telemetry(f["payload"]) if f["id"] == p.ID_TELEMETRY else f["payload"].hex(" ")
            print(f"id=0x{f['id']:02x} {extra}")
        except ValueError as e:
            print(f"raw {bytes(data).hex(' ')}  ({e})")

    async with BleakClient(ADDRESS) as c:
        print(f"Connected: {c.is_connected}. Subscribing to telemetry...")
        await c.start_notify(p.CHAR_NOTIFY, on_notify)
        await asyncio.sleep(30)
        await c.stop_notify(p.CHAR_NOTIFY)


async def send(cmd_hex, id_hex, payload_hex=""):
    cmd, msg_id = int(cmd_hex, 16), int(id_hex, 16)
    payload = bytes.fromhex(payload_hex)
    frame = p.build_frame(cmd, msg_id, payload)
    print(f"Writing to ff01: {frame.hex(' ')}")
    async with BleakClient(ADDRESS) as c:
        await c.start_notify(p.CHAR_NOTIFY,
                             lambda h, d: print("  <-", bytes(d).hex(" ")))
        await c.write_gatt_char(p.CHAR_WRITE, frame, response=False)
        await asyncio.sleep(2)   # watch for a reply on ff02


async def move(pan, tilt, seconds="1.0"):
    """Stream the joystick frame for `seconds`, then send neutral to stop."""
    pan, tilt, seconds = int(pan), int(tilt), float(seconds)
    frame = p.build_move(pan, tilt)
    stop  = p.build_move(0, 0)
    print(f"move pan={pan} tilt={tilt} for {seconds}s: {frame.hex(' ')}")
    async with BleakClient(ADDRESS) as c:
        for f in p.INIT_FRAMES:                # arm manual control first
            await c.write_gatt_char(p.CHAR_WRITE, f, response=False)
            await asyncio.sleep(0.08)
        await asyncio.sleep(0.2)
        deadline = asyncio.get_event_loop().time() + seconds
        while asyncio.get_event_loop().time() < deadline:
            await c.write_gatt_char(p.CHAR_WRITE, frame, response=False)
            await asyncio.sleep(0.05)          # ~20 Hz, like the app
        for _ in range(3):                     # make sure it stops
            await c.write_gatt_char(p.CHAR_WRITE, stop, response=False)
            await asyncio.sleep(0.05)
    print("stopped.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, args = sys.argv[1], sys.argv[2:]
    fn = {"scan": scan, "listen": listen, "move": move, "send": send}.get(cmd)
    if not fn:
        print(__doc__)
        return
    asyncio.run(fn(*args))


if __name__ == "__main__":
    main()
