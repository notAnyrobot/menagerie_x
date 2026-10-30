# Upper-arm collider ownership on shoulder-roll

The maintainer requested moving upper-arm colliders one body level higher to
avoid explicit elbow pairing, and chose to shorten the right shaft to match
the tuned left length. Work remains uncommitted on `codex/astro-palm-colliders`.

## Change and preservation

Both `{side}_upper_arm_capsule_collision` geoms now belong to
`{side}_shoulder_roll_link`, immediately above the shoulder-yaw body. Their
centerlines are `fromto="0 0 0 0 0 -0.124"` in the roll frame. This is the
left's former yaw-frame `0 0 0.114 0 0 -0.01` translated by the yaw body's
z=−0.114 m offset. The right shaft was shortened 50 mm as authorized; the
left's world-space occupied volume is unchanged through yaw rotation.

Radii remain 0.037 m left / 0.039 m right. No other retained collider attributes
are changed. Both explicit elbow pairs and the remaining right internal stop
sphere were removed. Default inventory is **52 collision geoms, zero explicit
pairs and two existing wrist body exclusions**. All 50 other retained shapes,
body/joint/inertia definitions, options, meshes and scene files are unchanged.
Both other Astro model XML files retain exact starting bytes.

Before the right shaft was shortened, moving it unchanged produced permanent
48.5 mm reference penetration against the forearm/hinge. The maintainer's
chosen shortening avoids this; the saved reference pose has no contacts.

## Automatic contact behavior

The relevant hierarchy is now the same on both sides:

```text
shoulder_roll_link   [upper-arm shaft]
└─ shoulder_yaw_link [real yaw joint]
   └─ elbow_link    [forearm capsules]
```

These collider bodies are grandparent/grandchild, so the immediate parent-child
collision filter does not suppress contact. All default collision shapes use
the existing (1, 1) contact masks. Their ordinary automatic contact settings
produce **condim=3 frictional contacts**, instead of the removed condim=1
frictionless pairs. No global filter was disabled and no new exclusions,
contact parameters or joint limits were introduced. Surface friction now
follows the roll body; geometric invariance under yaw does not preserve the
old yaw-body contact velocity or friction torque.

| Measurement | Left | Right |
|---|---:|---:|
| Reference clearance | 5.500 mm | 1.500 mm |
| Automatic contact onset | −0.374153 rad / −21.437° | −0.194564 rad / −11.148° |
| Penetration at q=−0.48 | 3.484 mm | 7.484 mm |
| Restoring torque at q=−0.48 | +2.727 Nm | +5.856 Nm |

The larger right radii make its contact begin earlier despite equal shaft
lengths. The native folded limit remains −0.52 rad (−29.79°); these are compliant
geometric stops, not an exact symmetric joint-limit calibration.

## Verification

- XML comparison permits only the two shaft ownership/coordinate changes,
  removal of the two pairs, and removal of the right proxy. All remaining
  tree structure/attributes match the pre-edit snapshot.
- Native probes at 51 combined shoulder poses per side verify frame conversion
  and yaw invariance. Left center positions differ by less than 3e−17 m from
  the previous model; radius, length and shaft-axis orientation are preserved.
- Regression verifies zero explicit pairs, no proxies, grandparent body
  ownership, reference clearance and generated contacts across yaw extremes.
- Four 0.3 s gravity-disabled folding probes at −1/−3 rad/s generate contact,
  reverse elbow velocity during the probe, stay within the native lower limit,
  and remain finite without warnings. Starting q is −0.3 left / −0.1 right,
  outside each side's contact region. Minimum angles were −0.384572/−0.402698
  left and −0.208294/−0.232772 right. The faster left probe later folds slightly
  again; a reversal is not a guarantee of settled or powered stability.
- `UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passes **23 methods**:
  2 layout/style and 21 model methods, including all native model/scene loads,
  standalone family copies and existing knee/contact regressions.

Default model SHA-256 before:
`677d68087455afb019922f99dc0ec4700437858c2a0e0846f37bfa5f36ae88b9`.
After:
`39b87c0ee5a43faccb8a783d9c0c7b72ddb2900d7756fc808e8e17269531f74c`.

MJX runtime, Workbench, URDF compatibility and controllers remain deferred.
No commit, merge or push was performed.
