# Astro P2 with Unitree Dex3-1 Hands Description (MJCF)

> [!IMPORTANT]
> Tested with MuJoCo 3.11.0, the version pinned by this repository.

## Changelog

Model history: [CHANGELOG.md](CHANGELOG.md).

## Overview

This sample combines the fixed-head Astro P2 body (29 DoFs) with official
left and right Unitree Dex3-1 hands (seven joints each). It retains vendor hand
sources from Unitree ROS revision `5994d4faef0a9cadd3287f8de0199a67eeb2a259`
and local assembly provenance in [SOURCE.json](SOURCE.json).

The palms use a sample attachment at the existing Astro hand frames. This
attachment has no fabricated adapter geometry or mass and is **not a verified
mechanical mount**.

<p float="left">
  <img src="astro_p2_43dof_dex3_1.png" alt="Astro P2 with Unitree Dex3-1 sample hands" width="400">
</p>

| Model | DoFs | Scene |
| --- | --- | --- |
| [astro_p2_43dof_dex3_1.xml](astro_p2_43dof_dex3_1.xml) | 43 | [scene.xml](scene.xml) |

DoF counts exclude the floating base. Open the scene to include the robot,
ground plane, and lighting. The images show native reference initialization,
without advancing simulation.

## MJCF derivation steps

1. Started from the retained [Astro 29-DoF body](../astro_p2_29dof/README.md) and pinned official Dex3-1 URDFs in `upstream/`.
2. Attached the palms at the existing hand frames using sample fixed joints, preserving vendor finger transforms, limits, and inertias.
3. Converted matching cylinder/sphere assemblies to native capsules and disabled inertia inference.
4. Applied the documented MJCF-only shin, torso, arm, pelvis, palm, and thumb collision refinements; retained the earlier URDF geometry separately.
5. Added the native `fist` keyframe. `scene.xml` includes the model and places a floor at `z=-0.75` without changing the robot datum.

## Model notes

The model has `nq=50`, `nv=49`, and no actuators or gains. The preview shows the
normal reference pose with open hands. Select the `fist` keyframe explicitly to
use the saved closure; native reference reset does not select it automatically.

Keep `meshes -> assets` beside the XML. Map joint arrays by name: the retained
application joint order differs from native MJCF tree order. Hand calibration,
retargeting, and hardware support are not supplied.

See [DERIVATION.md](DERIVATION.md) for the complete mounting assumptions, mass
accounting, joint order, historical build commands, validation records, and hand
images. [MJCF.md](MJCF.md) documents the later contact refinements and keyframe.
Rebuilding from URDF overwrites those MJCF-only edits.

## License

Unitree hand material retains [BSD-3-Clause terms](LICENSE.Unitree). The Astro
body's redistribution terms remain unresolved. [LICENSING.md](LICENSING.md)
explains this split; the Unitree license does not cover the body.
