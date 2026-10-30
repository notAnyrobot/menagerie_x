# Astro P1

Astro P1 robot descriptions.

## Menagerie entry points

| Edition | Internal DOF | Descriptions |
| --- | --- | --- |
| `30dof` | 30 | [URDF](urdf/astro_p1_30dof.urdf) · [source snapshot](mjcf/astro_p1_30dof.xml) · [model](astro_p1_30dof.xml) / [scene](scene.xml) |
| `27dof` | 27 | [URDF](urdf/astro_p1_27dof.urdf) · [source snapshot](mjcf/astro_p1_27dof.xml) · [model](astro_p1_27dof.xml) / [scene](scene_27dof.xml) |
| `with_racket` | 30 | [URDF](urdf/astro_p1_with_racket.urdf) |

The family-root model and scene XML are canonical and maintained directly.
Scenes include a sibling robot model and add presentation lighting and one
ground plane. Robot frames and physical descriptions are unchanged; the floor
is lowered where needed to preserve the original zero-height robot datum.
Meshes live in `assets/`, with the retained relative `meshes -> assets` alias.
Nested `mjcf/` imports, where present, are preserved source snapshots.
Workbench, URDF compatibility, and MJX are deferred; legacy application edits
may target those snapshots and do not update the canonical native XML.

See [LICENSING.md](LICENSING.md) for asset-specific terms and unresolved provenance.
