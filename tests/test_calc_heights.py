import pathlib
import unittest

from astro_description.tools import calc_heights

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROBOT_ROOT = ROOT / "src" / "astro_description" / "robots" / "astro"


class KeyframeParserTests(unittest.TestCase):
    def test_list_astro_keyframes_from_constants_source(self):
        keyframes = calc_heights.load_astro_keyframes(ROBOT_ROOT / "constants.py")

        self.assertEqual(sorted(keyframes), ["home", "knees_bent", "t_pose", "zero"])
        self.assertEqual(keyframes["knees_bent"].pos, (0.0, 0.0, 0.745))
        self.assertEqual(keyframes["knees_bent"].joint_pos[".*_knee_joint"], 0.669)
        self.assertEqual(keyframes["home"].joint_pos[".*_elbow_joint"], 1.5)

    def test_unknown_keyframe_raises_clear_error(self):
        config = calc_heights.create_astro_embodiment_config(ROBOT_ROOT)

        with self.assertRaisesRegex(calc_heights.HeightToolError, "unknown keyframe"):
            calc_heights.get_keyframe(config, "missing")


class EmbodimentConfigTests(unittest.TestCase):
    def test_astro_config_declares_expected_targets(self):
        config = calc_heights.create_astro_embodiment_config(ROBOT_ROOT)

        self.assertEqual(config.name, "astro")
        self.assertEqual(config.mjcf_path, ROBOT_ROOT / "mjcf" / "astro_v1.xml")
        self.assertEqual(config.floating_base_joint, "floating_base_joint")
        self.assertIn("pelvis", config.body_height_targets)
        self.assertIn("torso_link", config.body_height_targets)
        self.assertIn("left_shoulder_pitch_link", config.body_height_targets)
        self.assertIn("right_shoulder_pitch_link", config.body_height_targets)
        self.assertIn("left_foot1_collision", config.foot_collision_geom_names)
        self.assertIn("right_foot12_collision", config.foot_collision_geom_names)

    def test_bmp_data_url_has_expected_prefix(self):
        rgb = bytes([
            255, 0, 0,
            0, 255, 0,
            0, 0, 255,
            255, 255, 255,
        ])

        data_url = calc_heights.rgb_to_bmp_data_url(rgb, width=2, height=2)

        self.assertTrue(data_url.startswith("data:image/bmp;base64,"))


class MuJoCoHeightTests(unittest.TestCase):
    def test_compute_keyframe_heights_returns_all_target_bodies(self):
        config = calc_heights.create_astro_embodiment_config(ROBOT_ROOT)

        result = calc_heights.compute_keyframe_heights(config, "knees_bent", render=False)

        self.assertEqual(result.embodiment, "astro")
        self.assertEqual(result.keyframe, "knees_bent")
        self.assertEqual(set(result.body_heights), set(config.body_height_targets))
        self.assertGreater(result.body_heights["pelvis"], 0.1)
        self.assertGreater(result.body_heights["torso_link"], result.body_heights["pelvis"])
        self.assertAlmostEqual(result.feet_min_z_after_alignment, 0.0, places=6)

    def test_compute_keyframe_heights_can_render_bmp_data_url(self):
        config = calc_heights.create_astro_embodiment_config(ROBOT_ROOT)

        result = calc_heights.compute_keyframe_heights(config, "zero", render=True, width=160, height=120)

        self.assertIsNotNone(result.image_data_url)
        self.assertTrue(result.image_data_url.startswith("data:image/bmp;base64,"))


if __name__ == "__main__":
    unittest.main()
