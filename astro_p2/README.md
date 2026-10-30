# Astro P2 Description (MJCF)

> [!IMPORTANT]
> Tested with MuJoCo 3.11.0, the version pinned by this repository.

## Changelog

Model history: [CHANGELOG.md](CHANGELOG.md).

## Overview

This family contains one fixed-head Astro P2 body with two hand configurations
and an additional simplified-collision variant of the default model, following
the sibling-model and scene pattern used by Unitree G1. All variants share the
latest refined **29-DoF body**. The default Astro P2 model has 29
DoFs; the articulated Unitree Dex3-1 alternative adds 14 finger DoFs for
**43 total**. The articulated configuration is labeled **Astro P2 with hands**;
its Dex3-1 visual meshes use silver coloring to match the Astro body.

<p float="left">
  <img src="astro_p2.png" alt="Astro P2" width="400">
  <img src="astro_p2_with_hands.png" alt="Astro P2 with hands" width="400">
  <img src="astro_p2_simplified.png" alt="Astro P2 with simplified collisions" width="400">
</p>

| Model | Body DoFs | Hand DoFs | Scene |
| --- | --- | --- | --- |
| [astro_p2.xml](astro_p2.xml) — Astro P2 | 29 | 0 | [scene.xml](scene.xml) |
| [astro_p2_with_hands.xml](astro_p2_with_hands.xml) — Astro P2 with hands | 29 | 14 | [scene_with_hands.xml](scene_with_hands.xml) |
| [astro_p2_simplified.xml](astro_p2_simplified.xml) — Astro P2 with simplified collisions | 29 | 0 | [scene_simplified.xml](scene_simplified.xml) |

DoF counts exclude the floating base. Previews show native reference
initialization without simulation stepping, with collision overlays hidden.

## MJCF derivation steps

1. Retained the latest refined Astro/Dex3-1 MJCF as the common body baseline,
   preserving non-hand geometry, masses, inertias, joints, and collision settings.
2. Consolidated model variants and shared meshes into this family directory,
   with each scene including its sibling robot XML and a floor at `z=-0.75`.
3. For the default model, restored the original Astro left/right hand
   meshes, fixed-joint transforms, masses, and inertia tensors from the retained
   source revision. Restored the original hand collision cylinders/end spheres
   as equivalent native capsules. All 29 body joints and refined wrist housing
   collisions remain unchanged. The earlier G1 hand trial was superseded.
4. For the Dex3-1 variant, retained its 14 finger joints, collision refinements,
   and native `fist` keyframe. The renamed model retains its physical definition.
5. Preserved original conversion reports, URDFs, source XML, and licensing
   evidence under [provenance/](provenance/). Retired the former 30-DoF P2 choices.
6. Added a separate default-hand collision approximation inspired by Menagerie's
   G1 MJX contact design. Retained Astro's body, visuals, mass/inertias, joints,
   passive dynamics and coordinate datum; adapted primitive dimensions to Astro.
   Neither existing variant was replaced or retuned.

## Model notes

None of these models supplies actuators or gains. Astro P2 and the simplified
variant have `nq=36` and `nv=35`; the Dex3-1 model has `nq=50` and `nv=49`.
Select `fist` explicitly for the saved Dex3-1 closure; ordinary reset uses the
reference configuration.

The Dex3-1 variant still uses **sample attachments**, not verified mechanical
adapters. No hand calibration, retargeting, or hardware control is supplied.

Astro P2 weighs **40.58255359 kg**. Its source mesh hashes,
hand inertias, transforms, and capsule conversion are recorded in
[provenance/rubber_hands.json](provenance/rubber_hands.json). See the
[model restoration record](../docs/astro-native-hand-restoration.md).

## Simplified collision configuration

**Astro P2 with simplified collisions** reduces the default model's 60 collision
geoms to **27 primitives: 23 capsules, two spheres and two boxes**, while retaining
all 37 visual mesh geoms and the same fixed-head 29-joint body. It uses Astro's
original fixed hands; no simplified articulated-hand version is introduced.
Astro-specific collider dimensions and source hashes are recorded in
[provenance/simplified_collisions.json](provenance/simplified_collisions.json).
The simplified model retains the default model's mass of **40.58255359 kg**,
zero actuators, 0.002 s timestep and Euler integrator. No G1 controller, gains,
solver retuning or standing keyframe is copied.

Open **[scene_simplified.xml](scene_simplified.xml)** for the complete setup.
The robot XML disables automatic contacts and has no explicit pairs. The scene
supplies **49 selected pairs**: 26 frictionless self-contact pairs (`condim=1`)
and 23 floor-contact pairs (`condim=3`). Each foot uses three capsules for floor
contact and one box for selected self-contact. The six foot-floor pairs use
friction `1 1` and `solref="0.008 1"`. The scene retains Astro's floor at
`z=-0.75`. New environments must declare their own intended pairs; adding a
floor alone does not enable contacts for this robot.

<p float="left">
  <img src="astro_p2_simplified_colliders.png" alt="Astro P2 simplified collision primitives" width="400">
</p>

This is a manually designed, coarser collision envelope. It deliberately omits
the detailed model's small housing/handle features and detailed foot envelope;
its selected pairs do not reproduce every possible self/environment interaction.
It is not a measured mesh-coverage fit, calibrated contact model, performance
benchmark or standing controller. Previews show the unchanged reference pose
without simulation stepping; the image above displays collision groups 3 and 4.
Viewer group visibility does not alter collision selection.

The XML uses the G1 MJX **approach**, but native MuJoCo is the verification
target. MJX/JAX/Warp execution and performance remain deferred.

[Original fixed-head conversion notes](provenance/29dof/MJCF.md) and
[Dex3-1 derivation records](provenance/dex3_1/DERIVATION.md) are historical source
evidence. Their old paths/build commands are not supported regeneration steps
for these maintained models. The [migration receipt](provenance/migration.json)
records source-file moves and hashes. Edit the root XML directly.

Workbench, URDF compatibility, and MJX remain deferred. Retained URDFs document
earlier configurations and are not advertised as equivalent to the current
variants. The three root MJCF models are the maintained native Astro P2 entries.

## License

The Astro P2 body and default model are released under the
[Apache License, Version 2.0](LICENSE). The Dex3-1 alternative combines the same
Apache-2.0 body with Unitree hand material under
[BSD-3-Clause terms](LICENSE.Unitree). See [LICENSING.md](LICENSING.md) for the
file and source-record scope. The simplified robot remains Apache-2.0; its
scene's adapted Menagerie contact selection retains the upstream
[BSD-3-Clause notice](LICENSE.Menagerie).
