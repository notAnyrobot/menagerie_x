import dataclasses
import pathlib
import tempfile
import unittest

from menagerie_x.assets import Variant, get_variant, inspect_variant, variants


ROOT = pathlib.Path(__file__).resolve().parents[1]


class AssetInspectionTests(unittest.TestCase):
    def test_inspection_exposes_neutral_robot_description(self):
        inspection = inspect_variant(variants(ROOT)["astro_p1"])

        self.assertIsNotNone(inspection.description)
        assert inspection.description is not None
        self.assertTrue(inspection.description.links)
        self.assertTrue(inspection.description.links[0]["collisions"])

    def test_link_payload_projects_inertial_mass_and_origin(self):
        inspection = inspect_variant(variants(ROOT)["astro_p1"])

        assert inspection.description is not None
        pelvis = next(link for link in inspection.description.links if link["name"] == "pelvis")
        self.assertEqual(pelvis["inertial"], {"mass": 4.6593, "origin": {"xyz": [-0.0002233, 0.00012202, -0.076908], "rpy": [0.0, 0.0, 0.0]}})

    def test_link_payload_uses_null_when_inertial_is_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            urdf = root / "robot.urdf"
            urdf.write_text('<robot name="test"><link name="base"/></robot>', encoding="utf-8")
            variant = Variant("test", 0, urdf, None, root / "meshes", "test", "")

            inspection = inspect_variant(variant)

        assert inspection.description is not None
        self.assertIsNone(inspection.description.links[0]["inertial"])

    def test_urdf_only_variant_reports_missing_authored_mjcf(self):
        inspection = inspect_variant(get_variant("astro_with_racket", ROOT))

        self.assertTrue(any(issue.code == "mjcf-unavailable" for issue in inspection.issues))

    def test_validation_issues_retain_robot_element_identity(self):
        inspection = inspect_variant(variants(ROOT)["astro_p1"])

        link_issues = [issue for issue in inspection.issues if issue.element_type == "link"]
        self.assertTrue(link_issues)
        self.assertTrue(all(issue.element for issue in link_issues))

    def test_missing_urdf_returns_structured_issue(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = pathlib.Path(directory) / "missing.urdf"
            variant = dataclasses.replace(variants(ROOT)["astro_p2"], urdf=missing)

            inspection = inspect_variant(variant)

        self.assertIsNone(inspection.description)
        self.assertTrue(any(issue.code == "urdf-missing" and issue.path == str(missing) for issue in inspection.issues))

    def test_mesh_reference_cannot_escape_variant_mesh_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            meshes = root / "meshes"
            meshes.mkdir()
            urdf = root / "robot.urdf"
            urdf.write_text(
                """<robot name="test">
  <link name="base">
    <inertial><mass value="1"/></inertial>
    <visual><geometry><mesh filename="../outside.stl"/></geometry></visual>
  </link>
</robot>
""",
                encoding="utf-8",
            )
            variant = Variant("test", 0, urdf, None, meshes, "test", "")

            inspection = inspect_variant(variant)

        self.assertTrue(any(issue.code == "mesh-missing" for issue in inspection.issues))


if __name__ == "__main__":
    unittest.main()
