# Atom P3

Atom P3 imported MJCF-only description.

## Menagerie entry points

| Edition | Internal DOF | Descriptions |
| --- | --- | --- |
| `27dof` | 27 | [source MJCF](mjcf/atom_p3_27dof.xml) · [model](atom_p3_27dof.xml) / [scene](scene.xml) |

Mesh files live in `assets/`; `meshes/` is a relative compatibility link. Legacy source paths remain authoritative for the CLI, Workbench, and provenance hashes. Flat MJCF entry points and `scene*.xml` are maintained by `scripts/sync-menagerie.py`; scenes include the model and add presentation lighting and one ground plane. Where a source uses a zero-height robot datum, the floor is lowered by the catalog standing height so the original robot pose is preserved.

This MJCF has no actuators (`nu=0`). Loading and short simulation checks do not establish a usable controller.

See [LICENSING.md](LICENSING.md) for asset-specific terms and unresolved provenance.
