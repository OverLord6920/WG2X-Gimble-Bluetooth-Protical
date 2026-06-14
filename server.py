#!/usr/bin/env python3
"""
Web bridge: serves a control page and turns HTTP requests into BLE joystick
commands for the WG2X gimbal. Holds ONE persistent BLE connection and streams
the current velocity at ~20 Hz (the gimbal expects a continuous stream).

Run:  ./.venv/bin/python server.py    then open http://10.0.0.7:8095/
"""

import asyncio
import pathlib
import time

from aiohttp import web
from bleak import BleakClient

import protocol as p

ADDRESS = "24:0A:C4:9B:61:EE"          # FY_WG2X
HTTP_PORT = 8095
STREAM_HZ = 20
WEB_DIR = pathlib.Path(__file__).parent / "web"
PHOTO_DIR = WEB_DIR / "photos"
RTSP_LOCAL = "rtsp://localhost:8554/cam"   # MediaMTX live path

# shared control state, updated by HTTP, consumed by the BLE loop
state = {"pan": 0, "tilt": 0, "connected": False}


async def ble_manager(app):
    """Keep a connection to the gimbal and stream the current velocity."""
    period = 1.0 / STREAM_HZ
    while not app["closing"]:
        try:
            async with BleakClient(ADDRESS) as c:
                for f in p.INIT_FRAMES:                 # arm manual control
                    await c.write_gatt_char(p.CHAR_WRITE, f, response=False)
                    await asyncio.sleep(0.08)
                state["connected"] = True
                print("gimbal connected + armed")
                while c.is_connected and not app["closing"]:
                    frame = p.build_move(state["pan"], state["tilt"])
                    await c.write_gatt_char(p.CHAR_WRITE, frame, response=False)
                    await asyncio.sleep(period)
        except Exception as e:               # noqa: BLE-001 (reconnect on any error)
            print(f"gimbal link error: {e!r}; retrying in 2s")
        finally:
            state["connected"] = False
        await asyncio.sleep(2)


# ---- HTTP handlers ----
async def api_vel(request):
    """Set velocity. JSON or query: pan, tilt in [-200, 200]."""
    try:
        data = await request.json()
    except Exception:
        data = request.query
    state["pan"] = max(-200, min(200, int(data.get("pan", 0))))
    state["tilt"] = max(-200, min(200, int(data.get("tilt", 0))))
    return web.json_response({"pan": state["pan"], "tilt": state["tilt"]})


async def api_stop(request):
    state["pan"] = state["tilt"] = 0
    return web.json_response({"ok": True})


async def api_status(request):
    return web.json_response(state)


async def api_photo(request):
    """Grab a single frame from the live stream (instant, no feed interruption).
    For the full 4056x3040 sensor capture use rpi/snapshot.sh instead."""
    PHOTO_DIR.mkdir(exist_ok=True)
    name = time.strftime("photo_%Y%m%d_%H%M%S.jpg")
    out = PHOTO_DIR / name
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-rtsp_transport", "tcp", "-i", RTSP_LOCAL,
            "-frames:v", "1", "-q:v", "2", str(out),
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await asyncio.wait_for(proc.wait(), timeout=10)
    except FileNotFoundError:
        return web.json_response({"ok": False, "error": "ffmpeg not installed"}, status=500)
    except asyncio.TimeoutError:
        proc.kill()
        return web.json_response({"ok": False, "error": "capture timed out"}, status=504)
    if proc.returncode != 0 or not out.exists():
        return web.json_response({"ok": False, "error": "capture failed"}, status=500)
    return web.json_response({"ok": True, "url": f"/web/photos/{name}", "name": name})


SNAPSHOT_SCRIPT = pathlib.Path(__file__).parent / "rpi" / "snapshot.sh"


async def api_snapshot(request):
    """Full 4056x3040 capture via rpi/snapshot.sh. Briefly stops MediaMTX
    (camera is single-access), so the live feed pauses ~3s. Needs a NOPASSWD
    sudoers entry for `systemctl stop/start mediamtx` (see rpi/README)."""
    PHOTO_DIR.mkdir(exist_ok=True)
    name = time.strftime("snap_%Y%m%d_%H%M%S.jpg")
    out = PHOTO_DIR / name
    try:
        proc = await asyncio.create_subprocess_exec(
            "bash", str(SNAPSHOT_SCRIPT), str(out),
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await asyncio.wait_for(proc.wait(), timeout=30)
    except asyncio.TimeoutError:
        proc.kill()
        return web.json_response({"ok": False, "error": "snapshot timed out"}, status=504)
    if proc.returncode != 0 or not out.exists():
        return web.json_response({"ok": False, "error": "snapshot failed (sudoers?)"}, status=500)
    return web.json_response({"ok": True, "url": f"/web/photos/{name}", "name": name,
                              "fullres": True})


async def index(request):
    return web.FileResponse(WEB_DIR / "control.html")


async def on_startup(app):
    app["closing"] = False
    app["ble"] = asyncio.create_task(ble_manager(app))


async def on_cleanup(app):
    app["closing"] = True
    state["pan"] = state["tilt"] = 0
    await asyncio.sleep(0.2)
    app["ble"].cancel()


def make_app():
    app = web.Application()
    app.add_routes([
        web.get("/", index),
        web.post("/api/vel", api_vel),
        web.get("/api/vel", api_vel),
        web.post("/api/stop", api_stop),
        web.get("/api/status", api_status),
        web.post("/api/photo", api_photo),
        web.post("/api/snapshot", api_snapshot),
        web.static("/web", str(WEB_DIR)),
    ])
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(make_app(), host="0.0.0.0", port=HTTP_PORT)
