# Astro Robot Description

This repository packages the Dobot **Astro** humanoid robot descriptions as a `uv`-managed Python project. URDF is the maintained source format. Astro V1 retains MJCF and Isaac assets for legacy tooling; Astro V2 is URDF-only.

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

Robot assets are grouped first by Astro version. This lets one package release expose both robot generations without making a Git branch part of the runtime interface.

```text
src/astro_description/
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
  commands/               # implementations behind `uv run astro ...`
  tools/                  # reusable utilities
docs/
  robot_configuration.md  # detailed robot configuration reference
```

There is intentionally no top-level `scripts/`, `mjcf/`, `urdf/`, or `meshes/` directory. Use the `astro` CLI and the manifest rather than hard-coded checkout-root paths. V2 ships as a URDF-only description with its referenced meshes.

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

Robot-description variants are declared in `src/astro_description/assets/manifest.json`.

| Variant | DOFs | URDF | MJCF | Status |
|---|---:|---|---|---|
| `astro_v1` | 30 | `astro_v1/urdf/astro_v1.urdf` | `astro_v1/legacy/mjcf/astro_v1.xml` | legacy |
| `astro_v1_27dof` | 27 | `astro_v1/urdf/astro_v1_27dof.urdf` | `astro_v1/legacy/mjcf/astro_v1_27dof.xml` | legacy |
| `astro_with_racket` | 30 | `astro_v1/urdf/astro_with_racket.urdf` | - | variant |
| `astro_v2` | 30 | `astro_v2/urdf/astro_v2.urdf` | - | current |

Add or retire a version's URDF files by updating the manifest first, then run:

```bash
uv run astro validate
uv run astro mujoco --variant <variant> --check
```
