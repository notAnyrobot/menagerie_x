"""Explicit URDF-to-MJCF candidate conversion and authorization.

The commands in this module deliberately separate *generation* from
*installation*. A generated candidate is one reviewable MJCF XML file; it
cannot change what the workbench loads until ``authorize_candidate`` is
called for a manifest entry chosen by an operator.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from menagerie_x.assets import AssetError, Variant, get_asset_paths, get_variant, load_manifest


class MjcfCandidateError(AssetError):
    """Raised when a candidate cannot be safely generated or authorized."""


_CANDIDATE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_CONTACT_TYPES = frozenset({"box", "sphere", "cylinder", "capsule", "ellipsoid", "mesh"})
_CANDIDATE_COMMENT = re.compile(rb"<!--\s*menagerie_x_candidate:\s*(.*?)\s*-->", re.DOTALL)


def _import_mujoco() -> Any:
    try:
        import mujoco  # type: ignore
    except ImportError as exc:
        raise MjcfCandidateError("mujoco is not installed; run `uv sync` first") from exc
    return mujoco


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalise_candidate_id(candidate_id: str) -> str:
    candidate_id = candidate_id[:-4] if candidate_id.lower().endswith(".xml") else candidate_id
    if not _CANDIDATE_ID.fullmatch(candidate_id):
        raise MjcfCandidateError("candidate name must contain only letters, digits, dot, dash, and underscore")
    return candidate_id


def _atomic_write(path: Path, payload: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def _json_write(path: Path, value: dict[str, Any]) -> None:
    _atomic_write(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _candidate_metadata_from_xml(model_path: Path) -> dict[str, Any]:
    match = _CANDIDATE_COMMENT.search(model_path.read_bytes())
    if match is None:
        raise MjcfCandidateError("MJCF candidate metadata comment is missing")
    try:
        metadata = json.loads(match.group(1).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MjcfCandidateError("MJCF candidate metadata comment is invalid") from exc
    if not isinstance(metadata, dict):
        raise MjcfCandidateError("MJCF candidate metadata must be an object")
    return metadata


def candidate_metadata_payload(source: bytes, metadata: dict[str, Any]) -> bytes:
    """Return MJCF bytes with exactly one portable review-provenance comment."""
    source = _CANDIDATE_COMMENT.sub(b"", source)
    comment = b"<!-- menagerie_x_candidate: " + json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8") + b" -->\n"
    declaration_end = source.find(b"?>")
    return source[:declaration_end + 2] + b"\n" + comment + source[declaration_end + 2:] if declaration_end >= 0 else comment + source


def write_candidate_metadata(model_path: Path, metadata: dict[str, Any]) -> None:
    """Embed review provenance in the sole candidate XML artifact."""
    _atomic_write(model_path, candidate_metadata_payload(model_path.read_bytes(), metadata))


def read_candidate_metadata_file(model_path: Path) -> dict[str, Any]:
    """Read metadata from an MJCF artifact without resolving it as a candidate."""
    return _candidate_metadata_from_xml(model_path)


def _vector(raw: str | None, size: int, default: tuple[float, ...]) -> tuple[float, ...]:
    values = (raw or "").split()
    if not values:
        return default
    if len(values) != size:
        raise MjcfCandidateError(f"expected {size} values, got {raw!r}")
    try:
        result = tuple(float(value) for value in values)
    except ValueError as exc:
        raise MjcfCandidateError(f"invalid numeric value {raw!r}") from exc
    if not all(math.isfinite(value) for value in result):
        raise MjcfCandidateError("model values must be finite")
    return result


def _rpy_matrix(rpy: tuple[float, float, float]) -> tuple[tuple[float, float, float], ...]:
    roll, pitch, yaw = rpy
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return (
        (cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
        (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
        (-sp, cp * sr, cp * cr),
    )


def _matmul(left: tuple[tuple[float, float, float], ...], right: tuple[tuple[float, float, float], ...]) -> tuple[tuple[float, float, float], ...]:
    return tuple(tuple(sum(left[row][mid] * right[mid][column] for mid in range(3)) for column in range(3)) for row in range(3))


def _matvec(matrix: tuple[tuple[float, float, float], ...], vector: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3))


def _quat(matrix: tuple[tuple[float, float, float], ...]) -> tuple[float, float, float, float]:
    """Convert a proper rotation matrix to MuJoCo's w,x,y,z quaternion."""
    trace = matrix[0][0] + matrix[1][1] + matrix[2][2]
    if trace > 0:
        scale = math.sqrt(trace + 1.0) * 2
        return (0.25 * scale, (matrix[2][1] - matrix[1][2]) / scale, (matrix[0][2] - matrix[2][0]) / scale, (matrix[1][0] - matrix[0][1]) / scale)
    if matrix[0][0] > matrix[1][1] and matrix[0][0] > matrix[2][2]:
        scale = math.sqrt(1.0 + matrix[0][0] - matrix[1][1] - matrix[2][2]) * 2
        return ((matrix[2][1] - matrix[1][2]) / scale, 0.25 * scale, (matrix[0][1] + matrix[1][0]) / scale, (matrix[0][2] + matrix[2][0]) / scale)
    if matrix[1][1] > matrix[2][2]:
        scale = math.sqrt(1.0 + matrix[1][1] - matrix[0][0] - matrix[2][2]) * 2
        return ((matrix[0][2] - matrix[2][0]) / scale, (matrix[0][1] + matrix[1][0]) / scale, 0.25 * scale, (matrix[1][2] + matrix[2][1]) / scale)
    scale = math.sqrt(1.0 + matrix[2][2] - matrix[0][0] - matrix[1][1]) * 2
    return ((matrix[1][0] - matrix[0][1]) / scale, (matrix[0][2] + matrix[2][0]) / scale, (matrix[1][2] + matrix[2][1]) / scale, 0.25 * scale)


def _format(values: tuple[float, ...]) -> str:
    return " ".join(format(value, ".12g") for value in values)


def _urdf_links_and_fixed_frames(source: Path) -> tuple[str, dict[str, tuple[tuple[float, float, float], tuple[tuple[float, float, float], ...]]]]:
    """Return the root link and zero-pose transforms for fixed links.

    MuJoCo fuses fixed URDF bodies during conversion.  Named sites provide a
    stable, inspectable frame for those links without changing dynamics.
    """
    try:
        root = ET.fromstring(source.read_bytes())
    except ET.ParseError as exc:
        raise MjcfCandidateError(f"could not parse URDF: {exc}") from exc
    links = {element.get("name", "") for element in root.findall("link")} - {""}
    joints: list[tuple[str, str, str, tuple[float, float, float], tuple[tuple[float, float, float], ...]]] = []
    children: set[str] = set()
    for joint in root.findall("joint"):
        parent = joint.find("parent")
        child = joint.find("child")
        parent_name = parent.get("link", "") if parent is not None else ""
        child_name = child.get("link", "") if child is not None else ""
        if parent_name not in links or child_name not in links:
            continue
        children.add(child_name)
        origin = joint.find("origin")
        xyz = _vector(origin.get("xyz") if origin is not None else None, 3, (0.0, 0.0, 0.0))
        rpy = _vector(origin.get("rpy") if origin is not None else None, 3, (0.0, 0.0, 0.0))
        joints.append((joint.get("type", "fixed"), parent_name, child_name, xyz, _rpy_matrix(rpy)))
    roots = sorted(links - children)
    if len(roots) != 1:
        raise MjcfCandidateError(f"URDF must have exactly one root link, found {roots}")
    root_link = roots[0]
    transforms = {root_link: ((0.0, 0.0, 0.0), ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))}
    pending = joints[:]
    while pending:
        next_pending = []
        progress = False
        for joint_type, parent, child, position, rotation in pending:
            if parent not in transforms:
                next_pending.append((joint_type, parent, child, position, rotation))
                continue
            parent_pos, parent_rot = transforms[parent]
            offset = _matvec(parent_rot, position)
            transforms[child] = (tuple(parent_pos[index] + offset[index] for index in range(3)), _matmul(parent_rot, rotation))
            progress = True
        if not progress:
            break
        pending = next_pending
    fixed = {child: transforms[child] for kind, _parent, child, _pos, _rot in joints if kind == "fixed" and child in transforms}
    return root_link, fixed


def _prepare_urdf(source: Path) -> bytes:
    """Return a conversion-only URDF with a floating root and stable mesh paths."""
    root = ET.fromstring(source.read_bytes())
    root_link, _fixed = _urdf_links_and_fixed_frames(source)
    # Make each referenced mesh absolute so this temporary XML can live anywhere.
    for mesh in root.findall(".//mesh"):
        filename = mesh.get("filename")
        if filename:
            mesh.set("filename", str((source.parent / filename).resolve()))
    mujoco = root.find("mujoco")
    if mujoco is None:
        mujoco = ET.SubElement(root, "mujoco")
    compiler = mujoco.find("compiler")
    if compiler is None:
        compiler = ET.SubElement(mujoco, "compiler")
    compiler.set("discardvisual", "false")
    child_links = {element.get("link") for element in root.findall("joint/child")}
    if root_link not in child_links:
        ET.SubElement(root, "link", {"name": "workbench_world"})
        joint = ET.SubElement(root, "joint", {"name": "workbench_floating_base", "type": "floating"})
        ET.SubElement(joint, "parent", {"link": "workbench_world"})
        ET.SubElement(joint, "child", {"link": root_link})
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _add_missing_names_and_fixed_sites(model_xml: Path, source: Path) -> list[str]:
    root_link, fixed_frames = _urdf_links_and_fixed_frames(source)
    tree = ET.parse(model_xml)
    root = tree.getroot()
    worldbody = root.find("worldbody")
    if worldbody is None:
        raise MjcfCandidateError("MuJoCo conversion did not create a worldbody")
    body = worldbody.find(f".//body[@name='{root_link}']")
    if body is None:
        body = worldbody.find("body")
    if body is None:
        raise MjcfCandidateError("MuJoCo conversion has no robot body")
    for index, geom in enumerate(root.findall(".//geom")):
        if not geom.get("name"):
            geom.set("name", f"geom_{index + 1}")
    known = {site.get("name") for site in root.findall(".//site")}
    created: list[str] = []
    for link_name, (position, rotation) in sorted(fixed_frames.items()):
        site_name = f"frame__{link_name}"
        if site_name in known:
            continue
        ET.SubElement(body, "site", {"name": site_name, "type": "sphere", "size": "0.001", "rgba": "0 0 0 0", "pos": _format(position), "quat": _format(_quat(rotation))})
        created.append(site_name)
    compiler = root.find("compiler")
    if compiler is None:
        compiler = ET.Element("compiler")
        root.insert(0, compiler)
    # Candidates are portable review artifacts *for the target version layout*.
    compiler.set("meshdir", "../meshes")
    for mesh in root.findall(".//asset/mesh[@file]"):
        # ``mj_saveLastXML`` preserves our temporary absolute URDF paths.  The
        # installed candidate instead resolves through its version's meshes
        # sibling, so it remains valid after manual review and authorization.
        mesh.set("file", Path(mesh.get("file", "")).name)
    ET.indent(tree, space="  ")
    _atomic_write(model_xml, ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n")
    return created


def _compile_candidate_xml(model_path: Path, mesh_dir: Path):
    """Compile a candidate while resolving its portable ``../meshes`` path."""
    mujoco = _import_mujoco()
    root = ET.fromstring(model_path.read_bytes())
    compiler = root.find("compiler")
    if compiler is None:
        compiler = ET.Element("compiler")
        root.insert(0, compiler)
    compiler.set("meshdir", str(mesh_dir.resolve()))
    try:
        return mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))
    except ValueError as exc:
        raise MjcfCandidateError(f"MuJoCo could not compile candidate: {exc}") from exc


def _require_empty_xml(output: Path) -> None:
    if output.suffix.lower() != ".xml":
        raise MjcfCandidateError("candidate output must be a .xml file")
    if output.exists():
        raise MjcfCandidateError(f"refusing to overwrite existing candidate: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)


def managed_candidate_directory(variant: Variant, candidate_id: str, root: Path | None = None) -> Path:
    """Compatibility name for the managed single-file candidate path."""
    candidate_id = _normalise_candidate_id(candidate_id)
    paths = get_asset_paths(root)
    return paths.robot_dir(variant.robot_version) / "mjcf" / f"{candidate_id}.xml"


def create_managed_candidate(source_variant: str, candidate_id: str, root: Path | None = None) -> dict[str, Any]:
    """Generate one user-named review XML beside the version's mesh directory."""
    variant = get_variant(source_variant, root)
    output = managed_candidate_directory(variant, candidate_id, root)
    return convert_variant_to_candidate(source_variant, candidate_id, output, root)


def managed_candidate_path(source_variant: str, candidate_id: str, root: Path | None = None) -> Path:
    """Resolve a managed candidate without accepting arbitrary filesystem paths."""
    variant = get_variant(source_variant, root)
    candidate = managed_candidate_directory(variant, candidate_id, root)
    if candidate.is_file():
        return candidate
    # One-time compatibility with candidates created by the previous folder
    # layout. New generation and authorization never create this layout.
    legacy = candidate.parent / "candidates" / variant.name / candidate_id
    if legacy.is_dir():
        return legacy
    raise MjcfCandidateError(f"candidate {candidate_id!r} does not exist for {variant.name}")


def read_managed_candidate_metadata(source_variant: str, candidate_id: str, root: Path | None = None) -> tuple[dict[str, Any], Path]:
    """Read portable candidate provenance without requiring native MuJoCo."""
    variant = get_variant(source_variant, root)
    candidate = managed_candidate_path(source_variant, candidate_id, root)
    metadata, model = _candidate_metadata(candidate)
    if metadata.get("source_variant") != variant.name:
        raise MjcfCandidateError("candidate source variant does not match target")
    return metadata, model


def _manual_edition_record(candidate: Path, target: Variant) -> dict[str, Any]:
    """Describe a manually named MJCF edition without treating it as authorizable.

    Operators sometimes keep a collision-editing checkpoint by renaming the XML
    file directly.  Such a file has no portable candidate provenance comment,
    but it remains safe to inspect and continue editing when it is a complete
    local MJCF model.  It deliberately cannot be authorized through the
    candidate workflow without explicit provenance.
    """
    model_path = _candidate_model_path(candidate)
    source = model_path.read_bytes()
    if _CANDIDATE_COMMENT.search(source):
        raise MjcfCandidateError("candidate provenance comment is invalid")
    try:
        root = ET.fromstring(source)
    except ET.ParseError as exc:
        raise MjcfCandidateError("manual MJCF edition is not valid XML") from exc
    if root.tag != "mujoco":
        raise MjcfCandidateError("manual MJCF edition is not an MJCF document")
    free_roots = len(root.findall(".//freejoint")) + len(root.findall(".//joint[@type='free']"))
    if free_roots != 1:
        raise MjcfCandidateError(f"manual MJCF edition must contain exactly one free root, found {free_roots}")
    mesh_files = [mesh.get("file") for mesh in root.findall(".//asset/mesh") if mesh.get("file")]
    missing_meshes = [filename for filename in mesh_files if not (target.meshes_dir / filename).is_file()]
    if missing_meshes:
        raise MjcfCandidateError(f"manual MJCF edition references missing mesh: {missing_meshes[0]}")
    edition_id = candidate.stem if candidate.is_file() else candidate.name
    model = {"nbody": len(root.findall(".//body")), "ngeom": len(root.findall(".//geom"))}
    return {
        "id": edition_id,
        "candidate": {"candidate_id": edition_id, "source_variant": target.name, "kind": "manual"},
        "report": {"candidate_id": edition_id, "model": model, "manual": True},
        "model": model,
        "manual": True,
        "valid": True,
        "modified_at": dt.datetime.fromtimestamp(model_path.stat().st_mtime, dt.UTC).isoformat(),
        "output_path": str(model_path.resolve()),
    }


def list_managed_candidates(source_variant: str, root: Path | None = None) -> list[dict[str, Any]]:
    """List review candidates and structurally sound manually named editions."""
    variant = get_variant(source_variant, root)
    records: list[dict[str, Any]] = []
    directory = get_asset_paths(root).robot_dir(variant.robot_version) / "mjcf"
    paths: list[Path] = []
    if directory.is_dir():
        paths.extend(path for path in directory.glob("*.xml") if path != variant.mjcf)
        legacy = directory / "candidates" / variant.name
        if legacy.is_dir():
            paths.extend(path for path in legacy.iterdir() if path.is_dir() and _CANDIDATE_ID.fullmatch(path.name))
    for candidate_path in paths:
        try:
            # Discovery also sees selectable external editions.  A provenance
            # comment with an explicit non-candidate kind describes an
            # edition, not a failed review candidate, so it does not belong in
            # the candidate panel.
            if candidate_path.is_file():
                try:
                    metadata, _ = _candidate_metadata(candidate_path)
                except MjcfCandidateError:
                    metadata = None
                if isinstance(metadata, dict) and isinstance(metadata.get("kind"), str) and metadata["kind"] != "candidate":
                    continue
            checked = validate_candidate(candidate_path, variant)
            candidate = dict(checked["candidate"])
            records.append({
                # The filename is the addressable workbench edition ID. This
                # permits a reviewed XML to be renamed without making the old
                # embedded candidate ID point to a non-existent file.
                "id": candidate_path.stem if candidate_path.is_file() else candidate_path.name,
                "candidate": candidate,
                "report": checked["report"],
                "model": checked["model"],
                "source_drift_warning": checked["source_drift_warning"],
                "valid": True,
                "modified_at": dt.datetime.fromtimestamp(_candidate_model_path(candidate_path).stat().st_mtime, dt.UTC).isoformat(),
                "output_path": str(_candidate_model_path(candidate_path).resolve()),
            })
        except MjcfCandidateError as exc:
            try:
                records.append(_manual_edition_record(candidate_path, variant))
            except MjcfCandidateError:
                records.append({"id": candidate_path.stem, "valid": False, "error": str(exc), "output_path": str(candidate_path.resolve())})
    return sorted(records, key=lambda record: str(record.get("modified_at") or record.get("candidate", {}).get("created_at", "")), reverse=True)


def authorize_managed_candidate(source_variant: str, candidate_id: str, expected_source_revision: str, root: Path | None = None) -> dict[str, Any]:
    """Authorize exactly one reviewed candidate after its displayed revision is confirmed."""
    candidate_dir = managed_candidate_path(source_variant, candidate_id, root)
    target = get_variant(source_variant, root)
    checked = validate_candidate(candidate_dir, target)
    if checked["candidate"]["source_revision"] != expected_source_revision:
        raise MjcfCandidateError("candidate source revision changed; refresh the candidate review before authorizing")
    return authorize_candidate(candidate_dir, source_variant, root)


def discard_managed_candidate(source_variant: str, candidate_id: str, root: Path | None = None) -> None:
    """Remove one unregistered review artifact and nothing outside it."""
    candidate = managed_candidate_path(source_variant, candidate_id, root)
    variant = get_variant(source_variant, root)
    if variant.mjcf is not None and _candidate_model_path(candidate).resolve() == variant.mjcf.resolve():
        raise MjcfCandidateError("authorized MJCF cannot be discarded as a candidate")
    if candidate.is_dir():
        shutil.rmtree(candidate)
    else:
        candidate.unlink()


def next_collision_candidate_directory(source_variant: str, parent_candidate_id: str, root: Path | None = None) -> Path:
    """Return a readable filename for a collision-edited review candidate."""
    variant = get_variant(source_variant, root)
    timestamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    prefix = f"{parent_candidate_id[:34]}-collision-{timestamp}"
    suffix = 1
    while True:
        candidate_id = prefix if suffix == 1 else f"{prefix}-{suffix}"
        candidate = managed_candidate_directory(variant, candidate_id, root)
        if not candidate.exists():
            return candidate
        suffix += 1


def convert_variant_to_candidate(source_variant: str, candidate_id: str, output: Path, root: Path | None = None) -> dict[str, Any]:
    """Generate, but never register, one reviewable MJCF XML file."""
    candidate_id = _normalise_candidate_id(candidate_id)
    variant = get_variant(source_variant, root)
    _require_empty_xml(output)
    mujoco = _import_mujoco()
    source_revision = _sha256(variant.urdf)
    temporary = output.with_name(f".{output.stem}.conversion-input.urdf")
    model_path = output.with_name(f".{output.stem}.conversion.xml")
    try:
        _atomic_write(temporary, _prepare_urdf(variant.urdf))
        try:
            model = mujoco.MjModel.from_xml_path(str(temporary))
        except ValueError as exc:
            raise MjcfCandidateError(f"MuJoCo could not convert {variant.name}: {exc}") from exc
        mujoco.mj_saveLastXML(str(model_path), model)
    finally:
        temporary.unlink(missing_ok=True)
    fixed_sites = _add_missing_names_and_fixed_sites(model_path, variant.urdf)
    candidate = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "source_variant": variant.name,
        "source_revision": source_revision,
        "mujoco_version": str(mujoco.__version__),
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "fixed_link_frame_sites": fixed_sites,
    }
    write_candidate_metadata(model_path, candidate)
    try:
        _atomic_write(output, model_path.read_bytes())
    finally:
        model_path.unlink(missing_ok=True)
    checked = validate_candidate(output, variant)
    return {"candidate": candidate, "report": checked["report"], "output": str(output.resolve())}


def _free_root_count(model_path: Path) -> int:
    root = ET.fromstring(model_path.read_bytes())
    return len(root.findall(".//freejoint")) + len(root.findall(".//joint[@type='free']"))


def _candidate_model_path(candidate: Path) -> Path:
    return candidate if candidate.is_file() else candidate / "model.xml"


def _candidate_metadata(candidate: Path) -> tuple[dict[str, Any], Path]:
    model_path = _candidate_model_path(candidate)
    if not model_path.is_file():
        raise MjcfCandidateError("candidate MJCF file does not exist")
    if candidate.is_file():
        return _candidate_metadata_from_xml(model_path), model_path
    # Compatibility only for folders created before the single-file layout.
    metadata_path = candidate / "candidate.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MjcfCandidateError("legacy candidate metadata is invalid") from exc
    if not isinstance(metadata, dict):
        raise MjcfCandidateError("legacy candidate metadata must be an object")
    return metadata, model_path


def validate_candidate(candidate_dir: Path, target: Variant) -> dict[str, Any]:
    """Validate all authorization invariants without installing anything."""
    candidate, model_path = _candidate_metadata(candidate_dir)
    if candidate.get("source_variant") != target.name:
        raise MjcfCandidateError("candidate source variant does not match authorization target")
    if not isinstance(candidate.get("source_revision"), str) or len(candidate["source_revision"]) != 64:
        raise MjcfCandidateError("candidate is missing a valid source revision")
    root = ET.fromstring(model_path.read_bytes())
    if root.tag != "mujoco":
        raise MjcfCandidateError("candidate model.xml is not an MJCF document")
    free_roots = _free_root_count(model_path)
    if free_roots != 1:
        raise MjcfCandidateError(f"candidate must contain exactly one free root, found {free_roots}")
    names: set[tuple[str, str]] = set()
    all_names: set[str] = set()
    for element in root.findall(".//*[@name]"):
        name = element.get("name", "")
        key = (element.tag, name)
        if key in names:
            raise MjcfCandidateError(f"candidate contains duplicate {element.tag} name: {name}")
        names.add(key)
        all_names.add(name)
    mesh_files = [mesh.get("file") for mesh in root.findall(".//asset/mesh") if mesh.get("file")]
    missing_meshes = [filename for filename in mesh_files if not (target.meshes_dir / filename).is_file()]
    if missing_meshes:
        raise MjcfCandidateError(f"candidate references missing mesh: {missing_meshes[0]}")
    contact_geoms = []
    visual_geoms = []
    for geom in root.findall(".//geom"):
        contype = int(geom.get("contype", "1"))
        conaffinity = int(geom.get("conaffinity", "1"))
        (contact_geoms if contype or conaffinity else visual_geoms).append(geom)
    if not contact_geoms or not visual_geoms:
        raise MjcfCandidateError("candidate must retain both contact and visual geoms")
    unnamed_contact = [geom for geom in contact_geoms if not geom.get("name")]
    if unnamed_contact:
        raise MjcfCandidateError("all editable contact geoms must be named")
    expected_sites = candidate.get("fixed_link_frame_sites", [])
    if not isinstance(expected_sites, list) or any(name not in all_names for name in expected_sites):
        raise MjcfCandidateError("candidate fixed-link frame sites are missing")
    model = _compile_candidate_xml(model_path, target.meshes_dir)
    if int(model.nv) - 6 != target.dof:
        raise MjcfCandidateError(f"candidate DOF mismatch: expected {target.dof}, got {int(model.nv) - 6}")
    drift_warning = None
    current_revision = _sha256(target.urdf)
    if current_revision != candidate["source_revision"]:
        drift_warning = "URDF source changed since this candidate was converted; authorization preserves the reviewed candidate."
    report = {
        "candidate_id": candidate.get("candidate_id", model_path.stem),
        "model": {"nq": int(model.nq), "nv": int(model.nv), "nbody": int(model.nbody), "ngeom": int(model.ngeom)},
        "free_root_count": free_roots,
        "fixed_link_frame_sites": expected_sites,
        "unresolved_meshes": [],
    }
    return {
        "candidate": candidate,
        "report": report,
        "model": {"nq": int(model.nq), "nv": int(model.nv), "nbody": int(model.nbody), "ngeom": int(model.ngeom)},
        "source_drift_warning": drift_warning,
    }


def authorize_candidate(candidate_dir: Path, target_variant: str, root: Path | None = None) -> dict[str, Any]:
    """Atomically register one reviewed XML file for a deliberately declared variant."""
    paths = get_asset_paths(root)
    target = get_variant(target_variant, paths.root)
    if target.mjcf is not None:
        raise MjcfCandidateError(f"target {target.name!r} already has an authorized MJCF")
    result = validate_candidate(candidate_dir, target)
    model_path = _candidate_model_path(candidate_dir)
    robot_dir = paths.robot_dir(target.robot_version)
    install_path = robot_dir / "mjcf" / f"{result['candidate']['candidate_id']}.xml"
    if install_path.exists() and install_path.resolve() != model_path.resolve():
        raise MjcfCandidateError(f"refusing to overwrite existing MJCF file: {install_path}")
    install_path.parent.mkdir(parents=True, exist_ok=True)
    staged = install_path.with_name(f".{install_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        if install_path.resolve() != model_path.resolve():
            shutil.copyfile(model_path, staged)
            os.replace(staged, install_path)
        manifest = load_manifest(paths.root)
        entry = manifest.get("variants", {}).get(target.name)
        if not isinstance(entry, dict):
            raise MjcfCandidateError(f"manifest no longer defines target {target.name!r}")
        entry["mjcf"] = f"mjcf/{install_path.name}"
        entry["mjcf_provenance"] = {
            "candidate_id": result["candidate"]["candidate_id"],
            "source_revision": result["candidate"]["source_revision"],
            "mujoco_version": result["candidate"]["mujoco_version"],
            "authorized_at": dt.datetime.now(dt.UTC).isoformat(),
        }
        _json_write(paths.manifest_path, manifest)
    except Exception:
        staged.unlink(missing_ok=True)
        raise
    return {"target": target.name, "installed_mjcf": str(install_path.resolve()), **result}


def flatten_authorized_mjcf(target_variant: str, root: Path | None = None) -> dict[str, Any]:
    """Migrate one previous directory-style authorization to its single XML file.

    This intentionally handles only the old layout produced by this package;
    it never guesses at or rewrites arbitrary legacy MJCF assets.
    """
    paths = get_asset_paths(root)
    target = get_variant(target_variant, paths.root)
    source = target.mjcf
    if source is None or not source.is_file():
        raise MjcfCandidateError(f"target {target.name!r} has no authorized MJCF")
    if source.parent.name != target.name or source.name != "model.xml":
        return {"target": target.name, "installed_mjcf": str(source.resolve()), "migrated": False}
    candidate, model_path = _candidate_metadata(source.parent)
    legacy_report_path = source.parent / "report.json"
    if legacy_report_path.is_file() and "fixed_link_frame_sites" not in candidate:
        report = json.loads(legacy_report_path.read_text(encoding="utf-8"))
        if isinstance(report, dict):
            candidate["fixed_link_frame_sites"] = report.get("fixed_link_frame_sites", [])
    candidate_id = candidate.get("candidate_id")
    if not isinstance(candidate_id, str) or not _CANDIDATE_ID.fullmatch(candidate_id):
        raise MjcfCandidateError("authorized candidate has no valid candidate ID")
    destination = source.parent.parent / f"{candidate_id}.xml"
    if destination.exists():
        raise MjcfCandidateError(f"refusing to overwrite existing MJCF file: {destination}")
    staged = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        shutil.copyfile(model_path, staged)
        write_candidate_metadata(staged, candidate)
        os.replace(staged, destination)
        manifest = load_manifest(paths.root)
        entry = manifest.get("variants", {}).get(target.name)
        if not isinstance(entry, dict):
            raise MjcfCandidateError(f"manifest no longer defines target {target.name!r}")
        entry["mjcf"] = f"mjcf/{destination.name}"
        _json_write(paths.manifest_path, manifest)
        shutil.rmtree(source.parent)
        legacy_review = destination.parent / "candidates" / target.name / candidate_id
        if legacy_review.is_dir():
            shutil.rmtree(legacy_review)
        legacy_parent = legacy_review.parent
        if legacy_parent.is_dir() and not any(legacy_parent.iterdir()):
            legacy_parent.rmdir()
        candidates_parent = legacy_parent.parent
        if candidates_parent.is_dir() and not any(candidates_parent.iterdir()):
            candidates_parent.rmdir()
    except Exception:
        staged.unlink(missing_ok=True)
        raise
    return {"target": target.name, "installed_mjcf": str(destination.resolve()), "migrated": True}
