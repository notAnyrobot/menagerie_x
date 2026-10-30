# Astro P2

Astro P2 descriptions with mesh and primitive collision editions.

## Menagerie entry points

| Edition | Internal DOF | Descriptions |
| --- | --- | --- |
| `30dof_primitive_collision` | 30 | [URDF](urdf/astro_p2_30dof_primitive_collision.urdf) · [source MJCF](mjcf/astro_p2_30dof_primitive_collision.xml) · [model](astro_p2_30dof_primitive_collision.xml) / [scene](scene.xml) |
| `30dof_mesh_collision` | 30 | [URDF](urdf/astro_p2_30dof_mesh_collision.urdf) · [source MJCF](mjcf/astro_p2_30dof_mesh_collision.xml) · [model](astro_p2_30dof_mesh_collision.xml) / [scene](scene_30dof_mesh_collision.xml) |
| `30dof_primitive_collision_halfway` | 30 | [source MJCF](mjcf/astro_p2_30dof_primitive_collision_halfway.xml) · [model](astro_p2_30dof_primitive_collision_halfway.xml) / [scene](scene_30dof_primitive_collision_halfway.xml) |

Mesh files live in `assets/`; `meshes/` is a relative compatibility link. Legacy source paths remain authoritative for the CLI, Workbench, and provenance hashes. Flat MJCF entry points and `scene*.xml` are maintained by `scripts/sync-menagerie.py`; scenes include the model and add presentation lighting and one ground plane. Where a source uses a zero-height robot datum, the floor is lowered by the catalog standing height so the original robot pose is preserved.

See [LICENSING.md](LICENSING.md) for asset-specific terms and unresolved provenance.
