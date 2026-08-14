from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import urllib.parse
import webbrowser
from collections import Counter
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from menagerie_x.assets import AssetError, RobotInspection, Variant, get_asset_paths, inspect_variant, variants
from menagerie_x.workbench.collisions import (
    CollisionDocumentError,
    StaleCollisionDocumentError,
    export_collision_copy,
    load_collision_document,
)


class WorkbenchError(ValueError):
    """Raised when a workbench request cannot be served safely."""


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def _serialize_inspection(inspection: RobotInspection) -> dict[str, Any]:
    variant = inspection.variant
    counts = Counter(issue.severity for issue in inspection.issues)
    return {
        "id": variant.name,
        "name": variant.name,
        "robot_version": variant.robot_version,
        "dof": variant.dof,
        "status": variant.status,
        "notes": variant.notes,
        "formats": {"urdf": True, "mjcf": variant.mjcf is not None and variant.mjcf.is_file()},
        "scene": inspection.description.as_dict() if inspection.description is not None else {},
        "issues": [issue.as_dict() for issue in inspection.issues],
        "summary": {"errors": counts["error"], "warnings": counts["warning"], "info": counts["info"]},
    }


def _build_robot_catalog(root: Path | None = None) -> dict[str, Any]:
    return {"robots": [_serialize_inspection(inspect_variant(variant)) for variant in variants(root).values()]}


def _web_root() -> Path:
    return Path(__file__).with_name("web")


class WorkbenchRequestHandler(BaseHTTPRequestHandler):
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

    def _body_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise WorkbenchError("invalid request length") from exc
        if length <= 0 or length > 2_000_000:
            raise WorkbenchError("request body must be a JSON object smaller than 2 MB")
        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as exc:
            raise WorkbenchError("request body is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise WorkbenchError("request body must be a JSON object")
        return payload

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
            raise WorkbenchError("browser dependencies are missing; run npm install in src/menagerie_x/workbench/web")
        content_type = "application/wasm" if path.suffix == ".wasm" else "text/javascript; charset=utf-8"
        self._send(HTTPStatus.OK, path.read_bytes(), content_type)

    def do_GET(self) -> None:
        try:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/":
                self._serve_web_file("index.html")
                return
            if parsed.path in {"/app.js", "/collision-editor.js", "/styles.css"}:
                self._serve_web_file(parsed.path.lstrip("/"))
                return
            if parsed.path.startswith("/vendor/"):
                self._serve_vendor(parsed.path.removeprefix("/vendor/"))
                return
            if parsed.path == "/api/robots":
                self._json(HTTPStatus.OK, {"ok": True, **_build_robot_catalog(self.asset_root)})
                return
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) >= 3 and path_parts[:2] == ["api", "robots"]:
                variant = self._variant(urllib.parse.unquote(path_parts[2]))
                if len(path_parts) == 3:
                    self._json(HTTPStatus.OK, {"ok": True, "robot": _serialize_inspection(inspect_variant(variant))})
                    return
                if len(path_parts) == 4 and path_parts[3] == "source":
                    fmt = urllib.parse.parse_qs(parsed.query).get("format", ["urdf"])[0]
                    source = variant.urdf if fmt == "urdf" else variant.mjcf if fmt == "mjcf" else None
                    if source is None or not source.is_file():
                        raise WorkbenchError(f"{variant.name} has no {fmt.upper()} source")
                    self._send(HTTPStatus.OK, source.read_bytes(), "application/xml; charset=utf-8")
                    return
                if len(path_parts) == 4 and path_parts[3] == "collisions":
                    self._json(HTTPStatus.OK, {"ok": True, **load_collision_document(variant.urdf).as_dict()})
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

    def do_POST(self) -> None:
        try:
            parsed = urllib.parse.urlparse(self.path)
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) != 4 or path_parts[:2] != ["api", "robots"] or path_parts[3] != "collision-exports":
                raise WorkbenchError("not found")
            variant = self._variant(urllib.parse.unquote(path_parts[2]))
            payload = self._body_json()
            revision = payload.get("revision")
            if not isinstance(revision, str):
                raise CollisionDocumentError("revision is required")
            output = export_collision_copy(variant.urdf, revision, payload.get("collisions"))
            self._json(HTTPStatus.CREATED, {"ok": True, "output_path": str(output)})
        except StaleCollisionDocumentError as exc:
            self._json(HTTPStatus.CONFLICT, {"ok": False, "error": str(exc)})
        except (WorkbenchError, AssetError) as exc:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
        except CollisionDocumentError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}", file=sys.stderr)


def _make_handler(root: Path | None = None) -> type[WorkbenchRequestHandler]:
    class Handler(WorkbenchRequestHandler):
        pass

    Handler.asset_root = get_asset_paths(root).root
    return Handler


def create_server(
    root: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 0,
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _make_handler(root))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Browser workbench for Astro robot assets")
    parser.add_argument("--root", type=Path, default=None, help="Menagerie checkout or asset root")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)

    server = create_server(args.root, args.host, args.port)
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
