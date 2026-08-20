"""Build disposable MuJoCo runtime models for authored URDF descriptions.

The Workbench must never amend an authored URDF just to add its local floor,
gravity, or floating base.  This module is the one boundary that performs
that adaptation, always in a temporary file and always from a selected
manifest edition.
"""

from __future__ import annotations

import dataclasses
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from menagerie_x.assets import Edition


class UrdfRuntimeError(ValueError):
    """Raised when a URDF cannot be prepared for local MuJoCo simulation."""


def _mujoco() -> Any:
    try:
        import mujoco  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment configuration
        raise UrdfRuntimeError("mujoco is not installed; visual inspection remains available") from exc
    return mujoco


def _numbers(value: Any, field: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise UrdfRuntimeError(f"runtime scene {field} must contain three numbers")
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise UrdfRuntimeError(f"runtime scene {field} must contain three numbers") from exc


def _root_link(root: ET.Element) -> str:
    links = [link.get("name") for link in root.findall("link") if link.get("name")]
    if not links:
        raise UrdfRuntimeError("URDF has no named links")
    children = {child.get("link") for child in root.findall("joint/child") if child.get("link")}
    roots = [link for link in links if link not in children]
    if len(roots) != 1:
        raise UrdfRuntimeError("URDF must have exactly one root link for runtime preparation")
    return roots[0]


def _rewrite_meshes(root: ET.Element, source: Path) -> None:
    """Make only packaged meshes absolute for the disposable compiler input."""
    asset_root = source.parent.parent.resolve()
    for mesh in root.findall(".//mesh"):
        filename = mesh.get("filename")
        if not filename:
            continue
        relative = Path(filename.replace("package://", ""))
        candidate = (source.parent / relative).resolve()
        if not candidate.is_file() or not candidate.is_relative_to(asset_root):
            # A few vendor URDFs carry a package prefix while retaining their
            # assets in the edition's meshes sibling.  Resolve by basename,
            # but never accept a path outside that packaged directory.
            candidate = (asset_root / "meshes" / relative.name).resolve()
        if not candidate.is_file() or not candidate.is_relative_to(asset_root / "meshes"):
            raise UrdfRuntimeError(f"URDF mesh is not a packaged asset: {filename}")
        mesh.set("filename", str(candidate))


def _runtime_urdf(edition: Edition, source_path: Path | None = None) -> bytes:
    source_path = source_path or edition.urdf
    if source_path is None or not source_path.is_file():
        raise UrdfRuntimeError("selected edition has no URDF description")
    try:
        root = ET.fromstring(source_path.read_bytes())
    except ET.ParseError as exc:
        raise UrdfRuntimeError(f"could not parse URDF: {exc}") from exc
    if root.tag != "robot":
        raise UrdfRuntimeError("runtime preparation requires a URDF robot document")
    _rewrite_meshes(root, edition.urdf or source_path)
    if edition.base_mode == "free":
        robot_root = _root_link(root)
        ET.SubElement(root, "link", {"name": "workbench_runtime_world"})
        joint = ET.SubElement(root, "joint", {"name": "workbench_runtime_free_base", "type": "floating"})
        ET.SubElement(joint, "parent", {"link": "workbench_runtime_world"})
        ET.SubElement(joint, "child", {"link": robot_root})
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


@dataclasses.dataclass
class PreparedUrdfRuntime:
    """An owned, temporary MJCF file plus its compiled dimensions."""

    path: Path
    nq: int
    nv: int
    nbody: int
    ngeom: int

    def close(self) -> None:
        self.path.unlink(missing_ok=True)


def prepare_urdf_runtime(edition: Edition, scene: dict[str, Any], source_path: Path | None = None) -> PreparedUrdfRuntime:
    """Compile a URDF into a disposable MJCF world without changing its bytes."""
    mujoco = _mujoco()
    source = _runtime_urdf(edition, source_path)
    descriptor, urdf_name = tempfile.mkstemp(prefix=".workbench-runtime-", suffix=".urdf", dir=(edition.urdf or source_path).parent)
    runtime_name: str | None = None
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(source)
        model = mujoco.MjModel.from_xml_path(urdf_name)
        try:
            descriptor, runtime_name = tempfile.mkstemp(prefix=".workbench-runtime-", suffix=".xml")
            os.close(descriptor)
            mujoco.mj_saveLastXML(runtime_name, model)
        finally:
            del model
        root = ET.parse(runtime_name)
        mujoco_root = root.getroot()
        option = mujoco_root.find("option")
        if option is None:
            option = ET.Element("option")
            mujoco_root.insert(0, option)
        option.set("gravity", " ".join(format(value, ".12g") for value in _numbers(scene.get("gravity", [0, 0, -9.81]), "gravity")))
        worldbody = mujoco_root.find("worldbody")
        if worldbody is None:
            raise UrdfRuntimeError("MuJoCo did not produce a runtime worldbody")
        spawn = scene.get("robot_spawn", {})
        xyz = _numbers(spawn.get("xyz", [0, 0, 0.75]), "robot_spawn.xyz")
        rpy = _numbers(spawn.get("rpy", [0, 0, 0]), "robot_spawn.rpy")
        robot_body = next((body for body in worldbody.findall("body") if body.find("joint[@type='free']") is not None), None)
        if robot_body is not None:
            robot_body.set("pos", " ".join(format(value, ".12g") for value in xyz))
            robot_body.set("euler", " ".join(format(value, ".12g") for value in rpy))
        for terrain in scene.get("terrain_instances", []):
            if not isinstance(terrain, dict) or not terrain.get("collision") or terrain.get("geometry", {}).get("type") != "plane":
                continue
            size = terrain["geometry"].get("size", [16, 16])
            pose = terrain.get("pose", {})
            geom = ET.SubElement(worldbody, "geom", {"name": f"workbench_scene_{terrain.get('instance_id', 'floor')}", "type": "plane", "size": f"{float(size[0]) / 2:g} {float(size[1]) / 2:g} {float(terrain['geometry'].get('thickness', .1)):g}", "pos": " ".join(format(value, ".12g") for value in _numbers(pose.get("xyz", [0, 0, 0]), "terrain.pose.xyz")), "euler": " ".join(format(value, ".12g") for value in _numbers(pose.get("rpy", [0, 0, 0]), "terrain.pose.rpy")), "rgba": "0.01 0.042 0.021 1"})
            physics = terrain.get("physics", {})
            geom.set("friction", f"{float(physics.get('friction', 1)):g} .01 .001")
            break
        ET.indent(root, space="  ")
        root.write(runtime_name, encoding="utf-8", xml_declaration=True)
        runtime_model = mujoco.MjModel.from_xml_path(runtime_name)
        try:
            return PreparedUrdfRuntime(Path(runtime_name), int(runtime_model.nq), int(runtime_model.nv), int(runtime_model.nbody), int(runtime_model.ngeom))
        finally:
            del runtime_model
    except Exception:
        if runtime_name:
            Path(runtime_name).unlink(missing_ok=True)
        raise
    finally:
        Path(urdf_name).unlink(missing_ok=True)
