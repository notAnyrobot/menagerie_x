#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import base64
import dataclasses
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from menagerie_x.assets import get_asset_paths


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
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        pass
    if isinstance(node, ast.Name) and node.id == "ASTRO_MOTION_SAFE_Z_HEIGHT":
        return 0.745
    if isinstance(node, ast.Tuple):
        return tuple(_literal_eval_node(item) for item in node.elts)
    if isinstance(node, ast.List):
        return [_literal_eval_node(item) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {
            _literal_eval_node(key): _literal_eval_node(value)
            for key, value in zip(node.keys, node.values, strict=True)
            if key is not None
        }
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _literal_eval_node(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    raise HeightToolError(f"unsupported literal expression: {ast.dump(node)}")


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


def create_astro_embodiment_config(robot_root: Path | None = None) -> EmbodimentConfig:
    paths = get_asset_paths(robot_root)
    foot_geoms = tuple(
        f"{side}_foot{i}_collision"
        for side in ("left", "right")
        for i in range(1, 13)
    )
    robot_root = paths.default_robot_dir
    constants_path = robot_root / "constants.py"
    return EmbodimentConfig(
        name="astro",
        mjcf_path=robot_root / "mjcf" / "astro_p1_30dof.xml",
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
        row.extend(b"\x00" * (row_stride - width * 3))
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


def _load_mujoco_model(mujoco: Any, config: EmbodimentConfig) -> Any:
    try:
        return mujoco.MjModel.from_xml_path(str(config.mjcf_path))
    except ValueError as exc:
        robot_root = config.mjcf_path.parent.parent
        mesh_dir = robot_root / "meshes"
        if not mesh_dir.is_dir():
            raise HeightToolError(f"could not load MJCF and fallback mesh dir does not exist: {mesh_dir}") from exc
        root = ET.fromstring(config.mjcf_path.read_text(encoding="utf-8"))
        compiler = root.find("compiler")
        if compiler is None:
            raise HeightToolError("could not load MJCF and no <compiler> element exists for meshdir fallback") from exc
        compiler.set("meshdir", str(mesh_dir.resolve()))
        try:
            return mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))
        except ValueError as fallback_exc:
            raise HeightToolError(f"could not load MJCF from {config.mjcf_path}: {fallback_exc}") from fallback_exc


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
    model = _load_mujoco_model(mujoco, config)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute body heights for an embodied MuJoCo keyframe.")
    parser.add_argument("--config", default="knees_bent", choices=("home", "zero", "knees_bent", "t_pose"))
    parser.add_argument("--root", type=Path, default=None, help="Astro robot asset root or checkout root")
    args = parser.parse_args()
    config = create_astro_embodiment_config(args.root)
    result = compute_keyframe_heights(config, args.config, render=False)
    print(f"config: {result.keyframe}")
    for body_name, height_m in result.body_heights.items():
        print(f"{body_name}_height_from_ground: {height_m:.6f} m")
    print(f"floating_base_z_after_alignment: {result.base_z_after_alignment:.6f} m")
    print(f"feet_min_z_before_alignment: {result.feet_min_z_before_alignment:.6f} m")
    print(f"feet_min_z_after_alignment:  {result.feet_min_z_after_alignment:.6f} m")


if __name__ == "__main__":
    main()
