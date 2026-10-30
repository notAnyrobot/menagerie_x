# Changelog

## 2026-10-30

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
