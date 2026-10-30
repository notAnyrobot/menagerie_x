# Atom P3

Atom P3 imported MJCF-only description.

## Menagerie entry points

| Edition | Internal DOF | Descriptions |
| --- | --- | --- |
| `27dof` | 27 | [source snapshot](mjcf/atom_p3_27dof.xml) · [model](atom_p3_27dof.xml) / [scene](scene.xml) |

The family-root model and scene XML are canonical and maintained directly.
Scenes include a sibling robot model and add presentation lighting and one
ground plane. Robot frames and physical descriptions are unchanged; the floor
is lowered where needed to preserve the original zero-height robot datum.
Meshes live in `assets/`, with the retained relative `meshes -> assets` alias.
Nested `mjcf/` imports, where present, are preserved source snapshots.
Workbench, URDF compatibility, and MJX are deferred; legacy application edits
may target those snapshots and do not update the canonical native XML.

This MJCF has no actuators (`nu=0`). Loading and short simulation checks do not establish a usable controller.

See [LICENSING.md](LICENSING.md) for asset-specific terms and unresolved provenance.
