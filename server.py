#!/usr/bin/env python3
"""
Web bridge: serves a control page and turns HTTP requests into BLE joystick
commands for the WG2X gimbal. Holds ONE persistent BLE connection and streams
the current velocity at ~20 Hz (the gimbal expects a continuous stream).

Run:  ./.venv/bin/python server.py    then open http://10.0.0.7:8095/
"""

import asyncio
import pathlib

from aiohttp import web
from bleak import BleakClient

import protocol as p

ADDRESS = "24:0A:C4:9B:61:EE"          # FY_WG2X
HTTP_PORT = 8095
STREAM_HZ = 20
WEB_DIR = pathlib.Path(__file__).parent / "web"

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
        web.static("/web", str(WEB_DIR)),
    ])
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(make_app(), host="0.0.0.0", port=HTTP_PORT)
