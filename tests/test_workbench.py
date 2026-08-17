import json
import pathlib
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request

from menagerie_x.assets import variants
from menagerie_x.workbench import create_server
from menagerie_x.workbench.server import NativeViewerAlreadyRunningError, NativeViewerProcessManager, WorkbenchRequestHandler


ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "src" / "menagerie_x" / "workbench" / "web"


class FakeNativeViewerProcess:
    def __init__(self, stderr: str = ""):
        self.stderr_log = None
        self.initial_stderr = stderr
        self.returncode = None
        self._finished = threading.Event()
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def wait(self):
        self._finished.wait(timeout=3)
        return self.returncode if self.returncode is not None else -1

    def finish(self, returncode: int = 0):
        self.returncode = returncode
        self._finished.set()

    def write_stderr(self, message: str):
        assert self.stderr_log is not None
        self.stderr_log.write(message.encode("utf-8"))
        self.stderr_log.flush()

    def terminate(self):
        self.terminated = True
        self.finish(-15)

    def kill(self):
        self.killed = True
        self.finish(-9)


def wait_for_viewer_state(manager: NativeViewerProcessManager, state: str) -> dict:
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        status = manager.status()
        if status["state"] == state:
            return status
        time.sleep(0.01)
    raise AssertionError(f"native viewer did not reach {state}: {manager.status()}")


class NativeViewerProcessManagerTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.processes = []

        def factory(*args, **kwargs):
            self.calls.append((args, kwargs))
            process = FakeNativeViewerProcess()
            process.stderr_log = kwargs["stderr"]
            self.processes.append(process)
            return process

        self.manager = NativeViewerProcessManager(ROOT / "src" / "menagerie_x" / "assets", factory)
        self.variant = variants(ROOT)["astro_v2"]
        self.source = self.variant.mjcf

    def tearDown(self):
        self.manager.close()

    def test_launch_tracks_exact_saved_source_and_rejects_duplicates(self):
        status = self.manager.launch(self.variant, {"id": "authorized"}, self.source)

        self.assertEqual(status["state"], "running")
        self.assertEqual(status["launch"]["source"], str(self.source.resolve()))
        command = self.calls[0][0][0]
        self.assertIsNot(self.calls[0][1]["stderr"], subprocess.PIPE)
        self.assertEqual(command[:5], [sys.executable, "-m", "menagerie_x.cli", "--root", str((ROOT / "src" / "menagerie_x" / "assets").resolve())])
        self.assertEqual(command[-2:], ["--mjcf", str(self.source.resolve())])
        with self.assertRaises(NativeViewerAlreadyRunningError):
            self.manager.launch(self.variant, {"id": "authorized"}, self.variant.mjcf)

        self.processes[0].finish(0)
        self.assertEqual(wait_for_viewer_state(self.manager, "idle")["error"], None)

    def test_failed_exit_preserves_stderr_and_shutdown_terminates_owned_process(self):
        self.manager.launch(self.variant, {"id": "authorized"}, self.variant.mjcf)
        self.processes[0].write_stderr("GL context unavailable\n" + "x" * 2048)
        self.processes[0].finish(1)
        self.assertIn("GL context unavailable", wait_for_viewer_state(self.manager, "failed")["error"])

        self.manager.launch(self.variant, {"id": "authorized"}, self.variant.mjcf)
        process = self.processes[1]
        self.manager.close()
        self.assertTrue(process.terminated)


class NativeViewerEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.processes = []

        def factory(*_args, **_kwargs):
            process = FakeNativeViewerProcess()
            process.stderr_log = _kwargs["stderr"]
            cls.processes.append(process)
            return process

        cls.server = create_server(ROOT, process_factory=factory)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def _request(self, path: str, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers={"Content-Type": "application/json"} if payload is not None else {},
            method=method,
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_endpoint_resolves_saved_edition_server_side_and_reports_lifecycle(self):
        status_code, status = self._request("/api/native-viewer")
        self.assertEqual(status_code, 200)
        self.assertTrue(status["available"])
        self.assertEqual(status["state"], "idle")
        _, editions = self._request("/api/robots/astro_v2/editions")
        edition = editions["editions"][0]
        resolver = object.__new__(WorkbenchRequestHandler)
        resolver.asset_root = ROOT / "src" / "menagerie_x" / "assets"
        variant = variants(ROOT)["astro_v2"]
        for record in editions["editions"]:
            _record, source = resolver._edition(variant, record["id"])
            self.assertEqual(str(source.resolve()), record["output_path"])
        path = f"/api/robots/astro_v2/editions/{edition['id']}/native-viewer"
        status_code, launched = self._request(path, "POST", {})
        self.assertEqual(status_code, 202)
        self.assertEqual(launched["state"], "running")
        self.assertEqual(launched["launch"]["source"], edition["output_path"])
        self.assertEqual(self._request(path, "POST", {})[0], 409)
        self.assertEqual(self._request("/api/robots/astro_v2/editions/no-such-edition/native-viewer", "POST", {})[0], 404)
        self.assertEqual(self._request(path, "POST", {"mjcf": "/tmp/arbitrary.xml"})[0], 400)

        self.processes[-1].finish(0)
        self.assertEqual(wait_for_viewer_state(self.server.native_viewer, "idle")["state"], "idle")

    def test_remote_binding_refuses_native_viewer_launch(self):
        processes = []
        remote_server = create_server(ROOT, host="0.0.0.0", process_factory=lambda *_args, **_kwargs: processes.append(FakeNativeViewerProcess()) or processes[-1])
        remote_thread = threading.Thread(target=remote_server.serve_forever, daemon=True)
        remote_thread.start()
        try:
            _host, port = remote_server.server_address
            base_url = f"http://127.0.0.1:{port}"
            request = urllib.request.Request(
                f"{base_url}/api/robots/astro_v2/editions/authorized/native-viewer",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request)
            self.assertEqual(raised.exception.code, 403)
            self.assertEqual(processes, [])
        finally:
            remote_server.shutdown()
            remote_server.server_close()
            remote_thread.join(timeout=2)


class WorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(ROOT)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def _get_json(self, path: str) -> dict:
        with urllib.request.urlopen(f"{self.base_url}{path}") as response:
            return json.loads(response.read())

    def _post_json(self, path: str, payload: dict) -> tuple[int, dict]:
        return self._json_request(path, payload, "POST")

    def _json_request(self, path: str, payload: dict, method: str) -> tuple[int, dict]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_catalog_endpoint_preserves_robot_payload(self):
        catalog = self._get_json("/api/robots")

        self.assertEqual(
            [robot["id"] for robot in catalog["robots"]],
            ["astro_v1", "astro_v1_27dof", "astro_v2", "astro_with_racket", "unitree_g1"],
        )
        self.assertEqual(catalog["robots"][0]["formats"], {"urdf": True, "mjcf": True})
        self.assertTrue(catalog["robots"][2]["scene"]["links"])
        self.assertTrue(catalog["robots"][0]["scene"]["links"][0]["collisions"])
        self.assertIn("inertial", catalog["robots"][0]["scene"]["links"][0])
        self.assertEqual(catalog["robots"][0]["default_scene"], "flat_floor")
        self.assertEqual(catalog["robots"][2]["scene_description"]["id"], "flat_floor")
        self.assertEqual(catalog["robots"][2]["scene_description"]["robot_spawn"]["xyz"], [0.0, 0.0, 0.75])
        self.assertEqual(catalog["robots"][4]["dof"], 43)
        self.assertEqual(catalog["robots"][4]["formats"], {"urdf": True, "mjcf": True})
        self.assertEqual(catalog["robots"][4]["source_provenance"]["repository"], "https://github.com/unitreerobotics/unitree_ros")

    def test_unitree_g1_editions_report_official_metadata_and_exclude_retargeting_reference_from_candidates(self):
        editions = self._get_json("/api/robots/unitree_g1/editions")["editions"]
        default = next(edition for edition in editions if edition["default"])

        self.assertEqual(default["id"], "g1_29dof_with_hand_rev_1_0")
        self.assertEqual(default["kind"], "official")
        self.assertLess(default["modified_at"], 10**13)
        self.assertEqual(self._get_json("/api/robots/unitree_g1/mjcf-candidates")["candidates"], [])

    def test_flat_floor_scene_endpoint_and_workbench_adapter(self):
        scene = self._get_json("/api/scenes/flat_floor")["scene"]
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertEqual(scene["id"], "flat_floor")
        self.assertEqual(scene["terrain_instances"][0]["terrain"], "flat_floor")
        self.assertIn("appendMujocoTerrain", app)
        self.assertIn("scene-terrain", (WEB_ROOT / "mjcf-renderer.js").read_text(encoding="utf-8"))
        self.assertIn("workbench_scene_", app)
        self.assertIn("scene_description?.robot_spawn", app)

    def test_urdf_only_robot_reports_empty_mjcf_workspace(self):
        robot = self._get_json("/api/robots/astro_with_racket")["robot"]

        self.assertEqual(robot["formats"], {"urdf": True, "mjcf": False})
        self.assertFalse(robot["workbench_loadable"])
        self.assertIn("Import an MJCF edition", robot["conversion_guidance"])
        self.assertTrue(any(issue["code"] == "mjcf-unavailable" for issue in robot["issues"]))

    def test_mjcf_conversion_panel_and_candidate_routes_are_exposed(self):
        candidates = self._get_json("/api/robots/astro_with_racket/mjcf-candidates")
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertTrue(candidates["ok"])
        self.assertIsInstance(candidates["candidates"], list)
        self.assertIn('data-tab="mjcf"', page)
        self.assertIn('id="mjcf-generate"', page)
        self.assertIn('id="mjcf-candidate-list"', page)
        self.assertIn("create_managed_candidate", (ROOT / "src" / "menagerie_x" / "workbench" / "server.py").read_text(encoding="utf-8"))
        self.assertIn("previewMjcfCandidate", app)
        self.assertIn("authorizeMjcfCandidate", app)
        self.assertIn("no MJCF editions", app)
        self.assertIn("nextMjcfCandidateId", app)
        self.assertIn("Generate another review candidate without replacing this MJCF", app)
        self.assertIn("Official packaged MJCF", app)
        self.assertIn("Retargeting reference", app)
        self.assertNotIn("mjcfGenerate.disabled = authorized", app)
        self.assertIn("async function generateMjcfCandidate() {\n  if (!activeRobot) return;", app)

    def test_mjcf_editions_discover_actual_valid_files_without_candidate_assumptions(self):
        editions = self._get_json("/api/robots/astro_v2/editions")["editions"]

        self.assertEqual(editions[0]["id"], "astro_v2_primitive_collision")
        self.assertTrue(editions[0]["default"])
        self.assertEqual(editions[0]["role"], "default")
        self.assertTrue(editions[0]["source_id"])
        self.assertEqual(sum(record["default"] for record in editions), 1)
        self.assertIn("astro_v2_primitive_collision_halfway", {record["id"] for record in editions})
        self.assertNotIn("astro_v2-review_collision_edited_20260815T075510Z", {record["id"] for record in editions})
        self.assertNotIn("astro_v2-review_collision_edited_20260815T082637Z", {record["id"] for record in editions})
        self.assertTrue(all(len(record["revision"]) == 64 for record in editions))
        self.assertTrue(all("source_drift_warning" in record for record in editions))

    def test_workbench_starts_without_loading_a_default_edition(self):
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertNotIn("await selectRobot(catalog[0]?.id)", app)
        self.assertIn("function selectEdition(editionId", app)
        self.assertIn("/editions/${encodeURIComponent(edition.id)}", app)
        self.assertIn("Select a robot variant, then choose an MJCF edition.", page)
        self.assertIn('id="collision-overwrite"', page)

    def test_reload_description_control_reuses_the_edition_api_and_forces_a_same_id_reload(self):
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="reload-description"', page)
        self.assertIn("Reload menagerie", page)
        self.assertNotIn("Reload description", page)
        self.assertIn("async function reloadCurrentDescription()", app)
        self.assertIn('api("/api/robots")', app)
        self.assertIn("forceReload: true", app)
        self.assertIn('cache: options.forceReload ? "no-store" : "default"', app)
        self.assertIn("captureViewerView", app)
        self.assertIn("restoreViewerView", app)
        self.assertIn("previously selected MJCF edition is no longer available", app)
        self.assertIn("Discard the unsaved temporary collision draft and reload", app)
        self.assertIn("Never leave the prior", app)
        self.assertIn("disposeWasm();\n      clearRobot();\n      clearSceneObjects();", app)
        self.assertIn("throw error;", app)
        self.assertIn("const loaded = await loadMujocoModel", app)

    def test_workbench_uses_menagerie_workbench_branding(self):
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        server = (ROOT / "src" / "menagerie_x" / "workbench" / "server.py").read_text(encoding="utf-8")

        self.assertIn("<title>Menagerie Workbench</title>", page)
        self.assertIn("<h1>Menagerie Workbench</h1>", page)
        self.assertNotIn("Robot Menagerie", page)
        self.assertIn("Serving Menagerie Workbench", server)
        self.assertIn("Stopping Menagerie Workbench", server)

    def test_native_viewer_control_uses_saved_editions_and_warns_about_dirty_drafts(self):
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="open-native-viewer"', page)
        self.assertIn("async function openNativeViewer()", app)
        self.assertIn('api("/api/native-viewer")', app)
        self.assertIn('`${editionBase()}/native-viewer`', app)
        self.assertIn('"POST", {}', app)
        self.assertIn("MuJoCo viewer open", app)
        self.assertIn("Unsaved temporary collision edits will not appear", app)
        self.assertIn("Overwrite Current Edition or Export New Edition", app)
        self.assertIn("nativeViewerState === \"running\"", app)

    def test_diagnostics_module_is_served(self):
        with urllib.request.urlopen(f"{self.base_url}/diagnostics.js") as response:
            source = response.read().decode("utf-8")

        self.assertIn("createVisualDiagnostics", source)

    def test_contact_visualizer_module_is_served(self):
        with urllib.request.urlopen(f"{self.base_url}/contact-visualizer.js") as response:
            source = response.read().decode("utf-8")

        self.assertIn("createContactVisualizer", source)
        self.assertIn("mjv_updateScene", source)

        with urllib.request.urlopen(f"{self.base_url}/mujoco-visualization.js") as response:
            values = response.read().decode("utf-8")

        self.assertIn("mujocoEnumValue", values)
        self.assertIn("contactVisualizationValues", values)
        self.assertIn("mjVIS_CONTACTPOINT", values)
        self.assertIn("mjCAT_DECOR", values)

    def test_mjcf_renderer_uses_compiled_geom_poses_without_double_transforming_meshes(self):
        renderer = (WEB_ROOT / "mjcf-renderer.js").read_text(encoding="utf-8")

        self.assertIn("data.geom_xpos", renderer)
        self.assertIn("data.geom_xmat", renderer)
        self.assertNotIn("geometry.applyMatrix4", renderer)

    def test_joint_axis_diagnostics_sync_with_current_mujoco_kinematics(self):
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        diagnostics = (WEB_ROOT / "diagnostics.js").read_text(encoding="utf-8")

        self.assertIn("function syncMujoco(data)", diagnostics)
        self.assertIn("mujocoJointId", diagnostics)
        self.assertIn("data.xanchor", diagnostics)
        self.assertIn("data.xaxis", diagnostics)
        self.assertIn("diagnostics.syncMujoco(simulationData)", app)

    def test_asset_endpoint_rejects_path_traversal(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(f"{self.base_url}/api/robots/astro_v1/files/..%2Furdf%2Fastro_v1.urdf")

        self.assertEqual(raised.exception.code, 404)

    def test_workbench_exposes_simulation_and_interaction_controls(self):
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="physics-toggle"', page)
        self.assertIn('id="physics-reset"', page)
        self.assertIn('id="follow-toggle"', page)
        self.assertIn('id="random-pose"', page)
        self.assertIn("P</kbd> Physics", page)
        self.assertIn("R</kbd> Reset", page)
        self.assertIn("F</kbd> Follow", page)
        self.assertIn("mujoco.mj_step", app)
        self.assertIn("mujoco.mj_resetData", app)
        self.assertIn("syncVisualsFromMujoco", app)
        self.assertIn("applyDragForce", app)
        self.assertIn("xfrc_applied", app)
        self.assertIn("AbortController", app)
        self.assertIn("createMjcfRenderer", app)
        self.assertIn("/editions/${encodeURIComponent(edition.id)}", app)
        self.assertNotIn("workbench_root_collision", app)
        self.assertNotIn("robotGroup.position.addScaledVector", app)
        self.assertIn("new THREE.ArrowHelper", app)
        self.assertIn("updateDragForceIndicator", app)
        self.assertIn("setForceLinkHighlight", app)
        self.assertIn("forceMagnitude", app)
        self.assertIn("driveRandomPose", app)
        self.assertIn("limitedJointStates", app)
        self.assertIn("Random pose reached", app)

    def test_workbench_exposes_joint_inspector_and_limit_slider(self):
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn('data-tab="joints"', page)
        self.assertIn('id="joint-list"', page)
        self.assertNotIn('id="joint-detail"', page)
        self.assertNotIn('data-tab="validation"', page)
        self.assertIn("renderJointInspector", app)
        self.assertIn("setJointPosition", app)
        self.assertIn("data-joint-slider", app)
        self.assertIn("jnt_range", app)

    def test_workbench_exposes_visual_and_collision_toggles(self):
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="visual-mesh-toggle"', page)
        self.assertIn('id="collision-shape-toggle"', page)
        self.assertIn('id="contact-toggle"', page)
        self.assertIn("Collision shapes", page)
        self.assertNotIn("Collisions &amp; contacts", page)
        self.assertIn("toggleVisualMeshes", app)
        self.assertIn("toggleCollisionShapes", app)
        self.assertIn("toggleContacts", app)
        self.assertIn("contactsVisible", app)
        self.assertIn("collision-overlay", app)

    def test_collision_editor_endpoints_and_controls_are_exposed(self):
        document = self._get_json("/api/robots/astro_v1/collisions")
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertEqual(document["primitive_types"], ["box", "capsule", "cylinder", "sphere"])
        self.assertEqual(len(document["revision"]), 64)
        self.assertTrue(document["new_id_prefix"].startswith("new-"))
        self.assertTrue(any(item["editable"] and item["geometry"]["type"] == "capsule" for item in document["collisions"]))
        status, error = self._post_json("/api/robots/astro_with_racket/collision-drafts", {})
        self.assertEqual(status, 404)
        self.assertFalse(error["ok"])
        self.assertNotIn('data-tab="collisions"', page)
        self.assertIn('id="collision-editor-dock"', page)
        self.assertIn('id="collision-editor-toggle"', page)
        self.assertNotIn('id="collision-drawer"', page)
        self.assertIn('id="collision-export"', page)
        self.assertIn("enterCollisionMode", app)
        self.assertNotIn("nearestSnap", app)
        self.assertNotIn("beginCollisionDrag", app)
        self.assertNotIn("collisionGesture", app)
        self.assertIn("collisionId || hit?.object.userData.sourceCollisionId", app)
        self.assertIn("snapCollision", app)
        self.assertNotIn("Snap collision", page)
        self.assertIn("collision-drafts", app)
        self.assertIn("collisionMode", app)
        self.assertIn("compileDraftContacts", app)
        self.assertIn("collisionDraftSourcePath", app)
        self.assertIn("contactVisualizer", app)
        self.assertIn("syncDiagnosticPose", app)
        self.assertIn("collision-editor-open", app)
        self.assertNotIn("collisionDrawer", app)

    def test_collision_draft_session_endpoints_create_save_reset_export_and_discard(self):
        created_status, created = self._post_json("/api/robots/astro_v1/collision-drafts", {})

        self.assertEqual(created_status, 201)
        self.assertTrue(created["draft_id"])
        self.assertIsInstance(created["primitives"], list)
        self.assertIsInstance(created["retained_mesh_ids"], list)
        draft_path = f"/api/robots/astro_v1/collision-drafts/{created['draft_id']}"

        with urllib.request.urlopen(f"{self.base_url}{draft_path}/source") as response:
            self.assertIn("<mujoco", response.read().decode("utf-8"))

        saved_status, saved = self._json_request(
            draft_path,
            {
                "revision": created["revision"],
                "primitives": created["primitives"],
                "retained_mesh_ids": [],
            },
            "PUT",
        )
        self.assertEqual(saved_status, 200)
        self.assertEqual(saved["retained_mesh_ids"], [])

        reset_status, reset = self._post_json(f"{draft_path}/reset", {})
        self.assertEqual(reset_status, 200)
        self.assertEqual(reset["revision"], created["revision"])

        export_status, exported = self._post_json(f"{draft_path}/export", {"revision": reset["revision"]})
        self.assertEqual(export_status, 201)
        self.assertTrue(pathlib.Path(exported["output_path"]).is_file())
        pathlib.Path(exported["output_path"]).unlink()

        discarded_status, discarded = self._json_request(draft_path, {}, "DELETE")
        self.assertEqual(discarded_status, 200)
        self.assertTrue(discarded["ok"])

    def test_explicit_edition_draft_export_returns_a_selectable_edition(self):
        editions = self._get_json("/api/robots/astro_v2/editions")["editions"]
        edition = next(record for record in editions if not record["default"])
        base = f"/api/robots/astro_v2/editions/{edition['id']}/collision-drafts"
        created_status, created = self._post_json(base, {})
        self.assertEqual(created_status, 201)
        try:
            status, exported = self._post_json(f"{base}/{created['draft_id']}/export", {"revision": created["revision"]})
            self.assertEqual(status, 201)
            self.assertIn("edition_id", exported)
            self.assertTrue(pathlib.Path(exported["output_path"]).is_file())
            listed = self._get_json("/api/robots/astro_v2/editions")["editions"]
            self.assertIn(exported["edition_id"], {record["id"] for record in listed})
            pathlib.Path(exported["output_path"]).unlink()
        finally:
            self._json_request(f"{base}/{created['draft_id']}", {}, "DELETE")

    def test_workbench_exposes_visual_diagnostics_and_accessible_switches(self):
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        diagnostics = (WEB_ROOT / "diagnostics.js").read_text(encoding="utf-8")

        for control in ("physics-toggle", "follow-toggle", "visual-mesh-toggle", "collision-shape-toggle", "contact-toggle", "center-of-mass-toggle", "link-frame-toggle", "world-frame-toggle", "joint-axis-toggle"):
            self.assertIn(f'id="{control}"', page)
        self.assertEqual(page.count('role="switch"'), 9)
        self.assertIn('id="mesh-opacity"', page)
        self.assertIn('id="mesh-opacity-value"', page)
        self.assertIn("aria-checked", app)
        self.assertNotIn("aria-pressed", app)
        self.assertIn("applyVisualMeshOpacity", app)
        self.assertIn("createVisualDiagnostics", app)
        self.assertIn("!result.object.userData.visualDiagnostic", app)
        self.assertIn("world-frame", diagnostics)
        self.assertIn("center-of-mass", diagnostics)
        self.assertIn('new Set(["revolute", "continuous"])', diagnostics)
        self.assertIn("new THREE.Vector3(0, 0, 1)", diagnostics)
        self.assertIn("0xef4444", diagnostics)
        self.assertIn("0x22c55e", diagnostics)
        self.assertIn("0x3b82f6", diagnostics)
        self.assertIn("CylinderGeometry", diagnostics)
        self.assertIn("rotation-direction-arrow", diagnostics)
        self.assertIn("TubeGeometry", diagnostics)
        self.assertIn("0xf59e0b", diagnostics)
        self.assertIn("transparent: true, depthTest: false, depthWrite: false", diagnostics)

    def test_collision_editor_keeps_kinematic_pose_controls_and_native_contacts(self):
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        contacts = (WEB_ROOT / "contact-visualizer.js").read_text(encoding="utf-8")

        self.assertIn("C</kbd> Contacts", page)
        self.assertIn('id="robot-canvas" tabindex="0"', page)
        self.assertIn("canvas.focus({ preventScroll: true });", app)
        self.assertIn('event.key.toLowerCase() === "c"', app)
        self.assertIn("event.target.matches(\"input, textarea, select, button\")", app)
        self.assertIn("randomPoseButton.disabled = !simulationModel || !limitedJointStates().length", app)
        self.assertNotIn("slider.disabled = collisionMode", app)
        self.assertNotIn("|| collisionMode) return;\n  const joints = limitedJointStates", app)
        self.assertIn("currentNamedJointPose", app)
        self.assertIn("syncDiagnosticPose();", app)
        self.assertIn("syncPrimitiveToMjModel", app)
        self.assertIn("needsCompile && contactsVisible && collisionMode", app)
        self.assertIn("if (contactsVisible) void compileDraftContacts(collisionDraftId);", app)
        self.assertIn("Draft contact compilation superseded", app)
        self.assertIn("if (collisionMode && (!diagnosticModel || !diagnosticData))", app)
        self.assertIn("contactVisualizer.unbind();", app)
        self.assertIn("collisionDraftDirty = false;\n    setCollisionStatus(`Exported", app)
        self.assertNotIn("collisionDraftDirty = false;\n    if (collisionMode", app)
        self.assertIn("mjv_updateScene", contacts)
        self.assertIn("contactVisualizationValues", contacts)
        self.assertIn("mujocoEnumValue", contacts)
        self.assertNotIn("contactMarker", contacts)
        self.assertNotIn("EdgesGeometry", contacts)
        self.assertNotIn("LineSegments", contacts)
        self.assertNotIn("TorusGeometry", contacts)
        self.assertNotIn("Number(mujoco.mjt", contacts)
        self.assertNotIn("data.contact", contacts)
        self.assertNotIn("geom1", contacts)
        self.assertNotIn("lastCount", contacts)
        self.assertNotIn("get count", contacts)
        self.assertIn("THREE.ACESFilmicToneMapping", app)
        self.assertIn("const fillLight = new THREE.DirectionalLight", app)
        self.assertIn("new THREE.HemisphereLight(0xdce7f2, 0x18251d, 1.05)", app)

    def test_collision_shapes_use_solid_translucent_mujoco_style(self):
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        renderer = (WEB_ROOT / "mjcf-renderer.js").read_text(encoding="utf-8")

        self.assertIn("createCollisionMaterial", app)
        self.assertIn("new THREE.Mesh(geometry, createCollisionMaterial(THREE))", app)
        self.assertNotIn("new THREE.EdgesGeometry(geometry)", app)
        self.assertNotIn("new THREE.LineSegments(", app)
        self.assertIn("contact ? createCollisionMaterial(THREE) :", renderer)

    def test_edition_list_cannot_widen_or_horizontally_scroll_the_menagerie(self):
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn(".menagerie { min-width: 0; overflow-x: hidden; }", styles)
        self.assertIn(".robot-list, .element-list, .joint-list, .robot-entry, .edition-list { min-width: 0; }", styles)
        self.assertIn(".robot-name > span:first-child, .robot-meta { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }", styles)


if __name__ == "__main__":
    unittest.main()
