from __future__ import annotations

import dataclasses
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import Variant


@dataclasses.dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    element: str | None = None
    element_type: str | None = None
    path: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class RobotDescription:
    """Neutral link, joint, and geometry data parsed from a robot description."""

    links: tuple[dict[str, Any], ...]
    joints: tuple[dict[str, Any], ...]
    root_links: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "links": list(self.links),
            "joints": list(self.joints),
            "root_links": list(self.root_links),
        }


@dataclasses.dataclass(frozen=True)
class RobotInspection:
    variant: Variant
    description: RobotDescription | None
    issues: tuple[ValidationIssue, ...]


def _parse_origin(element: ET.Element | None) -> dict[str, list[float]]:
    if element is None:
        return {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]}

    def values(attribute: str) -> list[float]:
        raw = element.get(attribute, "0 0 0").split()
        try:
            parsed = [float(value) for value in raw]
        except ValueError:
            parsed = []
        return parsed if len(parsed) == 3 else [0.0, 0.0, 0.0]

    return {"xyz": values("xyz"), "rpy": values("rpy")}


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def _geometry_description(element: ET.Element, source_path: Path, fallback_name: str) -> dict[str, Any] | None:
    geometry = element.find("geometry")
    if geometry is None:
        return None
    result: dict[str, Any] = {
        "name": element.get("name", fallback_name),
        "origin": _parse_origin(element.find("origin")),
    }
    if (mesh := geometry.find("mesh")) is not None and (filename := mesh.get("filename")):
        result.update(
            {
                "type": "mesh",
                "filename": filename,
                "asset_path": str((source_path.parent / filename).resolve()),
                "scale": [float(value) for value in mesh.get("scale", "1 1 1").split()],
            }
        )
        return result
    if (box := geometry.find("box")) is not None and box.get("size"):
        result.update({"type": "box", "size": [float(value) for value in box.get("size", "").split()]})
        return result
    if (sphere := geometry.find("sphere")) is not None and sphere.get("radius"):
        result.update({"type": "sphere", "radius": float(sphere.get("radius", "0"))})
        return result
    if (cylinder := geometry.find("cylinder")) is not None and cylinder.get("radius") and cylinder.get("length"):
        result.update(
            {
                "type": "cylinder",
                "radius": float(cylinder.get("radius", "0")),
                "length": float(cylinder.get("length", "0")),
            }
        )
        return result
    return None


def _link_description(link: ET.Element, source_path: Path) -> dict[str, Any]:
    visuals = [
        description
        for visual in link.findall("visual")
        if (description := _geometry_description(visual, source_path, link.get("name", "visual"))) is not None
        and description["type"] == "mesh"
    ]
    collisions = [
        description
        for collision in link.findall("collision")
        if (description := _geometry_description(collision, source_path, link.get("name", "collision"))) is not None
    ]
    inertial = link.find("inertial")
    mass = inertial.find("mass") if inertial is not None else None
    inertial_description = None
    if inertial is not None and mass is not None:
        try:
            inertial_description = {
                "mass": float(mass.get("value", "0")),
                "origin": _parse_origin(inertial.find("origin")),
            }
        except ValueError:
            # Validation reports the malformed mass below while clients retain a
            # stable null shape rather than receiving a partially valid object.
            pass
    return {"name": link.get("name", ""), "visuals": visuals, "collisions": collisions, "inertial": inertial_description}


def _parse_urdf(variant: Variant) -> tuple[RobotDescription | None, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    try:
        root = ET.fromstring(variant.urdf.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [ValidationIssue("error", "urdf-missing", "URDF source file is missing", path=str(variant.urdf))]
    except ET.ParseError as exc:
        return None, [ValidationIssue("error", "urdf-xml", f"URDF XML is not well formed: {exc}", path=str(variant.urdf))]

    links = [_link_description(link, variant.urdf) for link in root.findall("link")]
    link_names = {link["name"] for link in links if link["name"]}
    for link_element, link in zip(root.findall("link"), links, strict=True):
        name = link["name"]
        inertial = link_element.find("inertial")
        if inertial is None:
            issues.append(ValidationIssue("warning", "inertial-missing", "Link has no inertial block", name, "link"))
        else:
            mass = inertial.find("mass")
            try:
                if mass is None or float(mass.get("value", "0")) <= 0.0:
                    issues.append(ValidationIssue("error", "mass-invalid", "Link mass must be positive", name, "link"))
            except ValueError:
                issues.append(ValidationIssue("error", "mass-invalid", "Link mass is not numeric", name, "link"))
        for visual in link["visuals"]:
            mesh_path = Path(visual["asset_path"])
            if not _is_within(mesh_path, variant.meshes_dir) or not mesh_path.is_file():
                issues.append(
                    ValidationIssue(
                        "error",
                        "mesh-missing",
                        f"Referenced mesh does not exist: {visual['filename']}",
                        name,
                        "link",
                        visual["filename"],
                    )
                )
            elif mesh_path.stat().st_size == 0:
                issues.append(ValidationIssue("error", "mesh-empty", "Referenced mesh file is empty", name, "link", visual["filename"]))

    joints: list[dict[str, Any]] = []
    for joint in root.findall("joint"):
        name = joint.get("name", "")
        parent = joint.find("parent")
        child = joint.find("child")
        parent_name = parent.get("link", "") if parent is not None else ""
        child_name = child.get("link", "") if child is not None else ""
        joints.append(
            {
                "name": name,
                "type": joint.get("type", "fixed"),
                "parent": parent_name,
                "child": child_name,
                "origin": _parse_origin(joint.find("origin")),
                "axis": [float(value) for value in joint.find("axis").get("xyz", "0 0 1").split()]
                if joint.find("axis") is not None
                else [0.0, 0.0, 1.0],
            }
        )
        if not name:
            issues.append(ValidationIssue("error", "joint-name-missing", "Joint has no name", None, "joint"))
        for role, link_name in (("parent", parent_name), ("child", child_name)):
            if link_name not in link_names:
                issues.append(
                    ValidationIssue(
                        "error",
                        "joint-link-missing",
                        f"Joint {role} link is not declared: {link_name or '(empty)'}",
                        name or None,
                        "joint",
                    )
                )
        if joint.get("type") in {"revolute", "prismatic"} and joint.find("limit") is None:
            issues.append(ValidationIssue("warning", "joint-limit-missing", "Movable joint has no limit block", name or None, "joint"))

    child_links = {joint["child"] for joint in joints if joint["child"]}
    roots = tuple(sorted(link_names - child_links))
    if not roots:
        issues.append(ValidationIssue("error", "root-link-missing", "URDF has no root link", None, "robot"))
    elif len(roots) > 1:
        issues.append(ValidationIssue("warning", "multiple-roots", f"URDF has {len(roots)} root links", None, "robot"))
    return RobotDescription(tuple(links), tuple(joints), roots), issues


def inspect_variant(variant: Variant) -> RobotInspection:
    """Parse and validate one robot variant without applying UI-specific projection."""

    description, issues = _parse_urdf(variant)
    if variant.mjcf is None:
        issues.append(
            ValidationIssue(
                "info",
                "mjcf-unavailable",
                "No authorized MJCF is packaged; Workbench is disabled until an operator converts and authorizes a candidate.",
                path=str(variant.urdf),
            )
        )
    elif not variant.mjcf.is_file():
        issues.append(ValidationIssue("error", "mjcf-missing", "Manifest references a missing MJCF file", path=str(variant.mjcf)))
    return RobotInspection(variant=variant, description=description, issues=tuple(issues))
