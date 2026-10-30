# SOMA-23

SOMA-23 free-base humanoid imported faithfully from ProtoMotions.

## Menagerie entry points

| Edition | Internal DOF | Descriptions |
| --- | --- | --- |
| `free_base` | 66 | [source snapshot](mjcf/soma23_free_base.xml) · [model](soma23_free_base.xml) / [scene](scene.xml) |

The family-root model and scene XML are canonical and maintained directly.
Scenes include a sibling robot model and add presentation lighting and one
ground plane. Robot frames and physical descriptions are unchanged; the floor
is lowered where needed to preserve the original zero-height robot datum.
Meshes live in `assets/`, with the retained relative `meshes -> assets` alias.
Nested `mjcf/` imports, where present, are preserved source snapshots.
Workbench, URDF compatibility, and MJX are deferred; legacy application edits
may target those snapshots and do not update the canonical native XML.

See [LICENSING.md](LICENSING.md) for asset-specific terms and unresolved provenance.
