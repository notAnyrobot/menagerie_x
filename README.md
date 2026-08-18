# Menagerie X

Menagerie X is a local catalog of robot-description assets and a browser Workbench for inspecting them. It packages versioned URDF and MJCF models, meshes, and metadata behind a manifest-driven Python CLI.

It can:

- browse the available robot variants;
- validate their manifests, descriptions, and mesh paths; and
- launch the local Workbench to visualize models and review or edit collisions for supported editions.

## Quick start

From this checkout, install the Python environment and the Workbench's browser dependencies:

```bash
uv sync
npm install --prefix src/menagerie_x/workbench/web
```

Browse the catalog and validate its packaged assets:

```bash
uv run menagerie_x variants
uv run menagerie_x validate
```

Launch the Workbench, then open <http://127.0.0.1:8000>:

```bash
uv run menagerie_x workbench
```

The Workbench listens on localhost by default. Select a variant to inspect it, run validation, and work with collision geometry where the selected source format and edition support it.

## Asset formats

The catalog supports both URDF and MJCF descriptions, depending on the robot version. Astro V2 is maintained from URDF; legacy Astro assets retain MJCF and Isaac material. MJCF-backed variants can also be checked or opened in native MuJoCo:

```bash
uv run menagerie_x mujoco --variant <variant> --check
```

Atom P3 is MJCF-only because its imported bundle does not include a URDF. It is available for inspection and simulation, but its default model has no actuator declarations (`nu=0`).

## Local scope

Menagerie X runs from this checkout and serves the Workbench locally; it does not provide a hosted catalog or remote robot-control service.
