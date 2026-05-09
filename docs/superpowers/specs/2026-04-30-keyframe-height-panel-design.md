# Keyframe Height Panel Design

Date: 2026-04-30

## Goal

Extend the local PD parameter tool with a Keyframe Heights panel. The panel lets the user select an Astro preset keyframe, computes body heights from MuJoCo forward kinematics, and displays a rendered still image of the selected pose.

## Non-Goals

- Do not change PD parameter table update behavior.
- Do not update `README.md` from the height panel.
- Do not add a native MuJoCo viewer button in v1.
- Do not implement multiple robot embodiments in v1.
- Do not require importing `android_playground` package paths for the standalone Astro checkout.

## Dependency Management

Add a minimal `pyproject.toml` for this checkout and manage the Python environment with `uv`.

The project must declare `mujoco` as a dependency. Do not add an image-encoding dependency in v1; encode the MuJoCo RGB frame as a simple browser-supported BMP data URL using the Python standard library.

Expected user commands:

```bash
uv sync
uv run python scripts/pd_params_tool.py --no-browser
uv run python -m unittest discover -s tests -v
```

## File Layout

Move the existing Astro-specific height script:

```text
constants/calc_heights.py -> scripts/calc_heights.py
```

After the move, `scripts/calc_heights.py` becomes an importable backend for height computation and snapshot rendering. It should retain a CLI mode for direct debugging.

## Embodiment Model

Implement a generic architecture with one Astro embodiment config in v1.

The embodiment config should define:

- `name`: `"astro"`
- `mjcf_path`: `mjcf/astro_v1.xml`
- `floating_base_joint`: `"floating_base_joint"`
- `foot_collision_geom_names`: generated from left/right `foot1_collision` through `foot12_collision`
- `body_height_targets`: `pelvis`, `torso_link`, `left_shoulder_pitch_link`, `right_shoulder_pitch_link`
- `keyframes`: `zero`, `home`, `t_pose`, `knees_bent`

The config should make it clear how a future embodiment would provide a different XML path, foot geoms, body targets, and keyframes.

## Keyframe Source

The Astro keyframes should be loaded from `constants/astro_constants.py`:

- `ZERO_KEYFRAME`
- `HOME_KEYFRAME`
- `T_POSE_KEYFRAME`
- `KNEES_BENT_KEYFRAME`

The height backend should apply each keyframe's floating-base position and regex-based `joint_pos` mapping in the same way as the current `constants/calc_heights.py` script.

Do not import `constants/astro_constants.py` at runtime for height extraction in v1. That file belongs to a larger package context and imports modules that are not part of this standalone checkout. Instead, parse the four keyframe definitions from the source file with Python's `ast` module and support the literal structures used by these keyframes:

- `pos=(...)`
- `joint_pos={...}`
- `joint_vel={...}`

If a future keyframe uses non-literal expressions that the parser cannot evaluate safely, the backend should raise a clear error naming the unsupported keyframe and field.

## Height Computation

For the selected keyframe:

1. Load the MuJoCo model from the embodiment's MJCF.
2. Initialize `qpos` from `model.qpos0`.
3. Apply floating-base `pos`.
4. Apply all regex-matched 1-DOF joint positions from `joint_pos`.
5. Run `mujoco.mj_forward`.
6. Find the minimum z height among the configured foot collision geoms.
7. Shift floating-base z so the lowest foot collision geom is at z=0.
8. Run `mujoco.mj_forward` again.
9. Return body z heights for:
   - `pelvis`
   - `torso_link`
   - `left_shoulder_pitch_link`
   - `right_shoulder_pitch_link`

The response should also include:

- `base_z_after_alignment`
- `feet_min_z_before_alignment`
- `feet_min_z_after_alignment`

## Snapshot Rendering

For each selected keyframe, render one still image using MuJoCo's renderer after ground alignment.

The web API should return the image as a browser-displayable data URL: `data:image/bmp;base64,...`. The BMP encoder should be local standard-library code that converts MuJoCo's RGB frame into a 24-bit BMP.

The snapshot is a preview aid, not a physics simulation. It should be deterministic for a given keyframe.

## Tool API

Add endpoints to `scripts/pd_params_tool.py`:

- `GET /api/keyframes`
  - returns available keyframes for the default Astro embodiment
- `GET /api/keyframe-heights?name=<keyframe>`
  - returns heights, alignment diagnostics, and rendered image data for the selected keyframe

Existing PD endpoints must keep their current behavior:

- `GET /api/table`
- `POST /api/preview`
- `POST /api/apply`

## UI Design

Keep the existing PD editor and add a compact panel named `Keyframe Heights`.

The panel should include:

- keyframe dropdown with `zero`, `home`, `t_pose`, `knees_bent`
- `Reload keyframes` action
- body height rows:
  - `pelvis`
  - `torso_link`
  - `left_shoulder_pitch_link`
  - `right_shoulder_pitch_link`
- alignment diagnostics in a small status area
- rendered MuJoCo snapshot for the selected keyframe

The panel should fit next to or below the PD table without turning the tool into a landing page. It should be useful for repeated engineering inspection.

## Error Handling

The tool should show clear UI errors when:

- MuJoCo cannot import.
- The MJCF path is missing.
- A configured body, joint, or foot geom name is missing.
- A keyframe name is unknown.
- Snapshot rendering fails.

Failures in the height panel must not break the PD table editor. The PD table should still load and remain usable if height computation fails.

## Testing

Add tests for:

- Astro keyframe listing.
- Applying regex-based joint positions.
- Height target config includes pelvis, torso, and both shoulder pitch links.
- Unknown keyframe rejection.
- `/api/keyframes` and `/api/keyframe-heights` response shape.
- Existing PD table tests still passing.

MuJoCo-dependent tests should run with `uv run`. Tests must use offscreen rendering. If offscreen rendering is unavailable in the local environment, the implementation plan should separate pure parser/API tests from live MuJoCo smoke validation and state the exact skipped command.

## Migration Notes

Because this checkout is not a Git repository, commit steps cannot run here. The implementation should still keep changes scoped and list created/moved files clearly.

The previous direct command `python3 constants/calc_heights.py --config knees_bent` currently fails in this environment because `mujoco` is not available on the default Python path. The new `uv` workflow should make the expected environment explicit.
