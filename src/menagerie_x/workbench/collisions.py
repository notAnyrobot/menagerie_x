"""URDF collision document projection and safe edited-copy export."""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import math
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


class CollisionDocumentError(ValueError):
    """Raised when collision data cannot be read or safely exported."""


class StaleCollisionDocumentError(CollisionDocumentError):
    """Raised when the URDF changed after the browser loaded its draft."""


PRIMITIVE_TYPES = frozenset({"box", "sphere", "cylinder"})


def _parser() -> ET.XMLParser:
    return ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))


def _source_revision(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _vector(raw: str | None, count: int, default: list[float]) -> list[float]:
    values = (raw or "").split()
    if not values:
        return default.copy()
    if len(values) != count:
        raise CollisionDocumentError(f"expected {count} numeric values, got {raw!r}")
    try:
        parsed = [float(value) for value in values]
    except ValueError as exc:
        raise CollisionDocumentError(f"invalid numeric values: {raw!r}") from exc
    if not all(math.isfinite(value) for value in parsed):
        raise CollisionDocumentError("collision values must be finite")
    return parsed


def _origin(collision: ET.Element) -> dict[str, list[float]]:
    origin = collision.find("origin")
    return {
        "xyz": _vector(origin.get("xyz") if origin is not None else None, 3, [0.0, 0.0, 0.0]),
        "rpy": _vector(origin.get("rpy") if origin is not None else None, 3, [0.0, 0.0, 0.0]),
    }


def _geometry(collision: ET.Element) -> dict[str, Any] | None:
    geometry = collision.find("geometry")
    if geometry is None:
        return None
    if (box := geometry.find("box")) is not None:
        return {"type": "box", "size": _vector(box.get("size"), 3, [])}
    if (sphere := geometry.find("sphere")) is not None:
        return {"type": "sphere", "radius": _positive(sphere.get("radius"), "radius")}
    if (cylinder := geometry.find("cylinder")) is not None:
        return {
            "type": "cylinder",
            "radius": _positive(cylinder.get("radius"), "radius"),
            "length": _positive(cylinder.get("length"), "length"),
        }
    if (mesh := geometry.find("mesh")) is not None:
        filename = mesh.get("filename")
        if filename:
            return {"type": "mesh", "filename": filename, "scale": _vector(mesh.get("scale"), 3, [1.0, 1.0, 1.0])}
    return None


def _positive(raw: str | None, name: str) -> float:
    try:
        value = float(raw or "")
    except ValueError as exc:
        raise CollisionDocumentError(f"invalid {name}") from exc
    if not math.isfinite(value) or value <= 0:
        raise CollisionDocumentError(f"{name} must be positive")
    return value


def _format(values: list[float]) -> str:
    return " ".join(format(value, ".12g") for value in values)


@dataclasses.dataclass(frozen=True)
class CollisionDocument:
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
        }


def load_collision_document(source: Path) -> CollisionDocument:
    """Return the editable collision projection for a URDF source file."""

    try:
        root = ET.fromstring(source.read_bytes(), parser=_parser())
    except (OSError, ET.ParseError) as exc:
        raise CollisionDocumentError(f"could not parse URDF: {exc}") from exc
    revision = _source_revision(source)
    links: list[str] = []
    collisions: list[dict[str, Any]] = []
    for link_index, link in enumerate(root.findall("link")):
        link_name = link.get("name")
        if not link_name:
            continue
        links.append(link_name)
        for collision_index, collision in enumerate(link.findall("collision")):
            geometry = _geometry(collision)
            if geometry is None:
                continue
            shape_type = geometry["type"]
            collisions.append(
                {
                    "id": f"collision-{link_index}-{collision_index}",
                    "link": link_name,
                    "name": collision.get("name", ""),
                    "origin": _origin(collision),
                    "geometry": geometry,
                    "editable": shape_type in PRIMITIVE_TYPES,
                }
            )
    return CollisionDocument(
        source=source,
        revision=revision,
        new_id_prefix=f"new-{revision[:16]}-",
        links=tuple(links),
        collisions=tuple(collisions),
    )


def _draft_vector(value: Any, field: str, count: int = 3) -> list[float]:
    if not isinstance(value, list) or len(value) != count:
        raise CollisionDocumentError(f"{field} must contain {count} numeric values")
    try:
        parsed = [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise CollisionDocumentError(f"{field} must contain numeric values") from exc
    if not all(math.isfinite(item) for item in parsed):
        raise CollisionDocumentError(f"{field} must be finite")
    return parsed


def _draft_positive(value: Any, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise CollisionDocumentError(f"{field} must be numeric") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise CollisionDocumentError(f"{field} must be positive")
    return parsed


def _validated_draft(document: CollisionDocument, draft: Any) -> list[dict[str, Any]]:
    if not isinstance(draft, list):
        raise CollisionDocumentError("collisions must be a list")
    existing = {item["id"]: item for item in document.collisions if item["editable"]}
    seen_ids: set[str] = set()
    names: dict[str, set[str]] = {link: set() for link in document.links}
    for item in document.collisions:
        if not item["editable"] and item["name"]:
            names[item["link"]].add(item["name"])
    parsed: list[dict[str, Any]] = []
    for item in draft:
        if not isinstance(item, dict):
            raise CollisionDocumentError("each collision must be an object")
        identifier = item.get("id")
        if not isinstance(identifier, str) or identifier in seen_ids:
            raise CollisionDocumentError("collision IDs must be unique")
        if identifier not in existing and not identifier.startswith(document.new_id_prefix):
            raise CollisionDocumentError(f"unknown collision ID: {identifier}")
        seen_ids.add(identifier)
        link = item.get("link")
        name = item.get("name")
        if link not in names:
            raise CollisionDocumentError(f"unknown link: {link!r}")
        if not isinstance(name, str) or not name.strip():
            raise CollisionDocumentError("primitive collision name is required")
        if name in names[link]:
            raise CollisionDocumentError(f"duplicate collision name on {link}: {name}")
        names[link].add(name)
        origin = item.get("origin")
        if not isinstance(origin, dict):
            raise CollisionDocumentError("collision origin is required")
        geometry = item.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") not in PRIMITIVE_TYPES:
            raise CollisionDocumentError("collision geometry must be a supported primitive")
        result = {
            "id": identifier,
            "link": link,
            "name": name.strip(),
            "origin": {"xyz": _draft_vector(origin.get("xyz"), "origin.xyz"), "rpy": _draft_vector(origin.get("rpy"), "origin.rpy")},
            "geometry": {"type": geometry["type"]},
        }
        if geometry["type"] == "box":
            size = _draft_vector(geometry.get("size"), "box size")
            if any(value <= 0 for value in size):
                raise CollisionDocumentError("box size must be positive")
            result["geometry"]["size"] = size
        elif geometry["type"] == "sphere":
            result["geometry"]["radius"] = _draft_positive(geometry.get("radius"), "sphere radius")
        else:
            result["geometry"]["radius"] = _draft_positive(geometry.get("radius"), "cylinder radius")
            result["geometry"]["length"] = _draft_positive(geometry.get("length"), "cylinder length")
        parsed.append(result)
    return parsed


def _primitive_collision(item: dict[str, Any]) -> ET.Element:
    collision = ET.Element("collision", {"name": item["name"]})
    ET.SubElement(collision, "origin", {"xyz": _format(item["origin"]["xyz"]), "rpy": _format(item["origin"]["rpy"])})
    geometry = ET.SubElement(collision, "geometry")
    shape = item["geometry"]
    if shape["type"] == "box":
        ET.SubElement(geometry, "box", {"size": _format(shape["size"])})
    elif shape["type"] == "sphere":
        ET.SubElement(geometry, "sphere", {"radius": format(shape["radius"], ".12g")})
    else:
        ET.SubElement(geometry, "cylinder", {"radius": format(shape["radius"], ".12g"), "length": format(shape["length"], ".12g")})
    return collision


def _timestamped_target(source: Path, now: dt.datetime | None = None) -> Path:
    timestamp = (now or dt.datetime.now(dt.UTC)).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{source.stem}_collision_edited_{timestamp}"
    candidate = source.with_name(f"{stem}{source.suffix}")
    index = 2
    while candidate.exists():
        candidate = source.with_name(f"{stem}_{index}{source.suffix}")
        index += 1
    return candidate


def export_collision_copy(source: Path, expected_revision: str, draft: Any, now: dt.datetime | None = None) -> Path:
    """Validate a primitive draft and atomically write a timestamped sibling URDF."""

    document = load_collision_document(source)
    if expected_revision != document.revision:
        raise StaleCollisionDocumentError("URDF changed; reload collision data before exporting")
    primitives = _validated_draft(document, draft)
    root = ET.fromstring(source.read_bytes(), parser=_parser())
    links = {link.get("name"): link for link in root.findall("link")}
    for link in links.values():
        for collision in list(link.findall("collision")):
            geometry = _geometry(collision)
            if geometry and geometry["type"] in PRIMITIVE_TYPES:
                link.remove(collision)
    for item in primitives:
        links[item["link"]].append(_primitive_collision(item))
    ET.indent(root, space="  ")
    target = _timestamped_target(source, now)
    payload = ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return target
