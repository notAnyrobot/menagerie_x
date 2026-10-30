# Unitree G1

Official Unitree G1 description with 29 body joints and 14 hand joints.

## Menagerie entry points

| Edition | Internal DOF | Descriptions |
| --- | --- | --- |
| `29dof_with_hand_rev_1_0` | 43 | [URDF](urdf/unitree_g1_29dof_with_hand_rev_1_0.urdf) · [source MJCF](mjcf/unitree_g1_29dof_with_hand_rev_1_0.xml) · [model](unitree_g1_29dof_with_hand_rev_1_0.xml) / [scene](scene.xml) |
| `29dof_box_feet` | 29 | [source MJCF](mjcf/unitree_g1_29dof_box_feet.xml) · [model](unitree_g1_29dof_box_feet.xml) / [scene](scene_29dof_box_feet.xml) |

Mesh files live in `assets/`; `meshes/` is a relative compatibility link. Legacy source paths remain authoritative for the CLI, Workbench, and provenance hashes. Flat MJCF entry points and `scene*.xml` are maintained by `scripts/sync-menagerie.py`; scenes include the model and add presentation lighting and one ground plane. Where a source uses a zero-height robot datum, the floor is lowered by the catalog standing height so the original robot pose is preserved.

See [LICENSING.md](LICENSING.md) for asset-specific terms and unresolved provenance.
