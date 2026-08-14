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
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_catalog_endpoint_preserves_robot_payload(self):
        catalog = self._get_json("/api/robots")

        self.assertEqual([robot["id"] for robot in catalog["robots"]], ["astro_v1", "astro_v1_27dof", "astro_with_racket", "astro_v2"])
        self.assertEqual(catalog["robots"][0]["formats"], {"urdf": True, "mjcf": True})
        self.assertTrue(catalog["robots"][-1]["scene"]["links"])
        self.assertTrue(catalog["robots"][0]["scene"]["links"][0]["collisions"])

    def test_urdf_only_robot_reports_missing_authored_mjcf(self):
        robot = self._get_json("/api/robots/astro_v2")["robot"]

        self.assertEqual(robot["formats"], {"urdf": True, "mjcf": False})
        self.assertTrue(any(issue["code"] == "mjcf-unavailable" for issue in robot["issues"]))

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
        self.assertIn("P</kbd> Physics", page)
        self.assertIn("R</kbd> Reset", page)
        self.assertIn("F</kbd> Follow", page)
        self.assertIn("mujoco.mj_step", app)
        self.assertIn("mujoco.mj_resetData", app)
        self.assertIn("syncVisualsFromMujoco", app)
        self.assertIn("applyDragForce", app)
        self.assertIn("xfrc_applied", app)
        self.assertIn("workbench_floating_base", app)
        self.assertIn("AbortController", app)
        self.assertIn("syncVisualJointTransforms", app)
        self.assertIn("workbench_root_collision", app)
        self.assertNotIn("robotGroup.position.addScaledVector", app)
        self.assertIn("new THREE.ArrowHelper", app)
        self.assertIn("updateDragForceIndicator", app)
        self.assertIn("setForceLinkHighlight", app)
        self.assertIn("forceMagnitude", app)

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
        self.assertIn("toggleVisualMeshes", app)
        self.assertIn("toggleCollisionShapes", app)
        self.assertIn("collision-overlay", app)

    def test_collision_editor_endpoints_and_controls_are_exposed(self):
        document = self._get_json("/api/robots/astro_v2/collisions")
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertEqual(document["primitive_types"], ["box", "cylinder", "sphere"])
        self.assertEqual(len(document["revision"]), 64)
        self.assertTrue(document["new_id_prefix"].startswith("new-"))
        self.assertTrue(any(not item["editable"] and item["geometry"]["type"] == "mesh" for item in document["collisions"]))
        status, error = self._post_json(
            "/api/robots/astro_v2/collision-exports",
            {"revision": "stale", "collisions": []},
        )
        self.assertEqual(status, 409)
        self.assertFalse(error["ok"])
        self.assertIn('data-tab="collisions"', page)
        self.assertIn('id="collision-export"', page)
        self.assertIn("enterCollisionMode", app)
        self.assertNotIn("nearestSnap", app)
        self.assertNotIn("collisionGesture", app)
        self.assertNotIn("Snap collision", page)
        self.assertIn("collision-exports", app)
        self.assertIn("collisionMode", app)


if __name__ == "__main__":
    unittest.main()
