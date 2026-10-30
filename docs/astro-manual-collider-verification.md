# Manual Astro collider verification

This is the receipt before [default-model propagation](astro-default-collider-propagation.md).
Subsequent manual narrowing of the optimized right forearm is recorded there.

Verified on 2026-10-30 with MuJoCo 3.11.0, on `codex/astro-palm-colliders`
after commit `846b744`. The maintainer's XML was not rewritten during this work.
Its SHA-256 before and after verification is
`270469a667acc18d4de973739b5a0e1164cc87d2b9e4cd4cc9c76b1120b354bb`.

## Preserved manual edits

- Both palm capsules: radius 0.05 m, centerline x=0.10–0.15 m.
- Both shin capsules: radius 0.053 m, centerline
  `0.015 0 -0.24 0.015 0 0.003`. This combines the maintainer's 10 mm
  ankle-side extension and 3 mm knee-side extension.
- Upper pelvis cylinder: radius 0.057 m, half-length 0.018 m,
  position `0 0 0.1`.
- All joint limits, body physics, meshes and the 68 scene contact pairs remain
  unchanged. Default and articulated-hand Astro variants are unchanged.

The remaining 37 non-arm collider definitions still match the default model.
Palm/ankle/waist hardware fit is not established by this knee verification.

## Extension stop

Native `mj_forward` contact generation and signed geom distances agree. The
contact is the existing ipsilateral thigh capsule
`{side}_hip_roll_link_1_capsule_collision` against the shin capsule
`{side}_knee_link_1_capsule_collision`; no new explicit pair is needed.

| Measurement | Left knee | Right knee |
|---|---:|---:|
| Contact onset | −0.067657 rad (−3.876°) | −0.067725 rad (−3.880°) |
| Straight-knee clearance | 1.005 mm | 1.006 mm |
| Penetration at −0.09 rad limit | 0.328 mm | 0.327 mm |
| Restoring constraint torque at q=−0.08 rad, velocity=−1 rad/s | +2.012 Nm | +2.008 Nm |

At the last probe each scene has exactly one contact, the intended thigh–shin
pair. The native knee-limit constraint is not yet active at −0.08 rad, so this
restoring torque comes from contact. The knee's configured lower limit stays
−0.09 rad (−5.157°); no ranges or solver settings were changed.

## Deep bending

The comparison model was built entirely in memory from the saved XML, changing
only each shin's proximal endpoint from +0.003 m back to 0. All other manual
edits were retained. A second comparison used the committed `846b744` model.

For each side, 2,934 scene configurations covered knee angles 0–2.44 rad at
0.005 rad spacing, hip yaw −0.5/0/+0.5 rad, and single-knee/both-knee bending.
Contact-pair sets involving the tested leg were identical before and after the
3 mm extension. Shared contact distances differed by less than 1e−12 m.
This is sampled coverage, not proof for every combined hip/ankle/body pose.

**Existing deep-flexion interference remains:** thigh–shin contact starts at
2.326964 rad left / 2.326976 rad right (about 133.3°), before the configured
2.44 rad (139.8°) maximum. Onset is identical in all three compared models.
At 2.44 rad the static penetration is 7.781 mm left / 7.780 mm right, also
unchanged. Therefore the new extension does not add deep-bending interference,
but the full configured range is not collision-free. Geometry was preserved
as requested; this pre-existing contact was not masked or removed.

## Native stepping and limits

Four full-scene kick probes started at a straight knee with velocity −1 or
−3 rad/s, one side at a time, for 0.2 s. Gravity was disabled only in memory
for these diagnostic probes; no controller, joint fixture or saved options
were added. Each probe generated thigh–shin contact, developed positive
restoring knee constraint torque, and reversed knee velocity. All states
remained finite with no MuJoCo warnings.

| Initial speed | Minimum left angle | Minimum right angle |
|---|---:|---:|
| −1 rad/s | −0.080281 rad | −0.080304 rad |
| −3 rad/s | −0.098846 rad | −0.098866 rad |

The faster probe overshoots the native limit by about 0.51°. Contact and native
joint limits are compliant: this is resistance near the stop, not an exact
angle clamp. These uncontrolled probes do not establish behavior under a
powered kick or hardware loads. Four additional native 0.1 s runs started at
2.2/2.44 rad, one side at a time, with normal gravity; all remained finite
without warnings.

## Acceptance checks

`UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passes 18 test methods:
2 directory/style checks and 16 native model checks, including standalone
family loading and stepping all retained model/scene entry points.

Two outdated geometry guards were updated to preserve the maintainer's palm
positions and the three calibrated non-arm geoms. A new regression checks
extension-contact activation and compares flexion contacts against the
in-memory pre-extension model at 123 knee angles and three hip-yaw settings
per side. Re-run with:

```sh
.venv/bin/python -m unittest test.model_test.AstroP2ArmCollisionTests
```

Collider previews have not been regenerated and predate these manual edits.
MJX runtime, controllers, Workbench and URDF compatibility remain deferred.
No merge or push was performed.
