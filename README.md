# Menagerie X

`menagerie_x` is a multi-robot description catalog and local browser workbench. It packages robot-specific URDF and MJCF descriptions, meshes, provenance, scenes, and utilities behind one manifest-driven Python interface. The current catalog includes Dobot Astro variants, Atom P3, and the Unitree G1, and is structured so additional robot families can be added without changing the package namespace.

For Astro-specific joint order, actuator constants, PD gains, default poses, body mapping, and simulator settings, see [Astro robot configuration](docs/robots/astro.md).

## Quickstart

Install the base environment:

```bash
uv sync
```

Validate the packaged robot assets:

```bash
uv run menagerie_x validate
uv run menagerie_x variants
uv run menagerie_x mujoco --check
```

`menagerie_x validate` checks the packaged manifest and asset paths. `menagerie_x variants` lists available URDF/MJCF variants. `menagerie_x mujoco --check` loads the catalog's default MJCF without opening a viewer.

## Visualize a robot

Open the catalog's default variant in the native MuJoCo viewer:

```bash
uv run menagerie_x mujoco
```

Open a specific MJCF-backed variant:

```bash
uv run menagerie_x mujoco --variant unitree_g1
```

Open one exact manual MJCF edition without changing the manifest:

```bash
uv run menagerie_x mujoco --mjcf src/menagerie_x/assets/astro_v2/mjcf/astro_v2_primitive_collision.xml
```

`--variant` and `--mjcf` are mutually exclusive. With neither selector, MuJoCo opens the manifest's `default_variant`, currently `astro_v2`.

The lightweight Viser command currently targets the legacy Astro V1 mesh set. To use that robot-specific viewer, install the optional visualization dependencies:

```bash
uv sync --extra viz
```

Start the Viser server:

```bash
uv run --extra viz menagerie_x viser --port 8080
```

Then open:

```text
http://127.0.0.1:8080
```

If port `8080` is already in use:

```bash
uv run --extra viz menagerie_x viser --port 42178
```

For headless systems or fast CI checks, use:

```bash
uv run menagerie_x mujoco --check
```

## Robot Workbench

The `workbench` module is the local browser UI for selecting, visualizing, and validating packaged robot descriptions. It discovers every variant declared in the asset manifest, keeps the robot list collapsible, and links validation findings to the corresponding link or joint where possible.

Install its browser-only dependencies once:

```bash
npm install --prefix src/menagerie_x/workbench/web
```

Then launch the workbench:

```bash
uv run menagerie_x workbench
```

The workbench listens at `http://127.0.0.1:8000` and does not open a browser tab by default. Open that address once; use **Restart workbench** in the toolbar when the local server needs restarting. It asks for confirmation, discards unsaved browser state, restarts the local server, and reloads the page. Use `uv run menagerie_x workbench --open-browser` only when you want the server to open a new tab. The workbench loads each selected MJCF edition into the official MuJoCo WASM bindings in the browser. Three.js renders the mesh scene and provides the orbit/click interaction layer; Viser is not required. Use **Reload menagerie** after editing an MJCF file outside the browser to rebuild the selected edition without restarting the Workbench. When it is bound to localhost, **Open in MuJoCo** launches the selected saved edition in one Workbench-owned native MuJoCo viewer; unsaved collision-editor drafts must be overwritten or exported first to appear there.

### MJCF editions

The manifest's `mjcf` path is the authorized edition for a variant. Additional complete `.xml` files placed in `src/menagerie_x/assets/<robot-version>/mjcf/` are discovered automatically:

- Files with `menagerie_x_candidate` provenance are managed review/collision-draft editions.
- Files without provenance are selectable **manual editions** when they have a `<mujoco>` root, exactly one free root joint, and mesh files resolvable from that robot version's `meshes/` directory.

Manual editions can be visualized and collision-edited, but are not authorizable until exported as a managed edition with review provenance.

### Included third-party descriptions

`assets/unitree_g1/` packages the official Unitree G1
`g1_29dof_with_hand_rev_1_0` URDF and MJCF, plus only the meshes they
reference.  The description originates from Unitree Robotics'
[`unitree_ros`](https://github.com/unitreerobotics/unitree_ros) repository at
revision `daadf41ee9afce8f90fdc09a98506012691fa122`; the included
[`LICENSE.Unitree`](src/menagerie_x/assets/unitree_g1/LICENSE.Unitree) retains
its BSD 3-Clause terms.  The packaged MJCF changes only its relative
`meshdir` because it lives in Menagerie's per-variant `mjcf/` workspace.

Use the Simulation panel or press `P` to toggle physics, `R` to reset the model, and `F` to toggle camera follow. Drag empty space to orbit; drag a robot link to apply a push.

## Repository layout

Robot assets are grouped by robot family or version. Each manifest variant points to its owning `robot_version`, so one package release can expose descriptions from multiple vendors and generations without encoding a particular robot in the package interface.

```text
src/menagerie_x/
  assets/
    manifest.json         # catalog of robot versions, variants, scenes, and defaults
    astro_v1/
      urdf/
      mjcf/
      meshes/
      legacy/isaac/
    astro_v2/
      urdf/
      mjcf/
      meshes/
    unitree_g1/
      urdf/
      mjcf/
      meshes/
  workbench/              # browser server and static workbench UI
  commands/               # implementations behind `uv run menagerie_x ...`
  tools/                  # reusable and robot-specific utilities
docs/
  robots/
    astro.md              # Astro-specific configuration reference
```

There is intentionally no top-level `scripts/`, `mjcf/`, `urdf/`, or `meshes/` directory. Use the `menagerie_x` CLI and manifest rather than hard-coded checkout-root paths. A robot version may choose its own maintained source format and retain other formats as imported, generated, or legacy assets; declare that policy in `manifest.json`.

## Robot-specific commands

Some utilities predate the multi-robot catalog and intentionally operate on Astro assets.

Compute keyframe body heights:

```bash
uv run menagerie_x heights --config knees_bent
```

Launch the PD parameter editor for [Astro robot configuration](docs/robots/astro.md):

```bash
uv run menagerie_x pd-tool
```

Generate an Astro URDF with extension capsule collision tags:

```bash
uv run menagerie_x urdf-capsules --output /tmp/astro_v1_capsules.urdf
```

## Asset Variants

Robot-description variants are declared in `src/menagerie_x/assets/manifest.json`.

| Variant | Robot version | DOFs | URDF | MJCF | Status |
|---|---|---:|---|---|---|
| `astro_v1` | `astro_v1` | 30 | `urdf/astro_v1.urdf` | `mjcf/astro_v1.xml` | legacy |
| `astro_v1_27dof` | `astro_v1` | 27 | `urdf/astro_v1_27dof.urdf` | `mjcf/astro_v1_27dof.xml` | legacy |
| `astro_with_racket` | `astro_v1` | 30 | `urdf/astro_with_racket.urdf` | - | variant |
| `astro_v2` | `astro_v2` | 30 | `urdf/astro_v2.urdf` | `mjcf/astro_v2_primitive_collision.xml` | current |
| `unitree_g1` | `unitree_g1` | 43 | `urdf/g1_29dof_with_hand_rev_1_0.urdf` | `mjcf/g1_29dof_with_hand_rev_1_0.xml` | imported |
| `atom_p3` | `atom_p3` | 27 | - | `mjcf/atom_p3_27dof_capsule_foot.xml` | imported |


Atom P3 is currently MJCF-only: no URDF was supplied with the imported bundle. Its default MJCF contains sensors but no actuator declarations (`nu=0`), so it is available for inspection and simulation but needs an actuator model before closed-loop control.

Add, update, or retire a robot version through the manifest first, then run:

```bash
uv run menagerie_x validate
uv run menagerie_x mujoco --variant <variant> --check
```
