"""Temporary, MJCF-native collision drafts for the browser workbench.

This module intentionally does not edit an authorized model in place.  Every
draft is a server-owned temporary copy and export is an unregistered candidate
directory that must still be explicitly authorized through the CLI.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import math
import os
import shutil
import tempfile
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from menagerie_x.commands.mjcf import write_candidate_metadata
from menagerie_x.workbench.collisions import CollisionDocumentError, CollisionDraftNotFoundError, StaleCollisionDocumentError


PRIMITIVE_TYPES = frozenset({"box", "sphere", "cylinder", "capsule"})


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _float_list(value: Any, field: str, count: int) -> list[float]:
    if not isinstance(value, list) or len(value) != count:
        raise CollisionDocumentError(f"{field} must contain {count} numeric values")
    try:
        values = [float(item) for item in value]
    except (ValueError, TypeError) as exc:
        raise CollisionDocumentError(f"{field} must contain numeric values") from exc
    if not all(math.isfinite(item) for item in values):
        raise CollisionDocumentError(f"{field} must be finite")
    return values


def _positive(value: Any, field: str) -> float:
    try:
        parsed = float(value)
    except (ValueError, TypeError) as exc:
        raise CollisionDocumentError(f"{field} must be numeric") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise CollisionDocumentError(f"{field} must be positive")
    return parsed


def _numbers(value: str | None, count: int, default: list[float]) -> list[float]:
    raw = (value or "").split()
    if not raw:
        return default.copy()
    if len(raw) != count:
        raise CollisionDocumentError(f"expected {count} values, got {value!r}")
    return _float_list(raw, "MJCF value", count)


def _format(values: list[float]) -> str:
    return " ".join(format(value, ".12g") for value in values)


def _rpy_to_quat(rpy: list[float]) -> list[float]:
    roll, pitch, yaw = rpy
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
    return [cy * cp * cr + sy * sp * sr, cy * cp * sr - sy * sp * cr, sy * cp * sr + cy * sp * cr, sy * cp * cr - cy * sp * sr]


def _quat_to_rpy(quat: list[float]) -> list[float]:
    w, x, y, z = quat
    sin_roll = 2 * (w * x + y * z)
    cos_roll = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sin_roll, cos_roll)
    sin_pitch = max(-1.0, min(1.0, 2 * (w * y - z * x)))
    pitch = math.asin(sin_pitch)
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return [roll, pitch, yaw]


def _default_geom_attributes(root: ET.Element) -> dict[str, dict[str, str]]:
    values: dict[str, dict[str, str]] = {"": {}}
    for node in root.findall(".//default"):
        name = node.get("class")
        geom = node.find("geom")
        if name and geom is not None:
            values[name] = dict(geom.attrib)
    return values


def _is_contact(geom: ET.Element, defaults: dict[str, dict[str, str]] | None = None) -> bool:
    inherited = (defaults or {}).get(geom.get("class", ""), {})
    try:
        return int(geom.get("contype", inherited.get("contype", "1"))) != 0 or int(geom.get("conaffinity", inherited.get("conaffinity", "1"))) != 0
    except ValueError:
        return True


def _geom_geometry(geom: ET.Element) -> dict[str, Any] | None:
    shape_type = geom.get("type", "sphere")
    size_count = 3 if shape_type == "box" else 1 if shape_type in {"sphere", "capsule"} and geom.get("fromto") else 1 if shape_type == "sphere" else 2
    size = _numbers(geom.get("size"), size_count, [])
    if shape_type == "box":
        return {"type": "box", "size": [value * 2 for value in size]}
    if shape_type == "sphere":
        return {"type": "sphere", "radius": size[0]}
    if shape_type in {"cylinder", "capsule"}:
        if shape_type == "capsule" and geom.get("fromto"):
            start_x, start_y, start_z, end_x, end_y, end_z = _numbers(geom.get("fromto"), 6, [])
            return {"type": shape_type, "radius": size[0], "length": math.dist((start_x, start_y, start_z), (end_x, end_y, end_z))}
        return {"type": shape_type, "radius": size[0], "length": size[1] * 2}
    if shape_type == "mesh":
        return {"type": "mesh", "filename": geom.get("mesh", "")}
    return None


def _origin(geom: ET.Element) -> dict[str, list[float]]:
    if geom.get("fromto"):
        start_x, start_y, start_z, end_x, end_y, end_z = _numbers(geom.get("fromto"), 6, [])
        dx, dy, dz = end_x - start_x, end_y - start_y, end_z - start_z
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length > 1e-12:
            # Quaternion rotating MuJoCo's local Z axis onto the fromto axis.
            ux, uy, uz = dx / length, dy / length, dz / length
            cross_x, cross_y, cross_z = -uy, ux, 0.0
            dot = uz
            if dot < -0.999999:
                quat = [0.0, 1.0, 0.0, 0.0]
            else:
                scale = math.sqrt((1 + dot) * 2)
                quat = [scale / 2, cross_x / scale, cross_y / scale, cross_z / scale]
            return {"xyz": [(start_x + end_x) / 2, (start_y + end_y) / 2, (start_z + end_z) / 2], "rpy": _quat_to_rpy(quat)}
    position = _numbers(geom.get("pos"), 3, [0.0, 0.0, 0.0])
    if geom.get("quat"):
        rpy = _quat_to_rpy(_numbers(geom.get("quat"), 4, [1.0, 0.0, 0.0, 0.0]))
    elif geom.get("euler"):
        rpy = _numbers(geom.get("euler"), 3, [0.0, 0.0, 0.0])
    else:
        rpy = [0.0, 0.0, 0.0]
    return {"xyz": position, "rpy": rpy}


@dataclasses.dataclass(frozen=True)
class MjcfCollisionDocument:
    source: Path
    revision: str
    new_id_prefix: str
    links: tuple[str, ...]
    collisions: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "new_id_prefix": self.new_id_prefix,
            "primitive_types": sorted(PRIMITIVE_TYPES),
            "links": list(self.links),
            "collisions": list(self.collisions),
            "model_format": "mjcf",
        }


def load_mjcf_collision_document(source: Path) -> MjcfCollisionDocument:
    try:
        root = ET.fromstring(source.read_bytes())
    except (OSError, ET.ParseError) as exc:
        raise CollisionDocumentError(f"could not parse MJCF: {exc}") from exc
    if root.tag != "mujoco":
        raise CollisionDocumentError("collision editor requires an MJCF model")
    revision = _sha256(source)
    links: list[str] = []
    collisions: list[dict[str, Any]] = []
    defaults = _default_geom_attributes(root)
    for body in root.findall(".//body"):
        link = body.get("name")
        if not link:
            continue
        links.append(link)
        for index, geom in enumerate(body.findall("geom")):
            if not _is_contact(geom, defaults):
                continue
            geometry = _geom_geometry(geom)
            if geometry is None:
                continue
            name = geom.get("name", "")
            identifier = f"geom-{hashlib.sha256((link + ':' + name + ':' + str(index)).encode()).hexdigest()[:20]}"
            collisions.append({
                "id": identifier,
                "link": link,
                "name": name,
                "origin": _origin(geom),
                "geometry": geometry,
                "editable": geometry["type"] in PRIMITIVE_TYPES,
            })
    return MjcfCollisionDocument(source.resolve(), revision, f"new-{revision[:16]}-", tuple(links), tuple(collisions))


def _validate(document: MjcfCollisionDocument, primitives: Any, retained_mesh_ids: Any) -> tuple[list[dict[str, Any]], set[str]]:
    if not isinstance(primitives, list):
        raise CollisionDocumentError("primitives must be a list")
    mesh_ids = {item["id"] for item in document.collisions if item["geometry"]["type"] == "mesh"}
    if not isinstance(retained_mesh_ids, list) or not all(isinstance(item, str) for item in retained_mesh_ids):
        raise CollisionDocumentError("retained_mesh_ids must be a list of collision IDs")
    retained = set(retained_mesh_ids)
    if len(retained) != len(retained_mesh_ids) or not retained <= mesh_ids:
        raise CollisionDocumentError("retained_mesh_ids contains an unknown or duplicate collision ID")
    known = {item["id"] for item in document.collisions if item["editable"]}
    names: dict[str, set[str]] = {link: set() for link in document.links}
    for mesh in document.collisions:
        if mesh["id"] in retained and mesh["name"]:
            names[mesh["link"]].add(mesh["name"])
    result: list[dict[str, Any]] = []
    ids: set[str] = set()
    for item in primitives:
        if not isinstance(item, dict):
            raise CollisionDocumentError("each primitive must be an object")
        identifier, link, name = item.get("id"), item.get("link"), item.get("name")
        if not isinstance(identifier, str) or identifier in ids or (identifier not in known and not identifier.startswith(document.new_id_prefix)):
            raise CollisionDocumentError("primitive IDs must be unique server-issued IDs")
        if link not in names or not isinstance(name, str) or not name.strip():
            raise CollisionDocumentError("primitive must have a link and non-empty name")
        if name.strip() in names[link]:
            raise CollisionDocumentError(f"duplicate collision name on {link}: {name.strip()}")
        origin = item.get("origin")
        geometry = item.get("geometry")
        if not isinstance(origin, dict) or not isinstance(geometry, dict) or geometry.get("type") not in PRIMITIVE_TYPES:
            raise CollisionDocumentError("primitive origin and supported geometry are required")
        parsed = {
            "id": identifier,
            "link": link,
            "name": name.strip(),
            "origin": {"xyz": _float_list(origin.get("xyz"), "origin.xyz", 3), "rpy": _float_list(origin.get("rpy"), "origin.rpy", 3)},
            "geometry": {"type": geometry["type"]},
        }
        if geometry["type"] == "box":
            size = _float_list(geometry.get("size"), "box size", 3)
            if any(value <= 0 for value in size):
                raise CollisionDocumentError("box dimensions must be positive")
            parsed["geometry"]["size"] = size
        elif geometry["type"] == "sphere":
            parsed["geometry"]["radius"] = _positive(geometry.get("radius"), "sphere radius")
        else:
            parsed["geometry"]["radius"] = _positive(geometry.get("radius"), f"{geometry['type']} radius")
            parsed["geometry"]["length"] = _positive(geometry.get("length"), f"{geometry['type']} length")
        ids.add(identifier)
        names[link].add(name.strip())
        result.append(parsed)
    return result, retained


def _source_ids(document: MjcfCollisionDocument) -> dict[tuple[str, str, int], str]:
    result: dict[tuple[str, str, int], str] = {}
    for item in document.collisions:
        prefix = f"geom-{hashlib.sha256((item['link'] + ':' + item['name'] + ':').encode()).hexdigest()[:0]}"
        # IDs are deterministic per current source; use an ordered lookup in materialization.
        result[(item["link"], item["name"], len(result))] = item["id"]
    return result


def _materialize(source: Path, document: MjcfCollisionDocument, primitives: list[dict[str, Any]], retained_meshes: set[str]) -> bytes:
    root = ET.fromstring(source.read_bytes())
    defaults = _default_geom_attributes(root)
    body_by_name = {body.get("name"): body for body in root.findall(".//body") if body.get("name")}
    id_by_element: dict[int, str] = {}
    for body in root.findall(".//body"):
        link = body.get("name", "")
        for contact_index, geom in enumerate(body.findall("geom")):
            if not _is_contact(geom, defaults) or _geom_geometry(geom) is None:
                continue
            name = geom.get("name", "")
            identifier = f"geom-{hashlib.sha256((link + ':' + name + ':' + str(contact_index)).encode()).hexdigest()[:20]}"
            id_by_element[id(geom)] = identifier
    for body in root.findall(".//body"):
        for geom in list(body.findall("geom")):
            identifier = id_by_element.get(id(geom))
            if identifier is None:
                continue
            geometry = _geom_geometry(geom)
            if geometry and (geometry["type"] in PRIMITIVE_TYPES or (geometry["type"] == "mesh" and identifier not in retained_meshes)):
                body.remove(geom)
    for primitive in primitives:
        body = body_by_name.get(primitive["link"])
        if body is None:
            raise CollisionDocumentError(f"unknown MJCF body: {primitive['link']}")
        geometry = primitive["geometry"]
        attributes = {"name": primitive["name"], "type": geometry["type"], "contype": "1", "conaffinity": "1", "group": "3", "pos": _format(primitive["origin"]["xyz"]), "quat": _format(_rpy_to_quat(primitive["origin"]["rpy"]))}
        if geometry["type"] == "box":
            attributes["size"] = _format([value / 2 for value in geometry["size"]])
        elif geometry["type"] == "sphere":
            attributes["size"] = format(geometry["radius"], ".12g")
        else:
            attributes["size"] = _format([geometry["radius"], geometry["length"] / 2])
        ET.SubElement(body, "geom", attributes)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def _candidate_output(source: Path, now: dt.datetime | None) -> Path:
    timestamp = (now or dt.datetime.now(dt.UTC)).strftime("%Y%m%dT%H%M%SZ")
    path = source.with_name(f"{source.stem}_collision_edited_{timestamp}.xml")
    suffix = 2
    while path.exists():
        path = source.with_name(f"{source.stem}_collision_edited_{timestamp}_{suffix}.xml")
        suffix += 1
    return path


@dataclasses.dataclass
class MjcfCollisionDraftSession:
    identifier: str
    source: Path
    document: MjcfCollisionDocument
    temporary: Path
    primitives: list[dict[str, Any]]
    retained_mesh_ids: set[str]
    updated_at: float

    def as_dict(self) -> dict[str, Any]:
        return {**self.document.as_dict(), "draft_id": self.identifier, "primitives": self.primitives, "retained_mesh_ids": sorted(self.retained_mesh_ids)}


class MjcfCollisionDraftStore:
    def __init__(self, ttl_seconds: float = 3600.0) -> None:
        self.ttl_seconds = ttl_seconds
        self.directory = Path(tempfile.mkdtemp(prefix="menagerie-workbench-mjcf-drafts-"))
        self.sessions: dict[str, MjcfCollisionDraftSession] = {}
        self.lock = threading.RLock()

    @staticmethod
    def _initial(document: MjcfCollisionDocument) -> tuple[list[dict[str, Any]], set[str]]:
        primitives = []
        retained = set()
        for item in document.collisions:
            if item["editable"]:
                primitives.append({"id": item["id"], "link": item["link"], "name": item["name"], "origin": {key: value.copy() for key, value in item["origin"].items()}, "geometry": {key: value.copy() if isinstance(value, list) else value for key, value in item["geometry"].items()}})
            elif item["geometry"]["type"] == "mesh":
                retained.add(item["id"])
        return primitives, retained

    def _get(self, identifier: str, source: Path) -> MjcfCollisionDraftSession:
        session = self.sessions.get(identifier)
        if session is None or session.source != source.resolve():
            raise CollisionDraftNotFoundError("collision draft not found")
        if time.monotonic() - session.updated_at >= self.ttl_seconds:
            self.sessions.pop(identifier, None)
            session.temporary.unlink(missing_ok=True)
            raise CollisionDraftNotFoundError("collision draft expired")
        return session

    def create(self, source: Path) -> MjcfCollisionDraftSession:
        with self.lock:
            document = load_mjcf_collision_document(source)
            primitives, retained = self._initial(document)
            identifier = uuid.uuid4().hex
            temporary = self.directory / f"{identifier}.xml"
            _atomic_write(temporary, source.read_bytes())
            session = MjcfCollisionDraftSession(identifier, source.resolve(), document, temporary, primitives, retained, time.monotonic())
            self.sessions[identifier] = session
            return session

    def update(self, identifier: str, source: Path, revision: str, primitives: Any, retained_mesh_ids: Any) -> MjcfCollisionDraftSession:
        with self.lock:
            session = self._get(identifier, source)
            current = load_mjcf_collision_document(source)
            if revision != session.document.revision or current.revision != session.document.revision:
                raise StaleCollisionDocumentError("MJCF changed; reset the collision draft before saving")
            parsed, retained = _validate(session.document, primitives, retained_mesh_ids)
            _atomic_write(session.temporary, _materialize(source, session.document, parsed, retained))
            session.primitives, session.retained_mesh_ids, session.updated_at = parsed, retained, time.monotonic()
            return session

    def reset(self, identifier: str, source: Path) -> MjcfCollisionDraftSession:
        with self.lock:
            session = self._get(identifier, source)
            session.document = load_mjcf_collision_document(source)
            session.primitives, session.retained_mesh_ids = self._initial(session.document)
            _atomic_write(session.temporary, source.read_bytes())
            session.updated_at = time.monotonic()
            return session

    def source_bytes(self, identifier: str, source: Path) -> bytes:
        """Read the server-owned current draft after validating ownership and TTL."""
        with self.lock:
            session = self._get(identifier, source)
            return session.temporary.read_bytes()

    def export(
        self,
        identifier: str,
        source: Path,
        revision: str,
        now: dt.datetime | None = None,
        source_variant: str | None = None,
        candidate_output: Path | None = None,
        parent_candidate: dict[str, Any] | None = None,
        parent_report: dict[str, Any] | None = None,
    ) -> Path:
        with self.lock:
            session = self._get(identifier, source)
            current = load_mjcf_collision_document(source)
            if revision != session.document.revision or current.revision != session.document.revision:
                raise StaleCollisionDocumentError("MJCF changed; reset the collision draft before exporting")
            target = candidate_output or _candidate_output(source, now)
            target_is_xml = target.suffix.lower() == ".xml"
            if target_is_xml:
                if target.exists():
                    raise CollisionDocumentError(f"refusing to overwrite existing candidate: {target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                model_path = target
            else:
                target.mkdir(parents=True)
                model_path = target / "model.xml"
            _atomic_write(model_path, session.temporary.read_bytes())
            candidate = {
                **(parent_candidate or {}),
                "schema_version": 1,
                "candidate_id": target.stem if target_is_xml else target.name,
                "source_variant": source_variant or (parent_candidate or {}).get("source_variant"),
                "source_revision": (parent_candidate or {}).get("source_revision", session.document.revision),
                "created_at": dt.datetime.now(dt.UTC).isoformat(),
                "kind": "collision-draft",
            }
            report = {**(parent_report or {}), "candidate_id": candidate["candidate_id"], "kind": "collision-draft", "source": str(source)}
            if target_is_xml:
                write_candidate_metadata(model_path, candidate)
            else:
                _atomic_write(target / "candidate.json", (json.dumps(candidate, indent=2, sort_keys=True) + "\n").encode())
                _atomic_write(target / "report.json", (json.dumps(report, indent=2, sort_keys=True) + "\n").encode())
            session.updated_at = time.monotonic()
            return target

    def discard(self, identifier: str, source: Path) -> None:
        with self.lock:
            session = self._get(identifier, source)
            self.sessions.pop(identifier, None)
            session.temporary.unlink(missing_ok=True)

    def close(self) -> None:
        with self.lock:
            self.sessions.clear()
            shutil.rmtree(self.directory, ignore_errors=True)
