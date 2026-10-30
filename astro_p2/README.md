# Astro P2

Astro P2 descriptions with mesh and primitive collision editions.

## Menagerie entry points

| Edition | Internal DOF | Descriptions |
| --- | --- | --- |
| `30dof_primitive_collision` | 30 | [URDF](urdf/astro_p2_30dof_primitive_collision.urdf) · [source snapshot](mjcf/astro_p2_30dof_primitive_collision.xml) · [model](astro_p2_30dof_primitive_collision.xml) / [scene](scene.xml) |
| `30dof_mesh_collision` | 30 | [URDF](urdf/astro_p2_30dof_mesh_collision.urdf) · [source snapshot](mjcf/astro_p2_30dof_mesh_collision.xml) · [model](astro_p2_30dof_mesh_collision.xml) / [scene](scene_30dof_mesh_collision.xml) |
| `30dof_primitive_collision_halfway` | 30 | [source snapshot](mjcf/astro_p2_30dof_primitive_collision_halfway.xml) · [model](astro_p2_30dof_primitive_collision_halfway.xml) / [scene](scene_30dof_primitive_collision_halfway.xml) |

The family-root model and scene XML are canonical and maintained directly.
Scenes include a sibling robot model and add presentation lighting and one
ground plane. Robot frames and physical descriptions are unchanged; the floor
is lowered where needed to preserve the original zero-height robot datum.
Meshes live in `assets/`, with the retained relative `meshes -> assets` alias.
Nested `mjcf/` imports, where present, are preserved source snapshots.
Workbench, URDF compatibility, and MJX are deferred; legacy application edits
may target those snapshots and do not update the canonical native XML.

See [LICENSING.md](LICENSING.md) for asset-specific terms and unresolved provenance.
