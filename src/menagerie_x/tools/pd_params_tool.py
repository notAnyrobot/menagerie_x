#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import difflib
import importlib.util
import json
import math
import pathlib
import sys
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from menagerie_x.assets import get_asset_paths


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
    "Damping Ratio",
    "$K_p$",
    "$K_d$",
    "Action Scale",
    "Effort ($\\text{N}\\cdot\\text{m}$)",
    "Vel ($\\text{rad/s}$)",
]


class ToolError(ValueError):
    """Raised when configuration-doc data or user input cannot be safely processed."""


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
        f"{row.frequency_hz:.1f} | {row.damping_ratio:.1f} | {computed.kp:.3f} | {computed.kd:.3f} | "
        f"{computed.action_scale:.4f} | {row.effort:.1f} | {row.velocity:.2f} |"
    )


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
        damping_ratio=_parse_float(cells[5], "damping_ratio", number),
        effort=_parse_float(cells[9], "effort", number),
        velocity=_parse_float(cells[10], "velocity", number),
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


def make_success_response(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, **data}


def make_error_response(error: Exception) -> dict[str, Any]:
    return {"ok": False, "error": str(error)}


def _asset_root_from_doc(doc_path: pathlib.Path) -> pathlib.Path:
    start = doc_path.resolve().parent
    for candidate in (start, *start.parents):
        paths = get_asset_paths(candidate)
        if paths.manifest_path.is_file():
            return paths.root
    return get_asset_paths(start).root


def _load_height_backend() -> Any:
    backend_path = pathlib.Path(__file__).with_name("calc_heights.py")
    spec = importlib.util.spec_from_file_location("calc_heights", backend_path)
    if spec is None or spec.loader is None:
        raise ToolError(f"could not load height backend from {backend_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def keyframes_response(repo_root: pathlib.Path) -> dict[str, Any]:
    backend = _load_height_backend()
    config = backend.create_astro_embodiment_config(repo_root)
    return make_success_response({"keyframes": backend.list_keyframes(config)})


def keyframe_heights_response(repo_root: pathlib.Path, keyframe_name: str, *, render: bool = True) -> dict[str, Any]:
    backend = _load_height_backend()
    try:
        config = backend.create_astro_embodiment_config(repo_root)
        result = backend.compute_keyframe_heights(config, keyframe_name, render=render)
        return make_success_response({"result": backend.result_to_json(result)})
    except Exception as exc:
        raise ToolError(str(exc)) from exc


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
    .layout { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 18px; align-items: start; }
    .panel { background: #fff; border: 1px solid #d9dee7; border-radius: 6px; padding: 12px; }
    .panel h2 { margin: 0 0 10px; font-size: 18px; }
    .height-row { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; border-bottom: 1px solid #eef2f7; font-size: 13px; }
    .height-row:last-child { border-bottom: 0; }
    .height-row span:last-child { font-variant-numeric: tabular-nums; }
    .snapshot { width: 100%; min-height: 180px; object-fit: contain; border: 1px solid #d9dee7; border-radius: 4px; background: #f6f7f9; margin-top: 10px; }
    select { width: 100%; box-sizing: border-box; border: 1px solid #b9c2cf; border-radius: 4px; padding: 6px; font: inherit; }
  </style>
</head>
<body>
<main>
  <header>
    <h1>PD Parameter Tool</h1>
    <div class="toolbar">
      <button onclick="loadTable()">Reload Config Doc</button>
      <button onclick="previewDiff()">Preview Config Diff</button>
      <button class="primary" onclick="applyReadme()">Update Config Doc</button>
    </div>
  </header>
  <div id="status" class="status">Loading configuration doc...</div>
  <div class="layout">
    <section>
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
    </section>
    <aside class="panel">
      <h2>Keyframe Heights</h2>
      <select id="keyframeSelect" onchange="loadKeyframeHeights()"></select>
      <div id="heightRows" style="margin-top:10px">
        <div class="height-row"><span>pelvis</span><span>-</span></div>
        <div class="height-row"><span>torso_link</span><span>-</span></div>
        <div class="height-row"><span>left_shoulder_pitch_link</span><span>-</span></div>
        <div class="height-row"><span>right_shoulder_pitch_link</span><span>-</span></div>
      </div>
      <button style="width:100%;margin-top:10px" onclick="loadKeyframes()">Reload keyframes</button>
      <div id="heightStatus" class="status">Loading keyframes...</div>
      <img id="keyframeSnapshot" class="snapshot" alt="MuJoCo keyframe snapshot">
    </aside>
  </div>
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

function updateComputedCells(tr, row) {
  recomputeRow(row);
  tr.cells[6].textContent = formatNumber(row.kp, 3);
  tr.cells[7].textContent = formatNumber(row.kd, 3);
  tr.cells[8].textContent = formatNumber(row.action_scale, 4);
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
    inputs[0].addEventListener("input", () => {
      const value = Number(inputs[0].value);
      if (Number.isFinite(value) && value > 0) {
        row.frequency_hz = value;
        updateComputedCells(tr, row);
      }
    });
    inputs[1].addEventListener("input", () => {
      const value = Number(inputs[1].value);
      if (Number.isFinite(value) && value >= 0) {
        row.damping_ratio = value;
        updateComputedCells(tr, row);
      }
    });
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
    setStatus(`Loaded ${rows.length} joint parameter rows from the configuration doc.`);
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function previewDiff() {
  try {
    const data = await api("/api/preview", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload())});
    document.getElementById("diff").textContent = data.diff || "(No changes.)";
    setStatus(data.changed ? "Preview ready." : "No configuration-doc changes.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function applyReadme() {
  try {
    const data = await api("/api/apply", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload())});
    rows = data.rows;
    renderRows();
    document.getElementById("diff").textContent = "(Configuration doc updated. Click Preview Config Diff for another check.)";
    setStatus(data.changed ? "Configuration doc updated." : "Configuration doc already matched these values.");
  } catch (error) {
    setStatus(error.message, true);
  }
}

function setHeightStatus(message, isError = false) {
  const el = document.getElementById("heightStatus");
  el.textContent = message;
  el.className = isError ? "status error" : "status";
}

function renderHeightRows(bodyHeights) {
  const order = ["pelvis", "torso_link", "left_shoulder_pitch_link", "right_shoulder_pitch_link"];
  const container = document.getElementById("heightRows");
  container.innerHTML = "";
  for (const name of order) {
    const row = document.createElement("div");
    row.className = "height-row";
    const value = bodyHeights && Number.isFinite(Number(bodyHeights[name]))
      ? `${Number(bodyHeights[name]).toFixed(4)} m`
      : "-";
    row.innerHTML = `<span>${name}</span><span>${value}</span>`;
    container.appendChild(row);
  }
}

async function loadKeyframes() {
  try {
    const data = await api("/api/keyframes");
    const select = document.getElementById("keyframeSelect");
    select.innerHTML = "";
    for (const keyframe of data.keyframes) {
      const option = document.createElement("option");
      option.value = keyframe.name;
      option.textContent = keyframe.label;
      select.appendChild(option);
    }
    select.value = data.keyframes.some(item => item.name === "knees_bent") ? "knees_bent" : data.keyframes[0]?.name;
    setHeightStatus(`Loaded ${data.keyframes.length} keyframes.`);
    await loadKeyframeHeights();
  } catch (error) {
    setHeightStatus(error.message, true);
  }
}

async function loadKeyframeHeights() {
  const select = document.getElementById("keyframeSelect");
  const name = select.value || "knees_bent";
  try {
    setHeightStatus(`Computing ${name}...`);
    const data = await api(`/api/keyframe-heights?name=${encodeURIComponent(name)}`);
    renderHeightRows(data.result.body_heights);
    document.getElementById("keyframeSnapshot").src = data.result.image_data_url || "";
    setHeightStatus(
      `Aligned feet min z ${Number(data.result.feet_min_z_after_alignment).toFixed(6)} m; base z ${Number(data.result.base_z_after_alignment).toFixed(4)} m.`
    );
  } catch (error) {
    renderHeightRows(null);
    document.getElementById("keyframeSnapshot").removeAttribute("src");
    setHeightStatus(error.message, true);
  }
}

loadTable();
loadKeyframes();
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
            if self.path == "/api/keyframes":
                self._send_json(HTTPStatus.OK, keyframes_response(_asset_root_from_doc(self.readme_path)))
                return
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/api/keyframe-heights":
                params = urllib.parse.parse_qs(parsed.query)
                keyframe_name = params.get("name", ["knees_bent"])[0]
                self._send_json(
                    HTTPStatus.OK,
                    keyframe_heights_response(_asset_root_from_doc(self.readme_path), keyframe_name, render=True),
                )
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
    parser.add_argument("--doc", type=pathlib.Path, default=pathlib.Path("docs/robot_configuration.md"))
    parser.add_argument("--readme", type=pathlib.Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)

    readme_path = (args.readme or args.doc).resolve()
    read_joint_parameters_table(readme_path.read_text(encoding="utf-8"))
    server = ThreadingHTTPServer((args.host, args.port), make_handler(readme_path))
    host, port = server.server_address
    url = f"http://{host}:{port}"
    print(f"Serving PD Parameter Tool at {url}", flush=True)
    print(f"Editing configuration table at {readme_path}", flush=True)
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
