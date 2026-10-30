# Changelog

## 2026-10-30

- Mark both P1 models as legacy and remove them from the active collection.
  Retain their assets and native checks pending a later retirement.

- Match the upstream README structure and add native model preview images,
  preserving the existing model descriptions and source records.

- Make family-root model/scene XML directly maintained native inputs; retire
  mirror regeneration and defer Workbench, URDF compatibility, and MJX.
- Preserve all existing robot descriptions, assets, source evidence, and notices.

- Move this existing family to the repository root; keep all original descriptions and meshes unchanged.
- Store mesh files in `assets/`, retaining `meshes/` and `robots/` compatibility paths.
- Document formats, provenance, and limitations; add native scenes for manifest-declared MJCF editions.
