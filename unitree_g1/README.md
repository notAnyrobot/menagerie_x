# Unitree G1 Description (MJCF)

> [!IMPORTANT]
> Tested with MuJoCo 3.11.0, the version pinned by this repository.

## Changelog

Model history: [CHANGELOG.md](CHANGELOG.md).

## Overview

This directory contains the locally selected Unitree G1 models: the 29-joint
body with 14 hand joints, and the 29-DoF box-feet model from ProtoMotions.
The official Unitree source is pinned at
`daadf41ee9afce8f90fdc09a98506012691fa122`; the ProtoMotions source is pinned at
`a6df301d312dc58ac40a4d994f4f1064728d854c`. Paths and hashes are recorded in the
[manifest](../manifest.json).

These are the retained Menagerie X descriptions, organized using MuJoCo
Menagerie's conventions. They have not been replaced by upstream Menagerie's
G1 model, gains, or keyframes.

<p float="left">
  <img src="unitree_g1_29dof_with_hand_rev_1_0.png" alt="Unitree G1 with articulated hands" width="400">
  <img src="unitree_g1_29dof_box_feet.png" alt="Unitree G1 with box feet" width="400">
</p>

| Model | DoFs | Scene |
| --- | --- | --- |
| [unitree_g1_29dof_with_hand_rev_1_0.xml](unitree_g1_29dof_with_hand_rev_1_0.xml) | 43 | [scene.xml](scene.xml) |
| [unitree_g1_29dof_box_feet.xml](unitree_g1_29dof_box_feet.xml) | 29 | [scene_29dof_box_feet.xml](scene_29dof_box_feet.xml) |

DoF counts exclude the floating base. Open the scene to include the robot,
ground plane, and lighting. The images show native reference initialization,
without advancing simulation.

## MJCF derivation steps

1. Retained the official Unitree description and the ProtoMotions box-feet MJCF as local source snapshots under `mjcf/`.
2. Placed maintained native models at the family root and pointed mesh lookup at `assets/`.
3. Separated the world-level demonstration floor from the robot-only entry points while preserving robot dynamics and control definitions.
4. Added sibling scenes with a single ground plane at `z=0` and presentation lighting.

## Model notes

The hand model has 43 actuators (`nq=50`, `nv=49`); the box-feet model has 29
(`nq=36`, `nv=35`). Existing gains are retained. No new standing keyframe or
controller tuning is introduced.

The official [URDF](urdf/unitree_g1_29dof_with_hand_rev_1_0.urdf) and a
[ProtoMotions retargeting URDF](urdf/for_retargeting/g1.urdf) remain as source
material. Maintain the root XML directly; nested MJCF files remain snapshots.
MJX compatibility is deferred.

## License

Unitree descriptions and meshes retain [BSD-3-Clause terms](LICENSE.Unitree).
ProtoMotions retargeting material retains [Apache-2.0 terms](LICENSE.ProtoMotions)
and its [notice](NOTICE.ProtoMotions). [LICENSING.md](LICENSING.md) explains which
terms apply to each part.
