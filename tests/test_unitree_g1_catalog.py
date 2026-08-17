"""Focused regression checks for the packaged Unitree G1 descriptions."""

from __future__ import annotations

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from menagerie_x.assets import get_variant, validate_assets


ASSETS = Path(__file__).resolve().parents[1] / "src" / "menagerie_x" / "assets"


class UnitreeG1CatalogTests(unittest.TestCase):
    def test_official_g1_variant_is_catalogued_with_its_default_descriptions(self) -> None:
        variant = get_variant("unitree_g1", ASSETS)

        self.assertEqual(variant.dof, 43)
        self.assertEqual(variant.urdf.name, "g1_29dof_with_hand_rev_1_0.urdf")
        self.assertEqual(variant.mjcf.name, "g1_29dof_with_hand_rev_1_0.xml")
        self.assertEqual(validate_assets(ASSETS), [])

    def test_packaged_urdfs_and_retargeting_mjcf_resolve_their_meshes(self) -> None:
        variant_dir = ASSETS / "unitree_g1"
        for urdf in (
            variant_dir / "urdf" / "g1_29dof_with_hand_rev_1_0.urdf",
            variant_dir / "urdf" / "for_retargeting" / "g1.urdf",
        ):
            root = ET.parse(urdf).getroot()
            filenames = [mesh.get("filename") for mesh in root.findall(".//mesh") if mesh.get("filename")]
            self.assertTrue(filenames)
            self.assertTrue(all((urdf.parent / filename).resolve().is_file() for filename in filenames))

        retargeting = ET.parse(variant_dir / "mjcf" / "protomotions_g1_retargeting_box_feet.xml").getroot()
        self.assertIsNotNone(retargeting.find(".//site[@name='imu']"))
