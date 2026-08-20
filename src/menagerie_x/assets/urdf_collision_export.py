"""Fail-closed transfer of saved MJCF collision primitives into a URDF."""

from __future__ import annotations

import dataclasses
import hashlib
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

import mujoco

from . import AssetError, Variant


SUPPORTED_MJCF_GEOMS = {
    mujoco.mjtGeom.mjGEOM_BOX: "box",
    mujoco.mjtGeom.mjGEOM_SPHERE: "sphere",
    mujoco.mjtGeom.mjGEOM_CYLINDER: "cylinder",
    mujoco.mjtGeom.mjGEOM_CAPSULE: "capsule",
}
FRAME_TRANSLATION_TOLERANCE = 1e-6
FRAME_ROTATION_TOLERANCE = 1e-6
_NAME = re.compile(r"^(?P<stem>.+)_(?P<shape>box|sphere|cylinder|capsule)_collision_?(?P<ordinal>[1-9][0-9]*)$")

Matrix = tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
Transform = tuple[tuple[float, float, float], Matrix]
_IDENTITY: Matrix = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


@dataclasses.dataclass(frozen=True)
class CollisionExportIssue:
    code: str
    message: str
    geom_id: int | None = None
    geom_name: str | None = None
    geom_type: str | None = None
    mjcf_body: str | None = None
    urdf_link: str | None = None

    def as_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class CollisionExportReport:
    source_urdf_revision: str
    source_mjcf_revision: str
    source_collision_count: int
    output_collision_count: int
    geometry_counts: dict[str, int]
    expanded_capsules: int
    issues: tuple[CollisionExportIssue, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {**dataclasses.asdict(self), "issues": [issue.as_dict() for issue in self.issues]}


@dataclasses.dataclass(frozen=True)
class UrdfCollisionExport:
    filename: str
    content: bytes
    report: CollisionExportReport


class UrdfCollisionExportError(AssetError):
    def __init__(self, message: str, report: CollisionExportReport):
        super().__init__(message)
        self.report = report


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _hash(path: Path | None) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path is not None and path.is_file() else ""


def _report(urdf: Path | None, mjcf: Path, source_count: int, issues: Iterable[CollisionExportIssue], *, output_count: int = 0, counts: dict[str, int] | None = None, capsules: int = 0) -> CollisionExportReport:
    return CollisionExportReport(
        source_urdf_revision=_hash(urdf),
        source_mjcf_revision=_hash(mjcf),
        source_collision_count=source_count,
        output_collision_count=output_count,
        geometry_counts=counts or {"box": 0, "sphere": 0, "cylinder": 0},
        expanded_capsules=capsules,
        issues=tuple(issues),
    )


def _raise(urdf: Path | None, mjcf: Path, source_count: int, issues: list[CollisionExportIssue]) -> None:
    report = _report(urdf, mjcf, source_count, issues)
    raise UrdfCollisionExportError("URDF collision export is not representable safely", report)


def _matmul(left: Matrix, right: Matrix) -> Matrix:
    return tuple(tuple(sum(left[row][k] * right[k][column] for k in range(3)) for column in range(3)) for row in range(3))  # type: ignore[return-value]


def _transpose(matrix: Matrix) -> Matrix:
    return tuple(tuple(matrix[column][row] for column in range(3)) for row in range(3))  # type: ignore[return-value]


def _matvec(matrix: Matrix, vector: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3))  # type: ignore[return-value]


def _compose(parent: Transform, child: Transform) -> Transform:
    parent_position, parent_rotation = parent
    child_position, child_rotation = child
    rotated = _matvec(parent_rotation, child_position)
    return (
        tuple(parent_position[index] + rotated[index] for index in range(3)),  # type: ignore[return-value]
        _matmul(parent_rotation, child_rotation),
    )


def _inverse(transform: Transform) -> Transform:
    position, rotation = transform
    inverse_rotation = _transpose(rotation)
    return tuple(-value for value in _matvec(inverse_rotation, position)), inverse_rotation  # type: ignore[return-value]


def _quat_matrix(values: Iterable[float]) -> Matrix:
    w, x, y, z = (float(value) for value in values)
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if norm == 0:
        return _IDENTITY
    w, x, y, z = w / norm, x / norm, y / norm, z / norm
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
        (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
        (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)),
    )


def _rpy_matrix(rpy: Iterable[float]) -> Matrix:
    roll, pitch, yaw = (float(value) for value in rpy)
    cr, sr, cp, sp, cy, sy = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    return (
        (cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
        (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
        (-sp, cp * sr, cp * cr),
    )


def _matrix_rpy(matrix: Matrix) -> tuple[float, float, float]:
    pitch = math.asin(max(-1.0, min(1.0, -matrix[2][0])))
    if abs(math.cos(pitch)) > 1e-10:
        return math.atan2(matrix[2][1], matrix[2][2]), pitch, math.atan2(matrix[1][0], matrix[0][0])
    return math.atan2(-matrix[1][2], matrix[1][1]), pitch, 0.0


def _number(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("non-finite numeric value")
    text = format(value, ".12g")
    return "0" if text in {"-0", "-0.0"} else text


def _numbers(value: str | None, count: int, default: tuple[float, ...]) -> tuple[float, ...]:
    if value is None:
        return default
    items = value.split()
    if len(items) != count:
        raise ValueError(f"expected {count} numeric values")
    numbers = tuple(float(item) for item in items)
    if not all(math.isfinite(number) for number in numbers):
        raise ValueError("numeric values must be finite")
    return numbers


def _urdf_transforms(root: ET.Element) -> dict[str, Transform]:
    links = {link.get("name"): link for link in root.findall("link") if link.get("name")}
    children = {joint.find("child").get("link") for joint in root.findall("joint") if joint.find("child") is not None and joint.find("child").get("link")}
    roots = [name for name in links if name not in children]
    transforms: dict[str, Transform] = {name: ((0.0, 0.0, 0.0), _IDENTITY) for name in roots}
    remaining = list(root.findall("joint"))
    while remaining:
        next_remaining: list[ET.Element] = []
        progressed = False
        for joint in remaining:
            parent = joint.find("parent")
            child = joint.find("child")
            if parent is None or child is None or parent.get("link") not in transforms or not child.get("link"):
                next_remaining.append(joint)
                continue
            origin = joint.find("origin")
            position = _numbers(origin.get("xyz") if origin is not None else None, 3, (0.0, 0.0, 0.0))
            rotation = _rpy_matrix(_numbers(origin.get("rpy") if origin is not None else None, 3, (0.0, 0.0, 0.0)))
            transforms[str(child.get("link"))] = _compose(transforms[str(parent.get("link"))], (position, rotation))  # type: ignore[arg-type]
            progressed = True
        if not progressed:
            break
        remaining = next_remaining
    return transforms


def _mjcf_transforms(model: mujoco.MjModel) -> dict[str, Transform]:
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    transforms: dict[str, Transform] = {}
    for body_id in range(1, model.nbody):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        if name:
            transforms[name] = (
                tuple(float(value) for value in data.xpos[body_id]),  # type: ignore[arg-type]
                tuple(tuple(float(value) for value in data.xmat[body_id][row * 3:(row + 1) * 3]) for row in range(3)),  # type: ignore[arg-type]
            )
    return transforms


def _body_root(model: mujoco.MjModel, body_id: int) -> int:
    while model.body_parentid[body_id] != 0:
        body_id = int(model.body_parentid[body_id])
    return body_id


def _relative_to_root(transform: Transform, root: Transform) -> Transform:
    return _compose(_inverse(root), transform)


def _frame_issue(body: str, link: str, mjcf: Transform, urdf: Transform) -> CollisionExportIssue | None:
    mjcf_position, mjcf_rotation = mjcf
    urdf_position, urdf_rotation = urdf
    translation_error = math.sqrt(sum((mjcf_position[index] - urdf_position[index]) ** 2 for index in range(3)))
    relative_rotation = _matmul(_transpose(mjcf_rotation), urdf_rotation)
    trace = relative_rotation[0][0] + relative_rotation[1][1] + relative_rotation[2][2]
    rotation_error = math.acos(max(-1.0, min(1.0, (trace - 1) / 2)))
    if translation_error <= FRAME_TRANSLATION_TOLERANCE and rotation_error <= FRAME_ROTATION_TOLERANCE:
        return None
    return CollisionExportIssue(
        "frame-mismatch",
        f"MJCF body {body!r} and URDF link {link!r} have incompatible zero-pose frames (translation {translation_error:.3g}, rotation {rotation_error:.3g})",
        mjcf_body=body,
        urdf_link=link,
    )


def _identity_for(name: str | None, body: str, shape: str, geom_id: int) -> tuple[str, str | None]:
    match = _NAME.fullmatch(name or "")
    if match:
        return f"{match.group('stem')}_{match.group('shape')}_collision_{match.group('ordinal')}", match.group("ordinal")
    return f"{body}_{shape}_collision_{geom_id + 1}", None


def _collision(name: str, shape: str, position: tuple[float, float, float], rotation: Matrix, dimensions: dict[str, float]) -> ET.Element:
    collision = ET.Element("collision", {"name": name})
    ET.SubElement(collision, "origin", {"xyz": " ".join(_number(value) for value in position), "rpy": " ".join(_number(value) for value in _matrix_rpy(rotation))})
    geometry = ET.SubElement(collision, "geometry")
    attrs = {key: _number(value) for key, value in dimensions.items()}
    ET.SubElement(geometry, shape, attrs)
    return collision


def export_urdf_with_mjcf_collisions(variant: Variant, mjcf_path: Path, *, edition_id: str, asset_root: Path) -> UrdfCollisionExport:
    """Return a downloaded URDF copy, or one complete report of every blocker."""
    root = asset_root.resolve()
    mjcf_path = mjcf_path.resolve()
    urdf_path = variant.urdf.resolve() if variant.urdf is not None else None
    issues: list[CollisionExportIssue] = []
    if not _within(mjcf_path, root) or not mjcf_path.is_file():
        issues.append(CollisionExportIssue("mjcf-path-unsafe", "selected MJCF edition is not beneath the registered asset root"))
    if urdf_path is None or not urdf_path.is_file():
        issues.append(CollisionExportIssue("urdf-unavailable", f"{variant.name} has no canonical URDF"))
    elif not _within(urdf_path, root):
        issues.append(CollisionExportIssue("urdf-path-unsafe", "canonical URDF is not beneath the registered asset root"))
    if issues:
        report = CollisionExportReport(
            source_urdf_revision=_hash(urdf_path) if urdf_path is not None and _within(urdf_path, root) else "",
            source_mjcf_revision=_hash(mjcf_path) if _within(mjcf_path, root) else "",
            source_collision_count=0,
            output_collision_count=0,
            geometry_counts={"box": 0, "sphere": 0, "cylinder": 0},
            expanded_capsules=0,
            issues=tuple(issues),
        )
        raise UrdfCollisionExportError("URDF collision export is not representable safely", report)

    source = mjcf_path.read_bytes()
    try:
        mjcf_xml = ET.fromstring(source)
    except ET.ParseError:
        mjcf_xml = None
    if mjcf_xml is not None and mjcf_xml.find(".//include") is not None:
        _raise(urdf_path, mjcf_path, 0, [CollisionExportIssue("mjcf-include", "MJCF includes are not supported for collision export")])
    try:
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        urdf_root = ET.fromstring(urdf_path.read_bytes(), parser=parser)
    except (ET.ParseError, OSError) as exc:
        _raise(urdf_path, mjcf_path, 0, [CollisionExportIssue("urdf-malformed", f"canonical URDF cannot be parsed: {exc}")])
    try:
        model = mujoco.MjModel.from_xml_path(str(mjcf_path))
    except Exception as exc:
        _raise(urdf_path, mjcf_path, 0, [CollisionExportIssue("mjcf-compile", f"saved MJCF cannot be compiled: {exc}")])

    links = [link for link in urdf_root.findall("link") if link.get("name")]
    link_by_name: dict[str, ET.Element] = {}
    for link in links:
        name = str(link.get("name"))
        if name in link_by_name:
            issues.append(CollisionExportIssue("duplicate-urdf-link", f"URDF link {name!r} is defined more than once", urdf_link=name))
        link_by_name[name] = link
    try:
        urdf_frames = _urdf_transforms(urdf_root)
    except ValueError as exc:
        issues.append(CollisionExportIssue("urdf-malformed", f"canonical URDF joint origin is malformed: {exc}"))
        urdf_frames = {}
    mjcf_frames = _mjcf_transforms(model)
    selected: list[tuple[int, str, str | None, str, tuple[float, float, float], Matrix, tuple[float, float, float]]] = []
    source_collision_count = 0
    for geom_id in range(model.ngeom):
        if model.geom_contype[geom_id] == 0 and model.geom_conaffinity[geom_id] == 0:
            continue
        source_collision_count += 1
        type_id = model.geom_type[geom_id]
        geom_type = SUPPORTED_MJCF_GEOMS.get(type_id)
        geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
        body_id = int(model.geom_bodyid[geom_id])
        body = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        raw_type = mujoco.mjtGeom(type_id).name.removeprefix("mjGEOM_").lower()
        if body_id == 0:
            issues.append(CollisionExportIssue("world-geom", "collision geom belongs to the MJCF world", geom_id, geom_name, raw_type))
            continue
        if not body:
            issues.append(CollisionExportIssue("unnamed-body", "collision geom belongs to an unnamed MJCF body", geom_id, geom_name, raw_type))
            continue
        if geom_type is None:
            issues.append(CollisionExportIssue("unsupported-geom", f"collision geom type {raw_type!r} cannot be represented by standard URDF", geom_id, geom_name, raw_type, body))
            continue
        if body not in link_by_name:
            issues.append(CollisionExportIssue("missing-urdf-link", f"MJCF body {body!r} has no same-named URDF link", geom_id, geom_name, geom_type, body, body))
            continue
        if body not in mjcf_frames or body not in urdf_frames:
            issues.append(CollisionExportIssue("unmapped-frame", f"cannot determine the zero-pose frame for MJCF body {body!r}", geom_id, geom_name, geom_type, body, body))
            continue
        root_id = _body_root(model, body_id)
        root_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, root_id)
        if not root_name or root_name not in urdf_frames:
            issues.append(CollisionExportIssue("unmapped-root", f"MJCF root body for {body!r} has no same-named URDF root link", geom_id, geom_name, geom_type, body, body))
            continue
        frame_issue = _frame_issue(body, body, _relative_to_root(mjcf_frames[body], mjcf_frames[root_name]), _relative_to_root(urdf_frames[body], urdf_frames[root_name]))
        if frame_issue is not None:
            issues.append(dataclasses.replace(frame_issue, geom_id=geom_id, geom_name=geom_name, geom_type=geom_type))
            continue
        size = tuple(float(value) for value in model.geom_size[geom_id])
        position = tuple(float(value) for value in model.geom_pos[geom_id])
        quaternion = tuple(float(value) for value in model.geom_quat[geom_id])
        rotation = _quat_matrix(quaternion)
        required = {"box": 3, "sphere": 1, "cylinder": 2, "capsule": 2}[geom_type]
        if not all(math.isfinite(value) and value > 0 for value in size[:required]) or not all(math.isfinite(value) for value in position) or not all(math.isfinite(value) for value in quaternion):
            issues.append(CollisionExportIssue("invalid-dimensions", "collision geom has non-finite or non-positive dimensions", geom_id, geom_name, geom_type, body, body))
            continue
        selected.append((geom_id, geom_type, geom_name, body, position, rotation, size))
    if issues:
        _raise(urdf_path, mjcf_path, source_collision_count, issues)

    by_link: dict[str, list[ET.Element]] = {str(link.get("name")): [] for link in links}
    used_names: set[str] = set()
    counts = {"box": 0, "sphere": 0, "cylinder": 0}
    expanded_capsules = 0
    for geom_id, shape, source_name, body, position, rotation, size in selected:
        identity, ordinal = _identity_for(source_name, body, shape, geom_id)
        if shape == "box":
            parts = [(identity, "box", position, rotation, {"size": 2 * size[0]}),]
            # URDF boxes carry all three dimensions in one size attribute.
            parts[0][4]["size_y"] = 2 * size[1]
            parts[0][4]["size_z"] = 2 * size[2]
        elif shape == "sphere":
            parts = [(identity, "sphere", position, rotation, {"radius": size[0]})]
        elif shape == "cylinder":
            parts = [(identity, "cylinder", position, rotation, {"radius": size[0], "length": 2 * size[1]})]
        else:
            expanded_capsules += 1
            match = _NAME.fullmatch(source_name or "")
            stem = match.group("stem") if match else body
            number = ordinal or str(geom_id + 1)
            axis = _matvec(rotation, (0.0, 0.0, size[1]))
            parts = [
                (f"{stem}_{number}_cylinder_collision_1", "cylinder", position, rotation, {"radius": size[0], "length": 2 * size[1]}),
                (f"{stem}_{number}_sphere_collision_1", "sphere", tuple(position[index] - axis[index] for index in range(3)), _IDENTITY, {"radius": size[0]}),
                (f"{stem}_{number}_sphere_collision_2", "sphere", tuple(position[index] + axis[index] for index in range(3)), _IDENTITY, {"radius": size[0]}),
            ]
        for name, part_shape, part_position, part_rotation, dimensions in parts:
            if name in used_names:
                _raise(urdf_path, mjcf_path, source_collision_count, [CollisionExportIssue("duplicate-output-name", f"generated collision name {name!r} is not unique", geom_id, source_name, shape, body, body)])
            used_names.add(name)
            if part_shape == "box":
                # Keep internal dimensions convenient, then emit standard URDF's single size field.
                dimensions = {"size": f"{_number(dimensions['size'])} {_number(dimensions['size_y'])} {_number(dimensions['size_z'])}"}  # type: ignore[dict-item]
                element = ET.Element("collision", {"name": name})
                ET.SubElement(element, "origin", {"xyz": " ".join(_number(value) for value in part_position), "rpy": " ".join(_number(value) for value in _matrix_rpy(part_rotation))})
                geometry = ET.SubElement(element, "geometry")
                ET.SubElement(geometry, "box", dimensions)
            else:
                element = _collision(name, part_shape, part_position, part_rotation, dimensions)
            by_link[body].append(element)
            counts[part_shape] += 1

    for link in links:
        for collision in list(link.findall("collision")):
            link.remove(collision)
        link.extend(by_link[str(link.get("name"))])
    ET.indent(urdf_root, space="  ")
    content = ET.tostring(urdf_root, encoding="utf-8", xml_declaration=True)
    report = _report(urdf_path, mjcf_path, source_collision_count, (), output_count=sum(counts.values()), counts=counts, capsules=expanded_capsules)
    return UrdfCollisionExport(f"{variant.name}-{edition_id}-collisions.urdf", content, report)
