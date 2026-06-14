# Pi 4 deployment — IMX477 stream + WG2X gimbal control

Self-contained replacement for the Akaso rig, on a **Raspberry Pi 4 (fixed
base)**: captures the **Arducam IMX477** over a CSI flex cable to a camera head
on the gimbal (hardware H.264), serves RTSP/HLS/WebRTC over **wired Gigabit
Ethernet**, talks BLE to the **WG2X over the Pi's onboard Bluetooth**, and hosts
the web control page. See `HARDWARE.md` for the physical build (enclosure,
cable routing, payload, lens).

> Pi Zero 2 W variant: see the **`rpi-zero2w`** branch (2.4 GHz wifi, mini-CSI,
> AC1200 dongle notes). This branch targets the Pi 4 wired build.

```
 IMX477 (CSI flex) ──► libcamera ──► MediaMTX (rpiCamera, HW H.264)
                                       ├─ RTSP   :8554/cam
                                       ├─ HLS    :8888/cam
                                       └─ WebRTC :8889/cam ──► browser (wired LAN)
 WG2X gimbal ◄── BLE (onboard hci0) ◄── server.py (HTTP :8095) ◄── D-pad
```

## 1. OS + camera
- Flash **Raspberry Pi OS Trixie, 64-bit** (Debian 13, current; always 64-bit
  on a Pi 4 for arm64 MediaMTX + better perf). Which variant depends on the
  touchscreen:
  - **With the DSI kiosk (this build): use the _Desktop_ image.** "Lite" has no
    GUI, so Chromium can't run. Desktop ships Chromium + the labwc (Wayland)
    compositor; the kiosk autostart (§3a) drops right in.
  - Headless (control only from phones/PCs): **Lite** is perfect.
  - Minimal touchscreen appliance: **Lite + `cage`** (see §3a option B).
- Enable SSH. Use **wired
  Ethernet** for the stream (no wifi/BT contention; the Pi 4 has separate
  radios anyway, so onboard Bluetooth for the gimbal is unaffected).
- The IMX477 needs its overlay. Edit `/boot/firmware/config.txt`:
  ```
  camera_auto_detect=0
  dtoverlay=imx477
  ```
  Reboot, then verify capture:
  ```
  rpicam-hello --list-cameras      # should list imx477
  rpicam-jpeg -o test.jpg          # grabs a frame
  ```
- **Auto IR-Cut:** the "Auto" board switches its IR-cut filter via an onboard
  light sensor — no software needed. (If yours is the GPIO-switched variant,
  it exposes a control pin; tell me and we'll add a small GPIO toggle service.)
- **Onboard Bluetooth:** on by default. Confirm with `hciconfig` / `bluetoothctl list`.
  The Pi 4 has separate wifi/BT/Ethernet radios, so the gimbal BLE link never
  competes with the (wired) video stream.

## 2. Install everything
```bash
git clone https://github.com/OverLord6920/WG2X-Gimble-Bluetooth-Protical.git feiyu-gimbal
cd feiyu-gimbal && git checkout rpi
bash rpi/install.sh
```
The script installs `rpicam-apps`, the arch-matched MediaMTX binary, a Python
venv with `bleak`+`aiohttp`, and enables two systemd services
(`mediamtx`, `gimbal-web`). It rewrites the unit paths to wherever you cloned.

## 3. Use it
- **Camera + D-pad (any browser):** `http://<pi-ip>:8095/`  (auto-points feed at the Pi)
- **Local touchscreen kiosk:** `http://<pi-ip>:8095/web/kiosk.html` (see §3a)
- **Raw RTSP:** `rtsp://<pi-ip>:8554/cam` (VLC/Jellyfin/Frigate)
- Status: `systemctl status mediamtx gimbal-web --no-pager`

## 3a. Touchscreen kiosk (DSI display)
`web/kiosk.html` is a full-screen touch UI for the Pi's own DSI display, with
**two control modes at once**:
- **Drag-to-move** — touch anywhere on the video and drag; direction = pan/tilt,
  distance from the touch point = speed (a virtual joystick). Release = stop.
- **Edge arrows** — fixed-speed ↑↓←→ pinned to the four edges.

```bash
sudo apt-get install -y chromium-browser
chmod +x rpi/kiosk.sh
```

### Option A — Desktop image (labwc, default; simplest)
Test from the desktop: `rpi/kiosk.sh`. Then autostart on boot by adding to
`~/.config/labwc/autostart`:
```
/home/<user>/feiyu-gimbal/rpi/kiosk.sh &
```

### Option B — Lite image + cage (minimal appliance)
`cage` is a one-app Wayland kiosk compositor — no desktop needed.
```bash
sudo apt-get install -y cage
sudo cp rpi/kiosk.service /etc/systemd/system/    # edit User/paths if not 'pi'
sudo systemctl enable --now kiosk
```
The service runs `cage -- rpi/kiosk.sh` on tty1 at boot.

Notes:
- The DSI touchscreen is usually auto-detected. To rotate, set `display_rotate`
  (or the Screen Configuration tool) — rotate the *display*, touch follows.
- The kiosk talks to the same `gimbal-web` service, so it works whether you
  drive from the touchscreen or a phone on the LAN (last input wins).

## 4. Resolution — what's actually possible
The Pi's **hardware H.264 encoder is capped at 1920×1080**, so the live stream
tops out at 1080p regardless of the IMX477's bigger sensor modes:

| Mode | Live H.264 stream? | Notes |
|------|--------------------|-------|
| 4056×3040 (12 MP full) | ❌ stills only | use `rpi/snapshot.sh` |
| 2028×1520 / 2028×1080  | ⚠️ downscaled to ≤1080p | these are *sensor* modes feeding the 1080p output |
| 1920×1080p30 | ✅ default | ~6 Mbps, solid on the Zero 2 W |
| 1920×1080p50 | ✅ encoder-OK | ~9 Mbps — **wifi-limited**, test it |
| 1280×720p60  | ✅ | smoother, lighter |
| 1332×990p120 | ✅ encoder-OK | niche; wifi can't carry 120 fps |

Edit the `rpiCamera*` values in `rpi/mediamtx.yml`, then
`sudo systemctl restart mediamtx`. The reason to stay at 1080p isn't the
encoder alone — the Zero 2 W's single-chip 2.4 GHz wifi (shared with the BT
gimbal link) is the real bottleneck above ~9 Mbps.

### Capture (buttons on both the kiosk and the control page)
- **📷 Photo (1080p)** → `POST /api/photo`: grabs a frame from the *live stream*
  via ffmpeg. Instant, **no interruption**. Good default.
- **🖼️ Snapshot (12 MP)** → `POST /api/snapshot`: full **4056×3040** via
  `rpicam-still`. The camera is single-access, so it briefly stops MediaMTX
  (~2-3 s feed pause) then resumes. Needs the NOPASSWD sudoers entry that
  `install.sh` adds (`systemctl stop/start mediamtx`).

Both save into `web/photos/` and return a viewable URL. Command-line equivalent
for full-res: `rpi/snapshot.sh [out.jpg]`.

## 5. Tuning
- **Upside-down mount:** set `rpiCameraVFlip: true` (and/or `HFlip`) in
  `rpi/mediamtx.yml`, then `sudo systemctl restart mediamtx`. (Done at the
  source now, so the control page no longer needs the CSS flip.)
- **Gimbal address:** same WG2X as before (`24:0A:C4:9B:61:EE` in `server.py`).

## Shared code (from repo root, unchanged)
- `protocol.py` — frame build/parse, CRC, INIT_FRAMES handshake
- `server.py` — HTTP→BLE bridge (works as-is on the Pi's onboard BT)
- `web/control.html` — feed host is auto-detected on this branch
