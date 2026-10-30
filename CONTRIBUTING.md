# Contributing to Menagerie X

Keep each existing robot family self-contained in a top-level folder. Use
`assets/` for actual mesh data, a flat robot XML per native MJCF entrypoint,
and a separate `scene.xml` (or `scene_<edition>.xml`) for presentation. Keep
robot dynamics out of scene changes. Preserve imported source files, license
notices, pinned revisions, and hashes.

## Development

```bash
uv sync --extra dev
npm ci --prefix src/menagerie_x/workbench/web
make all
```

`make all` checks generated entrypoints, runs the full Python suite including
native scene compilation and 0.1-second no-warning stepping, and runs the
Workbench JavaScript tests. Linux headless runs use EGL by default; override
`MUJOCO_GL` for your rendering backend. CI runs the same targets.

An optional `pre-commit install` enables the checks in `.pre-commit-config.yaml`.
The hook does not reformat imported source models.

## Editing assets

1. Update the authoritative URDF/MJCF source named in `manifest.json`, retaining
   license/provenance information and documenting any changed source hashes.
2. Update the manifest for new editions or default choices. Do not maintain a
   second native model map; `catalog.py` derives its entries from this manifest.
3. Run `make sync` to regenerate flat model/scene entrypoints, then `make all`.
4. Record model changes in the family's `CHANGELOG.md`; shared changes belong
   in the root changelog.

Generated native copies change only mesh search paths and separation of
world-level ground planes. Sources already at family root are preserved
without regeneration. Keep native scene files out of editable model edition
lists. URDF-only editions require no placeholder MJCF or scene.

New generated XML uses the upstream formatter: two-space indentation,
double-quoted attributes, `<foo/>` empty elements, and 120-column wrapping.
Legacy/source model formatting remains unchanged to preserve provenance hashes.
Sources named `scene.xml` or `scene_<name>.xml` receive a `model_` prefix in
their flat robot entrypoint. Synchronization validates the full output plan
before writing and rejects paths that would overwrite authoritative sources
or give different generated files the same destination.
See [UPSTREAM.md](UPSTREAM.md) for the pinned template and compatibility choices.
