# Pi Zero 2 W deployment — IMX477 stream + WG2X gimbal control

Self-contained replacement for the Akaso rig. One Raspberry Pi Zero 2 W does
everything: captures the **Arducam IMX477** via CSI (hardware H.264), serves
RTSP/HLS/WebRTC, talks BLE to the **WG2X gimbal over the Pi's onboard
Bluetooth** (no XIAO dongle), and hosts the web control page.

```
 IMX477 (CSI) ──► libcamera ──► MediaMTX (rpiCamera, HW H.264)
                                   ├─ RTSP   :8554/cam
                                   ├─ HLS    :8888/cam
                                   └─ WebRTC :8889/cam ──► browser
 WG2X gimbal ◄── BLE (onboard hci0) ◄── server.py (HTTP :8095) ◄── D-pad
```

## 1. OS + camera
- Flash **Raspberry Pi OS Bookworm (64-bit, Lite)**; enable SSH + your wifi.
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
  Note the Zero 2 W shares one chip for wifi+BT; BLE control traffic is tiny so
  it coexists fine with wifi streaming.

## 2. Install everything
```bash
git clone https://github.com/OverLord6920/WG2X-Gimble-Bluetooth-Protical.git feiyu-gimbal
cd feiyu-gimbal && git checkout rpi-zero2w
bash rpi/install.sh
```
The script installs `rpicam-apps`, the arch-matched MediaMTX binary, a Python
venv with `bleak`+`aiohttp`, and enables two systemd services
(`mediamtx`, `gimbal-web`). It rewrites the unit paths to wherever you cloned.

## 3. Use it
- **Camera + D-pad:** `http://<pi-ip>:8095/`  (page auto-points the feed at the Pi)
- **Raw RTSP:** `rtsp://<pi-ip>:8554/cam` (VLC/Jellyfin/Frigate)
- Status: `systemctl status mediamtx gimbal-web --no-pager`

## 4. Tuning
- **Upside-down mount:** set `rpiCameraVFlip: true` (and/or `HFlip`) in
  `rpi/mediamtx.yml`, then `sudo systemctl restart mediamtx`. (Done at the
  source now, so the control page no longer needs the CSS flip.)
- **Resolution/bitrate:** the Zero 2 W is happiest at 720p30 ~3 Mbps (default).
  720p is a good ceiling; 1080p30 may strain CPU/wifi on the Zero 2 W.
- **Gimbal address:** same WG2X as before (`24:0A:C4:9B:61:EE` in `server.py`).

## Shared code (from repo root, unchanged)
- `protocol.py` — frame build/parse, CRC, INIT_FRAMES handshake
- `server.py` — HTTP→BLE bridge (works as-is on the Pi's onboard BT)
- `web/control.html` — feed host is auto-detected on this branch
