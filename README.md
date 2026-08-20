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

The Workbench listens on localhost by default. Select a robot variant, then one logical edition. Editions can offer URDF, MJCF, or both; the viewer and collision editor require the selected edition to provide MJCF.

**Export URDF** transfers standard primitive collisions from the selected saved MJCF description into a downloaded copy of that edition's canonical URDF. It never overwrites catalog files, excludes unsaved collision-draft edits, and blocks the download when a collision cannot be represented safely. Version one requires an edition with both URDF and MJCF and does not convert MJCF-only robots or mesh collisions.

## Asset formats

Each immediate directory under `src/menagerie_x/assets/` is one robot variant. Its shallow `urdf/`, `mjcf/`, and shared `meshes/` directories hold format files named `<variant>_<dof>_<collision>.urdf` or `<variant>_<dof>_<collision>.xml` when collision geometry distinguishes editions. The manifest defines which files form one logical edition.

The catalog supports both URDF and MJCF descriptions, depending on the selected edition. Astro P2 is maintained from URDF; legacy Astro assets retain MJCF and Isaac material. MJCF-backed editions can also be checked or opened in native MuJoCo:

```bash
uv run menagerie_x mujoco --variant <variant> --check
```

Atom P3 is MJCF-only because its imported bundle does not include a URDF. It is available for inspection and simulation, but its default model has no actuator declarations (`nu=0`).

## Local scope

Menagerie X runs from this checkout and serves the Workbench locally; it does not provide a hosted catalog or remote robot-control service.
