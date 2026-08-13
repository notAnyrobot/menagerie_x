# menagerie_x

`menagerie_x` packages the Dobot **Astro** humanoid robot descriptions and a browser workbench as a `uv`-managed Python project. URDF is the maintained source format. Astro V1 retains MJCF and Isaac assets for legacy tooling; Astro V2 is URDF-only.

For detailed robot configuration, joint order, actuator constants, PD gains, default poses, body mapping, and simulator settings, see [Robot Configuration](docs/robot_configuration.md).

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

`menagerie_x validate` checks the packaged manifest and asset paths. `menagerie_x variants` lists available URDF/MJCF variants. `menagerie_x mujoco --check` loads the default MJCF without opening a viewer.

## Visualize Astro

Open the native MuJoCo viewer:

```bash
uv run menagerie_x mujoco
```

Open a non-default MJCF-backed variant:

```bash
uv run menagerie_x mujoco --variant astro_v1_27dof
```

For browser visualization with Viser, install optional visualization dependencies:

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

The workbench loads each selected model into the official MuJoCo WASM bindings in the browser. Three.js renders the mesh scene and provides the orbit/click interaction layer; Viser is not required. The workbench uses authored MJCF when available and otherwise compiles the declared URDF in MuJoCo WASM.

Use the Simulation panel or press `P` to toggle physics, `R` to reset the model, and `F` to toggle camera follow. Drag empty space to orbit; drag a robot link to apply a push.

## Repository Layout

Robot assets are grouped first by Astro version. This lets one package release expose both robot generations without making a Git branch part of the runtime interface.

```text
src/menagerie_x/
  assets/
    manifest.json         # catalog across robot versions
    astro_v1/
      urdf/               # maintained V1 source descriptions
      meshes/             # V1 STL visual/collision meshes
      legacy/
        mjcf/             # V1 MuJoCo descriptions
        isaac/            # V1 Isaac integration
    astro_v2/
      urdf/               # V2 maintained source descriptions
      meshes/             # V2 URDF-referenced geometry
  workbench/              # browser server and static workbench UI
  commands/               # implementations behind `uv run menagerie_x ...`
  tools/                  # reusable utilities
docs/
  robot_configuration.md  # detailed robot configuration reference
```

There is intentionally no top-level `scripts/`, `mjcf/`, `urdf/`, or `meshes/` directory. Use the `menagerie_x` CLI and the manifest rather than hard-coded checkout-root paths. V2 ships as a URDF-only description with its referenced meshes.

## Common Commands

Compute keyframe body heights:

```bash
uv run menagerie_x heights --config knees_bent
```

Launch the PD parameter editor for [Robot Configuration](docs/robot_configuration.md):

```bash
uv run menagerie_x pd-tool
```

Generate an Astro URDF with extension capsule collision tags:

```bash
uv run menagerie_x urdf-capsules --output /tmp/astro_v1_capsules.urdf
```

## Asset Variants

Robot-description variants are declared in `src/menagerie_x/assets/manifest.json`.

| Variant | DOFs | URDF | MJCF | Status |
|---|---:|---|---|---|
| `astro_v1` | 30 | `astro_v1/urdf/astro_v1.urdf` | `astro_v1/legacy/mjcf/astro_v1.xml` | legacy |
| `astro_v1_27dof` | 27 | `astro_v1/urdf/astro_v1_27dof.urdf` | `astro_v1/legacy/mjcf/astro_v1_27dof.xml` | legacy |
| `astro_with_racket` | 30 | `astro_v1/urdf/astro_with_racket.urdf` | - | variant |
| `astro_v2` | 30 | `astro_v2/urdf/astro_v2.urdf` | - | current |

Add or retire a version's URDF files by updating the manifest first, then run:

```bash
uv run menagerie_x validate
uv run menagerie_x mujoco --variant <variant> --check
```
