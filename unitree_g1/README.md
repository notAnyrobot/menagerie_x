# Unitree G1

Official Unitree G1 description with 29 body joints and 14 hand joints.

## Menagerie entry points

| Edition | Internal DOF | Descriptions |
| --- | --- | --- |
| `29dof_with_hand_rev_1_0` | 43 | [URDF](urdf/unitree_g1_29dof_with_hand_rev_1_0.urdf) · [source snapshot](mjcf/unitree_g1_29dof_with_hand_rev_1_0.xml) · [model](unitree_g1_29dof_with_hand_rev_1_0.xml) / [scene](scene.xml) |
| `29dof_box_feet` | 29 | [source snapshot](mjcf/unitree_g1_29dof_box_feet.xml) · [model](unitree_g1_29dof_box_feet.xml) / [scene](scene_29dof_box_feet.xml) |

The family-root model and scene XML are canonical and maintained directly.
Scenes include a sibling robot model and add presentation lighting and one
ground plane. Robot frames and physical descriptions are unchanged; the floor
is lowered where needed to preserve the original zero-height robot datum.
Meshes live in `assets/`, with the retained relative `meshes -> assets` alias.
Nested `mjcf/` imports, where present, are preserved source snapshots.
Workbench, URDF compatibility, and MJX are deferred; legacy application edits
may target those snapshots and do not update the canonical native XML.

See [LICENSING.md](LICENSING.md) for asset-specific terms and unresolved provenance.
