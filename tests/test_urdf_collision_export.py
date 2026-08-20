from __future__ import annotations

import hashlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from menagerie_x.assets import (
    UrdfCollisionExportError,
    Variant,
    export_urdf_with_mjcf_collisions,
    get_variant,
)


ROOT = Path(__file__).resolve().parents[1]


class UrdfCollisionExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.asset_root = Path(self.temporary.name)
        self.urdf = self.asset_root / "robot.urdf"
        self.mjcf = self.asset_root / "robot.xml"
        self.variant = Variant("robot", "robot", 0, self.urdf, self.mjcf, self.asset_root, "ready", "")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write(self, urdf: str, mjcf: str) -> None:
        self.urdf.write_text(urdf, encoding="utf-8")
        self.mjcf.write_text(mjcf, encoding="utf-8")

    def test_capsule_expands_to_three_standard_collisions(self) -> None:
        self._write(
            '<robot name="robot"><link name="pelvis"/></robot>',
            '<mujoco><worldbody><body name="pelvis"><geom name="pelvis_capsule_collision_1" type="capsule" size="0.1 0.2" contype="1" conaffinity="1"/></body></worldbody></mujoco>',
        )

        result = export_urdf_with_mjcf_collisions(self.variant, self.mjcf, edition_id="reviewed", asset_root=self.asset_root)

        root = ET.fromstring(result.content)
        collisions = root.findall("./link[@name='pelvis']/collision")
        self.assertEqual(len(collisions), 3)
        self.assertIsNotNone(collisions[0].find("./geometry/cylinder"))
        self.assertEqual(collisions[0].find("./geometry/cylinder").attrib, {"radius": "0.1", "length": "0.4"})
        self.assertEqual([node.find("origin").attrib["xyz"] for node in collisions[1:]], ["0 0 -0.2", "0 0 0.2"])
        self.assertFalse(root.findall(".//capsule"))
        self.assertEqual(result.filename, "robot-reviewed-collisions.urdf")

    def test_primitives_use_standard_urdf_dimensions_after_compilation(self) -> None:
        self._write(
            '<robot name="robot"><link name="pelvis"/></robot>',
            '''<mujoco><worldbody><body name="pelvis">
              <geom name="pelvis_box_collision_1" type="box" size="0.1 0.2 0.3" contype="1" conaffinity="1"/>
              <geom name="pelvis_sphere_collision_1" type="sphere" size="0.4" contype="1" conaffinity="1"/>
              <geom name="pelvis_cylinder_collision_1" type="cylinder" size="0.5 0.6" quat="0.707106781 0 0.707106781 0" contype="1" conaffinity="1"/>
              <geom name="pelvis_capsule_collision_2" type="capsule" fromto="0 0 0 0 0 0.4" size="0.05" contype="1" conaffinity="1"/>
            </body></worldbody></mujoco>''',
        )

        root = ET.fromstring(export_urdf_with_mjcf_collisions(self.variant, self.mjcf, edition_id="reviewed", asset_root=self.asset_root).content)
        self.assertEqual(root.find(".//box").attrib, {"size": "0.2 0.4 0.6"})
        self.assertEqual(root.find(".//sphere").attrib, {"radius": "0.4"})
        self.assertEqual(root.find(".//cylinder").attrib, {"radius": "0.5", "length": "1.2"})
        self.assertEqual(len(root.findall(".//collision")), 6)

    def test_preserves_non_collision_xml_and_source_bytes(self) -> None:
        self._write(
            '''<robot name="robot"><!-- keep me --><material name="green"/><link name="pelvis"><visual><geometry><mesh filename="mesh.stl"/></geometry></visual><collision><geometry><box size="1 1 1"/></geometry></collision></link><mujoco><compiler angle="radian"/></mujoco></robot>''',
            '<mujoco><worldbody><body name="pelvis"><geom name="pelvis_sphere_collision_1" type="sphere" size="0.1" contype="1" conaffinity="1"/></body></worldbody></mujoco>',
        )
        before = (hashlib.sha256(self.urdf.read_bytes()).hexdigest(), hashlib.sha256(self.mjcf.read_bytes()).hexdigest())

        result = export_urdf_with_mjcf_collisions(self.variant, self.mjcf, edition_id="reviewed", asset_root=self.asset_root)

        self.assertIn(b"<!-- keep me -->", result.content)
        root = ET.fromstring(result.content)
        self.assertEqual(root.find("material").attrib["name"], "green")
        self.assertEqual(root.find(".//mesh").attrib["filename"], "mesh.stl")
        self.assertIsNotNone(root.find("mujoco/compiler"))
        self.assertEqual(before, (hashlib.sha256(self.urdf.read_bytes()).hexdigest(), hashlib.sha256(self.mjcf.read_bytes()).hexdigest()))

    def test_include_is_a_complete_export_blocker(self) -> None:
        self._write('<robot name="robot"><link name="pelvis"/></robot>', '<mujoco><include file="parts.xml"/></mujoco>')
        with self.assertRaises(UrdfCollisionExportError) as raised:
            export_urdf_with_mjcf_collisions(self.variant, self.mjcf, edition_id="reviewed", asset_root=self.asset_root)
        self.assertEqual(raised.exception.report.issues[0].code, "mjcf-include")

    def test_astro_v2_reference_counts(self) -> None:
        variant = get_variant("astro_v2", ROOT)
        result = export_urdf_with_mjcf_collisions(
            variant,
            variant.mjcf,
            edition_id="astro_v2_primitive_collision",
            asset_root=ROOT / "src" / "menagerie_x" / "assets",
        )
        root = ET.fromstring(result.content)
        self.assertEqual(len(root.findall(".//collision")), 125)
        self.assertEqual(result.report.source_collision_count, 47)
        self.assertEqual(result.report.geometry_counts, {"box": 0, "sphere": 79, "cylinder": 46})
        self.assertEqual(result.report.expanded_capsules, 39)
        self.assertFalse(root.findall(".//capsule"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
