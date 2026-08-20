from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any


class AssetError(ValueError):
    """Raised when a robot-description asset or manifest entry is invalid."""


@dataclasses.dataclass(frozen=True)
class Edition:
    """One format-neutral configuration of a robot variant.

    A robot variant is the physical asset workspace.  An edition is a logical
    configuration within it (for example ``30dof`` or ``with_racket``), which
    may have a URDF, MJCF, or both.  MJCF authoring revisions deliberately do
    not create additional editions.
    """

    id: str
    variant_name: str
    dof: int
    urdf: Path | None
    mjcf: Path | None
    label: str
    base_mode: str
    default: bool = False
    kind: str | None = None
    notes: str = ""
    mjcf_provenance: dict[str, Any] | None = None
    source_provenance: dict[str, Any] | None = None
    mjcf_revisions: tuple[dict[str, Any], ...] = ()

    @property
    def formats(self) -> dict[str, bool]:
        return {"urdf": self.urdf is not None and self.urdf.is_file(), "mjcf": self.mjcf is not None and self.mjcf.is_file()}

    @property
    def workbench_loadable(self) -> bool:
        """Compatibility flag for legacy callers that require an MJCF model."""
        return self.formats["mjcf"]

    @property
    def viewable(self) -> bool:
        return any(self.formats.values())


@dataclasses.dataclass(frozen=True)
class Variant:
    name: str
    dof: int
    urdf: Path | None
    mjcf: Path | None
    meshes_dir: Path
    status: str
    notes: str
    default_scene: str | None = None
    spawn: dict[str, Any] = dataclasses.field(default_factory=lambda: {"scene_frame": "robot_spawn", "xyz": [0.0, 0.0, 0.75], "rpy": [0.0, 0.0, 0.0]})
    mjcf_provenance: dict[str, Any] | None = None
    source_provenance: dict[str, Any] | None = None
    editions: tuple[Edition, ...] = ()
    default_edition: str | None = None

    @property
    def robot_version(self) -> str:
        """Compatibility alias for the variant's on-disk workspace name."""
        return self.name

    @property
    def workbench_loadable(self) -> bool:
        """Compatibility flag for variants with a default MJCF model."""
        return self.mjcf is not None and self.mjcf.is_file()

    @property
    def urdf_revision(self) -> str | None:
        return hashlib.sha256(self.urdf.read_bytes()).hexdigest() if self.urdf is not None and self.urdf.is_file() else None

    @property
    def source_drift_warning(self) -> str | None:
        if not self.mjcf_provenance:
            return None
        revision = self.mjcf_provenance.get("source_revision")
        if isinstance(revision, str) and self.urdf_revision is not None and revision != self.urdf_revision:
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
        return self.robot_dir("astro_p1")

    @property
    def meshes_dir(self) -> Path:
        """V1 mesh directory retained for legacy callers."""
        return self.default_robot_dir / "meshes"

    @property
    def urdf_dir(self) -> Path:
        return self.default_robot_dir / "urdf"

    @property
    def mjcf_dir(self) -> Path:
        return self.default_robot_dir / "mjcf"


def package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_robot_root() -> Path:
    return package_root() / "assets" / "astro_p1"


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
        # Variant IDs are the on-disk workspace names.  Keep the
        # ``robot_version`` attribute only as a compatibility alias for
        # existing callers; never persist a second identity in the manifest.
        robot_version = name
        robot_root = paths.robot_dir(name)
        raw_editions = raw.get("editions")
        if not isinstance(raw_editions, dict) or not raw_editions:
            raise AssetError(f"variant {name!r} must define a non-empty editions object")
        default_edition = raw.get("default_edition")
        if not isinstance(default_edition, str) or default_edition not in raw_editions:
            raise AssetError(f"variant {name!r} default_edition must name a declared edition")
        parsed_editions: list[Edition] = []
        for edition_id, edition_raw in raw_editions.items():
            if not isinstance(edition_id, str) or not isinstance(edition_raw, dict):
                raise AssetError(f"variant {name!r} editions must map IDs to objects")
            urdf_value = edition_raw.get("urdf")
            mjcf_value = edition_raw.get("mjcf")
            revisions = edition_raw.get("mjcf_revisions", [])
            base_mode = edition_raw.get("base_mode")
            if base_mode not in {"free", "fixed"}:
                raise AssetError(f"variant {name!r} edition {edition_id!r} base_mode must be 'free' or 'fixed'")
            if not isinstance(revisions, list) or not all(isinstance(item, dict) for item in revisions):
                raise AssetError(f"variant {name!r} edition {edition_id!r} mjcf_revisions must be a list of objects")
            parsed_editions.append(
                Edition(
                    id=edition_id,
                    variant_name=name,
                    dof=int(edition_raw["dof"]),
                    urdf=robot_root / urdf_value if isinstance(urdf_value, str) and urdf_value else None,
                    mjcf=robot_root / mjcf_value if isinstance(mjcf_value, str) and mjcf_value else None,
                    label=str(edition_raw.get("label", edition_id)),
                    base_mode=base_mode,
                    default=edition_id == default_edition,
                    kind=str(edition_raw["kind"]) if isinstance(edition_raw.get("kind"), str) else None,
                    notes=str(edition_raw.get("notes", "")),
                    mjcf_provenance=dict(edition_raw["mjcf_provenance"]) if isinstance(edition_raw.get("mjcf_provenance"), dict) else None,
                    source_provenance=dict(edition_raw["source_provenance"]) if isinstance(edition_raw.get("source_provenance"), dict) else None,
                    mjcf_revisions=tuple(dict(item) for item in revisions),
                )
            )
        default_description = next(edition for edition in parsed_editions if edition.default)
        parsed[name] = Variant(
            name=name,
            dof=default_description.dof,
            urdf=default_description.urdf,
            mjcf=default_description.mjcf,
            meshes_dir=robot_root / "meshes",
            status=str(raw.get("status", "unknown")),
            notes=str(raw.get("notes", "")),
            default_scene=str(raw["default_scene"]) if raw.get("default_scene") is not None else None,
            spawn=dict(raw.get("spawn", {"scene_frame": "robot_spawn", "xyz": [0.0, 0.0, 0.75], "rpy": [0.0, 0.0, 0.0]})),
            mjcf_provenance=default_description.mjcf_provenance,
            source_provenance=default_description.source_provenance,
            editions=tuple(parsed_editions),
            default_edition=default_edition,
        )
    return parsed


def get_variant(name: str | None = None, root: Path | None = None) -> Variant:
    manifest = load_manifest(root)
    variant_name = name or str(manifest.get("default_variant", ""))
    all_variants = variants(root)
    if variant_name in all_variants:
        return all_variants[variant_name]
    aliases = manifest.get("legacy_variant_aliases", {})
    alias = aliases.get(variant_name) if isinstance(aliases, dict) else None
    if isinstance(alias, dict) and isinstance(alias.get("variant"), str) and isinstance(alias.get("edition"), str):
        edition = get_edition(alias["variant"], alias["edition"], root)
        base = all_variants[alias["variant"]]
        return dataclasses.replace(
            base,
            name=variant_name,
            dof=edition.dof,
            urdf=edition.urdf,
            mjcf=edition.mjcf,
            mjcf_provenance=edition.mjcf_provenance,
            source_provenance=edition.source_provenance,
            editions=(edition,),
            default_edition=edition.id,
        )
    valid = ", ".join(sorted(all_variants))
    raise AssetError(f"unknown variant {variant_name!r}; valid variants: {valid}")


def get_edition(variant_name: str, edition_id: str | None = None, root: Path | None = None) -> Edition:
    """Return a logical edition without inferring one from a source filename."""
    variant = variants(root).get(variant_name)
    if variant is None:
        raise AssetError(f"unknown variant {variant_name!r}")
    target = edition_id or variant.default_edition
    for edition in variant.editions:
        if edition.id == target:
            return edition
    valid = ", ".join(edition.id for edition in variant.editions)
    raise AssetError(f"unknown edition {edition_id!r} for {variant_name!r}; valid editions: {valid}")


def validate_assets(root: Path | None = None) -> list[str]:
    paths = get_asset_paths(root)
    errors: list[str] = []
    manifest = load_manifest(paths.root)
    raw_variants = manifest.get("variants")
    if not isinstance(raw_variants, dict) or not raw_variants:
        errors.append("manifest must define a non-empty variants object")
    else:
        excluded_directories = {"scenes", "terrains", "__pycache__"}
        asset_directories = {
            directory.name
            for directory in paths.root.iterdir()
            if directory.is_dir() and directory.name not in excluded_directories
        }
        declared_variants = set(raw_variants)
        for missing in sorted(asset_directories - declared_variants):
            errors.append(f"asset folder is not declared as a variant: {missing}")
        for missing in sorted(declared_variants - asset_directories):
            errors.append(f"variant has no asset folder: {missing}")

    for variant in variants(paths.root).values():
        if not variant.meshes_dir.is_dir():
            errors.append(f"{variant.name}: missing mesh directory: {variant.meshes_dir}")
        for edition in variant.editions:
            if edition.urdf is not None and not edition.urdf.is_file():
                errors.append(f"{variant.name}/{edition.id}: missing URDF {edition.urdf}")
            if edition.mjcf is not None and not edition.mjcf.is_file():
                errors.append(f"{variant.name}/{edition.id}: missing MJCF {edition.mjcf}")
            for revision in edition.mjcf_revisions:
                path = revision.get("mjcf")
                if not isinstance(path, str) or not (paths.robot_dir(variant.name) / path).is_file():
                    errors.append(f"{variant.name}/{edition.id}: missing MJCF revision {path!r}")
        try:
            resolve_scene(variant, paths.root)
        except AssetError as exc:
            errors.append(f"{variant.name}: invalid default scene: {exc}")
    for variant_name in sorted(raw_variants) if isinstance(raw_variants, dict) else ():
        for mesh in sorted(
            (path for path in paths.robot_dir(variant_name).joinpath("meshes").rglob("*") if path.is_file() and path.suffix.lower() == ".stl"),
            key=lambda path: str(path).casefold(),
        ):
            if mesh.stat().st_size == 0:
                errors.append(f"empty mesh file: {mesh}")
    return errors


from .inspection import RobotDescription, RobotInspection, ValidationIssue, inspect_variant
from .editions import (
    MjcfEditionError,
    delete_mjcf_edition,
    duplicate_mjcf_edition,
    edition_directory,
    edition_path,
    import_mjcf_edition,
    import_mjcf_variant,
    import_urdf_variant,
    list_mjcf_editions,
    rename_mjcf_edition,
    set_default_mjcf_edition,
    validate_mjcf_edition,
)
from .scenes import ResolvedScene, SceneDescription, TerrainDescription, load_scene, load_terrain, resolve_scene
from .urdf_collision_export import (
    CollisionExportIssue,
    CollisionExportReport,
    UrdfCollisionExport,
    UrdfCollisionExportError,
    export_urdf_with_mjcf_collisions,
)

__all__ = [
    "AssetError",
    "AssetPaths",
    "CollisionExportIssue",
    "CollisionExportReport",
    "Edition",
    "MjcfEditionError",
    "RobotDescription",
    "RobotInspection",
    "ResolvedScene",
    "SceneDescription",
    "TerrainDescription",
    "ValidationIssue",
    "Variant",
    "UrdfCollisionExport",
    "UrdfCollisionExportError",
    "default_robot_root",
    "get_asset_paths",
    "get_edition",
    "get_variant",
    "delete_mjcf_edition",
    "duplicate_mjcf_edition",
    "edition_directory",
    "edition_path",
    "export_urdf_with_mjcf_collisions",
    "import_mjcf_edition",
    "import_mjcf_variant",
    "import_urdf_variant",
    "inspect_variant",
    "load_manifest",
    "list_mjcf_editions",
    "load_scene",
    "load_terrain",
    "package_root",
    "resolve_scene",
    "rename_mjcf_edition",
    "set_default_mjcf_edition",
    "validate_assets",
    "validate_mjcf_edition",
    "variants",
]
