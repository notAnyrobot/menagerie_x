# Changelog

## 2026-10-30

- Revise the Astro collision alternative after visual review: restore all
  original non-arm colliders and their contact parameters, and optimize only
  arm/hand shapes. Preserve independent wrist articulation and the detailed
  feet; replace the earlier whole-body 27-shape target with an arm-focused scope.

- Add a separate simplified Astro P2 configuration with 27 collision primitives
  and an explicit scene contact list. Preserve the existing Astro variants,
  meshes, rigid-body/joint properties and unactuated controls. MJX runtime stays
  deferred. The active native collection now contains eight models.

- Label the articulated Astro variant Astro P2 with hands and render its hand
  meshes in silver. Preserve its dynamics, collisions and source meshes.
- Add MuJoCo Menagerie's G1 primitive configuration as a separate native model:
  27 collision primitives, 49 scene contact pairs, position servos and saved
  poses. Preserve the existing G1 variants; MJX runtime support stays deferred.
  The active collection now has seven models across four families.

- Release Astro P2 body/default-model material under Apache-2.0, retaining
  BSD-3-Clause terms for Unitree Dex3-1 hands. Label the default model simply
  Astro P2 in the gallery, family README, and application metadata.

- Restore Astro's original rubber-hand meshes, fixed transforms, masses, and
  inertias; replace the G1 trial's collision capsules with the original Astro
  envelopes. Keep the refined 29-DoF body and Dex3-1 variant unchanged.

- Prune Astro P2 to one family with a 29-DoF body and two hand configurations:
  fixed G1 rubber hands or 14-DoF Dex3-1 hands (43 total). Retire the three
  30-DoF P2 choices and consolidate the former separate Astro variant folders.
- Mark Astro P1 as legacy, retaining its two models and loading checks until
  later retirement. The active collection is six models across four families.

- Align root and robot READMEs with MuJoCo Menagerie's gallery, overview,
  derivation, changelog, and license sections. Add 11 native scene previews
  and preserve the detailed Dex3-1 build/validation record in `DERIVATION.md`.

- Retire the stale `robots/` compatibility links and remove them from source
  archives. Use top-level family paths; retain the family-local mesh aliases
  required by preserved native conversions and legacy descriptions.

- Complete the simplified native refactor: root model/scene XML is canonical,
  with an explicit upstream-style catalog and no mirror generator.
- Include the existing Astro 29 MJCF and its new scene in the 11-model native
  inventory; preserve the legacy manifest and every existing asset unchanged.
- Gate CI on native layout, load/step, keyframe reset, and standalone family
  checks. Workbench, URDF compatibility, and MJX remain deferred.

### Earlier scaffold work

- Adopt a pruned MuJoCo Menagerie scaffold while preserving Menagerie X's CLI
  and local browser Workbench.
- Move the original seven families and shared scene/terrain descriptions to
  the repository root, with `assets/` mesh storage and compatibility links.
- Add ten native MJCF robot entrypoints/scenes derived from the original
  manifest, preserving 12 logical editions and original source files/hashes.
- Add family documentation, licensing/provenance records, upstream attribution,
  generated-file checks, scene smoke tests, and shared development/CI commands.
- Fix reviewed import and edition workflows: preserve scene-prefixed model
  names, give new families portable mesh paths, and prevent native output
  collisions or overwrites of authoritative sources.
- Refresh collision-editing and contact controls when browser models finish
  loading, and cover the import/rename/default/sync flows with regression tests.
