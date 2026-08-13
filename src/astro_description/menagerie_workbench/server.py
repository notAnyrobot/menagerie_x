from __future__ import annotations

import argparse
import dataclasses
import json
import mimetypes
import sys
import urllib.parse
import webbrowser
import xml.etree.ElementTree as ET
from collections import Counter
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from astro_description.assets import AssetError, Variant, get_asset_paths, variants


class WorkbenchError(ValueError):
    """Raised when a workbench request cannot be served safely."""


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


def _robot_file_path(variant: Variant, source_path: Path, filename: str) -> Path:
    return (source_path.parent / filename).resolve()


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def _link_scene(link: ET.Element, source_path: Path) -> dict[str, Any]:
    visuals: list[dict[str, Any]] = []
    for visual in link.findall("visual"):
        mesh = visual.find("./geometry/mesh")
        filename = mesh.get("filename") if mesh is not None else None
        if not filename:
            continue
        mesh_path = _robot_file_path_placeholder(source_path, filename)
        visuals.append(
            {
                "name": visual.get("name", link.get("name", "visual")),
                "filename": filename,
                "asset_path": mesh_path,
                "origin": _parse_origin(visual.find("origin")),
                "scale": [float(value) for value in mesh.get("scale", "1 1 1").split()] if mesh is not None else [1.0] * 3,
            }
        )
    return {"name": link.get("name", ""), "visuals": visuals}


def _robot_file_path_placeholder(source_path: Path, filename: str) -> str:
    """Return the checkout-relative path later mapped to the asset endpoint."""
    return str((source_path.parent / filename).resolve())


def _parse_urdf(variant: Variant) -> tuple[dict[str, Any], list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    try:
        root = ET.fromstring(variant.urdf.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, [ValidationIssue("error", "urdf-missing", "URDF source file is missing", path=str(variant.urdf))]
    except ET.ParseError as exc:
        return {}, [ValidationIssue("error", "urdf-xml", f"URDF XML is not well formed: {exc}", path=str(variant.urdf))]

    links = [_link_scene(link, variant.urdf) for link in root.findall("link")]
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
                "axis": [float(value) for value in joint.find("axis").get("xyz", "0 0 1").split()] if joint.find("axis") is not None else [0.0, 0.0, 1.0],
            }
        )
        if not name:
            issues.append(ValidationIssue("error", "joint-name-missing", "Joint has no name", None, "joint"))
        for role, link_name in (("parent", parent_name), ("child", child_name)):
            if link_name not in link_names:
                issues.append(
                    ValidationIssue("error", "joint-link-missing", f"Joint {role} link is not declared: {link_name or '(empty)'}", name or None, "joint")
                )
        if joint.get("type") in {"revolute", "prismatic"} and joint.find("limit") is None:
            issues.append(ValidationIssue("warning", "joint-limit-missing", "Movable joint has no limit block", name or None, "joint"))

    child_links = {joint["child"] for joint in joints if joint["child"]}
    roots = sorted(link_names - child_links)
    if not roots:
        issues.append(ValidationIssue("error", "root-link-missing", "URDF has no root link", None, "robot"))
    elif len(roots) > 1:
        issues.append(ValidationIssue("warning", "multiple-roots", f"URDF has {len(roots)} root links", None, "robot"))
    return {"links": links, "joints": joints, "root_links": roots}, issues


def validate_robot(variant: Variant) -> dict[str, Any]:
    scene, issues = _parse_urdf(variant)
    if variant.mjcf is None:
        issues.append(
            ValidationIssue(
                "info",
                "mjcf-unavailable",
                "No authored MJCF is packaged; the browser will compile the URDF with MuJoCo WASM.",
                path=str(variant.urdf),
            )
        )
    elif not variant.mjcf.is_file():
        issues.append(ValidationIssue("error", "mjcf-missing", "Manifest references a missing MJCF file", path=str(variant.mjcf)))
    counts = Counter(issue.severity for issue in issues)
    return {
        "id": variant.name,
        "name": variant.name,
        "robot_version": variant.robot_version,
        "dof": variant.dof,
        "status": variant.status,
        "notes": variant.notes,
        "formats": {"urdf": True, "mjcf": variant.mjcf is not None and variant.mjcf.is_file()},
        "scene": scene,
        "issues": [issue.as_dict() for issue in issues],
        "summary": {"errors": counts["error"], "warnings": counts["warning"], "info": counts["info"]},
    }


def build_robot_catalog(root: Path | None = None) -> dict[str, Any]:
    return {"robots": [validate_robot(variant) for variant in variants(root).values()]}


def _web_root() -> Path:
    return Path(__file__).with_name("web")


class MenagerieRequestHandler(BaseHTTPRequestHandler):
    asset_root: Path

    def _send(self, status: HTTPStatus, content: bytes, content_type: str) -> None:
        self.send_response(status.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

    def _variant(self, name: str) -> Variant:
        try:
            return variants(self.asset_root)[name]
        except KeyError as exc:
            raise WorkbenchError(f"unknown robot {name!r}") from exc

    def _serve_web_file(self, relative: str) -> None:
        candidate = (_web_root() / relative).resolve()
        if not _is_within(candidate, _web_root()) or not candidate.is_file():
            raise WorkbenchError("not found")
        self._send(HTTPStatus.OK, candidate.read_bytes(), mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")

    def _serve_vendor(self, filename: str) -> None:
        vendor = {
            "three.module.js": _web_root() / "node_modules" / "three" / "build" / "three.module.js",
            "three.core.js": _web_root() / "node_modules" / "three" / "build" / "three.core.js",
            "OrbitControls.js": _web_root() / "node_modules" / "three" / "examples" / "jsm" / "controls" / "OrbitControls.js",
            "STLLoader.js": _web_root() / "node_modules" / "three" / "examples" / "jsm" / "loaders" / "STLLoader.js",
            "mujoco.js": _web_root() / "node_modules" / "@mujoco" / "mujoco" / "mujoco.js",
            "mujoco.wasm": _web_root() / "node_modules" / "@mujoco" / "mujoco" / "mujoco.wasm",
        }
        try:
            path = vendor[filename]
        except KeyError as exc:
            raise WorkbenchError("not found") from exc
        if not path.is_file():
            raise WorkbenchError("browser dependencies are missing; run npm install in menagerie_workbench/web")
        content_type = "application/wasm" if path.suffix == ".wasm" else "text/javascript; charset=utf-8"
        self._send(HTTPStatus.OK, path.read_bytes(), content_type)

    def do_GET(self) -> None:
        try:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/":
                self._serve_web_file("index.html")
                return
            if parsed.path in {"/app.js", "/styles.css"}:
                self._serve_web_file(parsed.path.lstrip("/"))
                return
            if parsed.path.startswith("/vendor/"):
                self._serve_vendor(parsed.path.removeprefix("/vendor/"))
                return
            if parsed.path == "/api/robots":
                self._json(HTTPStatus.OK, {"ok": True, **build_robot_catalog(self.asset_root)})
                return
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) >= 3 and path_parts[:2] == ["api", "robots"]:
                variant = self._variant(urllib.parse.unquote(path_parts[2]))
                if len(path_parts) == 3:
                    self._json(HTTPStatus.OK, {"ok": True, "robot": validate_robot(variant)})
                    return
                if len(path_parts) == 4 and path_parts[3] == "source":
                    fmt = urllib.parse.parse_qs(parsed.query).get("format", ["urdf"])[0]
                    source = variant.urdf if fmt == "urdf" else variant.mjcf if fmt == "mjcf" else None
                    if source is None or not source.is_file():
                        raise WorkbenchError(f"{variant.name} has no {fmt.upper()} source")
                    self._send(HTTPStatus.OK, source.read_bytes(), "application/xml; charset=utf-8")
                    return
                if len(path_parts) == 5 and path_parts[3] == "files":
                    requested = urllib.parse.unquote(path_parts[4])
                    candidate = (variant.meshes_dir / requested).resolve()
                    if not _is_within(candidate, variant.meshes_dir) or not candidate.is_file():
                        raise WorkbenchError("asset not found")
                    self._send(HTTPStatus.OK, candidate.read_bytes(), mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
                    return
            raise WorkbenchError("not found")
        except (WorkbenchError, AssetError) as exc:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}", file=sys.stderr)


def make_handler(root: Path | None = None) -> type[MenagerieRequestHandler]:
    class Handler(MenagerieRequestHandler):
        pass

    Handler.asset_root = get_asset_paths(root).root
    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Browser workbench for Astro robot assets")
    parser.add_argument("--root", type=Path, default=None, help="Astro description checkout or asset root")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), make_handler(args.root))
    host, port = server.server_address
    url = f"http://{host}:{port}"
    print(f"Serving Robot Menagerie Workbench at {url}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Robot Menagerie Workbench.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
