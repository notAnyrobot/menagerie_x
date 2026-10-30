# Changelog

## 2026-10-30

- Replace the oversized hand envelope with the G1-style palm capsule: radius
  0.05 m, centerline x=0.05–0.10 m. Fingers/thumb may extend outside. Keep all
  other geometry, the wrist cleanup and 68 contact pairs unchanged.

- Remove the two standalone wrist-roll collision proxies after checking
  neighboring coverage through wrist motion. Fit rounder hand capsules to
  Astro's own mesh using G1 as a shape reference; preserve wrist joints and
  non-arm colliders. The alternative now has 50 colliders and 68 explicit pairs.

- Narrow the collision alternative to arms and hands. Restore the default
  pelvis, legs, feet, torso/neck and head colliders and their automatic contact
  behavior. Use explicit scene pairs only for optimized arms; preserve the
  detailed variants and all body/joint/visual definitions.

- Add Astro P2 with simplified collisions as a separate native model/scene:
  27 Astro-sized primitives and 49 selected contact pairs. Preserve the existing
  default/articulated variants, physical body and visual meshes; keep native
  passive dynamics and defer MJX runtime support.
- Add reference-pose mesh and collision-only previews, and retain the upstream
  BSD notice for the adapted Menagerie G1 scene contact pattern.

- Label the articulated variant Astro P2 with hands and color its 16 hand visual
  meshes silver. Preserve hand geometry, dynamics, collision geoms, and the
  saved `fist` pose; refresh its native reference-pose preview.

- Release Astro P2 body/default-model material under Apache-2.0, retaining
  BSD-3-Clause terms for Unitree Dex3-1 hands. Label the default model simply
  Astro P2 in the gallery, family README, and application metadata.

- Restore Astro's original rubber-hand meshes, fixed transforms, masses, and
  inertias; replace the G1 trial's collision capsules with the original Astro
  envelopes. Keep the refined 29-DoF body and Dex3-1 variant unchanged.

- Consolidate the fixed-head Astro body and Dex3-1 configuration into one family
  with sibling `astro_p2.xml` / `astro_p2_with_hands.xml` models and scenes.
- Maintain only the 29-body-DoF versions; retire all three 30-DoF P2 model choices
  and their active gallery entries. The old history remains in Git.
- Reuse actual Unitree G1 left/right rubber hands, including standalone vendor
  hand masses and inertias, at explicitly documented sample Astro mounts.
- Keep both variants on the same latest refined Astro body. Preserve the Dex3-1
  finger definitions and `fist` keyframe.
- Deduplicate shared assets and preserve the old fixed-head/Dex3-1 sources,
  reports, URDFs, and licenses under `provenance/` with a migration hash receipt.
- Keep Workbench, URDF compatibility, and MJX deferred.
