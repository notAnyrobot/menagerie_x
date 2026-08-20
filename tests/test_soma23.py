"""Regression checks for the packaged ProtoMotions SOMA-23 description."""

from __future__ import annotations

import hashlib
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from menagerie_x.assets import get_variant, inspect_variant, load_manifest, resolve_scene, validate_assets
from menagerie_x.assets.editions import list_mjcf_editions
from menagerie_x.commands.mujoco import check_mujoco


ASSETS = Path(__file__).resolve().parents[1] / "src" / "menagerie_x" / "assets"
SOMA23 = ASSETS / "soma23"
MJCF = SOMA23 / "mjcf" / "soma23_free_base.xml"
SHA256 = "0b3b4cc6967d0ebe24dd54b87a8a4b3fe1c05d44a53a8f435e2b854f3189a1b3"
PROTOMOTIONS_REVISION = "a6df301d312dc58ac40a4d994f4f1064728d854c"


class Soma23CatalogTests(unittest.TestCase):
    def test_manifest_records_the_direct_protomotions_mjcf_provenance(self) -> None:
        manifest = load_manifest(ASSETS)
        entry = manifest["variants"]["soma23"]
        edition = entry["editions"]["free_base"]
        provenance = edition["source_provenance"]

        self.assertEqual(entry["status"], "imported")
        self.assertEqual(edition["urdf"], None)
        self.assertEqual(provenance["repository"], "https://github.com/NVlabs/ProtoMotions")
        self.assertEqual(provenance["revision"], PROTOMOTIONS_REVISION)
        self.assertEqual(provenance["source_path"], "protomotions/data/assets/mjcf/soma23_humanoid.xml")
        self.assertEqual(provenance["license"], "Apache-2.0")
        self.assertEqual(provenance["license_file"], "LICENSE.ProtoMotions")
        self.assertEqual(provenance["sha256"], SHA256)
        self.assertEqual(hashlib.sha256(MJCF.read_bytes()).hexdigest(), SHA256)
        self.assertTrue((SOMA23 / provenance["license_file"]).is_file())

    def test_mjcf_only_free_base_model_is_registered_for_the_workbench(self) -> None:
        variant = get_variant("soma23", ASSETS)
        inspection = inspect_variant(variant)
        root = ET.parse(MJCF).getroot()
        editions = list_mjcf_editions(variant, ASSETS)

        self.assertEqual(variant.dof, 66)
        self.assertIsNone(variant.urdf)
        self.assertTrue(variant.workbench_loadable)
        self.assertEqual(len(root.findall(".//freejoint")), 1)
        self.assertEqual(len(root.findall(".//actuator/motor")), 66)
        self.assertEqual(root.findall(".//asset/mesh"), [])
        self.assertTrue(any(issue.code == "urdf-unavailable" for issue in inspection.issues))
        self.assertEqual([(edition["id"], edition["kind"], edition["default"]) for edition in editions], [("soma23_free_base", "official", True)])

    def test_mujoco_loads_the_exact_actuated_dof_and_spawn_clears_flat_floor(self) -> None:
        variant = get_variant("soma23", ASSETS)
        result = check_mujoco("soma23", ASSETS)

        self.assertEqual(resolve_scene(variant, ASSETS).robot_spawn["xyz"], [0.0, 0.0, 1.0])
        self.assertEqual(
            {key: result[key] for key in ("nq", "nv", "nu", "nbody", "ngeom", "nsensor")},
            {"nq": 73, "nv": 72, "nu": 66, "nbody": 24, "ngeom": 23, "nsensor": 0},
        )
        self.assertEqual(validate_assets(ASSETS), [])


if __name__ == "__main__":
    unittest.main()
