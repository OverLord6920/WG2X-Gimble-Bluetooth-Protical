"""
FeiyuTech WG2X BLE protocol — reverse-engineered from nRF Connect captures.

Frame format (confirmed against 275 captured telemetry frames):

    A5 5A | cmd | id | len | payload[len] | crc16(2, little-endian)

  - A5 5A          : fixed frame magic
  - cmd            : 0x03 on the telemetry we captured (target/direction byte)
  - id             : message id (0x10 = the gimbal's angle telemetry stream)
  - len            : payload length in bytes
  - crc16          : CRC16/XMODEM (poly 0x1021, init 0x0000) computed over
                     everything AFTER the A5 5A header (cmd..end of payload),
                     stored little-endian.

GATT:
  service  0000ffff-0000-1000-8000-00805f9b34fb
    ff01  [Write No Response]  -> commands (host -> gimbal)
    ff02  [Notify]             -> telemetry/responses (gimbal -> host)
"""

import struct

HEADER = bytes([0xA5, 0x5A])

SERVICE_UUID = "0000ffff-0000-1000-8000-00805f9b34fb"
CHAR_WRITE   = "0000ff01-0000-1000-8000-00805f9b34fb"  # WNR: commands out
CHAR_NOTIFY  = "0000ff02-0000-1000-8000-00805f9b34fb"  # Notify: telemetry in

# --- message ids (confirmed from HCI snoop of the Feiyu ON app) ---
ID_TELEMETRY = 0x10   # gimbal -> host, periodic angle stream (cmd=0x03)
ID_MOVE      = 0x11   # host -> gimbal joystick: payload FF|pan(i16le)|tilt(i16le)
# provisional / not yet used:
#   cmd=0x02 id=0x0e len=1  -> button/mode codes (0x07..0x12)
#   cmd=0x00 id=0x10 len=5  -> second 5-byte control (roll/speed?)
#   cmd=0x00 id=0x06, cmd=0x02 id=0x40, cmd=0x04 id=0x01 -> handshake/config

MOVE_MIN, MOVE_MAX = -200, 200   # observed joystick range on both axes


def build_move(pan: int = 0, tilt: int = 0) -> bytes:
    """Joystick move frame. pan/tilt are velocities in [-200, 200].
    pan/tilt = 0 stops the gimbal. Stream this ~every 50ms while moving."""
    pan  = max(MOVE_MIN, min(MOVE_MAX, int(pan)))
    tilt = max(MOVE_MIN, min(MOVE_MAX, int(tilt)))
    payload = b"\xff" + struct.pack("<hh", pan, tilt)
    return build_frame(0x00, ID_MOVE, payload)


def crc16_xmodem(data: bytes) -> int:
    """CRC16/XMODEM: poly 0x1021, init 0x0000, no reflection, no xorout."""
    crc = 0x0000
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return crc


def build_frame(cmd: int, msg_id: int, payload: bytes = b"") -> bytes:
    """Assemble a full A5 5A frame with correct length + CRC."""
    body = bytes([cmd, msg_id, len(payload)]) + payload
    crc = crc16_xmodem(body)
    return HEADER + body + struct.pack("<H", crc)


def parse_frame(frame: bytes):
    """Validate + decode one frame. Returns dict or raises ValueError."""
    if len(frame) < 7 or frame[0:2] != HEADER:
        raise ValueError(f"bad header: {frame.hex(' ')}")
    cmd, msg_id, length = frame[2], frame[3], frame[4]
    payload = frame[5:5 + length]
    if len(payload) != length:
        raise ValueError(f"short payload: want {length}, got {len(payload)}")
    got_crc = struct.unpack("<H", frame[5 + length:7 + length])[0]
    want_crc = crc16_xmodem(frame[2:5 + length])
    if got_crc != want_crc:
        raise ValueError(f"crc mismatch: got {got_crc:04x} want {want_crc:04x}")
    return {"cmd": cmd, "id": msg_id, "len": length, "payload": payload}


def decode_telemetry(payload: bytes):
    """Best-effort decode of the id=0x10 angle stream (8-byte payload).

    Layout (provisional, from observation):
        [0]      flags/axis byte (0x11 seen)
        [1:5]    two int16 fields (angle-ish; one steady, one near-zero)
        [5:7]    uint16 sequence/timestamp counter (monotonic)
        [7]      trailing byte (0x51 seen, constant)
    """
    if len(payload) != 8:
        return {"raw": payload.hex(" ")}
    a0, a1 = struct.unpack("<hh", payload[1:5])
    seq = struct.unpack("<H", payload[5:7])[0]
    return {"flag": payload[0], "a0": a0, "a1": a1, "seq": seq, "tail": payload[7]}


if __name__ == "__main__":
    # Self-test: re-derive a known captured frame.
    sample = bytes.fromhex("a5 5a 03 10 08 11 cd b9 f5 ff 9f 10 51 a8 da".replace(" ", ""))
    p = parse_frame(sample)
    rebuilt = build_frame(p["cmd"], p["id"], p["payload"])
    print("parse  :", p, decode_telemetry(p["payload"]))
    print("rebuild:", rebuilt.hex(" "))
    assert rebuilt == sample, "frame builder does not reproduce capture!"
    print("OK: build/parse round-trips the captured frame.")
