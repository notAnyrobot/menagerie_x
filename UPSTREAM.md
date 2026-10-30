# Upstream scaffold

This refactor uses a pruned source scaffold from
[google-deepmind/mujoco_menagerie](https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc),
pinned at `f3b6013629c7b94f8ee93fd977b161fa8350f9bc` (2026-10-23).
Menagerie X keeps its own Git history, Python package, and existing assets.

| Local file | Upstream source and treatment |
| --- | --- |
| `format_xml.py` | Copied unchanged from upstream; Apache-2.0 copyright header retained. |
| `catalog.py` | Adapted from upstream catalog shape; replaces the complete model map with metadata derived from local `manifest.json`. |
| `tests/test_menagerie_models.py` | Adapts `test/model_test.py` deterministic 0.1-second controls/no-warning checks and `test/model_dir_test.py` layout checks to local inventory and unittest. Apache-2.0 headers retained. |
| `scripts/sync-menagerie.py`, family `scene*.xml` | Presentation structure adapted from `unitree_g1/scene.xml`; local model references, ground height, and names are substituted. Upstream G1 license retained in `LICENSES/MuJoCo-Menagerie-G1.txt`. |
| `Makefile`, `.pre-commit-config.yaml`, `.github/workflows/build.yml` | Adapt the upstream development/check patterns to the existing CLI/Workbench and unittest suite. |
| Family README/changelog and root documentation | Follow upstream organization using local inventory and provenance. |

Apache-2.0 terms for the copied/adapted Python tools are retained in
[LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt). Robot-specific notices remain
with each family. See [LICENSING.md](LICENSING.md) for scope.

## Compatibility choices

- Exactly the original seven families and 12 logical editions remain. Upstream
  G1 descriptions do not replace the locally selected Unitree/ProtoMotions models.
- `assets/` contains actual meshes; `meshes/` and `robots/<family>/` are relative
  compatibility links. They preserve existing URDFs, saved commands, and local
  retargeting work while new entrypoints use top-level family paths.
- `hatch_build.py` preserves those relative links in source distributions,
  avoiding omitted legacy mesh paths and duplicate asset storage. Wheels keep
  the existing code-only packaging policy.
- The manifest remains the single authority for editions, default choices,
  source descriptions, and provenance. The native catalog is derived from it.
- Imported and authored source descriptions stay byte-identical. Flat native
  copies for nested MJCF sources use `assets/` paths and omit world-level
  ground planes. The legacy G1 source retains its original demonstration floor;
  the flat G1 robot has none, and its scene supplies one.
- Source robot frames stay unchanged. A scene's floor height is the source root
  Z minus its manifest standing height. No controller or new actuator is added.
- Astro's URDF-only catalog edition and racket edition remain URDF-only. The
  separately maintained Astro 29-DOF MJCF conversion is not promoted silently.
- Layout checks accept explicit `LICENSING.md` records where license grants
  are unresolved instead of inventing a model `LICENSE`.
- The upstream download package, remote model archives, generated release
  registry, unrelated gallery assets, and release workflows are omitted. The
  existing Menagerie X package and local Workbench remain the delivery mechanism.

The [research report](docs/research/mujoco-menagerie.md) contains the underlying
source citations and tradeoffs.
