import dataclasses
import json
import pathlib
import unittest

from menagerie_x.tools import pd_params_tool

ROOT = pathlib.Path(__file__).resolve().parents[1]


class FormulaTests(unittest.TestCase):
    def test_compute_pd_uses_armature_multiplier_frequency_and_damping_ratio(self):
        row = pd_params_tool.JointParameterRow(
            number=4,
            joint_pattern="waist_pitch_joint",
            motor="5016-25",
            multiplier=2.0,
            frequency_hz=10.0,
            damping_ratio=2.0,
            effort=60.0,
            velocity=26.18,
        )

        computed = pd_params_tool.compute_pd(row)

        self.assertAlmostEqual(computed.kp, 69.569, places=3)
        self.assertAlmostEqual(computed.kd, 4.429, places=3)
        self.assertAlmostEqual(computed.action_scale, 0.2156, places=4)

    def test_format_row_uses_readme_precision(self):
        row = pd_params_tool.JointParameterRow(
            number=9,
            joint_pattern="head_yaw_joint",
            motor="3907-36",
            multiplier=1.0,
            frequency_hz=12.0,
            damping_ratio=2.0,
            effort=10.0,
            velocity=20.94,
        )

        rendered = pd_params_tool.render_joint_parameter_row(row)

        self.assertEqual(
            rendered,
            "| 9 | `head_yaw_joint` | 3907-36 | 1.0 | 12.0 | 2.0 | 13.570 | 0.720 | 0.1842 | 10.0 | 20.94 |",
        )

    def test_format_row_escapes_pipe_inside_joint_pattern(self):
        row = pd_params_tool.JointParameterRow(
            number=2,
            joint_pattern=".*_hip_(pitch|roll|yaw)_joint",
            motor="8514-25",
            multiplier=1.0,
            frequency_hz=8.0,
            damping_ratio=2.0,
            effort=130.0,
            velocity=18.85,
        )

        rendered = pd_params_tool.render_joint_parameter_row(row)

        self.assertIn("`.*_hip_(pitch\\|roll\\|yaw)_joint`", rendered)


class ReadmeTableTests(unittest.TestCase):
    SAMPLE_README = """# Astro

### Joint Parameters

| # | Joint Pattern | Motor | Mult | $f$ (Hz) | Damping Ratio | $K_p$ | $K_d$ | Action Scale | Effort ($\\text{N}\\cdot\\text{m}$) | Vel ($\\text{rad/s}$) |
|--:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `waist_yaw_joint` | 8514-25 | 1.0 | 8.0 | 2.0 | 205.745 | 16.373 | 0.2808 | 130.0 | 18.85 |
| 9 | `head_yaw_joint` | 3907-36 | 1.0 | 12.0 | 2.0 | 13.570 | 0.720 | 0.1842 | 10.0 | 20.94 |

> [!TIP]
> Keep this note.
"""

    def test_read_joint_parameters_table_parses_existing_rows(self):
        table = pd_params_tool.read_joint_parameters_table(self.SAMPLE_README)

        self.assertEqual(table.start_line, 4)
        self.assertEqual(table.end_line, 7)
        self.assertEqual(len(table.rows), 2)
        self.assertEqual(table.rows[0].joint_pattern, "waist_yaw_joint")
        self.assertEqual(table.rows[0].damping_ratio, 2.0)
        self.assertEqual(table.rows[1].motor, "3907-36")

    def test_replace_joint_parameters_table_preserves_surrounding_content(self):
        table = pd_params_tool.read_joint_parameters_table(self.SAMPLE_README)
        updated_rows = [
            dataclasses.replace(table.rows[0], frequency_hz=9.0, damping_ratio=1.5),
            table.rows[1],
        ]

        updated = pd_params_tool.replace_joint_parameters_table(self.SAMPLE_README, updated_rows)

        self.assertIn("# Astro", updated)
        self.assertIn("> Keep this note.", updated)
        self.assertIn("| 1 | `waist_yaw_joint` | 8514-25 | 1.0 | 9.0 | 1.5 | 260.396 | 13.814 | 0.1248 | 130.0 | 18.85 |", updated)
        self.assertIn("| 9 | `head_yaw_joint` | 3907-36 | 1.0 | 12.0 | 2.0 | 13.570 | 0.720 | 0.1842 | 10.0 | 20.94 |", updated)

    def test_parser_rejects_missing_joint_parameters_heading(self):
        with self.assertRaisesRegex(pd_params_tool.ToolError, "Joint Parameters"):
            pd_params_tool.read_joint_parameters_table("# Astro\n\nNo table here.\n")

    def test_parser_preserves_escaped_pipe_inside_joint_pattern(self):
        readme = """# Astro

### Joint Parameters

| # | Joint Pattern | Motor | Mult | $f$ (Hz) | Damping Ratio | $K_p$ | $K_d$ | Action Scale | Effort ($\\text{N}\\cdot\\text{m}$) | Vel ($\\text{rad/s}$) |
|--:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | `.*_hip_(pitch\\|roll\\|yaw)_joint` | 8514-25 | 1.0 | 8.0 | 2.0 | 205.745 | 16.373 | 0.2808 | 130.0 | 18.85 |
"""

        table = pd_params_tool.read_joint_parameters_table(readme)

        self.assertEqual(table.rows[0].joint_pattern, ".*_hip_(pitch|roll|yaw)_joint")


class PreviewApplyTests(unittest.TestCase):
    def test_rows_from_payload_preserves_readme_identity_and_accepts_user_inputs(self):
        table = pd_params_tool.read_joint_parameters_table(ReadmeTableTests.SAMPLE_README)
        payload = {
            "rows": [
                {"number": 1, "frequency_hz": 9.0, "damping_ratio": 1.5},
                {"number": 9, "frequency_hz": 12.0, "damping_ratio": 2.0},
            ]
        }

        rows = pd_params_tool.rows_from_payload(payload, table.rows)

        self.assertEqual(rows[0].joint_pattern, "waist_yaw_joint")
        self.assertEqual(rows[0].frequency_hz, 9.0)
        self.assertEqual(rows[0].damping_ratio, 1.5)

    def test_rows_from_payload_rejects_row_count_mismatch(self):
        table = pd_params_tool.read_joint_parameters_table(ReadmeTableTests.SAMPLE_README)

        with self.assertRaisesRegex(pd_params_tool.ToolError, "row count"):
            pd_params_tool.rows_from_payload({"rows": [{"number": 1, "frequency_hz": 8.0, "damping_ratio": 2.0}]}, table.rows)

    def test_preview_readme_update_returns_unified_diff_without_writing(self):
        readme_path = ROOT / "tests" / "tmp_preview_readme.md"
        readme_path.write_text(ReadmeTableTests.SAMPLE_README, encoding="utf-8")
        self.addCleanup(lambda: readme_path.unlink(missing_ok=True))

        payload = {
            "rows": [
                {"number": 1, "frequency_hz": 9.0, "damping_ratio": 1.5},
                {"number": 9, "frequency_hz": 12.0, "damping_ratio": 2.0},
            ]
        }

        result = pd_params_tool.preview_readme_update(readme_path, payload)

        self.assertIn("-| 1 | `waist_yaw_joint`", result["diff"])
        self.assertIn("+| 1 | `waist_yaw_joint` | 8514-25 | 1.0 | 9.0 | 1.5 | 260.396 | 13.814 | 0.1248 | 130.0 | 18.85 |", result["diff"])
        self.assertEqual(readme_path.read_text(encoding="utf-8"), ReadmeTableTests.SAMPLE_README)

    def test_apply_readme_update_writes_only_after_validation(self):
        readme_path = ROOT / "tests" / "tmp_apply_readme.md"
        readme_path.write_text(ReadmeTableTests.SAMPLE_README, encoding="utf-8")
        self.addCleanup(lambda: readme_path.unlink(missing_ok=True))
        payload = {
            "rows": [
                {"number": 1, "frequency_hz": 9.0, "damping_ratio": 1.5},
                {"number": 9, "frequency_hz": 12.0, "damping_ratio": 2.0},
            ]
        }

        result = pd_params_tool.apply_readme_update(readme_path, payload)

        self.assertTrue(result["changed"])
        self.assertIn("> Keep this note.", readme_path.read_text(encoding="utf-8"))
        self.assertIn("| 1 | `waist_yaw_joint` | 8514-25 | 1.0 | 9.0 | 1.5 | 260.396 | 13.814 | 0.1248 | 130.0 | 18.85 |", readme_path.read_text(encoding="utf-8"))


class KeyframeApiTests(unittest.TestCase):
    def test_keyframes_response_lists_astro_keyframes(self):
        response = pd_params_tool.keyframes_response(ROOT)

        self.assertEqual(response["ok"], True)
        self.assertEqual([item["name"] for item in response["keyframes"]], ["home", "knees_bent", "t_pose", "zero"])

    def test_keyframe_heights_response_rejects_unknown_keyframe(self):
        with self.assertRaisesRegex(pd_params_tool.ToolError, "unknown keyframe"):
            pd_params_tool.keyframe_heights_response(ROOT, "missing", render=False)


class UiSmokeTests(unittest.TestCase):
    def test_build_index_html_contains_expected_controls(self):
        page = pd_params_tool.build_index_html()

        self.assertIn("PD Parameter Tool", page)
        self.assertIn("Preview Config Diff", page)
        self.assertIn("Update Config Doc", page)
        self.assertIn("/api/table", page)
        self.assertIn("updateComputedCells", page)
        self.assertIn("Keyframe Heights", page)
        self.assertIn("/api/keyframes", page)
        self.assertIn("/api/keyframe-heights", page)
        self.assertIn("left_shoulder_pitch_link", page)
        self.assertIn("right_shoulder_pitch_link", page)

    def test_make_success_response_is_json_serializable(self):
        response = pd_params_tool.make_success_response({"changed": False})

        self.assertEqual(response["ok"], True)
        self.assertEqual(json.loads(json.dumps(response))["changed"], False)


if __name__ == "__main__":
    unittest.main()
