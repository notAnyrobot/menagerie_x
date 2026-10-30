# SOMA-23

SOMA-23 free-base humanoid imported faithfully from ProtoMotions.

## Menagerie entry points

| Edition | Internal DOF | Descriptions |
| --- | --- | --- |
| `free_base` | 66 | [source MJCF](mjcf/soma23_free_base.xml) · [model](soma23_free_base.xml) / [scene](scene.xml) |

Mesh files live in `assets/`; `meshes/` is a relative compatibility link. Legacy source paths remain authoritative for the CLI, Workbench, and provenance hashes. Flat MJCF entry points and `scene*.xml` are maintained by `scripts/sync-menagerie.py`; scenes include the model and add presentation lighting and one ground plane. Where a source uses a zero-height robot datum, the floor is lowered by the catalog standing height so the original robot pose is preserved.

See [LICENSING.md](LICENSING.md) for asset-specific terms and unresolved provenance.
