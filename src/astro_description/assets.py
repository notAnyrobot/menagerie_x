from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any


class AssetError(ValueError):
    """Raised when an Astro description asset or manifest entry is invalid."""


@dataclasses.dataclass(frozen=True)
class Variant:
    name: str
    dof: int
    urdf: Path
    mjcf: Path | None
    status: str
    notes: str


@dataclasses.dataclass(frozen=True)
class AssetPaths:
    root: Path
    meshes_dir: Path
    manifest_path: Path

    @property
    def urdf_dir(self) -> Path:
        return self.root / "urdf"

    @property
    def mjcf_dir(self) -> Path:
        return self.root / "mjcf"


def package_root() -> Path:
    return Path(__file__).resolve().parent


def default_robot_root() -> Path:
    return package_root() / "robots" / "astro"


def _resolve_robot_root(root: Path | None = None) -> Path:
    if root is None:
        return default_robot_root().resolve()
    resolved = root.resolve()
    if (resolved / "manifest.json").is_file():
        return resolved
    packaged_robot_root = resolved / "src" / "astro_description" / "robots" / "astro"
    if (packaged_robot_root / "manifest.json").is_file():
        return packaged_robot_root.resolve()
    return resolved


def get_asset_paths(root: Path | None = None) -> AssetPaths:
    resolved_root = _resolve_robot_root(root)
    return AssetPaths(
        root=resolved_root,
        meshes_dir=resolved_root / "meshes",
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
        mjcf_value = raw.get("mjcf")
        parsed[name] = Variant(
            name=name,
            dof=int(raw["dof"]),
            urdf=paths.root / str(raw["urdf"]),
            mjcf=paths.root / str(mjcf_value) if mjcf_value else None,
            status=str(raw.get("status", "unknown")),
            notes=str(raw.get("notes", "")),
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
    if not paths.meshes_dir.is_dir():
        errors.append(f"missing mesh directory: {paths.meshes_dir}")
    for variant in variants(paths.root).values():
        if not variant.urdf.is_file():
            errors.append(f"{variant.name}: missing URDF {variant.urdf}")
        if variant.mjcf is not None and not variant.mjcf.is_file():
            errors.append(f"{variant.name}: missing MJCF {variant.mjcf}")
    for mesh in sorted(paths.meshes_dir.glob("*.stl")):
        if mesh.stat().st_size == 0:
            errors.append(f"empty mesh file: {mesh}")
    return errors
