import json
import pathlib
import threading
import unittest
import urllib.error
import urllib.request

from menagerie_x.workbench import create_server


ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "src" / "menagerie_x" / "workbench" / "web"


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

        self.assertEqual([robot["id"] for robot in catalog["robots"]], ["astro_v1", "astro_v1_27dof", "astro_v2", "astro_with_racket"])
        self.assertEqual(catalog["robots"][0]["formats"], {"urdf": True, "mjcf": True})
        self.assertTrue(catalog["robots"][2]["scene"]["links"])
        self.assertTrue(catalog["robots"][0]["scene"]["links"][0]["collisions"])
        self.assertIn("inertial", catalog["robots"][0]["scene"]["links"][0])
        self.assertEqual(catalog["robots"][0]["default_scene"], "flat_floor")
        self.assertEqual(catalog["robots"][2]["scene_description"]["id"], "flat_floor")
        self.assertEqual(catalog["robots"][2]["scene_description"]["robot_spawn"]["xyz"], [0.0, 0.0, 0.75])

    def test_flat_floor_scene_endpoint_and_workbench_adapter(self):
        scene = self._get_json("/api/scenes/flat_floor")["scene"]
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertEqual(scene["id"], "flat_floor")
        self.assertEqual(scene["terrain_instances"][0]["terrain"], "flat_floor")
        self.assertIn("appendMujocoTerrain", app)
        self.assertIn("scene-terrain", (WEB_ROOT / "mjcf-renderer.js").read_text(encoding="utf-8"))
        self.assertIn("workbench_scene_", app)
        self.assertIn("scene_description?.robot_spawn", app)

    def test_urdf_only_robot_reports_missing_authored_mjcf(self):
        robot = self._get_json("/api/robots/astro_with_racket")["robot"]

        self.assertEqual(robot["formats"], {"urdf": True, "mjcf": False})
        self.assertFalse(robot["workbench_loadable"])
        self.assertIn("menagerie_x mjcf convert --source astro_with_racket", robot["conversion_guidance"])
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
        self.assertIn("MJCF required", app)
        self.assertIn("nextMjcfCandidateId", app)
        self.assertIn("Generate another review candidate without replacing this MJCF", app)
        self.assertNotIn("mjcfGenerate.disabled = authorized", app)
        self.assertIn("async function generateMjcfCandidate() {\n  if (!activeRobot) return;", app)

    def test_diagnostics_module_is_served(self):
        with urllib.request.urlopen(f"{self.base_url}/diagnostics.js") as response:
            source = response.read().decode("utf-8")

        self.assertIn("createVisualDiagnostics", source)

    def test_contact_visualizer_module_is_served(self):
        with urllib.request.urlopen(f"{self.base_url}/contact-visualizer.js") as response:
            source = response.read().decode("utf-8")

        self.assertIn("createContactVisualizer", source)
        self.assertIn("mjv_updateScene", source)
        self.assertIn("mjVIS_CONTACTPOINT", source)

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
        self.assertIn("/source?format=mjcf", app)
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
        self.assertIn("Collisions &amp; contacts", page)
        self.assertIn("toggleVisualMeshes", app)
        self.assertIn("toggleCollisionShapes", app)
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
        self.assertIn('id="collision-drawer"', page)
        self.assertIn('id="collision-drawer-toggle"', page)
        self.assertIn('id="collision-drawer-close"', page)
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

    def test_workbench_exposes_visual_diagnostics_and_accessible_switches(self):
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        diagnostics = (WEB_ROOT / "diagnostics.js").read_text(encoding="utf-8")

        for control in ("physics-toggle", "follow-toggle", "visual-mesh-toggle", "collision-shape-toggle", "center-of-mass-toggle", "link-frame-toggle", "world-frame-toggle", "joint-axis-toggle"):
            self.assertIn(f'id="{control}"', page)
        self.assertEqual(page.count('role="switch"'), 8)
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


if __name__ == "__main__":
    unittest.main()
