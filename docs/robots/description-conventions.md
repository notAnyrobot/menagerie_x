# Menagerie robot-description conventions

## Scope

This contract defines the canonical kinematic hierarchy and naming conventions
shared by Menagerie URDF and MJCF descriptions. It applies to authored
cross-format robot descriptions; robot-specific internal limb and head
structure remains outside this contract.

## Canonical kinematic hierarchy

`pelvis` is the canonical root. Floating-base behavior is not a parent link or
body in the robot hierarchy.

- The left leg, right leg, and waist branch from `pelvis`.
- The waist leads to the torso: `waist` → `torso`.
- The left arm, right arm, and head branch from the torso.

```text
pelvis
├── left leg
├── right leg
└── waist
    └── torso
        ├── left arm
        ├── right arm
        └── head
```

The internal structure of each leg, arm, and head is robot-specific. URDF and
MJCF must express this same canonical attachment hierarchy.

## Naming conventions

### Joint and link naming

Joint and link names use lowercase snake case:

```text
{side_}{body_part}{_motion}_{entity}
```

- `side_` is `left_` or `right_` for bilateral parts and is omitted for a
  centerline part.
- `motion` is optional and, when present, is `pitch`, `roll`, or `yaw`.
- `entity` is `joint` or `link`.

Examples: `left_hip_pitch_joint`, `right_knee_joint`, `waist_yaw_joint`,
`left_wrist_roll_link`, and `torso_link`. `pelvis` and `torso_link` are valid
concise exceptions. Mesh files follow their canonical link names. Hand naming
is deferred.

### Primitive collision-shape naming

Primitive collision shapes use:

```text
{side_}{semantic_part}_{primitive}_collision_{ordinal}
```

- `side_` is optional for centerline parts.
- `semantic_part` states what the shape represents.
- `primitive` is `capsule`, `cylinder`, `box`, or `sphere`.
- `ordinal` distinguishes shapes with the same semantic part and primitive.

Examples: `left_foot_capsule_collision_1`,
`right_foot_capsule_collision_2`, and `pelvis_cylinder_collision_1`. A
collision name gives the shape its semantic identity; the URDF/MJCF hierarchy
defines its owning attachment link or body.
