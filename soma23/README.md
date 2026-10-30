# SOMA-23 Description (MJCF)

> [!IMPORTANT]
> Tested with MuJoCo 3.11.0, the version pinned by this repository.

## Changelog

Model history: [CHANGELOG.md](CHANGELOG.md).

## Overview

This directory contains the free-base SOMA-23 humanoid from
[NVIDIA ProtoMotions](https://github.com/NVlabs/ProtoMotions/tree/a6df301d312dc58ac40a4d994f4f1064728d854c),
pinned at `a6df301d312dc58ac40a4d994f4f1064728d854c`. The source is
`protomotions/data/assets/mjcf/soma23_humanoid.xml`; its revision and SHA-256 are
retained in the [manifest](../manifest.json).

<p float="left">
  <img src="soma23_free_base.png" alt="SOMA-23 primitive humanoid" width="400">
</p>

| Model | DoFs | Scene |
| --- | --- | --- |
| [soma23_free_base.xml](soma23_free_base.xml) | 66 | [scene.xml](scene.xml) |

DoF counts exclude the floating base. Open the scene to include the robot,
ground plane, and lighting. The images show native reference initialization,
without advancing simulation.

## MJCF derivation steps

1. Imported the pinned ProtoMotions SOMA-23 MJCF and retained it as [source evidence](mjcf/soma23_free_base.xml).
2. Placed the directly maintained model at the family root, preserving its primitive geometry, free base, joints, and actuators.
3. Added `scene.xml` with lighting and a floor at `z=-1`, retaining the source robot's coordinate datum.

## Model notes

The model has 66 motor-actuated internal DoFs (`nq=73`, `nv=72`, `nu=66`).
It uses primitive geometry, with no external mesh dependency. The source name
SOMA-23 is retained; it does not indicate this model's joint count.

No URDF is supplied. Imported actuator parameters are retained without claiming
a tuned controller. Maintain the root XML directly; the nested MJCF is a source
snapshot.

## License

ProtoMotions material retains its [Apache-2.0 license](LICENSE.ProtoMotions).
See [LICENSING.md](LICENSING.md) for scope and scene attribution.
