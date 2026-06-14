# Physical build — IMX477 + WG2X gimbal + Pi 4

The Pi 4 sits on a **fixed base**. Only the lightweight camera head rides the
gimbal, connected back to the Pi by a CSI flex ribbon.

```
 [Pi 4 + Ethernet]  --- CSI flex ribbon --->  [IMX477 in GoPro-spec
   fixed base                                  3D-printed enclosure]
                                                  on WG2X gimbal
```

## Range of motion (design target)
Usage stays within roughly:
- **Pan:** ±60° (≈120° total) left/right
- **Tilt:** ±45° up/down

This limited travel is what makes the whole rig practical — see cable notes.

## CSI flex cable
- **Pi 4 + IMX477 are both 15-pin** standard CSI, so a plain 15 cm camera
  ribbon fits both ends (no 22-pin adapter — that's only Pi 5 / CM4).
- **15 cm is enough** given the limited travel: keep the straight-line base→head
  distance ≤ ~8–10 cm and the rest forms the service loop.
- **Service loop:** leave slack that pivots near each gimbal axis so the cable
  never goes taut across the ±60°/±45° range. The cable must never pull on the
  camera head.
- **Keep a spare** ribbon — flex cables on moving mounts eventually crack.

## Gimbal payload & balance (the hard constraint)
The WG2X is a *wearable* gimbal sized for a bare GoPro (~125 g) with small
motors:
- Keep camera-head total mass **near a GoPro's**, and place the **center of
  mass where a GoPro's would be** relative to the GoPro mount interface, or the
  gimbal won't balance and the motors overheat / drift.
- IMX477 board ~30 g + lens (10–40 g) + enclosure → stay light, especially the
  lens (see below).
- **Cable torque:** even at 15 cm, a stiff/badly-routed ribbon applies torque
  the little motors fight. Limited travel helps a lot, but route for zero
  tension at the neutral position.

## Enclosure
- 3D-printed, **matching GoPro form factor** so it drops into the WG2X's
  GoPro-style mount.
- Design the CoM to mimic a GoPro (counterweight if needed).
- Provide a strain-relief / anchor point for the ribbon at the head so flex
  happens in the service loop, not at the connector.

## Lens (FOV to match the "GoPro look")
- GoPro is ultra-wide (~120°+); the IMX477 stock 6 mm CS lens is only ~63°.
- For a GoPro-like wide field, fit a **wide M12/CS lens** — but watch weight,
  it feeds straight back into the payload/balance constraint.

## Software soft-limits (TODO, needs hardware)
The gimbal streams angle telemetry (`id 0x10`). Once the rig exists we can:
1. Move to known pan/tilt angles, capture telemetry, derive the angle scale
   (current decode of `a0`/`a1` is provisional/uncalibrated).
2. Add configurable soft limits in `server.py` so the bridge refuses to drive
   past ±60° / ±45°, protecting the CSI cable automatically.
