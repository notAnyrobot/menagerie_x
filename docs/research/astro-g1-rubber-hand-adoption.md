# Adopt G1 rubber hands for the fixed-head Astro P2 family

Investigated on 2026-10-30 for the requested two-variant Astro P2 family:
29 body DoFs with fixed rubber hands, or the same body with two seven-joint
Dex3-1 hands (43 internal DoFs total). Workbench, URDF compatibility, and MJX
remain deferred.

## Primary sources

- [Existing refined Astro Dex model](https://github.com/notAnyrobot/menagerie_x/blob/fcbb3f222359df8b275fee1bc79d47721efdd2ec/astro_p2_43dof_dex3_1/astro_p2_43dof_dex3_1.xml): the latest maintained body, collision refinements, fixed hand frames, and `fist` keyframe before consolidation.
- [Official Unitree G1 29-DoF URDF](https://github.com/unitreerobotics/unitree_ros/blob/daadf41ee9afce8f90fdc09a98506012691fa122/robots/g1_description/g1_29dof.urdf): active fixed `left_hand_palm_joint` / `right_hand_palm_joint` and standalone `left_rubber_hand` / `right_rubber_hand` links, including separate hand mass, COM, and full inertia tensors. Downloaded exact bytes through the GitHub contents API; Git blob `49aeacd82072a6cb9847fac05ba59d9c35b0664e`.
- [Pinned MuJoCo Menagerie G1](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1.xml): the rubber-hand visual placement and sibling model/scene organization.
- [Pinned ProtoMotions G1 box-feet model](https://github.com/NVlabs/ProtoMotions/blob/a6df301d312dc58ac40a4d994f4f1064728d854c/protomotions/data/assets/mjcf/g1_bm_box_feet.xml): the retained local G1 rubber-hand collision approximation, a capsule in wrist coordinates.
- [Retained G1 licensing scope](../../unitree_g1/LICENSING.md): Unitree hand/mesh material retains BSD-3-Clause terms, separate from Astro body licensing and ProtoMotions retargeting material.

## Hand identity, shape, and dynamics

The actual local G1 rubber meshes match the pinned Menagerie meshes exactly:

| Mesh | SHA-256 |
| --- | --- |
| `left_rubber_hand.stl` | `cff2221a690fa69303f61fce68f2d155c1517b52efb6ca9262dd56e0bc6e70fe` |
| `right_rubber_hand.stl` | `99533b778bca6246144fa511bb9d4e555e075c641f2a0251e04372869cd99d67` |

These are fixed rubber hand meshes, not new sphere surrogates or articulated
finger joints. The official Unitree URDF declares each hand as **0.170 kg**.
Its COM, expressed in the hand frame, is
`(0.05361310808, -0.00295905240, 0.00215413091)` m on the left and the Y-mirrored
value on the right. The candidate retains the six full-tensor inertia values
from those standalone links verbatim. The exact source URDF and values are
recorded alongside the candidate source record.

The upstream Menagerie MJCF instead declares the rubber visual on a wrist body
whose inertial mass is `0.254576` kg. That is not a standalone hand mass: the
source URDF separately gives the wrist `0.08457647` kg and the hand `0.170` kg.
Transplanting the combined wrist inertial would replace Astro wrist dynamics.
The new Astro model therefore retains Astro wrist inertias and adds only the
source's separate hand inertial at each retained Astro hand frame.

## Attachment and collision ownership

The source G1 fixed joint places each rubber hand at `(0.0415, ±0.003, 0)` m in
the wrist-yaw frame, with identity rotation. Astro's existing hand frames are
`(0.067502, 0, 0)` m on the left and `(0.0675, 0, 0)` m on the right. Those Astro
frames remain unchanged; the source hand-local mesh and inertial use identity
orientation at them. This reuses the actual hand geometry and source dynamics
without importing G1 wrist/arm placement or controller parameters.

This is an explicit **sample attachment assumption**, not a verified mechanical
adapter. No adapter mesh or mass is fabricated. The left and right source meshes
and inertia signs retain their original chirality. Whole-body and close-up native
renders were inspected; both meshes extend distally from their Astro wrist frames.

The local G1 box-feet model uses a rubber-hand capsule with radius `0.05` m and
wrist-local endpoints `(0.05, 0, 0)` and `(0.1, 0, 0)`. The new hand-local
collision expresses this same source shape by subtracting the source G1 fixed
hand translation: X endpoints `0.0085` and `0.0585`, with Y `-0.003` on the left
and `+0.003` on the right. It then moves with the retained Astro hand frame.
This inherits the source approximation; it does not claim an exact enclosing
mesh hull. Visual meshes remain collision-disabled in group 1; the capsules
are in group 3. Astro wrist collision cylinders and other body collision geoms
are unchanged.

## Shared body and mass accounting

The refined Dex3-1 model supplies the common 29-DoF body. Its 14 finger joints
and 16 hand descendant bodies are removed for the rubber variant, while the two
existing fixed Astro hand frames remain. Only those hand subtrees change. No
body joint axes, ranges, inertias, non-hand geoms, or actuators are imported from
G1. The `fist` keyframe belongs only to the articulated hand variant and is
removed from the rubber variant because its 50-coordinate state is incompatible
with the 36-coordinate model.

| Configuration | Internal DoFs | `nq` | `nv` | `nu` | Mass (kg) |
| --- | --- | --- | --- | --- | --- |
| Refined Astro + Dex3-1 | 43 = 29 body + 14 fingers | 50 | 49 | 0 | 41.69666115 |
| Shared Astro body without either hand pair | 29 | — | — | 0 | 40.30356917 |
| Shared Astro body + G1 rubber hands | 29 | 36 | 35 | 0 | 40.64356917 |

Mass arithmetic: `41.69666115 - 2 × 0.69654599 + 2 × 0.170 = 40.64356917` kg.
Both native descriptions have no actuators; this change supplies no controller.
The older Astro 29 body had earlier collision refinements and sphere surrogates;
it remains provenance material rather than a third maintained variant.

## Candidate verification

The integrated model is [astro_p2/astro_p2.xml](../../astro_p2/astro_p2.xml).
The [hand source record](../../astro_p2/provenance/rubber_hands.json) records
source hashes, tensors, collision transformation, explicit mount assumptions,
counts, and validation. Exact downloaded source bytes and notices are retained
under [rubber_hand_sources/](../../astro_p2/provenance/rubber_hand_sources/).
The initial candidate was built separately in `/tmp/astro-rubber-variant/`
before integration into the shared family.

With native MuJoCo 3.11.0:

- Robot and floor scene compile; the robot has `nq=36`, `nv=35`, `nu=0`.
- Each steps for 0.1 seconds with finite positions/velocities and no warnings.
- Name-based comparisons against the refined Dex baseline exactly preserve
  mass/inertia/COM/frame parameters for **38 non-hand named bodies**, geometry,
  pose, contact masks, and friction for **93 non-hand named geoms**, and
  type/position/axis/range/force limits for **30 named joints including the free
  base**. Damping, armature, and friction arrays also match for all 35 body
  DoFs, along with joint stiffness, limits, and solver parameters.
- All 14 hand hinge joints are absent; separate source hand masses total
  `0.340` kg. Both hand frames retain their original Astro placement.
- Whole-body and each-hand native renders were visually inspected. Source XML
  was not modified by rendering.

These are loading, preservation, and short simulation checks, not hardware
mount validation, calibrated rubber deformation, or exhaustive contact testing.

## Recommended permanent native tests

1. Assert the maintained Astro family has exactly the rubber (29 body DoFs) and
   Dex3-1 (29 + 14 finger DoFs) entries, with no head joint or 30-DoF choice.
2. Match the common bodies and joints by name, comparing physical parameters,
   body collision definitions, and poses despite different hand subtree sizes.
3. Pin the two rubber mesh hashes, the official hand mass/COM/full tensor record,
   fixed hand frame transforms, capsule dimensions, and total mass arithmetic.
4. Assert the rubber model has no hand hinge joints or incompatible fist state;
   assert the Dex variant retains its finger limits and named fist keyframe.
5. Compile and step both native model/scene pairs, and load a copied `astro_p2`
   folder without accessing G1, old Astro family folders, or global application
   metadata. Hand meshes must live inside the consolidated Astro `assets/`.
