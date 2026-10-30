# Default Astro upper-arm shaft consolidation

Historical consolidation receipt. The later
[elbow contact stops](astro-elbow-contact-stop.md) restore near-limit
forearm/upper-arm contact through two selected pairs without splitting the shafts.

The maintainer identified overlapping axial upper-arm capsules while manually
tuning `astro_p2.xml`. This step changes only that default model's upper-arm
shafts. Work remains uncommitted on `codex/astro-palm-colliders`.

## Findings and change

Each side had a proximal capsule on the shoulder-roll body, radius 0.037 m
and centerline z=−0.12 to 0, plus a distal capsule on the yaw body, centerline
z=−0.015 to −0.060 m. The yaw body is offset by z=−0.114 m, so the second
centerline is z=−0.129 to −0.174 m in the roll frame. Their round caps overlap.
They are on different articulated bodies, but both shafts are axisymmetric
about the shoulder-yaw axis: their geometric union is invariant under yaw.

The existing `{side}_upper_arm_capsule_collision` now spans
`fromto="0 0 0.114 0 0 -0.06"` on the shoulder-yaw body. It contains both old
shafts using radius 0.037 m left and 0.039 m right, preserving the maintainer's
larger right-arm tuning. The two redundant
`{side}_shoulder_roll_link_1_capsule_collision` geoms are removed. The separate
transverse shoulder-housing capsules remain unchanged; merging those would
require a broader envelope.

Using the larger radius expands each side's previously narrower shaft segment
by 2 mm. Filling the join also smooths its envelope; this is a conservative
approximation rather than an exact equal-volume replacement.

## Preservation and contact tradeoff

Snapshot comparison confirms **two shaft geoms modified, two removed, and all
50 other current colliders unchanged**. Total count falls **54 → 52**. All
non-target XML structure, visual meshes, physics, joints, options and contact
exclusions are unchanged. The maintainer's recent removal of wrist-roll/yaw
colliders and right-forearm radius change were already present at the start
and are preserved. The simplified and articulated-hand model XML files are
byte-identical to their starting snapshots.

The consolidated shaft is attached to the yaw body so the normal adjacent
elbow contact filter applies. This avoids permanent contact between the
extended shaft and the elbow; no new contact exclusions or masks are added.
It also removes the old proximal-shaft/forearm contacts near negative elbow
limits: the previous left model contacted at −0.52 rad (1.54 mm penetration),
and the previous right model contacted at −0.45 rad (0.81 mm penetration) and
−0.52 rad (3.54 mm penetration). Native elbow ranges remain −0.52 to 1.66 rad
and limits stay enabled, but the previous geometry-based elbow stop is no
longer reproduced. Friction on the unified shaft follows the yaw body;
geometric yaw invariance does not guarantee identical friction torques.

## Verification

- Native surface sampling of both original shafts at **153 shoulder poses
  per side** (pitch/roll extrema and 17 yaw angles) confirms containment by the
  merged shaft, with worst numerical outside distance below 2e−16 m.
- The regression checks continuous centerline position and orientation under
  combined shoulder motion, retained housing geoms, asymmetric radii and
  enabled native elbow limits.
- Default model has no contacts in its reference pose. Twelve additional
  gravity-on 0.1 s step probes at individual shoulder-joint limits remain
  finite without MuJoCo warnings. These passive checks do not validate a
  powered controller or all possible self-contact poses.
- `UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passes **20 test methods**:
  2 directory/style checks and 18 model checks, including all ten native
  model/scene pairs, standalone family loading and knee regression checks.
- Existing geometry guards were updated for the maintainer's right forearm
  and wrist removals; original wrist-roll shell evidence is now read from
  the untouched articulated-hand variant instead of the mutable default.
- A native collision preview was rendered and inspected without stepping.
  No meshes or saved material values were edited.

Default XML SHA-256 before:
`e880ad91c04c04fc041d447fd927e331c34d1e8dae432acc84a454943c82b3df`.
After:
`0347731e4c0c99cf8c9551cc6a22a6a2712bf74a489fdada7ca480d65ac21832`.

MJX runtime, Workbench, URDF compatibility and controllers remain deferred.
No commit, merge or push was performed.
