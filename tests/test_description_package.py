import pathlib
import unittest

from astro_description.assets import get_variant, validate_assets, variants
from astro_description.commands.mujoco import check_mujoco


ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "src" / "astro_description" / "assets"
ROBOT_ROOT = ASSET_ROOT / "astro_v1"


class AssetManifestTests(unittest.TestCase):
    def test_manifest_lists_expected_variants(self):
        parsed = variants(ROOT)

        self.assertEqual(sorted(parsed), ["astro_v1", "astro_v1_27dof", "astro_with_racket"])
        self.assertEqual(get_variant(root=ROOT).name, "astro_v1")
        self.assertEqual(parsed["astro_v1"].dof, 30)
        self.assertTrue(parsed["astro_v1"].urdf.exists())
        self.assertTrue(parsed["astro_v1"].mjcf.exists())
        self.assertEqual(parsed["astro_v1"].robot_version, "astro_v1")
        self.assertTrue((ASSET_ROOT / "astro_v2" / "urdf").is_dir())
        self.assertTrue((ASSET_ROOT / "astro_v2" / "meshes").is_dir())

    def test_validate_assets_accepts_current_checkout(self):
        self.assertEqual(validate_assets(ROOT), [])


class MujocoPackageTests(unittest.TestCase):
    def test_check_mujoco_loads_default_variant(self):
        result = check_mujoco(root=ROOT)

        self.assertEqual(result["variant"], "astro_v1")
        self.assertGreater(result["nbody"], 1)
        self.assertGreater(result["ngeom"], 1)

    def test_packaged_assets_resolve_v1_variant_paths(self):
        parsed = variants()

        self.assertEqual(parsed["astro_v1"].urdf, ROBOT_ROOT / "urdf" / "astro_v1.urdf")


if __name__ == "__main__":
    unittest.main()
