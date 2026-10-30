# Direct left forearm/upper-arm contact

Historical direct-pair receipt. Later [shoulder-roll ownership](astro-upper-arm-roll-owner.md)
enables automatic contacts on both arms and removes all elbow pairs/proxies.

The maintainer shortened the left upper-arm capsule's distal centerline
endpoint from z=−0.06 to −0.01 m, then observed visible forearm penetration
without contact. Diagnosis and fix used Matt's diagnosing-bugs workflow on
`codex/astro-palm-colliders`. No commit, merge or push was performed.

## Cause and reproduction

At left elbow q=−0.48 rad, native signed distance between
`left_upper_arm_capsule_collision` and `left_elbow_link_1_capsule_collision`
is **−3.483904 mm**. Both masks are (1, 1), but their bodies are directly
connected: `left_shoulder_yaw_link` is parent of `left_elbow_link`.
MuJoCo filters automatic parent-child contacts. The existing explicit pair
instead selected `left_elbow_stop_collision`, whose clearance after the
manual shortening was +25.22 mm at that pose. Thus the overlap was real;
the overlapping pair was never selected for contact generation.

An unattended native reproduction asserted negative distance and actual
contact at q=−0.48. Before the fix it printed:

```text
large-capsule gap=-3.483904 mm, native_contact=False
AssertionError: BUG: overlapping large upper-arm/forearm capsules produce no contact
```

Changing only the explicit pair target in memory made that same geometry
produce a frictionless native contact. The current left capsule has 5.5 mm
reference clearance, so direct selection no longer creates the permanent
hinge overlap that prevented it before the maintainer's geometry edit.

## Fix and preservation

- Retarget `left_elbow_flexion_stop` to
  `left_elbow_link_1_capsule_collision`, retaining the existing upper-arm
  capsule and `condim=1`.
- Remove only the now-unused `left_elbow_stop_collision` sphere.
- Keep all retained collider attributes/ownership, manual coordinates, body
  physics, native limits, contact masks and two existing wrist exclusions exact.
- Leave the right internal stop/pair, simplified model, articulated-hand model
  and all scene XML unchanged. Do not globally disable parent filtering.

The default now has **53 collision geoms**, **2 explicit pairs** and **2 body
exclusions**. XML-tree comparison against the starting snapshot confirms
that only the left pair target and the removed left sphere differ, apart
from XML comments/formatting. Other variant XML files retain exact bytes.

## Results

| Left elbow angle | Signed gap | Contact | Restoring torque |
|---|---:|---|---:|
| 0 | +5.500 mm | No | 0 Nm |
| −0.28 rad | +2.404 mm | No | 0 Nm |
| −0.40 rad | −0.776 mm | Yes | +0.649 Nm |
| −0.48 rad | −3.484 mm | Yes | +2.958 Nm |
| −0.52 rad | −5.008 mm | Yes | +4.163 Nm |

Contact onset is approximately **−0.374153 rad (−21.437°)**. At q=−0.48,
the contact force is **80.58 N**. Native angle limits are not active at that
interior pose, so resistance comes from contact. The onset differs from the
old internal sphere's −0.47 rad target because the actual hand-tuned capsule
surface now determines it. The right stop remains at approximately −0.47 rad.

Four 0.3 s gravity-disabled, uncontrolled folding probes from q=−0.3 rad at
−1/−3 rad/s generate contact and reverse motion before the native folded
limit. Minimum left angles were −0.387976/−0.408935 rad; right minima were
−0.484015/−0.506051 rad. The faster left probe later folds slightly again:
these compliant contacts are not rigid clamps or a stability guarantee.
All states stay finite without warnings.

Regression checks use the actual large left capsules, so a return to the
wrong proxy-only pair fails. Shoulder-yaw probes, reference clearance, the
unchanged right proxy and native stepping remain covered. Geometry guards
also respect manual near-zero coordinate cleanup (about 2e−12 compiled
quaternion difference) and the shortened left shaft.

`UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passes **23 test methods**:
2 directory/style and 21 native model methods. The minimized regression is:

```sh
.venv/bin/python -m unittest test.model_test.AstroP2VariantTests.test_left_overlapping_capsules_generate_actual_contact
```

Only local native verification was performed. MJX runtime, Workbench, URDF
compatibility and controllers remain deferred.
