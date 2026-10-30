# Menagerie X

A curated collection of native MuJoCo robot models and scenes, organized after
[MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie).
Only the seven existing local robot families are included. Each family has
maintained robot XML, scene XML, local assets, documentation, and provenance.

## Robot collection

| Robot family | Internal DOF by model | Default native scene |
| --- | --- | --- |
| [Astro P1](astro_p1/README.md) | 27 / 30 | [scene.xml](astro_p1/scene.xml) |
| [Astro P2](astro_p2/README.md) | 30, three collision choices | [scene.xml](astro_p2/scene.xml) |
| [Astro P2 fixed head](astro_p2_29dof/README.md) | 29 | [scene.xml](astro_p2_29dof/scene.xml) |
| [Astro P2 with Dex3-1 hands](astro_p2_43dof_dex3_1/README.md) | 43 | [scene.xml](astro_p2_43dof_dex3_1/scene.xml) |
| [Atom P3](atom_p3/README.md) | 27 | [scene.xml](atom_p3/scene.xml) |
| [SOMA-23](soma23/README.md) | 66 | [scene.xml](soma23/scene.xml) |
| [Unitree G1](unitree_g1/README.md) | 43 with hands / 29 box feet | [scene.xml](unitree_g1/scene.xml) |

There are **11 native models and 11 scenes**; alternate choices are linked in
each family README and curated in root `catalog.py`. Astro 29's already existing
MJCF conversion is now included in this native inventory. The separate legacy
application manifest retains its 12 editions and URDF-only Astro 29 entry.
Atom P3 and the Astro 29/Dex3-1 conversions have no actuators; the Dex3-1 sample
hand mount is unverified. Loading and short stepping do not establish controller
stability or hardware fidelity.

## Getting started

```bash
uv sync --locked --extra dev
uv run python -m mujoco.viewer --mjcf=astro_p2/scene.xml
```

Load a model or scene directly, without the Menagerie X application:

```python
import mujoco

model = mujoco.MjModel.from_xml_path("astro_p2/scene.xml")
data = mujoco.MjData(model)
mujoco.mj_step(model, data)
```

Scenes include their sibling robot XML and supply presentation lighting and one
ground plane. Robot coordinate frames, physical parameters, and existing
keyframes are preserved. Several zero-height robot datums use a lowered floor;
opening a scene uses normal MuJoCo reference initialization. Select any named
keyframe explicitly with MuJoCo's reset API or viewer controls.

Each family can be copied and loaded independently. Keep `assets/` and the
relative `meshes -> assets` link alongside the XML: the two preserved HHTools
conversions still use that original mesh path. No root manifest, Python catalog,
Workbench, or other robot family is needed to load the XML.

## Repository layout

```text
astro_p1/
  astro_p1_30dof.xml       # canonical native robot description
  astro_p1_27dof.xml       # alternate native robot
  scene.xml               # includes default robot, adds environment
  scene_27dof.xml          # alternate scene
  assets/                 # actual mesh data
  meshes -> assets        # retained relative mesh alias
  mjcf/, urdf/            # retained source snapshots / legacy URDF material
  README.md, CHANGELOG.md, LICENSING.md
astro_p2/, astro_p2_29dof/, astro_p2_43dof_dex3_1/
atom_p3/, soma23/, unitree_g1/
catalog.py                # curated native model/preview map, like upstream
format_xml.py             # upstream XML formatter
test/                     # native layout, loading, stepping, portability checks
docs/                     # investigation and accepted scope decisions
manifest.json, robots/    # retained legacy application metadata / paths
src/menagerie_x/, tests/  # retained CLI, Workbench, and application tests
scenes/, terrains/        # legacy Workbench JSON environments
```

Edit the family-root XML directly. Nested `mjcf/` imports remain unchanged as
source evidence; they are no longer the authority for native entry points.
There is no synchronization or regeneration step. Existing conversion scripts
are historical authoring tools and can overwrite manual MJCF refinements; read
the family documentation before using them.

## Development

```bash
make install
make all
```

Native acceptance checks use pinned MuJoCo 3.11.0, load all models and scenes,
step them for 0.1 seconds with deterministic controls, check keyframe reset, and
load copied standalone family bundles. CI runs the same checks without browser
or rendering dependencies. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Deferred application compatibility

CLI and Workbench code, URDFs, old paths, and application tests are preserved.
**Workbench, URDF compatibility, and MJX are deferred.** The legacy application
manifest may select nested snapshots rather than the canonical native XML;
application edits do not update the native model. Browser include/asset loading,
pose initialization, and collision-editor behavior are not native acceptance
gates. See the [compatibility findings](docs/research/mujoco-workbench-compatibility.md).
Optional `make legacy-test` and `make web-test` exercise the retained application
suites; browser dependencies must be installed separately where required.

## Licensing and provenance

See [UPSTREAM.md](UPSTREAM.md), the
[upstream investigation](docs/research/mujoco-menagerie.md), and
[LICENSING.md](LICENSING.md). Model licenses differ; some internal bundles have
unresolved redistribution terms. Upstream tooling does not relicense those
assets. Original meshes, descriptions, source records, and license notices are
preserved.
