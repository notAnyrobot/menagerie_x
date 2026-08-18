from __future__ import annotations

import argparse
import ipaddress
import json
import mimetypes
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser
import xml.etree.ElementTree as ET
from collections import Counter
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from menagerie_x.assets import (
    AssetError,
    MjcfEditionError,
    RobotInspection,
    Variant,
    delete_mjcf_edition,
    duplicate_mjcf_edition,
    edition_path,
    get_asset_paths,
    import_mjcf_edition,
    import_mjcf_variant,
    import_urdf_variant,
    inspect_variant,
    list_mjcf_editions,
    load_scene,
    rename_mjcf_edition,
    resolve_scene,
    set_default_mjcf_edition,
    variants,
)
from menagerie_x.commands.mjcf import (
    MjcfCandidateError,
    authorize_managed_candidate,
    create_managed_candidate,
    discard_managed_candidate,
    list_managed_candidates,
    managed_candidate_path,
    next_collision_candidate_directory,
    read_candidate_metadata_file,
    read_managed_candidate_metadata,
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


class NativeViewerAlreadyRunningError(WorkbenchError):
    """Raised when the workbench already owns a native MuJoCo viewer."""


class NativeViewerLaunchError(WorkbenchError):
    """Raised when the owned native MuJoCo process cannot be started."""


class NativeViewerRequestError(WorkbenchError):
    """Raised when a native viewer request contains unsupported input."""


def _workbench_restart_command(asset_root: Path, host: str, port: int) -> list[str]:
    """Return the exact local command used to restart this workbench server."""
    return [
        sys.executable,
        "-m",
        "menagerie_x.cli",
        "--root",
        str(asset_root),
        "workbench",
        "--host",
        host,
        "--port",
        str(port),
    ]


def _exec_workbench_restart(command: list[str]) -> None:
    os.execv(command[0], command)


def _loopback_host(host: str) -> bool:
    """Return whether a bound HTTP host is a numeric loopback address."""
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class NativeViewerProcessManager:
    """Own one native MuJoCo viewer process for a workbench server."""

    def __init__(
        self,
        asset_root: Path,
        process_factory: Callable[..., Any] = subprocess.Popen,
        executable: str | None = None,
    ) -> None:
        self._asset_root = asset_root.resolve()
        self._process_factory = process_factory
        self._executable = executable or sys.executable
        self._lock = threading.Lock()
        self._process: Any | None = None
        self._watcher: threading.Thread | None = None
        self._launch: dict[str, str] | None = None
        self._state = "idle"
        self._error: str | None = None

    def _read_stderr(self, stderr_log: Any) -> str:
        try:
            stderr_log.seek(0)
            output = stderr_log.read() or b""
            return output.decode("utf-8", errors="replace").strip() if isinstance(output, bytes) else str(output).strip()
        except (OSError, ValueError):
            return ""

    def _watch(self, process: Any, stderr_log: Any, launch: dict[str, str]) -> None:
        try:
            return_code = process.wait()
        except Exception as exc:  # pragma: no cover - defensive process cleanup
            return_code = -1
            stderr = str(exc)
        else:
            stderr = self._read_stderr(stderr_log)
        finally:
            stderr_log.close()
        with self._lock:
            if self._process is not process:
                return
            self._process = None
            self._watcher = None
            self._launch = launch
            if return_code == 0:
                self._state = "idle"
                self._error = None
            else:
                self._state = "failed"
                detail = stderr or f"MuJoCo viewer exited with status {return_code}."
                self._error = detail[:500]

    def launch(self, variant: Variant, edition: dict[str, Any], source: Path) -> dict[str, Any]:
        source = source.resolve()
        if not _is_within(source, self._asset_root) or not source.is_file():
            raise WorkbenchError("selected MJCF edition is not a packaged asset")
        launch = {"variant": variant.name, "edition": str(edition["id"]), "source": str(source)}
        command = [
            self._executable,
            "-m",
            "menagerie_x.cli",
            "--root",
            str(self._asset_root),
            "mujoco",
            "--mjcf",
            str(source),
        ]
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                raise NativeViewerAlreadyRunningError("a native MuJoCo viewer is already open")
            self._process = None
            self._watcher = None
            stderr_log = tempfile.TemporaryFile(mode="w+b")
            try:
                process = self._process_factory(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=stderr_log,
                )
            except OSError as exc:
                stderr_log.close()
                self._state = "failed"
                self._error = str(exc)[:500]
                self._launch = launch
                raise NativeViewerLaunchError(f"could not launch MuJoCo viewer: {exc}") from exc
            self._process = process
            self._launch = launch
            self._state = "running"
            self._error = None
            watcher = threading.Thread(target=self._watch, args=(process, stderr_log, launch), daemon=True)
            self._watcher = watcher
            watcher.start()
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": self._state,
                "launch": dict(self._launch) if self._launch else None,
                "error": self._error,
            }

    def close(self) -> None:
        with self._lock:
            process = self._process
            watcher = self._watcher
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
        if watcher is not None:
            watcher.join(timeout=2)
        if process.poll() is None:
            process.kill()
            if watcher is not None:
                watcher.join(timeout=2)


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def _serialize_inspection(inspection: RobotInspection, root: Path | None = None) -> dict[str, Any]:
    variant = inspection.variant
    counts = Counter(issue.severity for issue in inspection.issues)
    editions = list_mjcf_editions(variant, root)
    return {
        "id": variant.name,
        "name": variant.name,
        "robot_version": variant.robot_version,
        "dof": variant.dof,
        "status": variant.status,
        "notes": variant.notes,
        "formats": {"urdf": variant.urdf is not None, "mjcf": bool(editions)},
        "workbench_loadable": bool(editions),
        "conversion_guidance": None if editions else "Import an MJCF edition or convert this variant's URDF into its first edition.",
        "mjcf_provenance": variant.mjcf_provenance,
        "source_provenance": variant.source_provenance,
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
    native_viewer: NativeViewerProcessManager
    renderings_directory: Path
    restart_command: list[str]
    restart_executor: Callable[[list[str]], None]
    restart_lock: threading.Lock
    restart_scheduled: bool

    def _native_viewer_status(self) -> dict[str, Any]:
        status = self.native_viewer.status()
        return {"ok": True, "available": _loopback_host(str(self.server.server_address[0])), **status}

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

    def _save_rendering(self) -> Path:
        """Stream a browser-recorded video into the local renderings directory."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise WorkbenchError("invalid request length") from exc
        if length <= 0 or length > 2_000_000_000:
            raise WorkbenchError("rendering must be between 1 byte and 2 GB")

        filename = self.headers.get("X-Menagerie-Rendering-Filename", "")
        if not filename or Path(filename).name != filename:
            raise WorkbenchError("rendering filename must not include a path")
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].lower()
        extensions = {"video/mp4": ".mp4", "video/webm": ".webm"}
        expected_extension = extensions.get(content_type)
        if expected_extension is None or Path(filename).suffix.lower() != expected_extension:
            raise WorkbenchError("rendering must be an MP4 or WebM video with a matching filename extension")

        directory = self.renderings_directory
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / filename
        temporary: Path | None = None
        remaining = length
        try:
            with tempfile.NamedTemporaryFile(dir=directory, prefix=".rendering-", suffix=".part", delete=False) as stream:
                temporary = Path(stream.name)
                while remaining:
                    chunk = self.rfile.read(min(remaining, 1024 * 1024))
                    if not chunk:
                        raise WorkbenchError("rendering upload ended before all bytes were received")
                    stream.write(chunk)
                    remaining -= len(chunk)
            temporary.replace(output)
            return output
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def _schedule_restart(self) -> None:
        with self.restart_lock:
            if type(self).restart_scheduled:
                raise WorkbenchError("workbench restart is already in progress")
            type(self).restart_scheduled = True

        def restart_after_response() -> None:
            # Let the client receive its accepted response before exec closes the
            # listening socket. The browser then reloads the restarted server.
            time.sleep(0.2)
            try:
                self.native_viewer.close()
                self.draft_store.close()
                type(self).restart_executor(type(self).restart_command)
            except Exception as exc:  # pragma: no cover - only reached when exec fails
                with self.restart_lock:
                    type(self).restart_scheduled = False
                print(f"Workbench restart failed: {exc}", file=sys.stderr)

        threading.Thread(target=restart_after_response, name="menagerie-workbench-restart", daemon=True).start()

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
        try:
            checked = validate_candidate(directory, variant)
            report = dict(checked["report"])
            # validate_candidate intentionally keeps source drift alongside the
            # report.  Editions expose it as first-class selection metadata.
            report["source_drift_warning"] = checked.get("source_drift_warning")
            return dict(checked["candidate"]), report
        except MjcfCandidateError as exc:
            # Browser MuJoCo can still load a structurally sound candidate when
            # this optional Python validation dependency is unavailable.
            if "mujoco is not installed" not in str(exc):
                raise
            candidate, model = read_managed_candidate_metadata(variant.name, candidate_id, self.asset_root)
            root = ET.fromstring(model.read_bytes())
            if root.tag != "mujoco":
                raise WorkbenchError("candidate model is not an MJCF document")
            return candidate, {
                "candidate_id": candidate_id,
                "model": {"nbody": len(root.findall(".//body")), "ngeom": len(root.findall(".//geom"))},
                "unverified": "native MuJoCo validation is unavailable on the server",
            }

    def _edition(self, variant: Variant, edition_id: str) -> tuple[dict[str, Any], Path]:
        """Resolve a discovered edition; default is a marker, never a gate."""
        for record in list_mjcf_editions(variant, self.asset_root):
            if record["id"] == edition_id:
                source = Path(str(record["output_path"]))
                # Collision documents provide the revision used for optimistic
                # writes.  It is deliberately calculated from the saved XML.
                return {**record, "revision": load_mjcf_collision_document(source).revision}, source
        raise WorkbenchError(f"MJCF edition {edition_id!r} does not exist for {variant.name}")

    def _editions(self, variant: Variant) -> list[dict[str, Any]]:
        return [self._edition(variant, str(record["id"]))[0] for record in list_mjcf_editions(variant, self.asset_root)]

    def _edition_export_parent(self, variant: Variant, edition_id: str) -> tuple[dict[str, Any], dict[str, Any], str]:
        edition, _ = self._edition(variant, edition_id)
        provenance = edition.get("provenance") or variant.mjcf_provenance or {}
        return {
            "schema_version": 1,
            "source_variant": variant.name,
            "source_revision": provenance.get("source_revision", variant.urdf_revision),
            "mujoco_version": provenance.get("mujoco_version", "unknown"),
            "fixed_link_frame_sites": [],
        }, {}, edition_id

    def _edition_overwrite_metadata(
        self, variant: Variant, edition_id: str, source: Path
    ) -> tuple[dict[str, Any] | None, Path | None]:
        """Return metadata to preserve and its legacy sidecar, if any."""
        try:
            return read_candidate_metadata_file(source), None
        except MjcfCandidateError:
            # Older authorized MJCF files do not have review metadata to alter.
            return None, None

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
            if parsed.path in {"/app.js", "/collision-editor.js", "/contact-visualizer.js", "/diagnostics.js", "/mjcf-renderer.js", "/mujoco-visualization.js", "/scene-recording.js", "/styles.css"}:
                self._serve_web_file(parsed.path.lstrip("/"))
                return
            if parsed.path.startswith("/vendor/"):
                self._serve_vendor(parsed.path.removeprefix("/vendor/"))
                return
            if parsed.path == "/api/robots":
                self._json(HTTPStatus.OK, {"ok": True, **_build_robot_catalog(self.asset_root)})
                return
            if parsed.path == "/api/native-viewer":
                self._json(HTTPStatus.OK, self._native_viewer_status())
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
                if len(path_parts) == 4 and path_parts[3] == "editions":
                    self._json(HTTPStatus.OK, {"ok": True, "editions": self._editions(variant)})
                    return
                if len(path_parts) == 6 and path_parts[3] == "editions" and path_parts[5] == "source":
                    _, source = self._edition(variant, urllib.parse.unquote(path_parts[4]))
                    self._send(HTTPStatus.OK, source.read_bytes(), "application/xml; charset=utf-8")
                    return
                if len(path_parts) == 7 and path_parts[3] == "editions" and path_parts[5] == "files":
                    requested = urllib.parse.unquote(path_parts[6])
                    candidate = (variant.meshes_dir / requested).resolve()
                    if not _is_within(candidate, variant.meshes_dir) or not candidate.is_file():
                        raise WorkbenchError("asset not found")
                    self._send(HTTPStatus.OK, candidate.read_bytes(), mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
                    return
                if len(path_parts) == 6 and path_parts[3] == "editions" and path_parts[5] == "collisions":
                    _, source = self._edition(variant, urllib.parse.unquote(path_parts[4]))
                    self._json(HTTPStatus.OK, {"ok": True, **load_mjcf_collision_document(source).as_dict()})
                    return
                if len(path_parts) == 8 and path_parts[3] == "editions" and path_parts[5] == "collision-drafts" and path_parts[7] == "source":
                    _, source = self._edition(variant, urllib.parse.unquote(path_parts[4]))
                    payload = self.draft_store.source_bytes(path_parts[6], source)
                    self._send(HTTPStatus.OK, payload, "application/xml; charset=utf-8")
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
            if path_parts == ["api", "restart"]:
                if not _loopback_host(str(self.server.server_address[0])):
                    self._json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "workbench restart is available only on a loopback-bound workbench"})
                    return
                if self._body_json():
                    raise WorkbenchError("workbench restart requests must use an empty JSON object")
                self._schedule_restart()
                self._json(HTTPStatus.ACCEPTED, {"ok": True, "message": "workbench restart scheduled"})
                return
            if path_parts == ["api", "renderings"]:
                if not _loopback_host(str(self.server.server_address[0])):
                    self._json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "rendering export is available only on a loopback-bound workbench"})
                    return
                output = self._save_rendering()
                self._json(HTTPStatus.CREATED, {"ok": True, "output_path": str(output)})
                return
            if path_parts in (["api", "variants", "import-mjcf"], ["api", "variants", "import-urdf"]):
                if not _loopback_host(str(self.server.server_address[0])):
                    self._json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "asset import is available only on a loopback-bound workbench"})
                    return
                payload = self._body_json()
                variant_id = payload.get("variant_id")
                source_path = payload.get("source_path")
                if not isinstance(variant_id, str) or not isinstance(source_path, str):
                    raise WorkbenchError("variant_id and source_path are required")
                result = (
                    import_mjcf_variant(variant_id, Path(source_path), self.asset_root)
                    if path_parts[-1] == "import-mjcf"
                    else import_urdf_variant(variant_id, Path(source_path), self.asset_root)
                )
                self._json(HTTPStatus.CREATED, {"ok": True, **result})
                return
            if len(path_parts) < 4 or path_parts[:2] != ["api", "robots"]:
                raise WorkbenchError("not found")
            variant = self._variant(urllib.parse.unquote(path_parts[2]))
            payload = self._body_json()
            if len(path_parts) == 5 and path_parts[3:] == ["editions", "import"]:
                if not _loopback_host(str(self.server.server_address[0])):
                    self._json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "asset import is available only on a loopback-bound workbench"})
                    return
                source_path = payload.get("source_path")
                edition_id = payload.get("edition_id")
                if not isinstance(source_path, str) or not isinstance(edition_id, str):
                    raise WorkbenchError("source_path and edition_id are required")
                result = import_mjcf_edition(variant.name, Path(source_path), edition_id, self.asset_root)
                self._json(HTTPStatus.CREATED, {"ok": True, **result})
                return
            if len(path_parts) == 6 and path_parts[3] == "editions":
                edition_id = urllib.parse.unquote(path_parts[4])
                operation = path_parts[5]
                if operation == "duplicate":
                    new_id = payload.get("edition_id")
                    if not isinstance(new_id, str):
                        raise WorkbenchError("edition_id is required")
                    self._json(HTTPStatus.CREATED, {"ok": True, **duplicate_mjcf_edition(variant.name, edition_id, new_id, self.asset_root)})
                    return
                if operation == "rename":
                    new_id = payload.get("edition_id")
                    if not isinstance(new_id, str):
                        raise WorkbenchError("edition_id is required")
                    self._json(HTTPStatus.OK, {"ok": True, **rename_mjcf_edition(variant.name, edition_id, new_id, self.asset_root)})
                    return
                if operation == "set-default":
                    self._json(HTTPStatus.OK, {"ok": True, **set_default_mjcf_edition(variant.name, edition_id, self.asset_root)})
                    return
            if len(path_parts) == 6 and path_parts[3] == "editions" and path_parts[5] == "native-viewer":
                if payload:
                    raise NativeViewerRequestError("native viewer requests must use an empty JSON object")
                if not _loopback_host(str(self.server.server_address[0])):
                    self._json(HTTPStatus.FORBIDDEN, {"ok": False, "error": "native MuJoCo viewer launch is available only on a loopback-bound workbench"})
                    return
                edition, source = self._edition(variant, urllib.parse.unquote(path_parts[4]))
                self._json(HTTPStatus.ACCEPTED, self.native_viewer.launch(variant, edition, source) | {"ok": True, "available": True})
                return
            if len(path_parts) == 6 and path_parts[3] == "editions" and path_parts[5] == "collision-drafts":
                _, source = self._edition(variant, urllib.parse.unquote(path_parts[4]))
                self._json(HTTPStatus.CREATED, {"ok": True, **self.draft_store.create(source).as_dict()})
                return
            if len(path_parts) == 8 and path_parts[3] == "editions" and path_parts[5] == "collision-drafts" and path_parts[7] == "reset":
                _, source = self._edition(variant, urllib.parse.unquote(path_parts[4]))
                self._json(HTTPStatus.OK, {"ok": True, **self.draft_store.reset(path_parts[6], source).as_dict()})
                return
            if len(path_parts) == 8 and path_parts[3] == "editions" and path_parts[5] == "collision-drafts" and path_parts[7] == "mirror-preview":
                revision = payload.get("revision")
                direction = payload.get("direction")
                if not isinstance(revision, str):
                    raise CollisionDocumentError("revision is required")
                if not isinstance(direction, str):
                    raise CollisionDocumentError("mirror direction is required")
                _, source = self._edition(variant, urllib.parse.unquote(path_parts[4]))
                preview = self.draft_store.mirror_preview(path_parts[6], source, revision, direction)
                self._json(HTTPStatus.OK, {"ok": True, **preview})
                return
            if len(path_parts) == 8 and path_parts[3] == "editions" and path_parts[5] == "collision-drafts" and path_parts[7] == "mirror":
                revision = payload.get("revision")
                direction = payload.get("direction")
                if not isinstance(revision, str):
                    raise CollisionDocumentError("revision is required")
                if not isinstance(direction, str):
                    raise CollisionDocumentError("mirror direction is required")
                if payload.get("confirmed") is not True:
                    raise CollisionDocumentError("mirror confirmation is required before overwriting target collision shapes")
                _, source = self._edition(variant, urllib.parse.unquote(path_parts[4]))
                session, preview = self.draft_store.mirror(path_parts[6], source, revision, direction)
                self._json(HTTPStatus.OK, {"ok": True, **session.as_dict(), "mirror": preview})
                return
            if len(path_parts) == 8 and path_parts[3] == "editions" and path_parts[5] == "collision-drafts" and path_parts[7] == "export":
                revision = payload.get("revision")
                if not isinstance(revision, str):
                    raise CollisionDocumentError("revision is required")
                edition_id = urllib.parse.unquote(path_parts[4])
                _, source = self._edition(variant, edition_id)
                candidate, report, parent_id = self._edition_export_parent(variant, edition_id)
                output = self.draft_store.export(
                    path_parts[6], source, revision, source_variant=variant.name,
                    candidate_output=next_collision_candidate_directory(variant.name, parent_id, self.asset_root),
                    parent_candidate=candidate, parent_report=report,
                )
                self._json(HTTPStatus.CREATED, {"ok": True, "output_path": str(output), "edition_id": output.stem, "revision": load_mjcf_collision_document(output).revision})
                return
            if len(path_parts) == 8 and path_parts[3] == "editions" and path_parts[5] == "collision-drafts" and path_parts[7] == "overwrite":
                revision = payload.get("revision")
                edition_id = urllib.parse.unquote(path_parts[4])
                if not isinstance(revision, str):
                    raise CollisionDocumentError("revision is required")
                if payload.get("edition_id") != edition_id:
                    raise CollisionDocumentError("edition_id confirmation must match the selected edition")
                _, source = self._edition(variant, edition_id)
                metadata, metadata_path = self._edition_overwrite_metadata(variant, edition_id, source)
                output = self.draft_store.overwrite(
                    path_parts[6], source, revision, metadata, metadata_path
                )
                self._json(HTTPStatus.OK, {"ok": True, "output_path": str(output), "edition_id": edition_id, "revision": load_mjcf_collision_document(output).revision})
                return
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
        except NativeViewerAlreadyRunningError as exc:
            self._json(HTTPStatus.CONFLICT, {"ok": False, "error": str(exc)})
        except (NativeViewerLaunchError, NativeViewerRequestError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
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
            if len(path_parts) == 7 and path_parts[:2] == ["api", "robots"] and path_parts[3] == "editions" and path_parts[5] == "collision-drafts":
                variant = self._variant(urllib.parse.unquote(path_parts[2]))
                payload = self._body_json()
                revision = payload.get("revision")
                if not isinstance(revision, str):
                    raise CollisionDocumentError("revision is required")
                _, source = self._edition(variant, urllib.parse.unquote(path_parts[4]))
                session = self.draft_store.update(path_parts[6], source, revision, payload.get("primitives"), payload.get("retained_mesh_ids"))
                self._json(HTTPStatus.OK, {"ok": True, **session.as_dict()})
                return
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
            if len(path_parts) == 5 and path_parts[:2] == ["api", "robots"] and path_parts[3] == "editions":
                variant = self._variant(urllib.parse.unquote(path_parts[2]))
                delete_mjcf_edition(variant.name, urllib.parse.unquote(path_parts[4]), self.asset_root)
                self._json(HTTPStatus.OK, {"ok": True})
                return
            if len(path_parts) == 7 and path_parts[:2] == ["api", "robots"] and path_parts[3] == "editions" and path_parts[5] == "collision-drafts":
                variant = self._variant(urllib.parse.unquote(path_parts[2]))
                _, source = self._edition(variant, urllib.parse.unquote(path_parts[4]))
                self.draft_store.discard(path_parts[6], source)
                self._json(HTTPStatus.OK, {"ok": True})
                return
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
    """HTTP server that releases drafts and owned native viewers when it stops."""

    draft_store: MjcfCollisionDraftStore
    native_viewer: NativeViewerProcessManager

    def server_close(self) -> None:
        self.native_viewer.close()
        self.draft_store.close()
        super().server_close()


def _make_handler(
    root: Path | None = None,
    process_factory: Callable[..., Any] = subprocess.Popen,
    renderings_directory: Path | None = None,
    restart_executor: Callable[[list[str]], None] = _exec_workbench_restart,
) -> type[WorkbenchRequestHandler]:
    class Handler(WorkbenchRequestHandler):
        pass

    Handler.asset_root = get_asset_paths(root).root
    Handler.draft_store = MjcfCollisionDraftStore()
    Handler.native_viewer = NativeViewerProcessManager(Handler.asset_root, process_factory)
    Handler.renderings_directory = (renderings_directory or Path.home() / "Videos" / "menagerie_workbench" / "renderings").expanduser()
    Handler.restart_command = _workbench_restart_command(Handler.asset_root, "", 0)
    Handler.restart_executor = restart_executor
    Handler.restart_lock = threading.Lock()
    Handler.restart_scheduled = False
    return Handler


def create_server(
    root: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    process_factory: Callable[..., Any] = subprocess.Popen,
    renderings_directory: Path | None = None,
    restart_executor: Callable[[list[str]], None] = _exec_workbench_restart,
) -> WorkbenchServer:
    server = WorkbenchServer((host, port), _make_handler(root, process_factory, renderings_directory, restart_executor))
    server.draft_store = server.RequestHandlerClass.draft_store
    server.native_viewer = server.RequestHandlerClass.native_viewer
    bound_host, bound_port = server.server_address
    server.RequestHandlerClass.restart_command = _workbench_restart_command(server.RequestHandlerClass.asset_root, str(bound_host), bound_port)
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Browser workbench for packaged robot descriptions")
    parser.add_argument("--root", type=Path, default=None, help="Menagerie checkout or asset root")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="Stable local port for browser-refresh-friendly restarts")
    browser_mode = parser.add_mutually_exclusive_group()
    browser_mode.add_argument(
        "--open-browser",
        action="store_true",
        help="Open the workbench URL in a browser after starting (off by default so restarts reuse an existing tab).",
    )
    browser_mode.add_argument("--no-browser", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    server = create_server(args.root, args.host, args.port)
    host, port = server.server_address
    url = f"http://{host}:{port}"
    print(f"Serving Menagerie Workbench at {url}", flush=True)
    if args.open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Menagerie Workbench.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
