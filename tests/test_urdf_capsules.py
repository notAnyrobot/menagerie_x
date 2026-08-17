import pathlib
import unittest
import xml.etree.ElementTree as ET

from menagerie_x.commands.urdf_capsules import (
    add_capsule_extension_collisions,
    convert_mjcf_capsules_to_urdf,
    extract_capsules_from_mjcf,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
ROBOT_ROOT = ROOT / "src" / "menagerie_x" / "assets" / "astro_v1"


class UrdfCapsuleTests(unittest.TestCase):
    def test_extracts_capsule_collisions_from_mjcf_body_tree(self):
        capsules = extract_capsules_from_mjcf(ROBOT_ROOT / "mjcf" / "astro_v1.xml")

        names = {capsule.name for capsule in capsules}
        self.assertIn("left_knee_collision", names)
        self.assertIn("right_foot12_collision", names)

    def test_adds_extension_capsules_to_matching_urdf_links(self):
        urdf_text = '<robot name="astro"><link name="left_knee_link"/></robot>'
        capsules = [extract_capsules_from_mjcf(ROBOT_ROOT / "mjcf" / "astro_v1.xml")[1]]

        updated = add_capsule_extension_collisions(urdf_text, capsules)
        root = ET.fromstring(updated)
        capsule = root.find("./link/collision/geometry/capsule")

        self.assertIsNotNone(capsule)
        self.assertEqual(capsule.attrib["format"], "astro-extension-v1")
        self.assertIn(" ", capsule.attrib["fromto"])

    def test_converts_current_astro_urdf_with_capsule_extension_tags(self):
        updated = convert_mjcf_capsules_to_urdf(ROBOT_ROOT / "urdf" / "astro_v1.urdf", ROBOT_ROOT / "mjcf" / "astro_v1.xml")

        self.assertIn('<capsule radius="0.055"', updated)
        self.assertIn('format="astro-extension-v1"', updated)


if __name__ == "__main__":
    unittest.main()
