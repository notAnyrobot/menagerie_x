# Menagerie X

Menagerie X is a curated collection of robot descriptions, organized after
[MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie).
It contains the seven existing local robot families, with their URDF/MJCF
editions, meshes, provenance, and a local browser Workbench.

## Robot collection

| Robot family | Internal DOF by edition | Formats | Native scene |
| --- | --- | --- | --- |
| [Astro P1](astro_p1/README.md) | 27 / 30 | URDF, MJCF; racket edition URDF-only | [scene.xml](astro_p1/scene.xml) |
| [Astro P2](astro_p2/README.md) | 30 | URDF, MJCF | [scene.xml](astro_p2/scene.xml) |
| [Astro P2 fixed head](astro_p2_29dof/README.md) | 29 | URDF catalog; separate MJCF conversion | See [MJCF.md](astro_p2_29dof/MJCF.md) |
| [Astro P2 with Dex3-1 hands](astro_p2_43dof_dex3_1/README.md) | 43 | URDF, MJCF | [scene.xml](astro_p2_43dof_dex3_1/scene.xml) |
| [Atom P3](atom_p3/README.md) | 27 | MJCF | [scene.xml](atom_p3/scene.xml) |
| [SOMA-23](soma23/README.md) | 66 | MJCF | [scene.xml](soma23/scene.xml) |
| [Unitree G1](unitree_g1/README.md) | 43 with hands / 29 box feet | URDF, MJCF | [scene.xml](unitree_g1/scene.xml) |

The inventory contains 12 logical editions, ten with catalog-declared MJCF.
Each family README links its editions and alternate scenes. No additional
upstream robots are bundled. Atom P3 and the Astro Dex3-1 sample have no
actuators; the Dex3-1 assembly uses an unverified sample hand mount.

## Getting started

```bash
uv sync --extra dev
npm ci --prefix src/menagerie_x/workbench/web
uv run menagerie_x variants
uv run menagerie_x validate
```

Open a native scene, including its lighting and ground plane:

```bash
uv run menagerie_x mujoco --mjcf astro_p2/scene.xml
```

Compile-check it without opening a window:

```bash
uv run menagerie_x mujoco --mjcf astro_p2/scene.xml --check
```

The scene includes its sibling robot XML. Robot descriptions contain the
robot; scene files add the presentation environment. Scenes preserve each
source robot's coordinate datum, lowering the floor where necessary by the
catalog standing height. These are load/simulation examples, not controllers
or evidence of hardware fidelity.

## Browser Workbench

```bash
uv run menagerie_x workbench
```

Open <http://127.0.0.1:8000>, select a family and an edition, and inspect URDF or
MJCF. MJCF editions support collision review and editing. **Export URDF**
copies supported saved primitive collisions into a download; it requires both
formats, excludes unsaved drafts, and blocks unsupported collision geometry.

The CLI and Workbench continue to use the manifest's authoritative source
files. After editing those files, run `make sync` to refresh flat model and
scene entrypoints before using them in native MuJoCo.

## Repository layout

```text
astro_p1/                 # one top-level directory per robot family
  assets/                 # actual mesh files
  meshes -> assets        # compatibility path for retained descriptions
  astro_p1_30dof.xml       # flat native robot entrypoint
  scene.xml               # default presentation scene
  scene_27dof.xml          # alternate edition
  mjcf/, urdf/            # retained authoritative descriptions
  README.md, CHANGELOG.md, LICENSING.md
astro_p2/, astro_p2_29dof/, astro_p2_43dof_dex3_1/
atom_p3/, soma23/, unitree_g1/
manifest.json             # authoritative family/edition/provenance catalog
catalog.py                # native entrypoint metadata derived from the manifest
robots/                   # relative links for old robots/<family>/... paths
scenes/, terrains/        # existing Workbench scene descriptions
src/menagerie_x/          # Python CLI, asset tools, and Workbench
scripts/, tests/, docs/   # maintenance, verification, and research
```

The HHTools bundles retain root-level URDFs and `robot.yaml`. Their existing
MJCF files are preserved directly; flat models for nested legacy MJCFs are
generated copies with portable `assets/` paths. Original descriptions, meshes,
license files, and provenance hashes remain unchanged. See [UPSTREAM.md](UPSTREAM.md)
for copied scaffold files and deliberate compatibility differences.

Editable installs find this checkout from any working directory. The wheel
contains code; assets remain in the checkout. For a standalone installation,
pass `menagerie_x --root /path/to/menagerie_x ...`. Old catalog roots under
`robots/` are also accepted.

## Development and licensing

```bash
make sync   # regenerate flat models and scenes after source edits
make all    # generated-file checks, Python/scene tests, Workbench JS tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md), the
[upstream investigation](docs/research/mujoco-menagerie.md), and
[LICENSING.md](LICENSING.md). Model licenses differ, and several legacy/internal
bundles have unresolved redistribution terms. Copied upstream tooling does
not relicense those assets.
