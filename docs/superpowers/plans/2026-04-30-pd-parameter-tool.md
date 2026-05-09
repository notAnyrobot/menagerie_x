# PD Parameter Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local browser tool that computes Astro PD stiffness and damping per README joint group and updates only the `README.md` `Joint Parameters` table.

**Architecture:** Use one standard-library Python script at `scripts/pd_params_tool.py`. Keep formula, parsing, validation, diff, and write functions pure/importable for `unittest`, then layer a small `http.server` UI/API on top.

**Tech Stack:** Python 3 standard library, `unittest`, `http.server`, `json`, `difflib`, browser JavaScript.

---

## File Structure

- Create `scripts/pd_params_tool.py`: dataclasses, PD formulas, README table parser/replacer, validation, diff/apply helpers, embedded HTML/JS UI, and local HTTP server entrypoint.
- Create `tests/test_pd_params_tool.py`: standard-library `unittest` coverage for formulas, table parsing/replacement, validation, diff/apply helpers, and UI smoke checks.
- Modify `README.md`: only when the finished tool is manually tested through its apply action.
- Do not modify `config.yaml`.
- Do not modify `isaac_config/astro_delay.py`.

This checkout is currently not a Git repository. Run commit steps only if `git status --short --branch` succeeds in the environment where the plan is executed.

## Task 1: Formula Model And Computation

**Files:**
- Create: `tests/test_pd_params_tool.py`
- Create: `scripts/pd_params_tool.py`

- [ ] **Step 1: Write failing formula tests**

Create `tests/test_pd_params_tool.py` with this content:

```python
import dataclasses
import importlib.util
import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "pd_params_tool.py"
SPEC = importlib.util.spec_from_file_location("pd_params_tool", MODULE_PATH)
pd_params_tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pd_params_tool
assert SPEC.loader is not None
SPEC.loader.exec_module(pd_params_tool)


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
            "| 9 | `head_yaw_joint` | 3907-36 | 1.0 | 12.0 | 13.570 | 0.720 | 0.1842 | 10.0 | 20.94 |",
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the formula tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_pd_params_tool -v
```

Expected: fail with `FileNotFoundError` or an import error because `scripts/pd_params_tool.py` does not exist yet.

- [ ] **Step 3: Implement the formula model**

Create `scripts/pd_params_tool.py` with this content:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import difflib
import json
import math
import pathlib
import sys
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


ARMATURE_BY_MOTOR = {
    "3907-36": 0.002387,
    "5016-25": 0.008811,
    "8514-25": 0.081431,
}

REQUIRED_COLUMNS = [
    "#",
    "Joint Pattern",
    "Motor",
    "Mult",
    "$f$ (Hz)",
    "$K_p$",
    "$K_d$",
    "Action Scale",
    "Effort ($\\text{N}\\cdot\\text{m}$)",
    "Vel ($\\text{rad/s}$)",
]


class ToolError(ValueError):
    """Raised when README data or user input cannot be safely processed."""


@dataclasses.dataclass(frozen=True)
class JointParameterRow:
    number: int
    joint_pattern: str
    motor: str
    multiplier: float
    frequency_hz: float
    damping_ratio: float
    effort: float
    velocity: float


@dataclasses.dataclass(frozen=True)
class ComputedPD:
    kp: float
    kd: float
    action_scale: float


def compute_pd(row: JointParameterRow) -> ComputedPD:
    validate_row(row)
    armature = ARMATURE_BY_MOTOR[row.motor]
    effective_armature = armature * row.multiplier
    omega = 2.0 * math.pi * row.frequency_hz
    kp = effective_armature * omega * omega
    kd = 2.0 * row.damping_ratio * effective_armature * omega
    action_scale = 0.25 * row.effort / kp
    return ComputedPD(kp=kp, kd=kd, action_scale=action_scale)


def validate_row(row: JointParameterRow) -> None:
    if row.motor not in ARMATURE_BY_MOTOR:
        raise ToolError(f"unknown motor {row.motor!r} in row {row.number}")
    if row.multiplier <= 0.0:
        raise ToolError(f"multiplier must be positive in row {row.number}")
    if row.frequency_hz <= 0.0:
        raise ToolError(f"frequency_hz must be positive in row {row.number}")
    if row.damping_ratio < 0.0:
        raise ToolError(f"damping_ratio must be non-negative in row {row.number}")
    if row.effort <= 0.0:
        raise ToolError(f"effort must be positive in row {row.number}")


def _escape_joint_pattern(pattern: str) -> str:
    return pattern.replace("|", "\\|")


def _format_multiplier(value: float) -> str:
    rendered = f"{value:.2f}".rstrip("0").rstrip(".")
    return rendered if "." in rendered else f"{rendered}.0"


def render_joint_parameter_row(row: JointParameterRow) -> str:
    computed = compute_pd(row)
    return (
        f"| {row.number} | `{_escape_joint_pattern(row.joint_pattern)}` | {row.motor} | {_format_multiplier(row.multiplier)} | "
        f"{row.frequency_hz:.1f} | {computed.kp:.3f} | {computed.kd:.3f} | "
        f"{computed.action_scale:.4f} | {row.effort:.1f} | {row.velocity:.2f} |"
    )
```

- [ ] **Step 4: Run the formula tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_pd_params_tool -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Conditional commit**

Run:

```bash
git status --short --branch
```

If Git is available, run:

```bash
git add scripts/pd_params_tool.py tests/test_pd_params_tool.py
git commit -m "test: add pd parameter formula core"
```

Expected in this checkout: `git status` reports that this is not a Git repository, so skip the commit.

## Task 2: README Table Parser And Replacer

**Files:**
- Modify: `tests/test_pd_params_tool.py`
- Modify: `scripts/pd_params_tool.py`

- [ ] **Step 1: Add failing parser and replacement tests**

Append these tests inside `tests/test_pd_params_tool.py`, above the `if __name__ == "__main__":` block:

```python

class ReadmeTableTests(unittest.TestCase):
    SAMPLE_README = """# Astro

### Joint Parameters

| # | Joint Pattern | Motor | Mult | $f$ (Hz) | $K_p$ | $K_d$ | Action Scale | Effort ($\\text{N}\\cdot\\text{m}$) | Vel ($\\text{rad/s}$) |
|--:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `waist_yaw_joint` | 8514-25 | 1.0 | 8.0 | 205.745 | 16.373 | 0.2808 | 130.0 | 18.85 |
| 9 | `head_yaw_joint` | 3907-36 | 1.0 | 12.0 | 13.570 | 0.720 | 0.1842 | 10.0 | 20.94 |

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
        self.assertIn("| 1 | `waist_yaw_joint` | 8514-25 | 1.0 | 9.0 | 260.396 | 13.814 | 0.1248 | 130.0 | 18.85 |", updated)
        self.assertIn("| 9 | `head_yaw_joint` | 3907-36 | 1.0 | 12.0 | 13.570 | 0.720 | 0.1842 | 10.0 | 20.94 |", updated)

    def test_parser_rejects_missing_joint_parameters_heading(self):
        with self.assertRaisesRegex(pd_params_tool.ToolError, "Joint Parameters"):
            pd_params_tool.read_joint_parameters_table("# Astro\\n\\nNo table here.\\n")

    def test_parser_preserves_escaped_pipe_inside_joint_pattern(self):
        readme = """# Astro

### Joint Parameters

| # | Joint Pattern | Motor | Mult | $f$ (Hz) | $K_p$ | $K_d$ | Action Scale | Effort ($\\text{N}\\cdot\\text{m}$) | Vel ($\\text{rad/s}$) |
|--:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2 | `.*_hip_(pitch\\|roll\\|yaw)_joint` | 8514-25 | 1.0 | 8.0 | 205.745 | 16.373 | 0.2808 | 130.0 | 18.85 |
"""

        table = pd_params_tool.read_joint_parameters_table(readme)

        self.assertEqual(table.rows[0].joint_pattern, ".*_hip_(pitch|roll|yaw)_joint")
```

- [ ] **Step 2: Run tests and verify the new tests fail**

Run:

```bash
python3 -m unittest tests.test_pd_params_tool -v
```

Expected: fail with missing `read_joint_parameters_table` and `replace_joint_parameters_table`.

- [ ] **Step 3: Implement README table parsing and replacement**

Append this code to `scripts/pd_params_tool.py`:

```python

@dataclasses.dataclass(frozen=True)
class JointParameterTable:
    header: str
    alignment: str
    rows: list[JointParameterRow]
    start_line: int
    end_line: int


def _split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        raise ToolError(f"not a markdown table row: {line!r}")
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in stripped[1:-1]:
        if char == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
            continue
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            continue
        current.append(char)
    cells.append("".join(current).strip())
    return cells


def _unescape_joint_pattern(cell: str) -> str:
    cell = cell.strip()
    if cell.startswith("`") and cell.endswith("`"):
        cell = cell[1:-1]
    return cell.replace("\\|", "|")


def _parse_float(cell: str, field_name: str, row_number: int) -> float:
    try:
        return float(cell)
    except ValueError as exc:
        raise ToolError(f"invalid {field_name} in row {row_number}: {cell!r}") from exc


def _parse_readme_row(line: str) -> JointParameterRow:
    cells = _split_markdown_row(line)
    if len(cells) != len(REQUIRED_COLUMNS):
        raise ToolError(f"expected {len(REQUIRED_COLUMNS)} columns, found {len(cells)} in {line!r}")
    try:
        number = int(cells[0])
    except ValueError as exc:
        raise ToolError(f"invalid row number: {cells[0]!r}") from exc
    row = JointParameterRow(
        number=number,
        joint_pattern=_unescape_joint_pattern(cells[1]),
        motor=cells[2],
        multiplier=_parse_float(cells[3], "multiplier", number),
        frequency_hz=_parse_float(cells[4], "frequency_hz", number),
        damping_ratio=2.0,
        effort=_parse_float(cells[8], "effort", number),
        velocity=_parse_float(cells[9], "velocity", number),
    )
    validate_row(row)
    return row


def read_joint_parameters_table(readme_text: str) -> JointParameterTable:
    lines = readme_text.splitlines()
    heading_index = next(
        (idx for idx, line in enumerate(lines) if line.strip() == "### Joint Parameters"),
        None,
    )
    if heading_index is None:
        raise ToolError("could not find ### Joint Parameters heading")

    table_start = None
    for idx in range(heading_index + 1, len(lines)):
        if lines[idx].strip().startswith("|"):
            table_start = idx
            break
        if lines[idx].strip().startswith("### "):
            break
    if table_start is None or table_start + 1 >= len(lines):
        raise ToolError("could not find Joint Parameters markdown table")

    header = lines[table_start]
    alignment = lines[table_start + 1]
    header_cells = _split_markdown_row(header)
    if header_cells != REQUIRED_COLUMNS:
        raise ToolError(f"Joint Parameters table columns changed: {header_cells!r}")

    rows: list[JointParameterRow] = []
    table_end = table_start + 1
    for idx in range(table_start + 2, len(lines)):
        if not lines[idx].strip().startswith("|"):
            break
        rows.append(_parse_readme_row(lines[idx]))
        table_end = idx
    if not rows:
        raise ToolError("Joint Parameters table has no data rows")

    return JointParameterTable(
        header=header,
        alignment=alignment,
        rows=rows,
        start_line=table_start,
        end_line=table_end,
    )


def render_joint_parameters_table(rows: list[JointParameterRow], source_table: JointParameterTable) -> list[str]:
    if len(rows) != len(source_table.rows):
        raise ToolError(f"row count changed from {len(source_table.rows)} to {len(rows)}")
    return [source_table.header, source_table.alignment, *[render_joint_parameter_row(row) for row in rows]]


def replace_joint_parameters_table(readme_text: str, rows: list[JointParameterRow]) -> str:
    source_table = read_joint_parameters_table(readme_text)
    replacement_lines = render_joint_parameters_table(rows, source_table)
    lines = readme_text.splitlines()
    updated_lines = lines[: source_table.start_line] + replacement_lines + lines[source_table.end_line + 1 :]
    trailing_newline = "\n" if readme_text.endswith("\n") else ""
    return "\n".join(updated_lines) + trailing_newline
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_pd_params_tool -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Conditional commit**

If Git is available:

```bash
git add scripts/pd_params_tool.py tests/test_pd_params_tool.py
git commit -m "feat: parse and replace readme joint table"
```

Expected in this checkout: skip because Git is unavailable.

## Task 3: JSON Payload Validation, Preview, And Apply Helpers

**Files:**
- Modify: `tests/test_pd_params_tool.py`
- Modify: `scripts/pd_params_tool.py`

- [ ] **Step 1: Add failing preview/apply tests**

Append this test class above the `if __name__ == "__main__":` block:

```python

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
        self.assertIn("+| 1 | `waist_yaw_joint` | 8514-25 | 1.0 | 9.0 | 260.396 | 13.814 | 0.1248 | 130.0 | 18.85 |", result["diff"])
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
        self.assertIn("| 1 | `waist_yaw_joint` | 8514-25 | 1.0 | 9.0 | 260.396 | 13.814 | 0.1248 | 130.0 | 18.85 |", readme_path.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run tests and verify the new tests fail**

Run:

```bash
python3 -m unittest tests.test_pd_params_tool -v
```

Expected: fail with missing `rows_from_payload`, `preview_readme_update`, and `apply_readme_update`.

- [ ] **Step 3: Implement validation, preview, and apply helpers**

Append this code to `scripts/pd_params_tool.py`:

```python

def rows_from_payload(payload: dict[str, Any], source_rows: list[JointParameterRow]) -> list[JointParameterRow]:
    payload_rows = payload.get("rows")
    if not isinstance(payload_rows, list):
        raise ToolError("payload must contain a rows list")
    if len(payload_rows) != len(source_rows):
        raise ToolError(f"row count mismatch: expected {len(source_rows)}, received {len(payload_rows)}")

    updated_rows: list[JointParameterRow] = []
    for source, item in zip(source_rows, payload_rows, strict=True):
        if not isinstance(item, dict):
            raise ToolError(f"row {source.number} payload must be an object")
        if item.get("number") != source.number:
            raise ToolError(f"row number mismatch: expected {source.number}, received {item.get('number')!r}")
        try:
            frequency_hz = float(item["frequency_hz"])
            damping_ratio = float(item["damping_ratio"])
        except KeyError as exc:
            raise ToolError(f"row {source.number} missing {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise ToolError(f"row {source.number} frequency_hz and damping_ratio must be numeric") from exc
        updated = dataclasses.replace(source, frequency_hz=frequency_hz, damping_ratio=damping_ratio)
        validate_row(updated)
        updated_rows.append(updated)
    return updated_rows


def rows_to_json(rows: list[JointParameterRow]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        computed = compute_pd(row)
        result.append(
            {
                "number": row.number,
                "joint_pattern": row.joint_pattern,
                "motor": row.motor,
                "multiplier": row.multiplier,
                "frequency_hz": row.frequency_hz,
                "damping_ratio": row.damping_ratio,
                "kp": computed.kp,
                "kd": computed.kd,
                "action_scale": computed.action_scale,
                "effort": row.effort,
                "velocity": row.velocity,
            }
        )
    return result


def preview_readme_update(readme_path: pathlib.Path, payload: dict[str, Any]) -> dict[str, Any]:
    original = readme_path.read_text(encoding="utf-8")
    table = read_joint_parameters_table(original)
    updated_rows = rows_from_payload(payload, table.rows)
    updated = replace_joint_parameters_table(original, updated_rows)
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=str(readme_path),
            tofile=str(readme_path),
        )
    )
    return {"changed": original != updated, "diff": diff, "rows": rows_to_json(updated_rows)}


def apply_readme_update(readme_path: pathlib.Path, payload: dict[str, Any]) -> dict[str, Any]:
    original = readme_path.read_text(encoding="utf-8")
    table = read_joint_parameters_table(original)
    updated_rows = rows_from_payload(payload, table.rows)
    updated = replace_joint_parameters_table(original, updated_rows)
    if updated != original:
        readme_path.write_text(updated, encoding="utf-8")
    return {"changed": updated != original, "rows": rows_to_json(updated_rows)}
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_pd_params_tool -v
```

Expected: 11 tests pass.

- [ ] **Step 5: Conditional commit**

If Git is available:

```bash
git add scripts/pd_params_tool.py tests/test_pd_params_tool.py
git commit -m "feat: add readme preview and apply helpers"
```

Expected in this checkout: skip because Git is unavailable.

## Task 4: Browser UI And HTTP API

**Files:**
- Modify: `tests/test_pd_params_tool.py`
- Modify: `scripts/pd_params_tool.py`

- [ ] **Step 1: Add failing UI/API smoke tests**

Append this test class above the `if __name__ == "__main__":` block:

```python

class UiSmokeTests(unittest.TestCase):
    def test_build_index_html_contains_expected_controls(self):
        page = pd_params_tool.build_index_html()

        self.assertIn("PD Parameter Tool", page)
        self.assertIn("Preview README Diff", page)
        self.assertIn("Update README.md", page)
        self.assertIn("/api/table", page)

    def test_make_success_response_is_json_serializable(self):
        response = pd_params_tool.make_success_response({"changed": False})

        self.assertEqual(response["ok"], True)
        self.assertEqual(json.loads(json.dumps(response))["changed"], False)
```

- [ ] **Step 2: Run tests and verify the new tests fail**

Run:

```bash
python3 -m unittest tests.test_pd_params_tool -v
```

Expected: fail with missing `build_index_html` and `make_success_response`.

- [ ] **Step 3: Implement UI HTML, JSON helpers, request handler, and CLI entrypoint**

Append this code to `scripts/pd_params_tool.py`:

```python

def make_success_response(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, **data}


def make_error_response(error: Exception) -> dict[str, Any]:
    return {"ok": False, "error": str(error)}


def build_index_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PD Parameter Tool</title>
  <style>
    :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #17202a; }
    main { max-width: 1280px; margin: 0 auto; padding: 24px; }
    header { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 18px; }
    h1 { margin: 0; font-size: 24px; letter-spacing: 0; }
    .toolbar { display: flex; gap: 8px; flex-wrap: wrap; }
    button { border: 1px solid #b9c2cf; background: #fff; border-radius: 6px; padding: 8px 12px; cursor: pointer; }
    button.primary { background: #2457d6; border-color: #2457d6; color: #fff; }
    button:disabled { opacity: 0.55; cursor: not-allowed; }
    table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d9dee7; }
    th, td { border-bottom: 1px solid #e5e9f0; padding: 8px; text-align: left; font-size: 13px; vertical-align: middle; }
    th { background: #eef2f7; font-weight: 650; }
    td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
    input { width: 80px; box-sizing: border-box; border: 1px solid #b9c2cf; border-radius: 4px; padding: 5px 6px; font: inherit; }
    code { font-family: "SFMono-Regular", Consolas, monospace; }
    .status { margin: 14px 0; padding: 10px 12px; border: 1px solid #d9dee7; border-radius: 6px; background: #fff; min-height: 22px; }
    .status.error { border-color: #d33; color: #9b1c1c; }
    pre { white-space: pre-wrap; overflow: auto; border: 1px solid #d9dee7; border-radius: 6px; background: #101820; color: #f7fafc; padding: 12px; max-height: 360px; }
  </style>
</head>
<body>
<main>
  <header>
    <h1>PD Parameter Tool</h1>
    <div class="toolbar">
      <button onclick="loadTable()">Reload README.md</button>
      <button onclick="previewDiff()">Preview README Diff</button>
      <button class="primary" onclick="applyReadme()">Update README.md</button>
    </div>
  </header>
  <div id="status" class="status">Loading README.md...</div>
  <table>
    <thead>
      <tr>
        <th class="num">#</th><th>Joint Pattern</th><th>Motor</th><th class="num">Mult</th>
        <th class="num">f Hz</th><th class="num">Damping Ratio</th><th class="num">Kp</th>
        <th class="num">Kd</th><th class="num">Action Scale</th><th class="num">Effort</th><th class="num">Vel</th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>
  <h2>Diff Preview</h2>
  <pre id="diff">(No preview yet.)</pre>
</main>
<script>
let rows = [];

function setStatus(message, isError = false) {
  const el = document.getElementById("status");
  el.textContent = message;
  el.className = isError ? "status error" : "status";
}

function formatNumber(value, digits) {
  return Number(value).toFixed(digits);
}

function recomputeRow(row) {
  const armatures = {"3907-36": 0.002387, "5016-25": 0.008811, "8514-25": 0.081431};
  const omega = 2.0 * Math.PI * Number(row.frequency_hz);
  const effective = armatures[row.motor] * Number(row.multiplier);
  row.kp = effective * omega * omega;
  row.kd = 2.0 * Number(row.damping_ratio) * effective * omega;
  row.action_scale = 0.25 * Number(row.effort) / row.kp;
}

function renderRows() {
  const tbody = document.getElementById("rows");
  tbody.innerHTML = "";
  for (const row of rows) {
    recomputeRow(row);
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="num">${row.number}</td>
      <td><code>${escapeHtml(row.joint_pattern)}</code></td>
      <td>${row.motor}</td>
      <td class="num">${row.multiplier}</td>
      <td class="num"><input type="number" min="0.001" step="0.1" value="${formatNumber(row.frequency_hz, 1)}"></td>
      <td class="num"><input type="number" min="0" step="0.1" value="${formatNumber(row.damping_ratio, 1)}"></td>
      <td class="num">${formatNumber(row.kp, 3)}</td>
      <td class="num">${formatNumber(row.kd, 3)}</td>
      <td class="num">${formatNumber(row.action_scale, 4)}</td>
      <td class="num">${formatNumber(row.effort, 1)}</td>
      <td class="num">${formatNumber(row.velocity, 2)}</td>`;
    const inputs = tr.querySelectorAll("input");
    inputs[0].addEventListener("input", () => { row.frequency_hz = Number(inputs[0].value); renderRows(); });
    inputs[1].addEventListener("input", () => { row.damping_ratio = Number(inputs[1].value); renderRows(); });
    tbody.appendChild(tr);
  }
}

function escapeHtml(value) {
  const entityMap = {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"};
  return String(value).replace(/[&<>"']/g, ch => entityMap[ch]);
}

function payload() {
  return {rows: rows.map(row => ({number: row.number, frequency_hz: Number(row.frequency_hz), damping_ratio: Number(row.damping_ratio)}))};
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function loadTable() {
  try {
    const data = await api("/api/table");
    rows = data.rows;
    renderRows();
    document.getElementById("diff").textContent = "(No preview yet.)";
    setStatus(`Loaded ${rows.length} joint parameter rows from README.md.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function previewDiff() {
  try {
    const data = await api("/api/preview", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload())});
    document.getElementById("diff").textContent = data.diff || "(No changes.)";
    setStatus(data.changed ? "Preview ready." : "No README.md changes.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function applyReadme() {
  try {
    const data = await api("/api/apply", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload())});
    rows = data.rows;
    renderRows();
    document.getElementById("diff").textContent = "(README.md updated. Click Preview README Diff for another check.)";
    setStatus(data.changed ? "README.md updated." : "README.md already matched these values.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

loadTable();
</script>
</body>
</html>"""


class PDParameterRequestHandler(BaseHTTPRequestHandler):
    readme_path: pathlib.Path

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ToolError("request body must be valid JSON") from exc
        if not isinstance(data, dict):
            raise ToolError("request JSON must be an object")
        return data

    def do_GET(self) -> None:
        try:
            if self.path == "/":
                encoded = build_index_html().encode("utf-8")
                self.send_response(HTTPStatus.OK.value)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                return
            if self.path == "/api/table":
                readme_text = self.readme_path.read_text(encoding="utf-8")
                table = read_joint_parameters_table(readme_text)
                self._send_json(HTTPStatus.OK, make_success_response({"rows": rows_to_json(table.rows)}))
                return
            self._send_json(HTTPStatus.NOT_FOUND, make_error_response(ToolError("not found")))
        except Exception as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, make_error_response(exc))

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            if self.path == "/api/preview":
                self._send_json(HTTPStatus.OK, make_success_response(preview_readme_update(self.readme_path, payload)))
                return
            if self.path == "/api/apply":
                self._send_json(HTTPStatus.OK, make_success_response(apply_readme_update(self.readme_path, payload)))
                return
            self._send_json(HTTPStatus.NOT_FOUND, make_error_response(ToolError("not found")))
        except Exception as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, make_error_response(exc))

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}", file=sys.stderr)


def make_handler(readme_path: pathlib.Path) -> type[PDParameterRequestHandler]:
    class Handler(PDParameterRequestHandler):
        pass

    Handler.readme_path = readme_path
    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Interactive Astro PD parameter table editor")
    parser.add_argument("--readme", type=pathlib.Path, default=pathlib.Path("README.md"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)

    readme_path = args.readme.resolve()
    read_joint_parameters_table(readme_path.read_text(encoding="utf-8"))
    server = ThreadingHTTPServer((args.host, args.port), make_handler(readme_path))
    host, port = server.server_address
    url = f"http://{host}:{port}"
    print(f"Serving PD Parameter Tool at {url}")
    print(f"Editing README table at {readme_path}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_pd_params_tool -v
```

Expected: 13 tests pass.

- [ ] **Step 5: Conditional commit**

If Git is available:

```bash
git add scripts/pd_params_tool.py tests/test_pd_params_tool.py
git commit -m "feat: add browser ui for pd parameter tool"
```

Expected in this checkout: skip because Git is unavailable.

## Task 5: End-To-End Validation

**Files:**
- Modify: `README.md` only if manually applying a chosen PD configuration through the tool.

- [ ] **Step 1: Run the full unit test suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: all tests pass, including `FormulaTests`, `ReadmeTableTests`, `PreviewApplyTests`, and `UiSmokeTests`.

- [ ] **Step 2: Run syntax validation**

Run:

```bash
python3 -m py_compile scripts/pd_params_tool.py tests/test_pd_params_tool.py
```

Expected: no output and exit code 0.

- [ ] **Step 3: Start the tool without opening a browser**

Run:

```bash
python3 scripts/pd_params_tool.py --no-browser
```

Expected: prints a local URL such as `Serving PD Parameter Tool at http://127.0.0.1:xxxxx` and keeps running.

- [ ] **Step 4: Browser smoke test**

Open the printed URL. Verify:

- The table loads 10 rows from `README.md`.
- Editing `f` or damping ratio immediately updates `Kp`, `Kd`, and action scale in the same row.
- `Preview README Diff` shows a unified diff that only touches rows under `### Joint Parameters`.
- `Update README.md` writes the selected values only after the table validates.

- [ ] **Step 5: Confirm protected files are unchanged**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
for path in ["config.yaml", "isaac_config/astro_delay.py"]:
    print(path, Path(path).exists())
PY
```

Expected:

```text
config.yaml True
isaac_config/astro_delay.py True
```

If Git is available, additionally run:

```bash
git diff -- config.yaml isaac_config/astro_delay.py
```

Expected: no diff.

- [ ] **Step 6: Conditional final commit**

If Git is available and the manual README update is intended to be preserved:

```bash
git add scripts/pd_params_tool.py tests/test_pd_params_tool.py README.md
git commit -m "feat: add pd parameter readme editor"
```

If Git is unavailable, list changed files with:

```bash
find scripts tests docs/superpowers -maxdepth 3 -type f | sort
```

Expected: the new tool, tests, spec, and plan are visible.
