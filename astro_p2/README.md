# Astro P2 Description (MJCF)

> [!IMPORTANT]
> Tested with MuJoCo 3.11.0, the version pinned by this repository.

## Changelog

Model history: [CHANGELOG.md](CHANGELOG.md).

## Overview

This family contains one fixed-head Astro P2 body with two hand configurations,
following the sibling-model and scene pattern used by Unitree G1. Both variants
share the latest refined **29-DoF body**. The default uses its original native rubber
hands; the alternative uses articulated Unitree Dex3-1 hands, adding 14 finger
DoFs for **43 total**.

<p float="left">
  <img src="astro_p2.png" alt="Astro P2 with native rubber hands" width="400">
  <img src="astro_p2_with_hands.png" alt="Astro P2 with Dex3-1 hands" width="400">
</p>

| Model | Body DoFs | Hand DoFs | Scene |
| --- | --- | --- | --- |
| [astro_p2.xml](astro_p2.xml) — Native Astro rubber hands | 29 | 0 | [scene.xml](scene.xml) |
| [astro_p2_with_hands.xml](astro_p2_with_hands.xml) — Dex3-1 | 29 | 14 | [scene_with_hands.xml](scene_with_hands.xml) |

DoF counts exclude the floating base. Previews show native reference
initialization without simulation stepping, with collision overlays hidden.

## MJCF derivation steps

1. Retained the latest refined Astro/Dex3-1 MJCF as the common body baseline,
   preserving non-hand geometry, masses, inertias, joints, and collision settings.
2. Consolidated model variants and shared meshes into this family directory,
   with each scene including its sibling robot XML and a floor at `z=-0.75`.
3. For the rubber-hand variant, restored the original Astro left/right hand
   meshes, fixed-joint transforms, masses, and inertia tensors from the retained
   source revision. Restored the original hand collision cylinders/end spheres
   as equivalent native capsules. All 29 body joints and refined wrist housing
   collisions remain unchanged. The earlier G1 hand trial was superseded.
4. For the Dex3-1 variant, retained its 14 finger joints, collision refinements,
   and native `fist` keyframe. The renamed model retains its physical definition.
5. Preserved original conversion reports, URDFs, source XML, and licensing
   evidence under [provenance/](provenance/). Retired the former 30-DoF P2 choices.

## Model notes

Neither model supplies actuators or gains. The rubber model has `nq=36` and
`nv=35`; the Dex3-1 model has `nq=50` and `nv=49`. Select `fist` explicitly for
the saved Dex3-1 closure; ordinary reset uses the reference configuration.

The native rubber hands use the original Astro hand frames and source inertias.
The Dex3-1 variant still uses **sample attachments**, not verified mechanical
adapters. No hand calibration, retargeting, or hardware control is supplied.

The native rubber-hand model weighs **40.58255359 kg**. Its source mesh hashes,
hand inertias, transforms, and capsule conversion are recorded in
[provenance/rubber_hands.json](provenance/rubber_hands.json). See the
[native hand restoration record](../docs/astro-native-hand-restoration.md).
The original mesh hands are restored, rather than the 54 mm sphere stand-ins
used in an earlier fixed-head conversion.

[Original fixed-head conversion notes](provenance/29dof/MJCF.md) and
[Dex3-1 derivation records](provenance/dex3_1/DERIVATION.md) are historical source
evidence. Their old paths/build commands are not supported regeneration steps
for these maintained models. The [migration receipt](provenance/migration.json)
records source-file moves and hashes. Edit the root XML directly.

Workbench, URDF compatibility, and MJX remain deferred. Retained URDFs document
earlier configurations and are not advertised as equivalent to the new rubber
variant. Only the two root MJCF models are maintained native Astro P2 entries.

## License

The native Astro body and rubber-hand redistribution terms remain unresolved.
Dex3-1 hand material retains [BSD-3-Clause terms](LICENSE.Unitree). [LICENSING.md](LICENSING.md) identifies the source records and
license scope; the hand license does not cover the Astro body.
