# Keyframe Height Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the local PD parameter tool with a MuJoCo-backed Keyframe Heights panel that loads Astro preset keyframes, reports pelvis/torso/left shoulder/right shoulder heights, and renders a browser snapshot.

**Architecture:** Add a minimal `uv` project, move the current Astro-only height script to `scripts/calc_heights.py`, and refactor it into a generic embodiment backend with one Astro config. `scripts/pd_params_tool.py` imports that backend for `/api/keyframes` and `/api/keyframe-heights`, while preserving all existing PD table behavior.

**Tech Stack:** Python 3.12, `uv`, `mujoco`, standard-library `unittest`, `http.server`, `ast`, `base64`, browser JavaScript.

---

## File Structure

- Create `pyproject.toml`: minimal `uv` project declaring `mujoco`.
- Move `constants/calc_heights.py` to `scripts/calc_heights.py`: generic height/render backend plus CLI.
- Modify `scripts/pd_params_tool.py`: add keyframe API endpoints and UI panel.
- Modify `tests/test_pd_params_tool.py`: API/UI smoke tests for the new panel.
- Create `tests/test_calc_heights.py`: keyframe parser, config, BMP encoder, and pure helper tests.
- Do not change `README.md` behavior from the height panel.
- Do not modify `config.yaml` or `isaac_config/astro_delay.py`.

This checkout is not a Git repository. Run commit steps only if `git status --short --branch` succeeds in the environment where the plan is executed.

## Task 1: Minimal `uv` Project

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Create minimal project metadata**

Create `pyproject.toml` with:

```toml
[project]
name = "astro-menagerie-tools"
version = "0.1.0"
description = "Local tools for the Dobot Astro menagerie checkout"
requires-python = ">=3.12"
dependencies = [
    "mujoco>=3.2.0",
]

[tool.uv]
package = false
```

- [ ] **Step 2: Sync dependencies**

Run:

```bash
uv sync
```

Expected: `uv` creates or updates `.venv` and resolves `mujoco`.

- [ ] **Step 3: Verify MuJoCo imports under `uv`**

Run:

```bash
uv run python - <<'PY'
import mujoco
print(mujoco.__version__)
PY
```

Expected: prints the installed MuJoCo version and exits 0.

- [ ] **Step 4: Conditional commit**

If Git is available:

```bash
git add pyproject.toml uv.lock
git commit -m "build: add uv project for astro tools"
```

Expected in this checkout: skip because Git is unavailable.

## Task 2: Move And Refactor Height Backend Core

**Files:**
- Move: `constants/calc_heights.py` -> `scripts/calc_heights.py`
- Create: `tests/test_calc_heights.py`

- [ ] **Step 1: Write failing pure backend tests**

Create `tests/test_calc_heights.py` with:

```python
import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "calc_heights.py"
SPEC = importlib.util.spec_from_file_location("calc_heights", MODULE_PATH)
calc_heights = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = calc_heights
assert SPEC.loader is not None
SPEC.loader.exec_module(calc_heights)


class KeyframeParserTests(unittest.TestCase):
    def test_list_astro_keyframes_from_constants_source(self):
        keyframes = calc_heights.load_astro_keyframes(ROOT / "constants" / "astro_constants.py")

        self.assertEqual(sorted(keyframes), ["home", "knees_bent", "t_pose", "zero"])
        self.assertEqual(keyframes["knees_bent"].pos, (0.0, 0.0, 0.745))
        self.assertEqual(keyframes["knees_bent"].joint_pos[".*_knee_joint"], 0.669)
        self.assertEqual(keyframes["home"].joint_pos[".*_elbow_joint"], 1.5)

    def test_unknown_keyframe_raises_clear_error(self):
        config = calc_heights.create_astro_embodiment_config(ROOT)

        with self.assertRaisesRegex(calc_heights.HeightToolError, "unknown keyframe"):
            calc_heights.get_keyframe(config, "missing")


class EmbodimentConfigTests(unittest.TestCase):
    def test_astro_config_declares_expected_targets(self):
        config = calc_heights.create_astro_embodiment_config(ROOT)

        self.assertEqual(config.name, "astro")
        self.assertEqual(config.mjcf_path, ROOT / "mjcf" / "astro_v1.xml")
        self.assertEqual(config.floating_base_joint, "floating_base_joint")
        self.assertIn("pelvis", config.body_height_targets)
        self.assertIn("torso_link", config.body_height_targets)
        self.assertIn("left_shoulder_pitch_link", config.body_height_targets)
        self.assertIn("right_shoulder_pitch_link", config.body_height_targets)
        self.assertIn("left_foot1_collision", config.foot_collision_geom_names)
        self.assertIn("right_foot12_collision", config.foot_collision_geom_names)

    def test_bmp_data_url_has_expected_prefix(self):
        rgb = bytes([
            255, 0, 0,
            0, 255, 0,
            0, 0, 255,
            255, 255, 255,
        ])

        data_url = calc_heights.rgb_to_bmp_data_url(rgb, width=2, height=2)

        self.assertTrue(data_url.startswith("data:image/bmp;base64,"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify they fail on missing new API**

Run:

```bash
uv run python -m unittest tests.test_calc_heights -v
```

Expected: fail with missing functions or old Astro-only imports.

- [ ] **Step 3: Move the script**

Run:

```bash
mv constants/calc_heights.py scripts/calc_heights.py
```

Expected: `constants/calc_heights.py` no longer exists and `scripts/calc_heights.py` exists.

- [ ] **Step 4: Replace `scripts/calc_heights.py` with generic backend skeleton**

Replace `scripts/calc_heights.py` with:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import base64
import dataclasses
import re
import struct
from pathlib import Path
from typing import Any


class HeightToolError(ValueError):
    """Raised when a keyframe, model, or requested body cannot be processed."""


@dataclasses.dataclass(frozen=True)
class KeyframeConfig:
    name: str
    pos: tuple[float, float, float]
    joint_pos: dict[str, float]
    joint_vel: dict[str, float]


@dataclasses.dataclass(frozen=True)
class EmbodimentConfig:
    name: str
    mjcf_path: Path
    constants_path: Path
    floating_base_joint: str
    foot_collision_geom_names: tuple[str, ...]
    body_height_targets: tuple[str, ...]
    keyframes: dict[str, KeyframeConfig]


@dataclasses.dataclass(frozen=True)
class HeightComputationResult:
    embodiment: str
    keyframe: str
    body_heights: dict[str, float]
    base_z_after_alignment: float
    feet_min_z_before_alignment: float
    feet_min_z_after_alignment: float
    image_data_url: str | None = None


KEYFRAME_NAMES = {
    "ZERO_KEYFRAME": "zero",
    "HOME_KEYFRAME": "home",
    "T_POSE_KEYFRAME": "t_pose",
    "KNEES_BENT_KEYFRAME": "knees_bent",
}

ASTRO_BODY_HEIGHT_TARGETS = (
    "pelvis",
    "torso_link",
    "left_shoulder_pitch_link",
    "right_shoulder_pitch_link",
)


def _literal_eval_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Name) and node.id == "ASTRO_MOTION_SAFE_Z_HEIGHT":
        return 0.745
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError) as exc:
        raise HeightToolError(f"unsupported literal expression: {ast.dump(node)}") from exc


def _parse_initial_state_call(name: str, call: ast.Call) -> KeyframeConfig:
    fields: dict[str, Any] = {}
    for keyword in call.keywords:
        if keyword.arg in {"pos", "joint_pos", "joint_vel"}:
            fields[keyword.arg] = _literal_eval_node(keyword.value)
    if "pos" not in fields or "joint_pos" not in fields or "joint_vel" not in fields:
        raise HeightToolError(f"keyframe {name} is missing pos, joint_pos, or joint_vel")
    pos = tuple(float(value) for value in fields["pos"])
    if len(pos) != 3:
        raise HeightToolError(f"keyframe {name} pos must have length 3")
    return KeyframeConfig(
        name=KEYFRAME_NAMES[name],
        pos=(pos[0], pos[1], pos[2]),
        joint_pos={str(key): float(value) for key, value in dict(fields["joint_pos"]).items()},
        joint_vel={str(key): float(value) for key, value in dict(fields["joint_vel"]).items()},
    )


def load_astro_keyframes(constants_path: Path) -> dict[str, KeyframeConfig]:
    tree = ast.parse(constants_path.read_text(encoding="utf-8"), filename=str(constants_path))
    keyframes: dict[str, KeyframeConfig] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in KEYFRAME_NAMES:
            continue
        if not isinstance(node.value, ast.Call):
            raise HeightToolError(f"keyframe {target.id} must be an InitialStateCfg call")
        parsed = _parse_initial_state_call(target.id, node.value)
        keyframes[parsed.name] = parsed
    missing = sorted(set(KEYFRAME_NAMES.values()) - set(keyframes))
    if missing:
        raise HeightToolError(f"missing keyframes: {', '.join(missing)}")
    return keyframes


def create_astro_embodiment_config(repo_root: Path) -> EmbodimentConfig:
    foot_geoms = tuple(
        f"{side}_foot{i}_collision"
        for side in ("left", "right")
        for i in range(1, 13)
    )
    constants_path = repo_root / "constants" / "astro_constants.py"
    return EmbodimentConfig(
        name="astro",
        mjcf_path=repo_root / "mjcf" / "astro_v1.xml",
        constants_path=constants_path,
        floating_base_joint="floating_base_joint",
        foot_collision_geom_names=foot_geoms,
        body_height_targets=ASTRO_BODY_HEIGHT_TARGETS,
        keyframes=load_astro_keyframes(constants_path),
    )


def get_keyframe(config: EmbodimentConfig, name: str) -> KeyframeConfig:
    try:
        return config.keyframes[name]
    except KeyError as exc:
        valid = ", ".join(sorted(config.keyframes))
        raise HeightToolError(f"unknown keyframe {name!r}; valid keyframes: {valid}") from exc


def rgb_to_bmp_data_url(rgb: bytes, width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        raise HeightToolError("BMP width and height must be positive")
    expected = width * height * 3
    if len(rgb) != expected:
        raise HeightToolError(f"RGB buffer has {len(rgb)} bytes, expected {expected}")
    row_stride = ((width * 3 + 3) // 4) * 4
    pixel_size = row_stride * height
    file_size = 14 + 40 + pixel_size
    rows = []
    for y in range(height - 1, -1, -1):
        start = y * width * 3
        row = bytearray()
        for x in range(width):
            r, g, b = rgb[start + x * 3 : start + x * 3 + 3]
            row.extend((b, g, r))
        row.extend(b"\\x00" * (row_stride - width * 3))
        rows.append(bytes(row))
    header = (
        b"BM"
        + struct.pack("<IHHI", file_size, 0, 0, 54)
        + struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, pixel_size, 2835, 2835, 0, 0)
    )
    encoded = base64.b64encode(header + b"".join(rows)).decode("ascii")
    return f"data:image/bmp;base64,{encoded}"


def list_keyframes(config: EmbodimentConfig) -> list[dict[str, str]]:
    return [{"name": name, "label": name} for name in sorted(config.keyframes)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute body heights for an embodied MuJoCo keyframe.")
    parser.add_argument("--config", default="knees_bent", choices=("home", "zero", "knees_bent", "t_pose"))
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    config = create_astro_embodiment_config(args.repo_root)
    keyframe = get_keyframe(config, args.config)
    print(f"config: {keyframe.name}")
    print("MuJoCo height computation is added in the next task.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run pure backend tests**

Run:

```bash
uv run python -m unittest tests.test_calc_heights -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Conditional commit**

If Git is available:

```bash
git add pyproject.toml uv.lock scripts/calc_heights.py tests/test_calc_heights.py
git rm constants/calc_heights.py
git commit -m "feat: add generic keyframe height backend skeleton"
```

Expected in this checkout: skip because Git is unavailable.

## Task 3: MuJoCo Height Computation And Snapshot Rendering

**Files:**
- Modify: `tests/test_calc_heights.py`
- Modify: `scripts/calc_heights.py`

- [ ] **Step 1: Add failing live MuJoCo tests**

Append this test class above the `if __name__ == "__main__":` block in `tests/test_calc_heights.py`:

```python

class MuJoCoHeightTests(unittest.TestCase):
    def test_compute_keyframe_heights_returns_all_target_bodies(self):
        config = calc_heights.create_astro_embodiment_config(ROOT)

        result = calc_heights.compute_keyframe_heights(config, "knees_bent", render=False)

        self.assertEqual(result.embodiment, "astro")
        self.assertEqual(result.keyframe, "knees_bent")
        self.assertEqual(set(result.body_heights), set(config.body_height_targets))
        self.assertGreater(result.body_heights["pelvis"], 0.1)
        self.assertGreater(result.body_heights["torso_link"], result.body_heights["pelvis"])
        self.assertAlmostEqual(result.feet_min_z_after_alignment, 0.0, places=6)

    def test_compute_keyframe_heights_can_render_bmp_data_url(self):
        config = calc_heights.create_astro_embodiment_config(ROOT)

        result = calc_heights.compute_keyframe_heights(config, "zero", render=True, width=160, height=120)

        self.assertIsNotNone(result.image_data_url)
        self.assertTrue(result.image_data_url.startswith("data:image/bmp;base64,"))
```

- [ ] **Step 2: Run tests and verify MuJoCo functions are missing**

Run:

```bash
uv run python -m unittest tests.test_calc_heights -v
```

Expected: fail with missing `compute_keyframe_heights`.

- [ ] **Step 3: Implement MuJoCo helpers and rendering**

Append this code to `scripts/calc_heights.py` above `main()`:

```python

def _import_mujoco():
    try:
        import mujoco  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as exc:
        raise HeightToolError("mujoco and numpy must be installed; run `uv sync` first") from exc
    return mujoco, np


def _joint_qpos_dof(mujoco: Any, joint_type: int) -> int:
    if joint_type == mujoco.mjtJoint.mjJNT_FREE:
        return 7
    if joint_type == mujoco.mjtJoint.mjJNT_BALL:
        return 4
    if joint_type in (mujoco.mjtJoint.mjJNT_HINGE, mujoco.mjtJoint.mjJNT_SLIDE):
        return 1
    raise HeightToolError(f"unsupported joint type: {joint_type}")


def _set_named_joint_qpos(mujoco: Any, model: Any, qpos: Any, joint_name: str, value: float) -> None:
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if joint_id < 0:
        raise HeightToolError(f"joint not found: {joint_name}")
    dof = _joint_qpos_dof(mujoco, int(model.jnt_type[joint_id]))
    if dof != 1:
        raise HeightToolError(f"joint {joint_name} has qpos dof={dof}; expected 1")
    qpos[int(model.jnt_qposadr[joint_id])] = value


def _single_dof_joint_names(mujoco: Any, model: Any) -> list[str]:
    names: list[str] = []
    for joint_id in range(model.njnt):
        if _joint_qpos_dof(mujoco, int(model.jnt_type[joint_id])) != 1:
            continue
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
        if name is not None:
            names.append(name)
    return names


def _set_floating_base_pos(mujoco: Any, model: Any, qpos: Any, joint_name: str, pos: tuple[float, float, float]) -> int:
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if joint_id < 0:
        raise HeightToolError(f"floating-base joint not found: {joint_name}")
    qpos_adr = int(model.jnt_qposadr[joint_id])
    qpos[qpos_adr : qpos_adr + 3] = pos
    return qpos_adr


def _apply_keyframe_to_qpos(mujoco: Any, np: Any, model: Any, config: EmbodimentConfig, keyframe: KeyframeConfig) -> Any:
    qpos = np.array(model.qpos0, copy=True)
    _set_floating_base_pos(mujoco, model, qpos, config.floating_base_joint, keyframe.pos)
    joint_names = _single_dof_joint_names(mujoco, model)
    for pattern, value in keyframe.joint_pos.items():
        regex = re.compile(pattern)
        for joint_name in joint_names:
            if regex.fullmatch(joint_name):
                _set_named_joint_qpos(mujoco, model, qpos, joint_name, float(value))
    return qpos


def _ids_by_name(mujoco: Any, model: Any, obj_type: Any, names: tuple[str, ...]) -> list[int]:
    ids: list[int] = []
    for name in names:
        obj_id = mujoco.mj_name2id(model, obj_type, name)
        if obj_id < 0:
            raise HeightToolError(f"name not found in model: {name}")
        ids.append(int(obj_id))
    return ids


def _render_model_data(mujoco: Any, np: Any, model: Any, data: Any, width: int, height: int) -> str:
    renderer = mujoco.Renderer(model, height=height, width=width)
    try:
        renderer.update_scene(data)
        rgb = renderer.render()
    finally:
        renderer.close()
    return rgb_to_bmp_data_url(np.asarray(rgb, dtype=np.uint8).tobytes(), width=width, height=height)


def compute_keyframe_heights(
    config: EmbodimentConfig,
    keyframe_name: str,
    *,
    render: bool = False,
    width: int = 360,
    height: int = 280,
) -> HeightComputationResult:
    mujoco, np = _import_mujoco()
    if not config.mjcf_path.exists():
        raise HeightToolError(f"MJCF path does not exist: {config.mjcf_path}")
    keyframe = get_keyframe(config, keyframe_name)
    model = mujoco.MjModel.from_xml_path(str(config.mjcf_path))
    data = mujoco.MjData(model)

    qpos = _apply_keyframe_to_qpos(mujoco, np, model, config, keyframe)
    data.qpos[:] = qpos
    mujoco.mj_forward(model, data)

    foot_ids = _ids_by_name(mujoco, model, mujoco.mjtObj.mjOBJ_GEOM, config.foot_collision_geom_names)
    feet_min_z_before = min(float(data.geom_xpos[geom_id, 2]) for geom_id in foot_ids)

    qpos_aligned = np.array(qpos, copy=True)
    qpos_adr = _set_floating_base_pos(mujoco, model, qpos_aligned, config.floating_base_joint, keyframe.pos)
    qpos_aligned[qpos_adr + 2] -= feet_min_z_before
    data.qpos[:] = qpos_aligned
    mujoco.mj_forward(model, data)

    feet_min_z_after = min(float(data.geom_xpos[geom_id, 2]) for geom_id in foot_ids)
    body_ids = _ids_by_name(mujoco, model, mujoco.mjtObj.mjOBJ_BODY, config.body_height_targets)
    body_heights = {
        body_name: float(data.xpos[body_id, 2])
        for body_name, body_id in zip(config.body_height_targets, body_ids, strict=True)
    }
    image_data_url = _render_model_data(mujoco, np, model, data, width, height) if render else None
    return HeightComputationResult(
        embodiment=config.name,
        keyframe=keyframe.name,
        body_heights=body_heights,
        base_z_after_alignment=float(qpos_aligned[qpos_adr + 2]),
        feet_min_z_before_alignment=feet_min_z_before,
        feet_min_z_after_alignment=feet_min_z_after,
        image_data_url=image_data_url,
    )


def result_to_json(result: HeightComputationResult) -> dict[str, Any]:
    return {
        "embodiment": result.embodiment,
        "keyframe": result.keyframe,
        "body_heights": result.body_heights,
        "base_z_after_alignment": result.base_z_after_alignment,
        "feet_min_z_before_alignment": result.feet_min_z_before_alignment,
        "feet_min_z_after_alignment": result.feet_min_z_after_alignment,
        "image_data_url": result.image_data_url,
    }
```

- [ ] **Step 4: Update CLI to call real height computation**

Replace the body of `main()` after `config = ...` with:

```python
    result = compute_keyframe_heights(config, args.config, render=False)
    print(f"config: {result.keyframe}")
    for body_name, height_m in result.body_heights.items():
        print(f"{body_name}_height_from_ground: {height_m:.6f} m")
    print(f"floating_base_z_after_alignment: {result.base_z_after_alignment:.6f} m")
    print(f"feet_min_z_before_alignment: {result.feet_min_z_before_alignment:.6f} m")
    print(f"feet_min_z_after_alignment:  {result.feet_min_z_after_alignment:.6f} m")
```

- [ ] **Step 5: Run MuJoCo backend tests**

Run:

```bash
uv run python -m unittest tests.test_calc_heights -v
```

Expected: 6 tests pass. If offscreen rendering fails due to local GL configuration, keep the non-render height test passing, note the exact renderer error, and continue only after deciding whether to set `MUJOCO_GL=egl` or `MUJOCO_GL=osmesa`.

- [ ] **Step 6: Run CLI smoke**

Run:

```bash
uv run python scripts/calc_heights.py --config knees_bent
```

Expected: prints `config: knees_bent` plus heights for `pelvis`, `torso_link`, `left_shoulder_pitch_link`, and `right_shoulder_pitch_link`.

- [ ] **Step 7: Conditional commit**

If Git is available:

```bash
git add scripts/calc_heights.py tests/test_calc_heights.py
git commit -m "feat: compute keyframe body heights with mujoco"
```

Expected in this checkout: skip because Git is unavailable.

## Task 4: API Integration In PD Tool

**Files:**
- Modify: `tests/test_pd_params_tool.py`
- Modify: `scripts/pd_params_tool.py`

- [ ] **Step 1: Add failing API helper tests**

Append this class above `UiSmokeTests` in `tests/test_pd_params_tool.py`:

```python

class KeyframeApiTests(unittest.TestCase):
    def test_keyframes_response_lists_astro_keyframes(self):
        response = pd_params_tool.keyframes_response(ROOT)

        self.assertEqual(response["ok"], True)
        self.assertEqual([item["name"] for item in response["keyframes"]], ["home", "knees_bent", "t_pose", "zero"])

    def test_keyframe_heights_response_rejects_unknown_keyframe(self):
        with self.assertRaisesRegex(pd_params_tool.ToolError, "unknown keyframe"):
            pd_params_tool.keyframe_heights_response(ROOT, "missing", render=False)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run python -m unittest tests.test_pd_params_tool -v
```

Expected: fail with missing `keyframes_response` and `keyframe_heights_response`.

- [ ] **Step 3: Import backend and add API helper functions**

In `scripts/pd_params_tool.py`, add these imports near the top:

```python
import importlib.util
import urllib.parse
```

Add this helper near the existing response helpers:

```python

def _repo_root_from_readme(readme_path: pathlib.Path) -> pathlib.Path:
    return readme_path.resolve().parent


def _load_height_backend():
    backend_path = pathlib.Path(__file__).with_name("calc_heights.py")
    spec = importlib.util.spec_from_file_location("calc_heights", backend_path)
    if spec is None or spec.loader is None:
        raise ToolError(f"could not load height backend from {backend_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def keyframes_response(repo_root: pathlib.Path) -> dict[str, Any]:
    backend = _load_height_backend()
    config = backend.create_astro_embodiment_config(repo_root)
    return make_success_response({"keyframes": backend.list_keyframes(config)})


def keyframe_heights_response(repo_root: pathlib.Path, keyframe_name: str, *, render: bool = True) -> dict[str, Any]:
    backend = _load_height_backend()
    try:
        config = backend.create_astro_embodiment_config(repo_root)
        result = backend.compute_keyframe_heights(config, keyframe_name, render=render)
        return make_success_response({"result": backend.result_to_json(result)})
    except Exception as exc:
        raise ToolError(str(exc)) from exc
```

- [ ] **Step 4: Add HTTP routes**

In `PDParameterRequestHandler.do_GET`, after the `/api/table` block, add:

```python
            if self.path == "/api/keyframes":
                self._send_json(HTTPStatus.OK, keyframes_response(_repo_root_from_readme(self.readme_path)))
                return
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/api/keyframe-heights":
                params = urllib.parse.parse_qs(parsed.query)
                keyframe_name = params.get("name", ["knees_bent"])[0]
                self._send_json(
                    HTTPStatus.OK,
                    keyframe_heights_response(_repo_root_from_readme(self.readme_path), keyframe_name, render=True),
                )
                return
```

- [ ] **Step 5: Run API helper tests**

Run:

```bash
uv run python -m unittest tests.test_pd_params_tool -v
```

Expected: all existing PD tests plus the new keyframe API helper tests pass. If render is slow, tests use `render=False` and stay fast.

- [ ] **Step 6: Conditional commit**

If Git is available:

```bash
git add scripts/pd_params_tool.py tests/test_pd_params_tool.py
git commit -m "feat: expose keyframe height api"
```

Expected in this checkout: skip because Git is unavailable.

## Task 5: Keyframe Heights UI Panel

**Files:**
- Modify: `tests/test_pd_params_tool.py`
- Modify: `scripts/pd_params_tool.py`

- [ ] **Step 1: Add failing UI smoke assertions**

Update `UiSmokeTests.test_build_index_html_contains_expected_controls` in `tests/test_pd_params_tool.py` to include:

```python
        self.assertIn("Keyframe Heights", page)
        self.assertIn("/api/keyframes", page)
        self.assertIn("/api/keyframe-heights", page)
        self.assertIn("left_shoulder_pitch_link", page)
        self.assertIn("right_shoulder_pitch_link", page)
```

- [ ] **Step 2: Run tests and verify UI assertions fail**

Run:

```bash
uv run python -m unittest tests.test_pd_params_tool.UiSmokeTests -v
```

Expected: fail until the HTML includes the new panel and JavaScript calls.

- [ ] **Step 3: Add panel styles**

Inside `build_index_html()` CSS, add:

```css
    .layout { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 18px; align-items: start; }
    .panel { background: #fff; border: 1px solid #d9dee7; border-radius: 6px; padding: 12px; }
    .panel h2 { margin: 0 0 10px; font-size: 18px; }
    .height-row { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; border-bottom: 1px solid #eef2f7; font-size: 13px; }
    .height-row:last-child { border-bottom: 0; }
    .height-row span:last-child { font-variant-numeric: tabular-nums; }
    .snapshot { width: 100%; min-height: 180px; object-fit: contain; border: 1px solid #d9dee7; border-radius: 4px; background: #f6f7f9; margin-top: 10px; }
    select { width: 100%; box-sizing: border-box; border: 1px solid #b9c2cf; border-radius: 4px; padding: 6px; font: inherit; }
```

- [ ] **Step 4: Wrap table and add Keyframe Heights panel**

Replace the existing table and diff preview markup with:

```html
  <div class="layout">
    <section>
      <table>
        <thead>
          <tr>
            <th class="num">#</th><th>Joint Pattern</th><th>Motor</th><th class="num">Mult</th>
            <th class="num">f Hz</th><th class="num">Damping Ratio</th><th class="num">Kp</th>
            <th class="num">Kd</th><th class="num">Action Scale</th><th class="num">Effort</th><th class="num">Vel</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
      <h2>Diff Preview</h2>
      <pre id="diff">(No preview yet.)</pre>
    </section>
    <aside class="panel">
      <h2>Keyframe Heights</h2>
      <select id="keyframeSelect" onchange="loadKeyframeHeights()"></select>
      <div id="heightRows" style="margin-top:10px">
        <div class="height-row"><span>pelvis</span><span>-</span></div>
        <div class="height-row"><span>torso_link</span><span>-</span></div>
        <div class="height-row"><span>left_shoulder_pitch_link</span><span>-</span></div>
        <div class="height-row"><span>right_shoulder_pitch_link</span><span>-</span></div>
      </div>
      <button style="width:100%;margin-top:10px" onclick="loadKeyframes()">Reload keyframes</button>
      <div id="heightStatus" class="status">Loading keyframes...</div>
      <img id="keyframeSnapshot" class="snapshot" alt="MuJoCo keyframe snapshot">
    </aside>
  </div>
```

- [ ] **Step 5: Add JavaScript for keyframes**

Before `loadTable();`, add:

```javascript
function setHeightStatus(message, isError = false) {
  const el = document.getElementById("heightStatus");
  el.textContent = message;
  el.className = isError ? "status error" : "status";
}

function renderHeightRows(bodyHeights) {
  const order = ["pelvis", "torso_link", "left_shoulder_pitch_link", "right_shoulder_pitch_link"];
  const container = document.getElementById("heightRows");
  container.innerHTML = "";
  for (const name of order) {
    const row = document.createElement("div");
    row.className = "height-row";
    const value = bodyHeights && Number.isFinite(Number(bodyHeights[name]))
      ? `${Number(bodyHeights[name]).toFixed(4)} m`
      : "-";
    row.innerHTML = `<span>${name}</span><span>${value}</span>`;
    container.appendChild(row);
  }
}

async function loadKeyframes() {
  try {
    const data = await api("/api/keyframes");
    const select = document.getElementById("keyframeSelect");
    select.innerHTML = "";
    for (const keyframe of data.keyframes) {
      const option = document.createElement("option");
      option.value = keyframe.name;
      option.textContent = keyframe.label;
      select.appendChild(option);
    }
    select.value = data.keyframes.some(item => item.name === "knees_bent") ? "knees_bent" : data.keyframes[0]?.name;
    setHeightStatus(`Loaded ${data.keyframes.length} keyframes.`);
    await loadKeyframeHeights();
  } catch (error) {
    setHeightStatus(error.message, true);
  }
}

async function loadKeyframeHeights() {
  const select = document.getElementById("keyframeSelect");
  const name = select.value || "knees_bent";
  try {
    setHeightStatus(`Computing ${name}...`);
    const data = await api(`/api/keyframe-heights?name=${encodeURIComponent(name)}`);
    renderHeightRows(data.result.body_heights);
    document.getElementById("keyframeSnapshot").src = data.result.image_data_url || "";
    setHeightStatus(
      `Aligned feet min z ${Number(data.result.feet_min_z_after_alignment).toFixed(6)} m; base z ${Number(data.result.base_z_after_alignment).toFixed(4)} m.`
    );
  } catch (error) {
    renderHeightRows(null);
    document.getElementById("keyframeSnapshot").removeAttribute("src");
    setHeightStatus(error.message, true);
  }
}
```

Then replace:

```javascript
loadTable();
```

with:

```javascript
loadTable();
loadKeyframes();
```

- [ ] **Step 6: Run UI tests**

Run:

```bash
uv run python -m unittest tests.test_pd_params_tool -v
```

Expected: all PD and UI smoke tests pass.

- [ ] **Step 7: Conditional commit**

If Git is available:

```bash
git add scripts/pd_params_tool.py tests/test_pd_params_tool.py
git commit -m "feat: add keyframe height panel ui"
```

Expected in this checkout: skip because Git is unavailable.

## Task 6: End-To-End Validation

**Files:**
- No planned source changes.

- [ ] **Step 1: Run full tests under `uv`**

Run:

```bash
uv run python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run syntax validation**

Run:

```bash
uv run python -m py_compile scripts/pd_params_tool.py scripts/calc_heights.py tests/test_pd_params_tool.py tests/test_calc_heights.py
```

Expected: no output and exit code 0.

- [ ] **Step 3: Run height CLI smoke**

Run:

```bash
uv run python scripts/calc_heights.py --config knees_bent
```

Expected output includes:

```text
config: knees_bent
pelvis_height_from_ground:
torso_link_height_from_ground:
left_shoulder_pitch_link_height_from_ground:
right_shoulder_pitch_link_height_from_ground:
```

- [ ] **Step 4: Start local tool**

Run:

```bash
uv run python scripts/pd_params_tool.py --no-browser
```

Expected: prints `Serving PD Parameter Tool at http://127.0.0.1:<port>` and keeps running.

- [ ] **Step 5: API smoke**

In another shell, run with the printed URL:

```bash
uv run python - <<'PY'
from urllib.request import urlopen
import json

base = "http://127.0.0.1:PORT"
with urlopen(base + "/api/keyframes", timeout=10) as response:
    keyframes = json.load(response)
print(keyframes["ok"], [item["name"] for item in keyframes["keyframes"]])

with urlopen(base + "/api/keyframe-heights?name=knees_bent", timeout=30) as response:
    heights = json.load(response)
print(heights["ok"], sorted(heights["result"]["body_heights"]))
print(heights["result"]["image_data_url"][:22])
PY
```

Expected: keyframes include `home`, `knees_bent`, `t_pose`, `zero`; body heights include the four target bodies; image prefix is `data:image/bmp;base64,`.

- [ ] **Step 6: Browser smoke**

Open the printed URL. Verify:

- Existing PD table still loads.
- Keyframe dropdown loads four keyframes.
- Default selection can be set to `knees_bent`.
- Heights render for `pelvis`, `torso_link`, `left_shoulder_pitch_link`, and `right_shoulder_pitch_link`.
- Snapshot image appears in the panel.
- Preview README Diff still works and only touches the PD table.

- [ ] **Step 7: Confirm protected files**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
for path in ["README.md", "config.yaml", "isaac_config/astro_delay.py"]:
    print(path, Path(path).exists())
PY
```

Expected:

```text
README.md True
config.yaml True
isaac_config/astro_delay.py True
```

If Git is available, additionally run:

```bash
git diff -- README.md config.yaml isaac_config/astro_delay.py
```

Expected: no diff unless the user intentionally used `Update README.md`.

- [ ] **Step 8: Conditional final commit**

If Git is available:

```bash
git add pyproject.toml uv.lock scripts/calc_heights.py scripts/pd_params_tool.py tests/test_calc_heights.py tests/test_pd_params_tool.py docs/superpowers/specs/2026-04-30-keyframe-height-panel-design.md docs/superpowers/plans/2026-04-30-keyframe-height-panel.md
git rm constants/calc_heights.py
git commit -m "feat: add mujoco keyframe height panel"
```

Expected in this checkout: skip because Git is unavailable.
