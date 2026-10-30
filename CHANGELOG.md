# Changelog

## 2026-10-30

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
