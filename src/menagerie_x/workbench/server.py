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

from menagerie_x.assets import AssetError, RobotInspection, Variant, get_asset_paths, inspect_variant, load_scene, resolve_scene, variants
from menagerie_x.commands.mjcf import (
    MjcfCandidateError,
    authorize_managed_candidate,
    create_managed_candidate,
    discard_managed_candidate,
    list_managed_candidates,
    managed_candidate_path,
    next_collision_candidate_directory,
    validate_candidate,
)
from menagerie_x.workbench.collisions import (
    CollisionDraftNotFoundError,
    CollisionDocumentError,
    StaleCollisionDocumentError,
)
from menagerie_x.workbench.mjcf_collisions import MjcfCollisionDraftStore, load_mjcf_collision_document


class WorkbenchError(ValueError):
    """Raised when a workbench request cannot be served safely."""


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def _serialize_inspection(inspection: RobotInspection, root: Path | None = None) -> dict[str, Any]:
    variant = inspection.variant
    counts = Counter(issue.severity for issue in inspection.issues)
    return {
        "id": variant.name,
        "name": variant.name,
        "robot_version": variant.robot_version,
        "dof": variant.dof,
        "status": variant.status,
        "notes": variant.notes,
        "formats": {"urdf": True, "mjcf": variant.workbench_loadable},
        "workbench_loadable": variant.workbench_loadable,
        "conversion_guidance": None if variant.workbench_loadable else f"menagerie_x mjcf convert --source {variant.name} --candidate-id <reviewed-id> --output <empty-directory>",
        "mjcf_provenance": variant.mjcf_provenance,
        "source_revision": variant.urdf_revision,
        "source_drift_warning": variant.source_drift_warning,
        # URDF remains provenance and inspection input; the browser does not use
        # this hierarchy for rendering or simulation.
        "scene": inspection.description.as_dict() if inspection.description is not None else {},
        "default_scene": variant.default_scene,
        "scene_description": resolve_scene(variant, root).as_dict(),
        "issues": [issue.as_dict() for issue in inspection.issues],
        "summary": {"errors": counts["error"], "warnings": counts["warning"], "info": counts["info"]},
    }


def _build_robot_catalog(root: Path | None = None) -> dict[str, Any]:
    return {"robots": [_serialize_inspection(inspect_variant(variant), root) for variant in variants(root).values()]}


def _web_root() -> Path:
    return Path(__file__).with_name("web")


class WorkbenchRequestHandler(BaseHTTPRequestHandler):
    asset_root: Path
    draft_store: MjcfCollisionDraftStore

    def _send(self, status: HTTPStatus, content: bytes, content_type: str) -> None:
        try:
            self.send_response(status.value)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            # Browser loads are intentionally abortable when the selected model
            # changes. A cancelled mesh fetch is not a server error.
            return

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

    def _candidate_model(self, variant: Variant, candidate_id: str) -> Path:
        candidate = managed_candidate_path(variant.name, candidate_id, self.asset_root)
        model = candidate if candidate.is_file() else candidate / "model.xml"
        if not model.is_file():
            raise WorkbenchError(f"candidate {candidate_id!r} has no model.xml")
        return model

    def _candidate_metadata(self, variant: Variant, candidate_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        directory = managed_candidate_path(variant.name, candidate_id, self.asset_root)
        checked = validate_candidate(directory, variant)
        return dict(checked["candidate"]), dict(checked["report"])

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
            if parsed.path in {"/app.js", "/collision-editor.js", "/contact-visualizer.js", "/diagnostics.js", "/mjcf-renderer.js", "/mujoco-visualization.js", "/styles.css"}:
                self._serve_web_file(parsed.path.lstrip("/"))
                return
            if parsed.path.startswith("/vendor/"):
                self._serve_vendor(parsed.path.removeprefix("/vendor/"))
                return
            if parsed.path == "/api/robots":
                self._json(HTTPStatus.OK, {"ok": True, **_build_robot_catalog(self.asset_root)})
                return
            if parsed.path.startswith("/api/scenes/"):
                scene_id = urllib.parse.unquote(parsed.path.removeprefix("/api/scenes/"))
                if not scene_id or "/" in scene_id:
                    raise WorkbenchError("not found")
                self._json(HTTPStatus.OK, {"ok": True, "scene": load_scene(scene_id, self.asset_root).as_dict()})
                return
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) >= 3 and path_parts[:2] == ["api", "robots"]:
                variant = self._variant(urllib.parse.unquote(path_parts[2]))
                if len(path_parts) == 3:
                    self._json(HTTPStatus.OK, {"ok": True, "robot": _serialize_inspection(inspect_variant(variant), self.asset_root)})
                    return
                if len(path_parts) == 4 and path_parts[3] == "source":
                    fmt = urllib.parse.parse_qs(parsed.query).get("format", ["mjcf"])[0]
                    if fmt != "mjcf" or not variant.workbench_loadable:
                        raise WorkbenchError(f"{variant.name} has no authorized MJCF source")
                    source = variant.mjcf
                    self._send(HTTPStatus.OK, source.read_bytes(), "application/xml; charset=utf-8")
                    return
                if len(path_parts) == 4 and path_parts[3] == "mjcf-candidates":
                    self._json(HTTPStatus.OK, {"ok": True, "candidates": list_managed_candidates(variant.name, self.asset_root)})
                    return
                if len(path_parts) == 6 and path_parts[3] == "mjcf-candidates" and path_parts[5] == "source":
                    source = self._candidate_model(variant, urllib.parse.unquote(path_parts[4]))
                    self._send(HTTPStatus.OK, source.read_bytes(), "application/xml; charset=utf-8")
                    return
                if len(path_parts) == 7 and path_parts[3] == "mjcf-candidates" and path_parts[5] == "files":
                    requested = urllib.parse.unquote(path_parts[6])
                    candidate = (variant.meshes_dir / requested).resolve()
                    if not _is_within(candidate, variant.meshes_dir) or not candidate.is_file():
                        raise WorkbenchError("asset not found")
                    self._send(HTTPStatus.OK, candidate.read_bytes(), mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
                    return
                if len(path_parts) == 6 and path_parts[3] == "mjcf-candidates" and path_parts[5] == "collisions":
                    self._json(HTTPStatus.OK, {"ok": True, **load_mjcf_collision_document(self._candidate_model(variant, urllib.parse.unquote(path_parts[4]))).as_dict()})
                    return
                if len(path_parts) == 8 and path_parts[3] == "mjcf-candidates" and path_parts[5] == "collision-drafts" and path_parts[7] == "source":
                    source = self._candidate_model(variant, urllib.parse.unquote(path_parts[4]))
                    payload = self.draft_store.source_bytes(path_parts[6], source)
                    self._send(HTTPStatus.OK, payload, "application/xml; charset=utf-8")
                    return
                if len(path_parts) == 4 and path_parts[3] == "collisions":
                    if not variant.workbench_loadable or variant.mjcf is None:
                        raise WorkbenchError(f"{variant.name} has no authorized MJCF; collision editing is unavailable")
                    self._json(HTTPStatus.OK, {"ok": True, **load_mjcf_collision_document(variant.mjcf).as_dict()})
                    return
                if len(path_parts) == 6 and path_parts[3] == "collision-drafts" and path_parts[5] == "source":
                    if not variant.workbench_loadable or variant.mjcf is None:
                        raise WorkbenchError(f"{variant.name} has no authorized MJCF; collision editing is unavailable")
                    payload = self.draft_store.source_bytes(path_parts[4], variant.mjcf)
                    self._send(HTTPStatus.OK, payload, "application/xml; charset=utf-8")
                    return
                if len(path_parts) == 5 and path_parts[3] == "files":
                    requested = urllib.parse.unquote(path_parts[4])
                    candidate = (variant.meshes_dir / requested).resolve()
                    if not _is_within(candidate, variant.meshes_dir) or not candidate.is_file():
                        raise WorkbenchError("asset not found")
                    self._send(HTTPStatus.OK, candidate.read_bytes(), mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
                    return
            raise WorkbenchError("not found")
        except (WorkbenchError, AssetError, MjcfCandidateError) as exc:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def do_POST(self) -> None:
        try:
            parsed = urllib.parse.urlparse(self.path)
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) < 4 or path_parts[:2] != ["api", "robots"]:
                raise WorkbenchError("not found")
            variant = self._variant(urllib.parse.unquote(path_parts[2]))
            payload = self._body_json()
            if len(path_parts) == 4 and path_parts[3] == "mjcf-candidates":
                candidate_id = payload.get("candidate_id")
                if not isinstance(candidate_id, str):
                    raise MjcfCandidateError("candidate_id is required")
                self._json(HTTPStatus.CREATED, {"ok": True, **create_managed_candidate(variant.name, candidate_id, self.asset_root)})
                return
            if len(path_parts) == 6 and path_parts[3] == "mjcf-candidates" and path_parts[5] == "authorize":
                expected_revision = payload.get("expected_source_revision")
                if not isinstance(expected_revision, str):
                    raise MjcfCandidateError("expected_source_revision is required")
                result = authorize_managed_candidate(variant.name, urllib.parse.unquote(path_parts[4]), expected_revision, self.asset_root)
                self._json(HTTPStatus.OK, {"ok": True, **result})
                return
            if len(path_parts) == 6 and path_parts[3] == "mjcf-candidates" and path_parts[5] == "collision-drafts":
                source = self._candidate_model(variant, urllib.parse.unquote(path_parts[4]))
                self._json(HTTPStatus.CREATED, {"ok": True, **self.draft_store.create(source).as_dict()})
                return
            if len(path_parts) == 8 and path_parts[3] == "mjcf-candidates" and path_parts[5] == "collision-drafts" and path_parts[7] == "reset":
                source = self._candidate_model(variant, urllib.parse.unquote(path_parts[4]))
                self._json(HTTPStatus.OK, {"ok": True, **self.draft_store.reset(path_parts[6], source).as_dict()})
                return
            if len(path_parts) == 8 and path_parts[3] == "mjcf-candidates" and path_parts[5] == "collision-drafts" and path_parts[7] == "export":
                revision = payload.get("revision")
                if not isinstance(revision, str):
                    raise CollisionDocumentError("revision is required")
                candidate_id = urllib.parse.unquote(path_parts[4])
                source = self._candidate_model(variant, candidate_id)
                candidate, report = self._candidate_metadata(variant, candidate_id)
                output = self.draft_store.export(
                    path_parts[6], source, revision, source_variant=variant.name,
                    candidate_output=next_collision_candidate_directory(variant.name, candidate_id, self.asset_root),
                    parent_candidate=candidate, parent_report=report,
                )
                self._json(HTTPStatus.CREATED, {"ok": True, "output_path": str(output), "candidate_id": output.stem})
                return
            if not variant.workbench_loadable or variant.mjcf is None:
                raise WorkbenchError(f"{variant.name} has no authorized MJCF; collision editing is unavailable")
            if len(path_parts) == 4 and path_parts[3] == "collision-drafts":
                self._json(HTTPStatus.CREATED, {"ok": True, **self.draft_store.create(variant.mjcf).as_dict()})
                return
            if len(path_parts) == 6 and path_parts[3] == "collision-drafts" and path_parts[5] == "reset":
                self._json(HTTPStatus.OK, {"ok": True, **self.draft_store.reset(path_parts[4], variant.mjcf).as_dict()})
                return
            if len(path_parts) == 6 and path_parts[3] == "collision-drafts" and path_parts[5] == "export":
                revision = payload.get("revision")
                if not isinstance(revision, str):
                    raise CollisionDocumentError("revision is required")
                provenance = variant.mjcf_provenance or {}
                output = self.draft_store.export(
                    path_parts[4], variant.mjcf, revision, source_variant=variant.name,
                    parent_candidate={
                        "schema_version": 1,
                        "source_variant": variant.name,
                        "source_revision": provenance.get("source_revision", variant.urdf_revision),
                        "mujoco_version": provenance.get("mujoco_version", "unknown"),
                        "fixed_link_frame_sites": [],
                    },
                )
                self._json(HTTPStatus.CREATED, {"ok": True, "output_path": str(output)})
                return
            raise WorkbenchError("not found")
        except StaleCollisionDocumentError as exc:
            self._json(HTTPStatus.CONFLICT, {"ok": False, "error": str(exc)})
        except CollisionDraftNotFoundError as exc:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
        except (WorkbenchError, AssetError, MjcfCandidateError) as exc:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
        except CollisionDocumentError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def do_PUT(self) -> None:
        try:
            parsed = urllib.parse.urlparse(self.path)
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) == 7 and path_parts[:2] == ["api", "robots"] and path_parts[3] == "mjcf-candidates" and path_parts[5] == "collision-drafts":
                variant = self._variant(urllib.parse.unquote(path_parts[2]))
                payload = self._body_json()
                revision = payload.get("revision")
                if not isinstance(revision, str):
                    raise CollisionDocumentError("revision is required")
                source = self._candidate_model(variant, urllib.parse.unquote(path_parts[4]))
                session = self.draft_store.update(path_parts[6], source, revision, payload.get("primitives"), payload.get("retained_mesh_ids"))
                self._json(HTTPStatus.OK, {"ok": True, **session.as_dict()})
                return
            if len(path_parts) != 5 or path_parts[:2] != ["api", "robots"] or path_parts[3] != "collision-drafts":
                raise WorkbenchError("not found")
            variant = self._variant(urllib.parse.unquote(path_parts[2]))
            if not variant.workbench_loadable or variant.mjcf is None:
                raise WorkbenchError(f"{variant.name} has no authorized MJCF; collision editing is unavailable")
            payload = self._body_json()
            revision = payload.get("revision")
            if not isinstance(revision, str):
                raise CollisionDocumentError("revision is required")
            session = self.draft_store.update(
                path_parts[4],
                variant.mjcf,
                revision,
                payload.get("primitives"),
                payload.get("retained_mesh_ids"),
            )
            self._json(HTTPStatus.OK, {"ok": True, **session.as_dict()})
        except StaleCollisionDocumentError as exc:
            self._json(HTTPStatus.CONFLICT, {"ok": False, "error": str(exc)})
        except CollisionDraftNotFoundError as exc:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
        except (WorkbenchError, AssetError, MjcfCandidateError) as exc:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
        except CollisionDocumentError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def do_DELETE(self) -> None:
        try:
            parsed = urllib.parse.urlparse(self.path)
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) == 7 and path_parts[:2] == ["api", "robots"] and path_parts[3] == "mjcf-candidates" and path_parts[5] == "collision-drafts":
                variant = self._variant(urllib.parse.unquote(path_parts[2]))
                self.draft_store.discard(path_parts[6], self._candidate_model(variant, urllib.parse.unquote(path_parts[4])))
                self._json(HTTPStatus.OK, {"ok": True})
                return
            if len(path_parts) != 5 or path_parts[:2] != ["api", "robots"] or path_parts[3] != "collision-drafts":
                if len(path_parts) == 5 and path_parts[:2] == ["api", "robots"] and path_parts[3] == "mjcf-candidates":
                    variant = self._variant(urllib.parse.unquote(path_parts[2]))
                    discard_managed_candidate(variant.name, urllib.parse.unquote(path_parts[4]), self.asset_root)
                    self._json(HTTPStatus.OK, {"ok": True})
                    return
                raise WorkbenchError("not found")
            variant = self._variant(urllib.parse.unquote(path_parts[2]))
            if not variant.workbench_loadable or variant.mjcf is None:
                raise WorkbenchError(f"{variant.name} has no authorized MJCF; collision editing is unavailable")
            self.draft_store.discard(path_parts[4], variant.mjcf)
            self._json(HTTPStatus.OK, {"ok": True})
        except CollisionDraftNotFoundError as exc:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
        except (WorkbenchError, AssetError, MjcfCandidateError) as exc:
            self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(exc)})
        except CollisionDocumentError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except Exception as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}", file=sys.stderr)


class WorkbenchServer(ThreadingHTTPServer):
    """HTTP server that releases temporary collision drafts when it stops."""

    draft_store: MjcfCollisionDraftStore

    def server_close(self) -> None:
        super().server_close()
        self.draft_store.close()


def _make_handler(root: Path | None = None) -> type[WorkbenchRequestHandler]:
    class Handler(WorkbenchRequestHandler):
        pass

    Handler.asset_root = get_asset_paths(root).root
    Handler.draft_store = MjcfCollisionDraftStore()
    return Handler


def create_server(
    root: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 0,
) -> WorkbenchServer:
    server = WorkbenchServer((host, port), _make_handler(root))
    server.draft_store = server.RequestHandlerClass.draft_store
    return server


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
