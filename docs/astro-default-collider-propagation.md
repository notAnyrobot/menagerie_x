# Astro default collider propagation

Historical receipt before subsequent maintainer wrist-collider removals and
[upper-arm consolidation](astro-upper-arm-refinement.md). Its 58-collider count
and retained wrist-roll/yaw housing statements describe that earlier snapshot.

The maintainer requested copying only tuned palms, shins, the upper pelvis
cylinder and the circled wrist capsules from `astro_p2_simplified.xml` into
`astro_p2.xml`. Work remains on `codex/astro-palm-colliders`; nothing was
committed, merged or pushed in this step.

## Geometry and scope

- Palms: radius 0.05 m; centerline x=0.10–0.15 m in the wrist-yaw frame.
  Existing hand-body ownership and geom names are preserved by subtracting
  the fixed hand translation. Left local x endpoints are 0.032498/0.082498 m;
  right endpoints are 0.0325/0.0825 m. Native world-space geometry matches
  the tuned source through combined wrist-roll/pitch/yaw poses.
- Shins: radius 0.053 m, `fromto="0.015 0 -0.24 0.015 0 0.003"`.
- Upper pelvis cylinder: radius 0.057 m, half-length 0.018 m, center z=0.10 m.
- Wrist-pitch capsules: replace each pair of transverse 0.03 m-radius shapes
  with one radius-0.045 m capsule, `fromto="0 0 0 0.044 0 0"`, on the existing
  wrist-pitch body. Retain the first geom name and remove the second geom.

Compared with the default model at `846b744`, exactly seven geoms changed
attributes and the two second wrist-pitch capsules were removed. The other
**51 colliders** retain exact XML attributes and ownership. This includes both
forearms, all shoulder/upper-arm shapes, wrist-roll shells, wrist-yaw cylinders,
feet and other torso/leg/head shapes. Default count is now **58 colliders**.
Non-geom XML structure, visual geoms, body/joint/inertial definitions, meshes
and scene XML are unchanged.

The entire source model XML, including the maintainer's newer right-forearm
radius of 0.045 m, and `astro_p2_with_hands.xml` remain byte-identical to their
snapshots at the start of this step. Source SHA-256:
`ca1172bd1e4e81cc48587bdb08cb1f1e99da4205fdd7b489d46e5a11f1669a12`.
Result default XML SHA-256:
`96c4ac875092737f3e1ac81eec90fc7f470da6c73eb98a90e4153177d50c7b17`.

## Contact behavior

Directly copying the merged wrist-pitch shape creates 11 mm reference-pose
overlap with each original forearm capsule. The source alternative does not
select this same-arm contact. The default retains automatic contacts and adds
only two body exclusions: left elbow/wrist-pitch and right elbow/wrist-pitch.
These exclude the redundant forearm/wrist overlap while preserving wrist-roll
and yaw colliders and all contacts of the wrist capsules with other bodies or
the floor. No global contact filter, masks or solver settings were changed.
Default model and scene both have zero contacts in the saved reference pose.

Knee regression verifies intended extension contact at −0.08 rad, no contact
at 0 or 2.3 rad, and the existing deep-flexion contact at 2.44 rad, on both
sides. The prior [knee measurements](astro-manual-collider-verification.md)
still describe the copied geometry: extension onset around −3.88°, versus the
−5.16° joint limit; existing flexion contact around 133.3°, versus the 139.8°
configured maximum. This does not remove that existing deep-flexion restriction.

The source alternative's newer right-forearm edit predates this propagation
and fails the old full wrist-shell-containment assertion. It leaves up to
3.82 mm sampled uncovered distance on the removed right wrist-roll shell.
The regression now bounds that known gap at 4 mm while retaining full left
containment. It does not inflate the manual geometry. The default model still
has both original wrist-roll shells; its forearms were not copied from the
source alternative.

## Verification

`UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passes **19 methods**:
2 directory/style checks and 17 model tests. These include native loading and
short stepping of all ten model/scene pairs, standalone family copies, copied
palm/wrist geometry through combined wrist poses, default reference contacts,
knee contacts, physical invariants and untouched default colliders checked
against the articulated-hand model. A separate XML comparison against the
pre-edit snapshot confirmed the exact seven-changed/two-removed scope.

Source hand meshes and vendor evidence remain unchanged. Provenance now
distinguishes original hand capsules from current default palm geometry.
Collider previews predate the manual geometry changes. MJX runtime, Workbench,
URDF compatibility and controllers remain deferred.
