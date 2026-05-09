import pathlib
import unittest

from astro_description.assets import get_variant, validate_assets, variants
from astro_description.mujoco_tools import check_mujoco


ROOT = pathlib.Path(__file__).resolve().parents[1]
ROBOT_ROOT = ROOT / "src" / "astro_description" / "robots" / "astro"


class AssetManifestTests(unittest.TestCase):
    def test_manifest_lists_expected_variants(self):
        parsed = variants(ROOT)

        self.assertEqual(sorted(parsed), ["astro_v1", "astro_v1_27dof", "astro_with_racket"])
        self.assertEqual(get_variant(root=ROOT).name, "astro_v1")
        self.assertEqual(parsed["astro_v1"].dof, 30)
        self.assertTrue(parsed["astro_v1"].urdf.exists())
        self.assertTrue(parsed["astro_v1"].mjcf.exists())

    def test_validate_assets_accepts_current_checkout(self):
        self.assertEqual(validate_assets(ROOT), [])


class MujocoPackageTests(unittest.TestCase):
    def test_check_mujoco_loads_default_variant(self):
        result = check_mujoco(root=ROOT)

        self.assertEqual(result["variant"], "astro_v1")
        self.assertGreater(result["nbody"], 1)
        self.assertGreater(result["ngeom"], 1)

    def test_packaged_robot_root_is_default_asset_root(self):
        parsed = variants()

        self.assertEqual(parsed["astro_v1"].urdf, ROBOT_ROOT / "urdf" / "astro_v1.urdf")


if __name__ == "__main__":
    unittest.main()
