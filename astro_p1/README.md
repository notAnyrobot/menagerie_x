# Astro P1

Astro P1 robot descriptions.

## Menagerie entry points

| Edition | Internal DOF | Descriptions |
| --- | --- | --- |
| `30dof` | 30 | [URDF](urdf/astro_p1_30dof.urdf) · [source MJCF](mjcf/astro_p1_30dof.xml) · [model](astro_p1_30dof.xml) / [scene](scene.xml) |
| `27dof` | 27 | [URDF](urdf/astro_p1_27dof.urdf) · [source MJCF](mjcf/astro_p1_27dof.xml) · [model](astro_p1_27dof.xml) / [scene](scene_27dof.xml) |
| `with_racket` | 30 | [URDF](urdf/astro_p1_with_racket.urdf) |

Mesh files live in `assets/`; `meshes/` is a relative compatibility link. Legacy source paths remain authoritative for the CLI, Workbench, and provenance hashes. Flat MJCF entry points and `scene*.xml` are maintained by `scripts/sync-menagerie.py`; scenes include the model and add presentation lighting and one ground plane. Where a source uses a zero-height robot datum, the floor is lowered by the catalog standing height so the original robot pose is preserved.

See [LICENSING.md](LICENSING.md) for asset-specific terms and unresolved provenance.
