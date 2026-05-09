# Astro Robot Description

This repository packages the Dobot **Astro** humanoid robot description as a `uv`-managed Python project. It includes packaged URDF, MJCF, STL meshes, version metadata, validation commands, and MuJoCo/Viser visualization entrypoints.

For detailed robot configuration, joint order, actuator constants, PD gains, default poses, body mapping, and simulator settings, see [Robot Configuration](docs/robot_configuration.md).

## Quickstart

Install the base environment:

```bash
uv sync
```

Validate the packaged robot assets:

```bash
uv run astro validate
uv run astro variants
uv run astro mujoco --check
```

`astro validate` checks the packaged manifest and asset paths. `astro variants` lists available URDF/MJCF variants. `astro mujoco --check` loads the default MJCF without opening a viewer.

## Visualize Astro

Open the native MuJoCo viewer:

```bash
uv run astro mujoco
```

Open a non-default MJCF-backed variant:

```bash
uv run astro mujoco --variant astro_v1_27dof
```

For browser visualization with Viser, install optional visualization dependencies:

```bash
uv sync --extra viz
```

Start the Viser server:

```bash
uv run --extra viz astro viser --port 8080
```

Then open:

```text
http://127.0.0.1:8080
```

If port `8080` is already in use:

```bash
uv run --extra viz astro viser --port 42178
```

For headless systems or fast CI checks, use:

```bash
uv run astro mujoco --check
```

## Repository Layout

The robot description is packaged under `src/astro_description/robots/astro/` so the URDF, MJCF, meshes, constants, and simulator-specific config travel with the Python package.

```text
src/astro_description/
  tools/                  # importable tools exposed by `uv run astro ...`
  robots/astro/
    manifest.json         # variant registry and version metadata
    constants.py          # Astro keyframes and control constants
    config.yaml           # deployment/control config
    mjcf/                 # MuJoCo descriptions
    urdf/                 # URDF descriptions
    meshes/               # STL visual/collision meshes
    isaac/                # Isaac-specific integration config
docs/
  robot_configuration.md  # detailed robot configuration reference
```

There is intentionally no top-level `scripts/`, `mjcf/`, `urdf/`, or `meshes/` directory. Use the `astro` CLI and the manifest rather than hard-coded checkout-root paths.

## Common Commands

Compute keyframe body heights:

```bash
uv run astro heights --config knees_bent
```

Launch the PD parameter editor for [Robot Configuration](docs/robot_configuration.md):

```bash
uv run astro pd-tool
```

Generate an Astro URDF with extension capsule collision tags:

```bash
uv run astro urdf-capsules --output /tmp/astro_v1_capsules.urdf
```

## Asset Variants

Robot-description variants are declared in `src/astro_description/robots/astro/manifest.json`.

| Variant | DOFs | URDF | MJCF | Status |
|---|---:|---|---|---|
| `astro_v1` | 30 | `urdf/astro_v1.urdf` | `mjcf/astro_v1.xml` | current |
| `astro_v1_27dof` | 27 | `urdf/astro_v1_27dof.urdf` | `mjcf/astro_v1_27dof.xml` | current |
| `astro_with_racket` | 30 | `urdf/astro_with_racket.urdf` | - | variant |

Add or retire URDF/MJCF files by updating the manifest first, then run:

```bash
uv run astro validate
uv run astro mujoco --variant <variant> --check
```
