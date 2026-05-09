# PD Parameter Tool Design

Date: 2026-04-30

## Goal

Build a small local tool for interactively computing Astro actuator PD parameters. The user can tune natural frequency `f` in Hz and damping ratio per joint group, inspect computed stiffness `Kp`, damping `Kd`, and action scale, then update only the `Joint Parameters` table in `README.md`.

## Non-Goals

- Do not update `config.yaml`.
- Do not update `isaac_config/astro_delay.py`.
- Do not run a robot simulation or controller loop.
- Do not introduce a database or persistent project state outside `README.md`.

## User Workflow

1. Run the tool from the Astro repo, for example `python3 scripts/pd_params_tool.py`.
2. Open the local browser page printed by the script.
3. Edit `f` and damping ratio for each joint group row.
4. Review live computed values for `Kp`, `Kd`, and action scale.
5. Click `Preview README Diff` to inspect the markdown table change.
6. Click `Update README.md` to replace only the `### Joint Parameters` table rows.

## Formulas

For each row:

```text
omega = 2 * pi * f
effective_armature = armature * multiplier
Kp = effective_armature * omega^2
Kd = 2 * damping_ratio * effective_armature * omega
action_scale = 0.25 * effort_limit / Kp
```

The table uses these fixed precision rules:

- `Kp`: 3 decimals
- `Kd`: 3 decimals
- `Action Scale`: 4 decimals
- `f`: 1 decimal

## Architecture

The tool is a single local Python script under `scripts/` using the Python standard library. It serves a browser UI through `http.server`, exposes small JSON endpoints, and writes `README.md` only after validation.

Core units:

- `JointParameterRow`: structured representation of one README table row.
- `compute_pd(row)`: pure function for `Kp`, `Kd`, and action scale.
- `read_joint_parameters_table(readme_text)`: parses only the `### Joint Parameters` markdown table.
- `render_joint_parameters_table(rows)`: generates replacement markdown rows.
- `replace_joint_parameters_table(readme_text, rows)`: replaces only the target table.
- HTTP handlers:
  - `GET /`: returns the UI.
  - `GET /api/table`: returns parsed rows and computed values.
  - `POST /api/preview`: returns the markdown diff.
  - `POST /api/apply`: validates and writes `README.md`.

## UI Design

The page is a compact table editor:

- One row per existing `README.md` joint group.
- Read-only columns: row number, joint pattern, motor, multiplier, effort, velocity.
- Editable columns: `f` and damping ratio.
- Computed columns: `Kp`, `Kd`, and action scale.
- Buttons: `Preview README Diff`, `Update README.md`, and a reset/reload control.
- Status panel: table validation state, write result, and error messages.

The UI should be utilitarian and dense enough to compare joint groups quickly. It should not be a landing page.

## README Update Boundary

The apply operation must:

- Locate the heading `### Joint Parameters`.
- Locate the markdown table immediately under that heading.
- Preserve the table header and alignment row.
- Replace only data rows in that table.
- Preserve all other README content exactly, including the formulas, notes, comparison table, and other sections.

The apply operation must refuse to write if the table structure is not recognized or if the submitted row count does not match the parsed row count.

## Validation And Errors

The tool must reject:

- Missing or malformed `README.md`.
- Missing `### Joint Parameters` heading.
- Missing required table columns.
- Non-positive natural frequency.
- Negative damping ratio.
- Missing armature, multiplier, or effort values.
- Mismatched row count during preview or apply.

Errors should be shown in the page and returned as JSON from API endpoints. Failed writes must leave `README.md` unchanged.

## Testing

Add focused tests for:

- PD formula computation, including multiplier handling.
- Action scale computation.
- README table parsing.
- README table replacement that leaves surrounding sections unchanged.
- Validation failures for malformed input.

If the repo does not already have a test framework, use `unittest` with standard-library-only tests so the tool remains easy to run in this checkout.

## Implementation Shape

The implementation should start with one standard-library Python script at `scripts/pd_params_tool.py` and one focused test file. Pure helper functions should stay importable from the script so tests can exercise formula and README update logic without starting the HTTP server.
