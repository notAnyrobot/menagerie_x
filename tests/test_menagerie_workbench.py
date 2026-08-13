import pathlib
import unittest

from astro_description.menagerie_workbench.server import build_robot_catalog, validate_robot
from astro_description.assets import variants


ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "src" / "astro_description" / "menagerie_workbench" / "web"


class MenagerieWorkbenchTests(unittest.TestCase):
    def test_catalog_discovers_manifest_variants_with_validation_results(self):
        catalog = build_robot_catalog(ROOT)

        self.assertEqual([robot["id"] for robot in catalog["robots"]], ["astro_v1", "astro_v1_27dof", "astro_with_racket", "astro_v2"])
        self.assertEqual(catalog["robots"][0]["formats"], {"urdf": True, "mjcf": True})
        self.assertTrue(catalog["robots"][-1]["scene"]["links"])

    def test_urdf_only_robot_explains_its_wasm_compile_path(self):
        robot = validate_robot(variants(ROOT)["astro_v2"])

        self.assertEqual(robot["formats"], {"urdf": True, "mjcf": False})
        self.assertTrue(any(issue["code"] == "mjcf-unavailable" for issue in robot["issues"]))

    def test_validation_issues_retain_robot_element_identity(self):
        robot = validate_robot(variants(ROOT)["astro_v1"])

        link_issues = [issue for issue in robot["issues"] if issue["element_type"] == "link"]
        self.assertTrue(link_issues)
        self.assertTrue(all(issue["element"] for issue in link_issues))

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

    def test_workbench_exposes_joint_inspector_and_limit_slider(self):
        page = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn('data-tab="joints"', page)
        self.assertIn('id="joint-list"', page)
        self.assertIn('id="joint-detail"', page)
        self.assertNotIn('data-tab="validation"', page)
        self.assertIn("renderJointInspector", app)
        self.assertIn("setJointPosition", app)
        self.assertIn("jnt_range", app)


if __name__ == "__main__":
    unittest.main()
