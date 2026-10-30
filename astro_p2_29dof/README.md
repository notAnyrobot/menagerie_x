# Astro P2 29 DOF

Self-contained HHTools bundle with the head fixed at zero.

## Menagerie entry points

| Edition | Internal DOF | Descriptions |
| --- | --- | --- |
| `29dof_primitive_collision` | 29 | [URDF](astro_p2_29dof.urdf) |

Mesh files live in `assets/`; `meshes/` is a relative compatibility link. Legacy source paths remain authoritative for the CLI, Workbench, and provenance hashes. Flat MJCF entry points and `scene*.xml` are maintained by `scripts/sync-menagerie.py`; scenes include the model and add presentation lighting and one ground plane. Where a source uses a zero-height robot datum, the floor is lowered by the catalog standing height so the original robot pose is preserved.

The catalog still declares this edition URDF-only. The existing root-level `astro_p2_29dof.xml` is a separately maintained conversion described in [MJCF.md](MJCF.md); it is not silently promoted into the catalog. No default `scene.xml` is advertised for this family.

See [LICENSING.md](LICENSING.md) for asset-specific terms and unresolved provenance.
