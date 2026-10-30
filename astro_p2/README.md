# Astro P2 Description (MJCF)

> [!IMPORTANT]
> Tested with MuJoCo 3.11.0, the version pinned by this repository.

## Changelog

Model history: [CHANGELOG.md](CHANGELOG.md).

## Overview

This family contains one fixed-head Astro P2 body with two hand configurations,
following the sibling-model and scene pattern used by Unitree G1. Both variants
share the latest refined **29-DoF body**. The default uses fixed Unitree G1 rubber
hands; the alternative uses articulated Unitree Dex3-1 hands, adding 14 finger
DoFs for **43 total**.

<p float="left">
  <img src="astro_p2.png" alt="Astro P2 with G1 rubber hands" width="400">
  <img src="astro_p2_with_hands.png" alt="Astro P2 with Dex3-1 hands" width="400">
</p>

| Model | Body DoFs | Hand DoFs | Scene |
| --- | --- | --- | --- |
| [astro_p2.xml](astro_p2.xml) — G1 rubber hands | 29 | 0 | [scene.xml](scene.xml) |
| [astro_p2_with_hands.xml](astro_p2_with_hands.xml) — Dex3-1 | 29 | 14 | [scene_with_hands.xml](scene_with_hands.xml) |

DoF counts exclude the floating base. Previews show native reference
initialization without simulation stepping, with collision overlays hidden.

## MJCF derivation steps

1. Retained the latest refined Astro/Dex3-1 MJCF as the common body baseline,
   preserving non-hand geometry, masses, inertias, joints, and collision settings.
2. Consolidated model variants and shared meshes into this family directory,
   with each scene including its sibling robot XML and a floor at `z=-0.75`.
3. For the rubber-hand variant, replaced the Dex3-1 hand subtrees with actual
   left/right Unitree G1 rubber-hand meshes and their separate vendor inertial
   records. The rubber hands are fixed; all 29 body joints remain unchanged.
4. For the Dex3-1 variant, retained its 14 finger joints, collision refinements,
   and native `fist` keyframe. The renamed model retains its physical definition.
5. Preserved original conversion reports, URDFs, source XML, and licensing
   evidence under [provenance/](provenance/). Retired the former 30-DoF P2 choices.

## Model notes

Neither model supplies actuators or gains. The rubber model has `nq=36` and
`nv=35`; the Dex3-1 model has `nq=50` and `nv=49`. Select `fist` explicitly for
the saved Dex3-1 closure; ordinary reset uses the reference configuration.

The hand mounts are **sample attachments at the existing Astro hand frames**,
not verified mechanical adapters. Unitree hand-local geometry and inertias do
not establish Astro flange fit, wrist torque capacity, or hardware calibration.
No hand calibration, retargeting, or hardware control is supplied.

The rubber-hand adoption report records source mesh hashes, standalone hand
mass/inertia, transforms, and checks. The original G1 wrist inertia is composite
and is not transplanted into Astro. See the
[hand adoption investigation](../docs/research/astro-g1-rubber-hand-adoption.md).

[Original fixed-head conversion notes](provenance/29dof/MJCF.md) and
[Dex3-1 derivation records](provenance/dex3_1/DERIVATION.md) are historical source
evidence. Their old paths/build commands are not supported regeneration steps
for these maintained models. The [migration receipt](provenance/migration.json)
records source-file moves and hashes. Edit the root XML directly.

Workbench, URDF compatibility, and MJX remain deferred. Retained URDFs document
earlier configurations and are not advertised as equivalent to the new rubber
variant. Only the two root MJCF models are maintained native Astro P2 entries.

## License

Both hand configurations use Unitree material under
[BSD-3-Clause terms](LICENSE.Unitree). The Astro body's redistribution terms
remain unresolved. [LICENSING.md](LICENSING.md) identifies the source records and
license scope; the hand license does not cover the Astro body.
