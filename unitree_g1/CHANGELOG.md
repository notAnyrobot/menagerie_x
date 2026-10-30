# Changelog

## 2026-10-30

- Add MuJoCo Menagerie's pinned `g1_mjx.xml` / `scene_mjx.xml` as an additional
  native configuration: 29 joint position actuators, 27 primitive collision
  geoms, 49 explicit scene contact pairs, and `home` / `knees_bent` poses.
- Preserve the upstream XML bytes, physical parameters, license notice and
  mesh bytes; add the two uppercase rubber-hand asset filenames and a native
  preview using the `home` pose. Existing G1 models and source assets are unchanged.
- Record upstream provenance; MJX runtime and URDF/Workbench compatibility
  remain deferred.

- Match the upstream README structure and add native model preview images,
  preserving the existing model descriptions and source records.

- Make family-root model/scene XML directly maintained native inputs; retire
  mirror regeneration and defer Workbench, URDF compatibility, and MJX.
- Preserve all existing robot descriptions, assets, source evidence, and notices.

- Move this existing family to the repository root; keep all original descriptions and meshes unchanged.
- Store mesh files in `assets/`, retaining `meshes/` and `robots/` compatibility paths.
- Document formats, provenance, and limitations; add native scenes for manifest-declared MJCF editions.
