# Astro P2 Description (MJCF)

> [!IMPORTANT]
> Tested with MuJoCo 3.11.0, the version pinned by this repository.

## Changelog

Model history: [CHANGELOG.md](CHANGELOG.md).

## Overview

This directory contains three 30-DoF Astro P2 descriptions with different
collision models: primitive, mesh, and the retained intermediate primitive
choice. Original MJCF and available URDF descriptions remain in `mjcf/` and
`urdf/`. Their complete public derivation history is not available.

<p float="left">
  <img src="astro_p2_30dof_primitive_collision.png" alt="Astro P2 with primitive collisions" width="400">
  <img src="astro_p2_30dof_mesh_collision.png" alt="Astro P2 with mesh collisions" width="400">
  <img src="astro_p2_30dof_primitive_collision_halfway.png" alt="Astro P2 intermediate primitive model" width="400">
</p>

| Model | DoFs | Scene |
| --- | --- | --- |
| [astro_p2_30dof_primitive_collision.xml](astro_p2_30dof_primitive_collision.xml) | 30 | [scene.xml](scene.xml) |
| [astro_p2_30dof_mesh_collision.xml](astro_p2_30dof_mesh_collision.xml) | 30 | [scene_30dof_mesh_collision.xml](scene_30dof_mesh_collision.xml) |
| [astro_p2_30dof_primitive_collision_halfway.xml](astro_p2_30dof_primitive_collision_halfway.xml) | 30 | [scene_30dof_primitive_collision_halfway.xml](scene_30dof_primitive_collision_halfway.xml) |

DoF counts exclude the floating base. Open the scene to include the robot,
ground plane, and lighting. The images show native reference initialization,
without advancing simulation.

## MJCF derivation steps

1. Retained the three existing MJCF collision choices and their original source snapshots.
2. Placed the maintained robot XML at the family root, using `assets/` for mesh dependencies.
3. Preserved each model's physical parameters and collision definitions; no actuators or new gains were added.
4. Added one scene per model. Each scene keeps the zero-height robot datum and places the floor at `z=-0.75`.

## Model notes

All three models have no actuators (`nu=0`). Primitive and mesh choices share
visual geometry, so their preview images look alike; their collision geometry
differs. The intermediate primitive model is retained as an existing choice,
without an additional fidelity claim.

Retained URDFs are available for the
[primitive](urdf/astro_p2_30dof_primitive_collision.urdf) and
[mesh](urdf/astro_p2_30dof_mesh_collision.urdf) descriptions.
Maintain root XML directly; nested MJCF files remain source evidence.

## License

No explicit redistribution license accompanies the retained Astro assets.
[LICENSING.md](LICENSING.md) records the unresolved terms and presentation-scene
attribution.
