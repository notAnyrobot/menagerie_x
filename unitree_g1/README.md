# Unitree G1 Description (MJCF)

> [!IMPORTANT]
> Tested with MuJoCo 3.11.0, the version pinned by this repository.

## Changelog

Model history: [CHANGELOG.md](CHANGELOG.md).

## Overview

This directory contains the locally selected Unitree G1 models: the 29-joint
body with 14 hand joints, the 29-DoF box-feet model from ProtoMotions, and
MuJoCo Menagerie's 29-DoF model with 27 primitive collision geoms.
The official Unitree source is pinned at
`daadf41ee9afce8f90fdc09a98506012691fa122`; the ProtoMotions source is pinned at
`a6df301d312dc58ac40a4d994f4f1064728d854c`. Paths and hashes are recorded in the
[manifest](../manifest.json).

The retained Unitree and ProtoMotions descriptions preserve their original
controls and contacts. The primitive variant is an additional, byte-identical
copy of MuJoCo Menagerie's `g1_mjx.xml` and `scene_mjx.xml`, pinned to
`f3b6013629c7b94f8ee93fd977b161fa8350f9bc`; see its
[source and asset hashes](provenance/menagerie_mjx.json).

<p float="left">
  <img src="unitree_g1_29dof_with_hand_rev_1_0.png" alt="Unitree G1 with articulated hands" width="400">
  <img src="unitree_g1_29dof_box_feet.png" alt="Unitree G1 with box feet" width="400">
  <img src="g1_mjx.png" alt="Unitree G1 with primitive collisions" width="400">
</p>

| Model | DoFs | Scene |
| --- | --- | --- |
| [unitree_g1_29dof_with_hand_rev_1_0.xml](unitree_g1_29dof_with_hand_rev_1_0.xml) | 43 | [scene.xml](scene.xml) |
| [unitree_g1_29dof_box_feet.xml](unitree_g1_29dof_box_feet.xml) | 29 | [scene_29dof_box_feet.xml](scene_29dof_box_feet.xml) |
| [g1_mjx.xml](g1_mjx.xml) — primitive collisions | 29 | [scene_mjx.xml](scene_mjx.xml) |

DoF counts exclude the floating base. Open the scene to include the robot,
ground plane, and lighting. The retained-model images show native reference
initialization; the primitive-model image selects its `home` keyframe. No
simulation steps are taken for these images.

## MJCF derivation steps

1. Retained the official Unitree description and the ProtoMotions box-feet MJCF as local source snapshots under `mjcf/`.
2. Placed maintained native models at the family root and pointed mesh lookup at `assets/`.
3. Separated the world-level demonstration floor from the robot-only entry points while preserving robot dynamics and control definitions.
4. Added sibling scenes with a single ground plane at `z=0` and presentation lighting.
5. Added the pinned upstream primitive model and scene unchanged, including
   their position servos, numerical settings, explicit contact pairs and poses.
   Reused 33 matching mesh files and added the two exact uppercase rubber-hand
   filenames required by upstream; existing lowercase assets remain unchanged.

## Model notes

The hand model has 43 actuators (`nq=50`, `nv=49`); the box-feet model has 29
(`nq=36`, `nv=35`). Their existing torque controls and physical descriptions
remain unchanged.

The primitive variant also has `nq=36`, `nv=35`, and 29 actuators, but uses
**position targets in radians**, rather than the retained models' torque
controls. Its 27 collision geoms are 23 capsules, two spheres and two boxes;
35 visual mesh geoms retain the robot's appearance. The timestep is 0.004 s,
with upstream position gains of 75 (20 for ankles and wrists), velocity gains
of 2, and the original joint-specific armatures and solver settings.

Open **[scene_mjx.xml](scene_mjx.xml)** for the complete primitive configuration.
The robot XML disables automatic contacts and declares no contact pairs. Its
scene supplies **49 explicit pairs** (26 self-contact and 23 floor-contact
pairs), plus `home` and `knees_bent` keyframes with matching position targets.
Loading the robot XML alone does not reproduce those contacts or poses. Select
a keyframe explicitly; a normal reset uses the reference configuration.

This configuration matches the upstream MJX model, but here it is verified
with **native MuJoCo only**. MJX/JAX/Warp execution, throughput and backend
compatibility remain deferred and untested. No controller training or hardware
readiness is implied by native loading.

The official [URDF](urdf/unitree_g1_29dof_with_hand_rev_1_0.urdf) and a
[ProtoMotions retargeting URDF](urdf/for_retargeting/g1.urdf) remain as source
material. Maintain the root XML directly; nested MJCF files remain snapshots.
The primitive model does not add a URDF compatibility path.

## License

Unitree descriptions and meshes retain [BSD-3-Clause terms](LICENSE.Unitree).
The copied Menagerie primitive model, scene and source assets retain the
upstream [BSD-3-Clause notice](LICENSE.Menagerie).
ProtoMotions retargeting material retains [Apache-2.0 terms](LICENSE.ProtoMotions)
and its [notice](NOTICE.ProtoMotions). [LICENSING.md](LICENSING.md) explains which
terms apply to each part.
