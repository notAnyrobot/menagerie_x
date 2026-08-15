"""Portable terrain and scene-description loading for Menagerie assets."""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import AssetError, get_asset_paths, load_manifest

if TYPE_CHECKING:
    from . import Variant


SCENE_SCHEMA_VERSION = 1


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssetError(f"{field} must be an object")
    return value


def _numbers(value: Any, field: str, count: int) -> list[float]:
    if not isinstance(value, list) or len(value) != count:
        raise AssetError(f"{field} must contain {count} numeric values")
    try:
        parsed = [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise AssetError(f"{field} must contain numeric values") from exc
    if not all(math.isfinite(item) for item in parsed):
        raise AssetError(f"{field} must contain finite values")
    return parsed


def _pose(value: Any, field: str) -> dict[str, list[float]]:
    raw = _mapping(value, field)
    return {"xyz": _numbers(raw.get("xyz"), f"{field}.xyz", 3), "rpy": _numbers(raw.get("rpy"), f"{field}.rpy", 3)}


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        import json

        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssetError(f"{label} does not exist: {path}") from exc
    except ValueError as exc:
        raise AssetError(f"{label} is not valid JSON: {path}") from exc
    return _mapping(value, label)


def _manifest_asset_path(category: str, identifier: str, root: Path | None) -> Path:
    paths = get_asset_paths(root)
    manifest = load_manifest(paths.root)
    entries = _mapping(manifest.get(category), f"manifest.{category}")
    relative = entries.get(identifier)
    if not isinstance(relative, str) or not relative:
        raise AssetError(f"unknown {category.removesuffix('s')}: {identifier!r}")
    candidate = (paths.root / relative).resolve()
    try:
        candidate.relative_to(paths.root)
    except ValueError as exc:
        raise AssetError(f"{category.removesuffix('s')} path escapes asset root: {relative!r}") from exc
    return candidate


@dataclasses.dataclass(frozen=True)
class TerrainDescription:
    identifier: str
    source: Path
    geometry: dict[str, Any]
    pose: dict[str, list[float]]
    appearance: dict[str, Any]
    physics: dict[str, Any]
    collision: bool
    overrides: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.identifier,
            "geometry": self.geometry,
            "pose": self.pose,
            "appearance": self.appearance,
            "physics": self.physics,
            "collision": self.collision,
            "overrides": self.overrides,
        }


@dataclasses.dataclass(frozen=True)
class SceneDescription:
    identifier: str
    source: Path
    gravity: list[float]
    terrain_instances: tuple[dict[str, Any], ...]
    prop_instances: tuple[dict[str, Any], ...]
    spawn_frames: dict[str, dict[str, list[float]]]
    overrides: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.identifier,
            "gravity": self.gravity,
            "terrain_instances": list(self.terrain_instances),
            "prop_instances": list(self.prop_instances),
            "spawn_frames": self.spawn_frames,
            "overrides": self.overrides,
        }


@dataclasses.dataclass(frozen=True)
class ResolvedScene:
    identifier: str
    gravity: list[float]
    terrain_instances: tuple[dict[str, Any], ...]
    prop_instances: tuple[dict[str, Any], ...]
    spawn_frames: dict[str, dict[str, list[float]]]
    robot_spawn: dict[str, list[float]]
    overrides: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.identifier,
            "gravity": self.gravity,
            "terrain_instances": list(self.terrain_instances),
            "prop_instances": list(self.prop_instances),
            "spawn_frames": self.spawn_frames,
            "robot_spawn": self.robot_spawn,
            "overrides": self.overrides,
        }


def load_terrain(identifier: str, root: Path | None = None) -> TerrainDescription:
    source = _manifest_asset_path("terrains", identifier, root)
    raw = _load_json(source, f"terrain {identifier!r}")
    if raw.get("schema_version") != SCENE_SCHEMA_VERSION:
        raise AssetError(f"terrain {identifier!r} has unsupported schema version")
    if raw.get("id") != identifier:
        raise AssetError(f"terrain {identifier!r} has a mismatched id")
    geometry = _mapping(raw.get("geometry"), f"terrain {identifier!r}.geometry")
    if geometry.get("type") != "plane":
        raise AssetError(f"terrain {identifier!r} must use plane geometry")
    size = _numbers(geometry.get("size"), f"terrain {identifier!r}.geometry.size", 2)
    thickness = float(geometry.get("thickness", 0.1))
    if not math.isfinite(thickness) or thickness <= 0 or any(value <= 0 for value in size):
        raise AssetError(f"terrain {identifier!r} geometry dimensions must be positive")
    appearance = _mapping(raw.get("appearance"), f"terrain {identifier!r}.appearance")
    rgba = _numbers(appearance.get("rgba"), f"terrain {identifier!r}.appearance.rgba", 4)
    if any(value < 0 or value > 1 for value in rgba):
        raise AssetError(f"terrain {identifier!r} appearance.rgba values must be between 0 and 1")
    physics = _mapping(raw.get("physics"), f"terrain {identifier!r}.physics")
    friction = float(physics.get("friction", -1))
    restitution = float(physics.get("restitution", -1))
    if not math.isfinite(friction) or friction < 0:
        raise AssetError(f"terrain {identifier!r} physics.friction must be non-negative")
    if not math.isfinite(restitution) or not 0 <= restitution <= 1:
        raise AssetError(f"terrain {identifier!r} physics.restitution must be between 0 and 1")
    overrides = raw.get("overrides", {})
    return TerrainDescription(
        identifier=identifier,
        source=source,
        geometry={"type": "plane", "size": size, "thickness": thickness},
        pose=_pose(raw.get("pose"), f"terrain {identifier!r}.pose"),
        appearance={"rgba": rgba},
        physics={"friction": friction, "restitution": restitution},
        collision=bool(raw.get("collision", True)),
        overrides=_mapping(overrides, f"terrain {identifier!r}.overrides"),
    )


def load_scene(identifier: str, root: Path | None = None) -> SceneDescription:
    source = _manifest_asset_path("scenes", identifier, root)
    raw = _load_json(source, f"scene {identifier!r}")
    if raw.get("schema_version") != SCENE_SCHEMA_VERSION:
        raise AssetError(f"scene {identifier!r} has unsupported schema version")
    if raw.get("id") != identifier:
        raise AssetError(f"scene {identifier!r} has a mismatched id")
    terrain_instances: list[dict[str, Any]] = []
    instance_ids: set[str] = set()
    raw_terrain = raw.get("terrain_instances")
    if not isinstance(raw_terrain, list) or not raw_terrain:
        raise AssetError(f"scene {identifier!r} must contain at least one terrain instance")
    for index, value in enumerate(raw_terrain):
        instance = _mapping(value, f"scene {identifier!r}.terrain_instances[{index}]")
        instance_id = instance.get("id")
        terrain = instance.get("terrain")
        if not isinstance(instance_id, str) or not instance_id or instance_id in instance_ids:
            raise AssetError(f"scene {identifier!r} terrain instance IDs must be unique")
        if not isinstance(terrain, str) or not terrain:
            raise AssetError(f"scene {identifier!r} terrain instance requires a terrain id")
        instance_ids.add(instance_id)
        terrain_instances.append({"id": instance_id, "terrain": terrain, "pose": _pose(instance.get("pose"), f"scene {identifier!r}.terrain_instances[{index}].pose")})
    raw_frames = _mapping(raw.get("spawn_frames"), f"scene {identifier!r}.spawn_frames")
    if not raw_frames:
        raise AssetError(f"scene {identifier!r} must define at least one spawn frame")
    spawn_frames = {name: _pose(value, f"scene {identifier!r}.spawn_frames.{name}") for name, value in raw_frames.items() if isinstance(name, str) and name}
    if len(spawn_frames) != len(raw_frames):
        raise AssetError(f"scene {identifier!r} spawn frame names must be non-empty strings")
    raw_props = raw.get("prop_instances", [])
    if not isinstance(raw_props, list):
        raise AssetError(f"scene {identifier!r}.prop_instances must be a list")
    return SceneDescription(
        identifier=identifier,
        source=source,
        gravity=_numbers(raw.get("gravity"), f"scene {identifier!r}.gravity", 3),
        terrain_instances=tuple(terrain_instances),
        prop_instances=tuple(_mapping(item, f"scene {identifier!r}.prop_instances") for item in raw_props),
        spawn_frames=spawn_frames,
        overrides=_mapping(raw.get("overrides", {}), f"scene {identifier!r}.overrides"),
    )


def resolve_scene(variant: Variant, root: Path | None = None) -> ResolvedScene:
    """Resolve a variant's default scene into portable concrete terrain records."""

    if not variant.default_scene:
        raise AssetError(f"variant {variant.name!r} has no default scene")
    scene = load_scene(variant.default_scene, root)
    terrain_instances: list[dict[str, Any]] = []
    for instance in scene.terrain_instances:
        terrain = load_terrain(instance["terrain"], root).as_dict()
        terrain["instance_id"] = instance["id"]
        terrain["pose"] = instance["pose"]
        terrain_instances.append(terrain)
    spawn = variant.spawn
    frame = spawn.get("scene_frame") if isinstance(spawn, dict) else None
    if not isinstance(frame, str) or frame not in scene.spawn_frames:
        raise AssetError(f"variant {variant.name!r} references an unknown scene spawn frame")
    offset = _pose(spawn, f"variant {variant.name!r}.spawn")
    frame_pose = scene.spawn_frames[frame]
    # First scenes use identity spawn-frame rotations. Keep both poses explicit
    # rather than hiding frame composition in every renderer adapter.
    if any(frame_pose["rpy"]):
        raise AssetError("non-zero scene spawn-frame rotations are not supported yet")
    return ResolvedScene(
        identifier=scene.identifier,
        gravity=scene.gravity,
        terrain_instances=tuple(terrain_instances),
        prop_instances=scene.prop_instances,
        spawn_frames=scene.spawn_frames,
        robot_spawn={"xyz": [frame_pose["xyz"][index] + offset["xyz"][index] for index in range(3)], "rpy": offset["rpy"]},
        overrides=scene.overrides,
    )
