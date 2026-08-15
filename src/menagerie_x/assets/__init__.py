from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any


class AssetError(ValueError):
    """Raised when a robot-description asset or manifest entry is invalid."""


@dataclasses.dataclass(frozen=True)
class Variant:
    name: str
    robot_version: str
    dof: int
    urdf: Path
    mjcf: Path | None
    meshes_dir: Path
    status: str
    notes: str
    default_scene: str | None = None
    spawn: dict[str, Any] = dataclasses.field(default_factory=lambda: {"scene_frame": "robot_spawn", "xyz": [0.0, 0.0, 0.75], "rpy": [0.0, 0.0, 0.0]})
    mjcf_provenance: dict[str, Any] | None = None

    @property
    def workbench_loadable(self) -> bool:
        """Only an explicitly authorized, present MJCF may enter Workbench."""
        return self.mjcf is not None and self.mjcf.is_file()

    @property
    def urdf_revision(self) -> str:
        return hashlib.sha256(self.urdf.read_bytes()).hexdigest()

    @property
    def source_drift_warning(self) -> str | None:
        if not self.mjcf_provenance:
            return None
        revision = self.mjcf_provenance.get("source_revision")
        if isinstance(revision, str) and revision != self.urdf_revision:
            return "URDF source has changed since the authorized MJCF was reviewed. Workbench continues to use the authorized MJCF."
        return None


@dataclasses.dataclass(frozen=True)
class AssetPaths:
    root: Path
    manifest_path: Path

    def robot_dir(self, robot_version: str) -> Path:
        return self.root / robot_version

    @property
    def default_robot_dir(self) -> Path:
        return self.robot_dir("astro_v1")

    @property
    def meshes_dir(self) -> Path:
        """V1 mesh directory retained for legacy callers."""
        return self.default_robot_dir / "meshes"

    @property
    def urdf_dir(self) -> Path:
        return self.default_robot_dir / "urdf"

    @property
    def mjcf_dir(self) -> Path:
        return self.default_robot_dir / "legacy" / "mjcf"


def package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_robot_root() -> Path:
    return package_root() / "assets" / "astro_v1"


def _resolve_asset_root(root: Path | None = None) -> Path:
    if root is None:
        return (package_root() / "assets").resolve()
    resolved = root.resolve()
    if (resolved / "manifest.json").is_file():
        return resolved
    packaged_asset_root = resolved / "src" / "menagerie_x" / "assets"
    if (packaged_asset_root / "manifest.json").is_file():
        return packaged_asset_root.resolve()
    for candidate in resolved.parents:
        if (candidate / "manifest.json").is_file():
            return candidate
    return resolved


def get_asset_paths(root: Path | None = None) -> AssetPaths:
    resolved_root = _resolve_asset_root(root)
    return AssetPaths(
        root=resolved_root,
        manifest_path=resolved_root / "manifest.json",
    )


def load_manifest(root: Path | None = None) -> dict[str, Any]:
    paths = get_asset_paths(root)
    try:
        return json.loads(paths.manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssetError(f"manifest does not exist: {paths.manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise AssetError(f"manifest is not valid JSON: {paths.manifest_path}") from exc


def variants(root: Path | None = None) -> dict[str, Variant]:
    paths = get_asset_paths(root)
    manifest = load_manifest(paths.root)
    raw_variants = manifest.get("variants")
    if not isinstance(raw_variants, dict) or not raw_variants:
        raise AssetError("manifest must define a non-empty variants object")

    parsed: dict[str, Variant] = {}
    for name, raw in raw_variants.items():
        if not isinstance(raw, dict):
            raise AssetError(f"variant {name!r} must be an object")
        robot_version = str(raw.get("robot_version", "astro_v1"))
        robot_root = paths.robot_dir(robot_version)
        mjcf_value = raw.get("mjcf")
        parsed[name] = Variant(
            name=name,
            robot_version=robot_version,
            dof=int(raw["dof"]),
            urdf=robot_root / str(raw["urdf"]),
            mjcf=robot_root / str(mjcf_value) if mjcf_value else None,
            meshes_dir=robot_root / "meshes",
            status=str(raw.get("status", "unknown")),
            notes=str(raw.get("notes", "")),
            default_scene=str(raw["default_scene"]) if raw.get("default_scene") is not None else None,
            spawn=dict(raw.get("spawn", {"scene_frame": "robot_spawn", "xyz": [0.0, 0.0, 0.75], "rpy": [0.0, 0.0, 0.0]})),
            mjcf_provenance=dict(raw["mjcf_provenance"]) if isinstance(raw.get("mjcf_provenance"), dict) else None,
        )
    return parsed


def get_variant(name: str | None = None, root: Path | None = None) -> Variant:
    manifest = load_manifest(root)
    variant_name = name or str(manifest.get("default_variant", ""))
    all_variants = variants(root)
    try:
        return all_variants[variant_name]
    except KeyError as exc:
        valid = ", ".join(sorted(all_variants))
        raise AssetError(f"unknown variant {variant_name!r}; valid variants: {valid}") from exc


def validate_assets(root: Path | None = None) -> list[str]:
    paths = get_asset_paths(root)
    errors: list[str] = []
    manifest = load_manifest(paths.root)
    raw_versions = manifest.get("robot_versions")
    if not isinstance(raw_versions, dict) or not raw_versions:
        errors.append("manifest must define a non-empty robot_versions object")
    else:
        for robot_version in sorted(raw_versions):
            robot_root = paths.robot_dir(robot_version)
            for directory in (robot_root / "urdf", robot_root / "meshes"):
                if not directory.is_dir():
                    errors.append(f"{robot_version}: missing asset directory: {directory}")

    for variant in variants(paths.root).values():
        if not variant.meshes_dir.is_dir():
            errors.append(f"{variant.name}: missing mesh directory: {variant.meshes_dir}")
        if not variant.urdf.is_file():
            errors.append(f"{variant.name}: missing URDF {variant.urdf}")
        if variant.mjcf is not None and not variant.mjcf.is_file():
            errors.append(f"{variant.name}: missing MJCF {variant.mjcf}")
        try:
            resolve_scene(variant, paths.root)
        except AssetError as exc:
            errors.append(f"{variant.name}: invalid default scene: {exc}")
    for robot_version in sorted(raw_versions) if isinstance(raw_versions, dict) else ():
        for mesh in sorted(paths.robot_dir(robot_version).joinpath("meshes").glob("*.stl")):
            if mesh.stat().st_size == 0:
                errors.append(f"empty mesh file: {mesh}")
    return errors


from .inspection import RobotDescription, RobotInspection, ValidationIssue, inspect_variant
from .scenes import ResolvedScene, SceneDescription, TerrainDescription, load_scene, load_terrain, resolve_scene

__all__ = [
    "AssetError",
    "AssetPaths",
    "RobotDescription",
    "RobotInspection",
    "ResolvedScene",
    "SceneDescription",
    "TerrainDescription",
    "ValidationIssue",
    "Variant",
    "default_robot_root",
    "get_asset_paths",
    "get_variant",
    "inspect_variant",
    "load_manifest",
    "load_scene",
    "load_terrain",
    "package_root",
    "resolve_scene",
    "validate_assets",
    "variants",
]
