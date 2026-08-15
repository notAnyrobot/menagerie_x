import pathlib
import unittest

from menagerie_x.assets import get_variant, load_scene, resolve_scene, validate_assets, variants
from menagerie_x.commands.mujoco import check_mujoco


ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "src" / "menagerie_x" / "assets"
ROBOT_ROOT = ASSET_ROOT / "astro_v1"


class AssetManifestTests(unittest.TestCase):
    def test_manifest_lists_expected_variants(self):
        parsed = variants(ROOT)

        self.assertEqual(sorted(parsed), ["astro_v1", "astro_v1_27dof", "astro_v2", "astro_with_racket"])
        self.assertEqual(get_variant(root=ROOT).name, "astro_v1")
        self.assertEqual(parsed["astro_v1"].dof, 30)
        self.assertTrue(parsed["astro_v1"].urdf.exists())
        self.assertTrue(parsed["astro_v1"].mjcf.exists())
        self.assertEqual(parsed["astro_v1"].robot_version, "astro_v1")
        self.assertEqual(parsed["astro_v2"].robot_version, "astro_v2")
        self.assertEqual(parsed["astro_v2"].dof, 30)
        self.assertTrue(parsed["astro_v2"].urdf.exists())
        self.assertIsNone(parsed["astro_v2"].mjcf)
        self.assertTrue((ASSET_ROOT / "astro_v2" / "urdf").is_dir())
        self.assertTrue((ASSET_ROOT / "astro_v2" / "meshes").is_dir())

    def test_validate_assets_accepts_current_checkout(self):
        self.assertEqual(validate_assets(ROOT), [])

    def test_flat_floor_scene_resolves_for_current_robot_versions(self):
        scene = load_scene("flat_floor", ROOT)
        self.assertEqual(scene.gravity, [0.0, 0.0, -9.81])
        self.assertEqual(scene.terrain_instances[0]["terrain"], "flat_floor")
        for variant_name in ("astro_v1", "astro_v2"):
            resolved = resolve_scene(variants(ROOT)[variant_name], ROOT)
            self.assertEqual(resolved.identifier, "flat_floor")
            self.assertEqual(resolved.robot_spawn, {"xyz": [0.0, 0.0, 0.75], "rpy": [0.0, 0.0, 0.0]})
            floor = resolved.terrain_instances[0]
            self.assertEqual(floor["geometry"], {"type": "plane", "size": [16.0, 16.0], "thickness": 0.1})
            self.assertEqual(floor["pose"]["xyz"], [0.0, 0.0, 0.0])

    def test_authored_urdfs_remain_robot_only(self):
        for variant_name in ("astro_v1", "astro_v2"):
            source = variants(ROOT)[variant_name].urdf.read_text(encoding="utf-8")
            self.assertNotIn("workbench_floor", source)
            self.assertNotIn("flat_floor", source)


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
