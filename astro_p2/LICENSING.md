# Licensing and provenance

## Astro P2 — Apache-2.0

The Astro P2 body model, default model, and Astro-origin meshes and descriptions
are released under the [Apache License, Version 2.0](LICENSE). This covers the
Astro body shared by `astro_p2.xml` and `astro_p2_with_hands.xml`, the default
model's original Astro hand material, and the corresponding Astro-origin
source descriptions retained under `provenance/`.

## Third-party hand material

Unitree Dex3-1 hand definitions and meshes retain the
[BSD-3-Clause terms](LICENSE.Unitree). The complete `astro_p2_with_hands.xml`
combines Apache-2.0 Astro body material with BSD-3-Clause Unitree hand material;
both notices apply. Unitree hand meshes are the sixteen
`assets/{left,right}_hand_{palm,thumb_*,index_*,middle_*}_link.STL` files.
The default model's `assets/{left,right}_hand_link.stl` files are Astro material.

Historical G1 hand-trial sources retain their Unitree and ProtoMotions notices
under `provenance/rubber_hand_sources/`; they are not part of the default model.
Presentation scenes retain their separate
[upstream G1 notice](../LICENSES/MuJoCo-Menagerie-G1.txt).

## Source records

Original conversion reports, URDFs, source XML, and documentation are preserved
byte-for-byte under `provenance/29dof/` and `provenance/dex3_1/`.
`provenance/migration.json` records their hashes. Historical licensing notes
reflect their recording date; this Apache-2.0 grant supplies the current terms
for Astro P2 material and does not change any third-party terms.

[Repository licensing](../LICENSING.md) identifies the terms for the rest of the
collection. No whole-repository license is implied by the Astro P2 grant.
