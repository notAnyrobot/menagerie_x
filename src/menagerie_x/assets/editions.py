"""Managed MJCF edition workspaces.

The asset manifest names a *default* MJCF for a variant.  It does not grant
that XML any exclusive rights: all valid XML files in the variant workspace
are selectable and editable editions.  Keeping this policy here means the
HTTP workbench never needs to make filesystem or provenance decisions.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import AssetError, get_asset_paths, get_variant, load_manifest

if TYPE_CHECKING:
    from . import Variant


class MjcfEditionError(AssetError):
    """Raised when a managed MJCF edition operation is unsafe or invalid."""


_EDITION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_VARIANT_ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_CANDIDATE_COMMENT = re.compile(rb"<!--\s*menagerie_x_candidate:\s*(.*?)\s*-->", re.DOTALL)


def _safe_id(value: str, kind: str = "edition") -> str:
    value = value[:-4] if value.lower().endswith(".xml") else value
    if not _EDITION_ID.fullmatch(value):
        raise MjcfEditionError(f"{kind} name must contain only letters, digits, dot, dash, and underscore")
    return value


def _within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def edition_directory(variant: Variant, root: Path | None = None) -> Path:
    """Return the managed directory containing a variant's MJCF editions.

    Existing packages used the version-level ``mjcf`` directory.  A manifest
    can opt into a dedicated ``mjcf_workspace`` without moving legacy files.
    """
    paths = get_asset_paths(root)
    manifest = load_manifest(paths.root)
    raw = manifest.get("variants", {}).get(variant.name, {})
    workspace = raw.get("mjcf_workspace") if isinstance(raw, dict) else None
    if isinstance(workspace, str) and workspace:
        candidate = (paths.root / workspace).resolve()
        if not _within(candidate, paths.root):
            raise MjcfEditionError("MJCF workspace escapes the asset root")
        return candidate
    if variant.mjcf is None:
        # Legacy robot versions can host several manifest variants.  A variant
        # without a default gets its own workspace instead of inheriting a
        # sibling's editions merely because they share meshes.
        return paths.robot_dir(variant.name) / "mjcf" / variant.name
    return paths.robot_dir(variant.name) / "mjcf"


def _mesh_path(variant: Variant, filename: str) -> Path:
    relative = Path(filename)
    if relative.is_absolute() or ".." in relative.parts:
        raise MjcfEditionError(f"MJCF mesh reference must stay inside meshes: {filename}")
    target = (variant.meshes_dir / relative).resolve()
    if not _within(target, variant.meshes_dir):
        raise MjcfEditionError(f"MJCF mesh reference escapes meshes: {filename}")
    return target


def validate_mjcf_edition(path: Path, variant: Variant) -> dict[str, Any]:
    """Perform dependency-free validation suitable for discovery and import."""
    try:
        source = path.read_bytes()
        root = ET.fromstring(source)
    except FileNotFoundError as exc:
        raise MjcfEditionError("MJCF edition does not exist") from exc
    except ET.ParseError as exc:
        raise MjcfEditionError(f"MJCF edition is not valid XML: {exc}") from exc
    if root.tag != "mujoco":
        raise MjcfEditionError("MJCF edition root element must be <mujoco>")
    mesh_files = [mesh.get("file") for mesh in root.findall(".//asset/mesh") if mesh.get("file")]
    for filename in mesh_files:
        if not _mesh_path(variant, str(filename)).is_file():
            raise MjcfEditionError(f"MJCF edition references missing mesh: {filename}")
    provenance: dict[str, Any] | None = None
    match = _CANDIDATE_COMMENT.search(source)
    if match is not None:
        try:
            decoded = json.loads(match.group(1).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MjcfEditionError("MJCF provenance metadata is invalid") from exc
        if isinstance(decoded, dict):
            provenance = decoded
    return {
        "model": {"nbody": len(root.findall(".//body")), "ngeom": len(root.findall(".//geom"))},
        "provenance": provenance,
        "revision": hashlib.sha256(source).hexdigest(),
    }


def list_mjcf_editions(variant: Variant, root: Path | None = None) -> list[dict[str, Any]]:
    """Discover all valid MJCF XML files in a managed variant workspace."""
    directory = edition_directory(variant, root)
    default = variant.mjcf.resolve() if variant.mjcf and variant.mjcf.is_file() else None
    manifest = load_manifest(get_asset_paths(root).root)
    manifest_entry = manifest.get("variants", {}).get(variant.name, {})
    raw_editions = manifest_entry.get("editions", {}) if isinstance(manifest_entry, dict) else {}
    canonical_descriptions = {
        (get_asset_paths(root).robot_dir(variant.name) / raw["mjcf"]).resolve()
        for raw in raw_editions.values()
        if isinstance(raw, dict) and isinstance(raw.get("mjcf"), str)
    }
    records: list[dict[str, Any]] = []
    if not directory.is_dir():
        return records
    for path in sorted(directory.glob("*.xml"), key=lambda item: item.name.casefold()):
        if path.resolve() in canonical_descriptions and path.resolve() != default:
            continue
        try:
            checked = validate_mjcf_edition(path, variant)
        except MjcfEditionError:
            # Invalid files are deliberately not selectable.  The import path
            # reports precise failures before such a file is admitted.
            continue
        provenance = checked["provenance"] or {}
        is_default = default is not None and path.resolve() == default
        manifest_provenance = variant.mjcf_provenance or (manifest_entry.get("mjcf_provenance", {}) if isinstance(manifest_entry, dict) else {})
        source_provenance = variant.source_provenance or (manifest_entry.get("source_provenance", {}) if isinstance(manifest_entry, dict) else {})
        source_type = provenance.get("kind") if isinstance(provenance.get("kind"), str) else None
        if source_type is None:
            # A packaged default is not a legacy edition merely because it was
            # not produced by Menagerie's candidate workflow.  The source
            # provenance is enough to make that distinction without adding a
            # synthetic comment to the vendor XML.
            if is_default and isinstance(source_provenance, dict) and source_provenance:
                source_type = "official"
            elif is_default and isinstance(manifest_provenance, dict) and manifest_provenance:
                source_type = "authorized"
            else:
                source_type = "legacy" if is_default else "manual"
        records.append({
            "id": path.stem,
            "label": path.stem,
            "default": is_default,
            "role": "default" if is_default else "edition",
            "kind": source_type,
            "source_id": provenance.get("candidate_id") or (manifest_provenance.get("candidate_id") if is_default and isinstance(manifest_provenance, dict) else None) or path.stem,
            "provenance": provenance or None,
            "source_revision": provenance.get("source_revision") or (manifest_provenance.get("source_revision") if is_default and isinstance(manifest_provenance, dict) else None),
            "source_drift_warning": None,
            "validation": "valid",
            "model": checked["model"],
            "revision": checked["revision"],
            # Browser Date accepts Unix milliseconds, not the nanoseconds
            # returned by pathlib.  Keep the API convention explicit so every
            # selectable edition formats consistently.
            "modified_at": path.stat().st_mtime_ns // 1_000_000,
            "output_path": str(path.resolve()),
        })
    return sorted(records, key=lambda record: (not bool(record["default"]), str(record["label"]).casefold()))


def edition_path(variant: Variant, edition_id: str, root: Path | None = None) -> Path:
    edition_id = _safe_id(edition_id)
    for record in list_mjcf_editions(variant, root):
        if record["id"] == edition_id:
            return Path(str(record["output_path"]))
    raise MjcfEditionError(f"MJCF edition {edition_id!r} does not exist for {variant.name}")


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    _atomic_write(path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def set_default_mjcf_edition(variant_name: str, edition_id: str, root: Path | None = None) -> dict[str, Any]:
    paths = get_asset_paths(root)
    variant = get_variant(variant_name, paths.root)
    edition = edition_path(variant, edition_id, paths.root)
    manifest = load_manifest(paths.root)
    entry = manifest.get("variants", {}).get(variant.name)
    if not isinstance(entry, dict):
        raise MjcfEditionError(f"manifest no longer defines variant {variant.name!r}")
    default_id = entry.get("default_edition")
    editions = entry.get("editions")
    if not isinstance(default_id, str) or not isinstance(editions, dict) or not isinstance(editions.get(default_id), dict):
        raise MjcfEditionError(f"manifest has no mutable default edition for {variant.name!r}")
    editions[default_id]["mjcf"] = str(edition.relative_to(paths.robot_dir(variant.name)))
    _write_manifest(paths.manifest_path, manifest)
    return {"variant": variant.name, "edition_id": edition.stem, "output_path": str(edition.resolve())}


def _copy_referenced_meshes(source: Path, variant: Variant, *, source_root: Path) -> None:
    root = ET.fromstring(source.read_bytes())
    compiler = root.find("compiler")
    mesh_root = source_root
    bundle_root = source_root
    if compiler is not None and compiler.get("meshdir"):
        configured = Path(str(compiler.get("meshdir")))
        if configured.is_absolute():
            raise MjcfEditionError("imported MJCF compiler meshdir must be relative")
        # ``mjcf/model.xml`` plus ``meshes`` is a common portable layout.
        # Permit one level up to the bundle root, but never arbitrary traversal.
        if configured.parts.count("..") > 1 or any(part == ".." for part in configured.parts[1:]):
            raise MjcfEditionError("imported MJCF compiler meshdir escapes the import bundle")
        bundle_root = source_root.parent if configured.parts and configured.parts[0] == ".." else source_root
        mesh_root = (source_root / configured).resolve()
        if not _within(mesh_root, bundle_root):
            raise MjcfEditionError("imported MJCF compiler meshdir escapes the import folder")
    for mesh in root.findall(".//asset/mesh[@file]"):
        filename = str(mesh.get("file"))
        relative = Path(filename)
        if relative.is_absolute() or ".." in relative.parts:
            raise MjcfEditionError(f"imported MJCF mesh path escapes its package: {filename}")
        original = (mesh_root / relative).resolve()
        if not _within(original, mesh_root) or not original.is_file():
            raise MjcfEditionError(f"imported MJCF references missing mesh: {filename}")
        destination = _mesh_path(variant, filename)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copyfile(original, destination)


def import_mjcf_edition(variant_name: str, source: Path, edition_id: str, root: Path | None = None) -> dict[str, Any]:
    """Copy an external MJCF and its local mesh dependencies into an edition workspace."""
    paths = get_asset_paths(root)
    variant = get_variant(variant_name, paths.root)
    source = source.resolve()
    if not source.is_file() or source.suffix.lower() != ".xml":
        raise MjcfEditionError("imported MJCF must be an existing .xml file")
    identifier = _safe_id(edition_id)
    destination = edition_directory(variant, paths.root) / f"{identifier}.xml"
    if destination.exists():
        raise MjcfEditionError(f"MJCF edition already exists: {identifier}")
    _copy_referenced_meshes(source, variant, source_root=source.parent)
    _atomic_write(destination, source.read_bytes())
    try:
        checked = validate_mjcf_edition(destination, variant)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {"variant": variant.name, "edition_id": identifier, "output_path": str(destination.resolve()), **checked}


def import_mjcf_variant(variant_id: str, source: Path, root: Path | None = None) -> dict[str, Any]:
    """Create a self-contained MJCF-only variant from a user-selected file.

    Imported MJCF is allowed to have no URDF.  The manifest retains that fact
    rather than manufacturing a misleading source description.
    """
    if not _VARIANT_ID.fullmatch(variant_id):
        raise MjcfEditionError("variant ID must start with a lowercase letter and use lowercase letters, digits, dash, or underscore")
    paths = get_asset_paths(root)
    source = source.resolve()
    if not source.is_file() or source.suffix.lower() != ".xml":
        raise MjcfEditionError("imported MJCF must be an existing .xml file")
    manifest = load_manifest(paths.root)
    entries = manifest.get("variants")
    if not isinstance(entries, dict):
        raise MjcfEditionError("manifest variants are invalid")
    if variant_id in entries:
        raise MjcfEditionError(f"variant already exists: {variant_id}")
    robot_dir = paths.robot_dir(variant_id)
    if robot_dir.exists():
        raise MjcfEditionError(f"variant workspace already exists: {variant_id}")
    try:
        (robot_dir / "mjcf").mkdir(parents=True)
        (robot_dir / "meshes").mkdir()
        # Build a temporary Variant-shaped view so import validation shares the
        # exact same mesh and path rules as existing workspaces.
        from . import Variant
        edition_id = "default"
        temporary = Variant(variant_id, 0, None, robot_dir / "mjcf" / f"{variant_id}_{edition_id}.xml", robot_dir / "meshes", "imported", "Imported MJCF variant")
        _copy_referenced_meshes(source, temporary, source_root=source.parent)
        destination = temporary.mjcf
        _atomic_write(destination, source.read_bytes())
        checked = validate_mjcf_edition(destination, temporary)
        entries[variant_id] = {
            "status": "imported",
            "notes": "Imported MJCF workspace.",
            "default_scene": "flat_floor",
            "spawn": {"scene_frame": "robot_spawn", "xyz": [0.0, 0.0, 0.75], "rpy": [0.0, 0.0, 0.0]},
            "default_edition": edition_id,
            "editions": {edition_id: {"base_mode": "free", "dof": 0, "label": "Default", "urdf": None, "mjcf": f"mjcf/{destination.name}"}},
        }
        _write_manifest(paths.manifest_path, manifest)
        return {"variant": variant_id, "edition_id": edition_id, "output_path": str(destination.resolve()), **checked}
    except Exception:
        shutil.rmtree(robot_dir, ignore_errors=True)
        raise


def import_urdf_variant(variant_id: str, source: Path, root: Path | None = None) -> dict[str, Any]:
    """Import a URDF workspace and convert its first MJCF edition when available."""
    if not _VARIANT_ID.fullmatch(variant_id):
        raise MjcfEditionError("variant ID must start with a lowercase letter and use lowercase letters, digits, dash, or underscore")
    paths = get_asset_paths(root)
    source = source.resolve()
    if not source.is_file() or source.suffix.lower() != ".urdf":
        raise MjcfEditionError("imported URDF must be an existing .urdf file")
    manifest = load_manifest(paths.root)
    entries = manifest.get("variants")
    if not isinstance(entries, dict):
        raise MjcfEditionError("manifest variants are invalid")
    if variant_id in entries:
        raise MjcfEditionError(f"variant already exists: {variant_id}")
    robot_dir = paths.robot_dir(variant_id)
    if robot_dir.exists():
        raise MjcfEditionError(f"variant workspace already exists: {variant_id}")
    try:
        urdf_dir = robot_dir / "urdf"
        mesh_dir = robot_dir / "meshes"
        urdf_dir.mkdir(parents=True)
        mesh_dir.mkdir()
        edition_id = "default"
        target_urdf = urdf_dir / f"{variant_id}_{edition_id}.urdf"
        _atomic_write(target_urdf, source.read_bytes())
        xml = ET.fromstring(source.read_bytes())
        for mesh in xml.findall(".//mesh[@filename]"):
            filename = str(mesh.get("filename"))
            relative = Path(filename)
            if relative.is_absolute() or relative.parts.count("..") > 1:
                raise MjcfEditionError(f"imported URDF mesh path escapes its package: {filename}")
            bundle_root = source.parent.parent if relative.parts and relative.parts[0] == ".." else source.parent
            original = (source.parent / relative).resolve()
            if not _within(original, bundle_root) or not original.is_file():
                raise MjcfEditionError(f"imported URDF references missing mesh: {filename}")
            # The stored URDF keeps its relative relationship to ``urdf/``.
            destination = (urdf_dir / relative).resolve()
            if not _within(destination, robot_dir):
                raise MjcfEditionError(f"imported URDF mesh path escapes workspace: {filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, destination)
            # Conversion creates an MJCF that refers to the workspace mesh dir.
            mesh_destination = mesh_dir / original.name
            if not mesh_destination.exists():
                shutil.copyfile(original, mesh_destination)
        dof = sum(1 for joint in xml.findall("joint") if joint.get("type", "fixed") in {"revolute", "continuous", "prismatic"})
        entries[variant_id] = {
            "status": "imported",
            "notes": "Imported URDF workspace.",
            "default_scene": "flat_floor",
            "spawn": {"scene_frame": "robot_spawn", "xyz": [0.0, 0.0, 0.75], "rpy": [0.0, 0.0, 0.0]},
            "default_edition": edition_id,
            "editions": {edition_id: {"base_mode": "free", "dof": dof, "label": "Default", "urdf": f"urdf/{target_urdf.name}", "mjcf": None}},
        }
        _write_manifest(paths.manifest_path, manifest)
        from menagerie_x.commands.mjcf import convert_variant_to_candidate
        output = robot_dir / "mjcf" / f"{variant_id}_{edition_id}.xml"
        result = convert_variant_to_candidate(variant_id, variant_id, output, paths.root)
        manifest = load_manifest(paths.root)
        manifest["variants"][variant_id]["editions"][edition_id]["mjcf"] = f"mjcf/{output.name}"
        _write_manifest(paths.manifest_path, manifest)
        return {"variant": variant_id, "edition_id": edition_id, "output_path": str(output.resolve()), "conversion": result}
    except Exception:
        shutil.rmtree(robot_dir, ignore_errors=True)
        _write_manifest(paths.manifest_path, manifest)
        raise


def duplicate_mjcf_edition(variant_name: str, edition_id: str, new_edition_id: str, root: Path | None = None) -> dict[str, Any]:
    paths = get_asset_paths(root)
    variant = get_variant(variant_name, paths.root)
    source = edition_path(variant, edition_id, paths.root)
    target_id = _safe_id(new_edition_id)
    destination = edition_directory(variant, paths.root) / f"{target_id}.xml"
    if destination.exists():
        raise MjcfEditionError(f"MJCF edition already exists: {target_id}")
    _atomic_write(destination, source.read_bytes())
    return {"variant": variant.name, "edition_id": target_id, "output_path": str(destination.resolve())}


def rename_mjcf_edition(variant_name: str, edition_id: str, new_edition_id: str, root: Path | None = None) -> dict[str, Any]:
    paths = get_asset_paths(root)
    variant = get_variant(variant_name, paths.root)
    source = edition_path(variant, edition_id, paths.root)
    target_id = _safe_id(new_edition_id)
    destination = edition_directory(variant, paths.root) / f"{target_id}.xml"
    if destination.exists():
        raise MjcfEditionError(f"MJCF edition already exists: {target_id}")
    os.replace(source, destination)
    if variant.mjcf is not None and source.resolve() == variant.mjcf.resolve():
        set_default_mjcf_edition(variant.name, target_id, paths.root)
    return {"variant": variant.name, "edition_id": target_id, "output_path": str(destination.resolve())}


def delete_mjcf_edition(variant_name: str, edition_id: str, root: Path | None = None) -> None:
    paths = get_asset_paths(root)
    variant = get_variant(variant_name, paths.root)
    source = edition_path(variant, edition_id, paths.root)
    if variant.mjcf is not None and source.resolve() == variant.mjcf.resolve():
        raise MjcfEditionError("set another MJCF edition as default before deleting the default")
    source.unlink()
