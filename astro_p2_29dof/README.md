# Astro P2 29 DOF

Self-contained HHTools bundle with the head fixed at zero.

## Menagerie entry points

| Edition | Internal DOF | Descriptions |
| --- | --- | --- |
| `29dof_primitive_collision` | 29 | [model](astro_p2_29dof.xml) / [scene](scene.xml) · retained [URDF](astro_p2_29dof.urdf) |

The family-root model and scene XML are canonical and maintained directly.
Scenes include a sibling robot model and add presentation lighting and one
ground plane. Robot frames and physical descriptions are unchanged; the floor
is lowered where needed to preserve the original zero-height robot datum.
Meshes live in `assets/`, with the retained relative `meshes -> assets` alias.
Nested `mjcf/` imports, where present, are preserved source snapshots.
Workbench, URDF compatibility, and MJX are deferred; legacy application edits
may target those snapshots and do not update the canonical native XML.

The native catalog now includes the existing `astro_p2_29dof.xml` conversion
and a scene with a floor at `z=-0.75`. The robot's root pose is unchanged. This
model has no actuators. The legacy application manifest still declares its
edition URDF-only; that application migration is deferred. See [MJCF.md](MJCF.md)
for conversion history and retained provenance.

See [LICENSING.md](LICENSING.md) for asset-specific terms and unresolved provenance.
