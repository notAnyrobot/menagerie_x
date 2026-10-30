# Astro P2 29 DoF Description (MJCF)

> [!IMPORTANT]
> Tested with MuJoCo 3.11.0, the version pinned by this repository.

## Changelog

Model history: [CHANGELOG.md](CHANGELOG.md).

## Overview

This directory contains the fixed-head Astro P2 conversion retained in the
HHTools bundle. The head is fixed at zero yaw while its geometry and inertia
remain present. [SOURCE.json](SOURCE.json) records the baseline revision and
local changes.

<p float="left">
  <img src="astro_p2_29dof.png" alt="Astro P2 with the head fixed at zero" width="400">
</p>

| Model | DoFs | Scene |
| --- | --- | --- |
| [astro_p2_29dof.xml](astro_p2_29dof.xml) | 29 | [scene.xml](scene.xml) |

DoF counts exclude the floating base. Open the scene to include the robot,
ground plane, and lighting. The images show native reference initialization,
without advancing simulation.

## MJCF derivation steps

1. Derived the fixed-head [URDF](astro_p2_29dof.urdf) from the Astro P2 primitive-collision description; retained the source record in `SOURCE.json`.
2. Converted the URDF to MJCF while preserving explicit inertias and named fixed frames, with inertia inference disabled.
3. Replaced 39 matching cylinder-and-end-sphere assemblies with native capsule geoms; kept the remaining primitive shapes.
4. Retained the root XML as a directly maintained model. Added `scene.xml` with a floor at `z=-0.75`, preserving the robot's zero-height datum.

## Model notes

This free-base model has `nq=36`, `nv=35`, and no actuators. Visuals are in
group 1; primitive collisions are in group 3. Keep the relative
`meshes -> assets` link alongside the XML.

[MJCF.md](MJCF.md) describes the conversion, foot shapes, checks, and historical
conversion command. Re-running that command overwrites the maintained MJCF.
`robot.yaml` is retained as HHTools source material. Native use does not require
it or the legacy application manifest, which still lists this edition as
URDF-only.

## License

The Astro assets have no bundled explicit redistribution license.
See [LICENSING.md](LICENSING.md) and [SOURCE.json](SOURCE.json).
