# MJCF Collision to URDF Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-destructive Workbench action that downloads a standards-compliant URDF whose collision elements come from the selected saved MJCF edition while all canonical URDF non-collision content is preserved.

**Architecture:** A deep module in `menagerie_x.assets` compiles the selected MJCF with MuJoCo 3.11.0, validates exact body-to-link frame compatibility, converts supported contact geoms, rewrites only URDF collision elements, and returns bytes plus a structured report. The Workbench server is a thin HTTP adapter, while a small browser module downloads the response from a new left-panel action.

**Tech Stack:** Python 3.12, MuJoCo 3.11.0, `xml.etree.ElementTree`, `unittest`, the existing `BaseHTTPRequestHandler` Workbench server, browser JavaScript modules, and Node's built-in test runner.

**Spec:** `docs/superpowers/specs/2026-08-19-mjcf-to-urdf-export-design.md`

## Global Constraints

- Version one transfers collision geometry only from a selected saved MJCF edition into an existing canonical URDF.
- Never modify packaged URDF, MJCF, manifest, edition metadata, or collision-editor drafts.
- Leave `src/menagerie_x/workbench/collisions.py`, `src/menagerie_x/workbench/mjcf_collisions.py`, `src/menagerie_x/workbench/web/collision-editor.js`, and the mirror feature unchanged.
- Emit only standard URDF `box`, `sphere`, and `cylinder` geometry; never emit the custom capsule extension.
- Expand one MJCF capsule into one cylinder followed by its negative-local-Z and positive-local-Z spheres.
- Fail the complete export on any unsupported, unsafe, unnamed, unmapped, or malformed collision; never silently omit a contact geom.
- Resolve variant and edition paths server-side. The HTTP request accepts no filesystem path.
- Use only the selected saved edition. Unsaved collision-draft state is never an export input.
- Output is an in-memory download only; do not create a server-side export file, catalog edition, commit, push, release, or CLI command.
- Astro V2 is the reference: 39 capsules, seven cylinders, and one sphere become 125 URDF collision elements.
- The standards guarantee applies to generated collision geometry. Preserve the canonical URDF's non-collision extensions, including Astro's existing top-level `<mujoco>` element.

---

## File Structure

- Create `src/menagerie_x/assets/urdf_collision_export.py`: the sole conversion and reporting module.
- Modify `src/menagerie_x/assets/__init__.py`: re-export the module's public interface.
- Create `tests/test_urdf_collision_export.py`: focused converter, preservation, safety, and Astro reference tests.
- Modify `src/menagerie_x/workbench/server.py`: one download endpoint and structured 422 response.
- Modify `tests/test_workbench.py`: endpoint and static page integration tests.
- Create `src/menagerie_x/workbench/web/urdf-export.js`: response parsing and browser download helpers.
- Create `src/menagerie_x/workbench/web/urdf-export.test.js`: Node tests for the browser helper.
- Modify `src/menagerie_x/workbench/web/index.html`: left-panel button and accessible status.
- Modify `src/menagerie_x/workbench/web/app.js`: selection gating and click orchestration.
- Modify `src/menagerie_x/workbench/web/styles.css`: three-action layout and status styling.
- Modify `README.md`: document download-only semantics and version-one limits.

### Task 1: Build the standards-compliant collision exporter

**Files:**
- Create: `src/menagerie_x/assets/urdf_collision_export.py`
- Modify: `src/menagerie_x/assets/__init__.py`
- Create: `tests/test_urdf_collision_export.py`

**Interfaces:**
- Consumes: `menagerie_x.assets.Variant`, a server-resolved saved MJCF `Path`, an edition identifier, and the registered asset root.
- Produces: `export_urdf_with_mjcf_collisions(variant, mjcf_path, *, edition_id, asset_root) -> UrdfCollisionExport`.
- Produces: immutable `UrdfCollisionExport`, `CollisionExportReport`, and `CollisionExportIssue` records with `as_dict()` methods.
- Produces: `UrdfCollisionExportError(AssetError)` carrying the complete failure report.

- [ ] **Step 1: Write failing primitive and capsule tests**

Add compact temporary URDF/MJCF fixtures and assert exact standard dimensions and capsule endpoints:

```python
def test_capsule_expands_to_three_standard_collisions(self):
    result = export_urdf_with_mjcf_collisions(
        self.variant,
        self.mjcf,
        edition_id="reviewed",
        asset_root=self.asset_root,
    )
    root = ET.fromstring(result.content)
    collisions = root.findall("./link[@name='pelvis']/collision")
    self.assertEqual(len(collisions), 3)
    self.assertIsNotNone(collisions[0].find("./geometry/cylinder"))
    self.assertEqual(collisions[0].find("./geometry/cylinder").attrib, {"radius": "0.1", "length": "0.4"})
    self.assertEqual(
        [node.find("origin").attrib["xyz"] for node in collisions[1:]],
        ["0 0 -0.2", "0 0 0.2"],
    )
    self.assertFalse(root.findall(".//capsule"))
```

Also add `test_box_sphere_and_cylinder_use_standard_urdf_dimensions`, including a rotated cylinder and an MJCF `fromto` capsule so compilation, not raw-attribute assumptions, determines pose and size.

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```bash
UV_CACHE_DIR=/tmp/menagerie-x-urdf-export-cache uv run python -m unittest tests.test_urdf_collision_export -v
```

Expected: import failure for `menagerie_x.assets.urdf_collision_export`.

- [ ] **Step 3: Define the public records and error contract**

Implement these exact public shapes:

```python
@dataclasses.dataclass(frozen=True)
class CollisionExportIssue:
    code: str
    message: str
    geom_id: int | None = None
    geom_name: str | None = None
    geom_type: str | None = None
    mjcf_body: str | None = None
    urdf_link: str | None = None

    def as_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class CollisionExportReport:
    source_urdf_revision: str
    source_mjcf_revision: str
    source_collision_count: int
    output_collision_count: int
    geometry_counts: dict[str, int]
    expanded_capsules: int
    issues: tuple[CollisionExportIssue, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            **dataclasses.asdict(self),
            "issues": [issue.as_dict() for issue in self.issues],
        }


@dataclasses.dataclass(frozen=True)
class UrdfCollisionExport:
    filename: str
    content: bytes
    report: CollisionExportReport


class UrdfCollisionExportError(AssetError):
    def __init__(self, message: str, report: CollisionExportReport):
        super().__init__(message)
        self.report = report
```

Define the public function with this exact signature:
`export_urdf_with_mjcf_collisions(variant: Variant, mjcf_path: Path, *,
edition_id: str, asset_root: Path) -> UrdfCollisionExport`. Steps 4 through 7
define its complete implementation.

Re-export all five names from `menagerie_x.assets` and include them in `__all__`.

- [ ] **Step 4: Implement compiled MJCF selection and fail-closed validation**

Inside the new module:

```python
SUPPORTED_MJCF_GEOMS = {
    mujoco.mjtGeom.mjGEOM_BOX: "box",
    mujoco.mjtGeom.mjGEOM_SPHERE: "sphere",
    mujoco.mjtGeom.mjGEOM_CYLINDER: "cylinder",
    mujoco.mjtGeom.mjGEOM_CAPSULE: "capsule",
}
FRAME_TRANSLATION_TOLERANCE = 1e-6
FRAME_ROTATION_TOLERANCE = 1e-6
```

Resolve both inputs beneath `asset_root`; require `variant.urdf` to exist; reject `<include>` before compilation; compile with `mujoco.MjModel.from_xml_path`; and select every geom where compiled `geom_contype[id] != 0 or geom_conaffinity[id] != 0`.

For each selected geom, obtain the compiled owning body name, type, size, local position, and local quaternion. Aggregate an issue for world geoms, missing or duplicate URDF links, unnamed/unmapped bodies, unsupported geom types, non-finite dimensions, and paths escaping the registered asset root. Raise one `UrdfCollisionExportError` containing every issue.

- [ ] **Step 5: Implement zero-pose frame verification**

Build root-relative zero-pose transforms for named MJCF bodies and URDF links. Exclude MJCF world placement and the free joint. Compare same-named body/link transforms before using the compiled geom-local pose:

```python
translation_error = math.sqrt(sum((mjcf_position[i] - urdf_position[i]) ** 2 for i in range(3)))
relative_rotation = _matrix_multiply(_matrix_transpose(mjcf_rotation), urdf_rotation)
trace = relative_rotation[0][0] + relative_rotation[1][1] + relative_rotation[2][2]
rotation_error = math.acos(max(-1.0, min(1.0, (trace - 1) / 2)))
```

Use ordinary Python matrix helpers; do not add NumPy as a dependency. Emit
`frame-mismatch` when either error exceeds its tolerance.

- [ ] **Step 6: Implement deterministic primitive conversion and naming**

Use compiled sizes and local poses. Normalize finite floats with `format(value, ".12g")`, converting `-0` to `0`. Serialize capsule parts in this order:

```python
parts = [
    ("cylinder", center, rotation, {"radius": radius, "length": 2 * half_length}),
    ("sphere", center - rotation_z * half_length, identity, {"radius": radius}),
    ("sphere", center + rotation_z * half_length, identity, {"radius": radius}),
]
```

Normalize a source name ending in `_collision1` to `_collision_1`. For a capsule named `<stem>_collision_<n>`, emit:

```text
<stem>_<n>_cylinder_collision_1
<stem>_<n>_sphere_collision_1
<stem>_<n>_sphere_collision_2
```

For an absent name, use `<body>_<shape>_collision_<geom_id + 1>` as the deterministic source identity. Reject duplicate output names.

- [ ] **Step 7: Replace collision elements while preserving non-collision semantics**

Parse the canonical URDF with comments enabled:

```python
parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
urdf_root = ET.fromstring(variant.urdf.read_bytes(), parser=parser)
```

Remove only direct `collision` children from each `link`, append converted collisions in URDF link order and compiled geom order, indent deterministically, and encode UTF-8 XML. Set the filename to:

```python
f"{variant.name}-{edition_id}-collisions.urdf"
```

Return the completed report only after the entire output is generated in memory.

- [ ] **Step 8: Add preservation, blocker, and Astro reference tests**

Add tests that:

- compare collision-stripped semantic XML for the source and output;
- prove comments, `<mujoco>`, links, joints, inertials, visuals, materials, limits, and mesh filenames remain;
- aggregate unsupported mesh, plane, unnamed body, missing link, frame mismatch, and `<include>` issues;
- leave source URDF and MJCF SHA-256 values unchanged;
- export Astro V2 as 125 collisions with 46 cylinders, 79 spheres, and zero mesh/custom capsule elements; and
- report 47 source geoms and 39 expanded capsules.

- [ ] **Step 9: Run focused and package tests**

Run:

```bash
UV_CACHE_DIR=/tmp/menagerie-x-urdf-export-cache uv run python -m unittest tests.test_urdf_collision_export tests.test_description_package -v
```

Expected: all tests pass.

- [ ] **Step 10: Commit the deep module**

```bash
git add src/menagerie_x/assets/urdf_collision_export.py src/menagerie_x/assets/__init__.py tests/test_urdf_collision_export.py
git commit -m "feat(assets): export MJCF collisions as standard URDF"
```

### Task 2: Serve a non-destructive URDF attachment

**Files:**
- Modify: `src/menagerie_x/workbench/server.py`
- Modify: `tests/test_workbench.py`

**Interfaces:**
- Consumes: Task 1's `export_urdf_with_mjcf_collisions(...)` and `UrdfCollisionExportError`.
- Produces: `GET /api/robots/{variant}/editions/{edition}/export-urdf`.
- Produces: XML attachment on success and structured JSON with HTTP 422 on representability failure.

- [ ] **Step 1: Write failing endpoint tests**

Add `WorkbenchUrdfExportEndpointTests` with this successful contract:

```python
status, headers, body = self._get_raw(
    "/api/robots/astro_v2/editions/astro_v2_primitive_collision/export-urdf"
)
self.assertEqual(status, 200)
self.assertEqual(headers["Content-Type"], "application/xml; charset=utf-8")
self.assertIn('filename="astro_v2-astro_v2_primitive_collision-collisions.urdf"', headers["Content-Disposition"])
self.assertEqual(headers["X-Menagerie-MJCF-Collision-Count"], "47")
self.assertEqual(headers["X-Menagerie-URDF-Collision-Count"], "125")
self.assertEqual(len(ET.fromstring(body).findall(".//collision")), 125)
```

Also assert: `soma23` returns 422 with `urdf-unavailable`; G1 returns 422 listing every unsupported contact mesh; unknown or traversal-like editions return 404; and source hashes do not change.

- [ ] **Step 2: Run endpoint tests and confirm RED**

```bash
UV_CACHE_DIR=/tmp/menagerie-x-urdf-export-cache uv run python -m unittest tests.test_workbench.WorkbenchUrdfExportEndpointTests -v
```

Expected: 404 for the missing export route.

- [ ] **Step 3: Extend `_send` with explicit response headers**

Change the helper without altering existing callers:

```python
def _send(
    self,
    status: HTTPStatus,
    content: bytes,
    content_type: str,
    headers: dict[str, str] | None = None,
) -> None:
    self.send_response(status.value)
    self.send_header("Content-Type", content_type)
    self.send_header("Content-Length", str(len(content)))
    self.send_header("Cache-Control", "no-store")
    for name, value in (headers or {}).items():
        self.send_header(name, value)
    self.end_headers()
    self.wfile.write(content)
```

Retain the existing broken-pipe handling.

- [ ] **Step 4: Add the export route and structured failure mapping**

In `do_GET`, after resolving the variant and edition, call:

```python
result = export_urdf_with_mjcf_collisions(
    variant,
    source,
    edition_id=edition_id,
    asset_root=self.asset_root,
)
self._send(
    HTTPStatus.OK,
    result.content,
    "application/xml; charset=utf-8",
    {
        "Content-Disposition": f'attachment; filename="{result.filename}"',
        "X-Menagerie-MJCF-Collision-Count": str(result.report.source_collision_count),
        "X-Menagerie-URDF-Collision-Count": str(result.report.output_collision_count),
    },
)
```

Catch `UrdfCollisionExportError` before the broad `AssetError` branch and return:

```python
{
    "ok": False,
    "error": str(exc),
    "report": exc.report.as_dict(),
}
```

with HTTP 422. Do not add a loopback-only restriction or accept a request body.

- [ ] **Step 5: Run endpoint and Workbench regression tests**

```bash
UV_CACHE_DIR=/tmp/menagerie-x-urdf-export-cache uv run python -m unittest tests.test_workbench.WorkbenchUrdfExportEndpointTests tests.test_workbench.WorkbenchTests -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit the HTTP adapter**

```bash
git add src/menagerie_x/workbench/server.py tests/test_workbench.py
git commit -m "feat(workbench): serve URDF collision downloads"
```

### Task 3: Add the left-panel Export URDF action

**Files:**
- Create: `src/menagerie_x/workbench/web/urdf-export.js`
- Create: `src/menagerie_x/workbench/web/urdf-export.test.js`
- Modify: `src/menagerie_x/workbench/web/index.html`
- Modify: `src/menagerie_x/workbench/web/app.js`
- Modify: `src/menagerie_x/workbench/web/styles.css`
- Modify: `tests/test_workbench.py`

**Interfaces:**
- Consumes: Task 2's attachment endpoint and response headers.
- Produces: `requestUrdfExport(fetchImpl, url) -> Promise<UrdfDownload>` in `urdf-export.js`.
- Produces: `downloadUrdf(documentRef, urlApi, download)` for a transient Blob URL.
- Produces: a left-panel `#export-urdf` button and `#urdf-export-status` live region.

- [ ] **Step 1: Write failing JavaScript helper tests**

Cover successful metadata parsing and structured 422 failures:

```javascript
function responseStub({ status, body, headers }) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Unprocessable Entity",
    headers: new Headers(headers),
    blob: async () => new Blob([body], { type: "application/xml" }),
    json: async () => JSON.parse(body),
  };
}

test("returns a URDF download with server counts", async () => {
  const result = await requestUrdfExport(async () => responseStub({
    status: 200,
    body: "<robot name=\"astro_v2\"/>",
    headers: {
      "content-disposition": 'attachment; filename="astro_v2-reviewed-collisions.urdf"',
      "x-menagerie-mjcf-collision-count": "47",
      "x-menagerie-urdf-collision-count": "125",
    },
  }), "/export");
  assert.equal(result.filename, "astro_v2-reviewed-collisions.urdf");
  assert.equal(result.sourceCollisionCount, 47);
  assert.equal(result.outputCollisionCount, 125);
});
```

Also verify object-URL revocation and that every 422 issue message is retained in the thrown `UrdfExportRequestError`.

- [ ] **Step 2: Run the Node test and confirm RED**

```bash
node --test src/menagerie_x/workbench/web/urdf-export.test.js
```

Expected: module-not-found failure.

- [ ] **Step 3: Implement the browser download helper**

Export these exact names:

```javascript
export class UrdfExportRequestError extends Error {
  constructor(message, report = null) {
    super(message);
    this.name = "UrdfExportRequestError";
    this.report = report;
  }
}

export async function requestUrdfExport(fetchImpl, url) {
  const response = await fetchImpl(url, { cache: "no-store" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: response.statusText, report: null }));
    throw new UrdfExportRequestError(payload.error || "URDF export failed", payload.report || null);
  }
  const disposition = response.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="([^"/\\]+\.urdf)"/i);
  const sourceCollisionCount = Number(response.headers.get("x-menagerie-mjcf-collision-count"));
  const outputCollisionCount = Number(response.headers.get("x-menagerie-urdf-collision-count"));
  if (!match || !Number.isInteger(sourceCollisionCount) || !Number.isInteger(outputCollisionCount)) {
    throw new UrdfExportRequestError("URDF export response metadata is invalid");
  }
  return { filename: match[1], blob: await response.blob(), sourceCollisionCount, outputCollisionCount };
}

export function downloadUrdf(documentRef, urlApi, download) {
  const objectUrl = urlApi.createObjectURL(download.blob);
  try {
    const anchor = documentRef.createElement("a");
    anchor.href = objectUrl;
    anchor.download = download.filename;
    documentRef.body.append(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    urlApi.revokeObjectURL(objectUrl);
  }
}
```

Require an attachment filename ending in `.urdf`, parse integer count headers, parse JSON on 422, and throw a clear error for malformed success metadata.

- [ ] **Step 4: Add accessible left-panel markup and styling**

Inside `.menagerie-actions`, add:

```html
<button id="export-urdf" type="button" disabled>Export URDF</button>
```

Immediately after the actions add:

```html
<p id="urdf-export-status" class="urdf-export-status" aria-live="polite"></p>
```

Make `.menagerie-actions` a three-column grid that stacks at the existing narrow breakpoint. Style the status as compact secondary text and `.error` with the existing danger color.

- [ ] **Step 5: Wire selection, busy state, saved-edition confirmation, and status**

In `app.js`, import the helper and add:

```javascript
let urdfExportBusy = false;

function updateUrdfExportControl() {
  const available = Boolean(activeRobot && activeEdition && activeRobot.formats?.urdf);
  exportUrdfButton.disabled = urdfExportBusy || !available;
  exportUrdfButton.title = !activeRobot
    ? "Select a robot variant"
    : !activeEdition
      ? "Select a saved MJCF edition"
      : !activeRobot.formats?.urdf
        ? "This variant has no canonical URDF"
        : "Download a URDF using collisions from the selected saved MJCF edition";
}
```

Call it after catalog, robot, edition, and busy-state changes. `exportSelectedUrdf()` must confirm when `collisionDraftHasChanges()` is true, request `${editionBase()}/export-urdf`, download the result, and display:

```text
Downloaded <filename>: <source> MJCF geoms → <output> URDF collisions.
```

Render every structured issue on failure. Do not save the draft, refresh the catalog, or touch collision-editor state.

- [ ] **Step 6: Add static integration assertions**

In `tests/test_workbench.py`, assert the button and live region are in the left menagerie panel, the helper module is imported, the edition URL is used, the dirty-draft confirmation mentions the saved edition, and the collision-editor module remains unchanged by this commit.

- [ ] **Step 7: Run browser and Workbench UI tests**

```bash
node --test src/menagerie_x/workbench/web/urdf-export.test.js src/menagerie_x/workbench/web/collision-editor.test.js src/menagerie_x/workbench/web/mujoco-visualization.test.js src/menagerie_x/workbench/web/scene-recording.test.js
node --check src/menagerie_x/workbench/web/app.js
UV_CACHE_DIR=/tmp/menagerie-x-urdf-export-cache uv run python -m unittest tests.test_workbench -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit the Workbench action**

```bash
git add src/menagerie_x/workbench/web/urdf-export.js src/menagerie_x/workbench/web/urdf-export.test.js src/menagerie_x/workbench/web/index.html src/menagerie_x/workbench/web/app.js src/menagerie_x/workbench/web/styles.css tests/test_workbench.py
git commit -m "feat(workbench): add Export URDF action"
```

### Task 4: Document and verify the complete feature

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the completed assets module, endpoint, and left-panel action.
- Produces: user-facing documentation and final verification evidence.

- [ ] **Step 1: Document exact version-one behavior**

Add a concise Workbench paragraph stating:

```text
Export URDF transfers standard primitive collisions from the selected saved MJCF edition into a downloaded copy of the variant's canonical URDF. It never overwrites catalog files, excludes unsaved collision-draft edits, and blocks the download when a collision cannot be represented safely. Version one requires an existing canonical URDF and does not convert MJCF-only robots or mesh collisions.
```

- [ ] **Step 2: Run final automated verification**

```bash
git diff --check
UV_CACHE_DIR=/tmp/menagerie-x-urdf-export-cache uv run python -m unittest discover -s tests -v
node --test src/menagerie_x/workbench/web/urdf-export.test.js src/menagerie_x/workbench/web/collision-editor.test.js src/menagerie_x/workbench/web/mujoco-visualization.test.js src/menagerie_x/workbench/web/scene-recording.test.js
node --check src/menagerie_x/workbench/web/app.js
UV_CACHE_DIR=/tmp/menagerie-x-urdf-export-cache uv run menagerie_x --root . validate
UV_CACHE_DIR=/tmp/menagerie-x-urdf-export-cache uv run menagerie_x --root . mujoco --variant astro_v2 --check
UV_CACHE_DIR=/tmp/menagerie-x-urdf-export-cache uv build
```

Expected: all tests and commands pass. If the ordinary full suite cannot create a GL context, rerun only that graphical boundary with `MUJOCO_GL=egl` and report the environment limitation separately.

- [ ] **Step 3: Run the manual Workbench smoke**

Start Workbench, select `astro_v2`, select `astro_v2_primitive_collision`, choose **Export URDF**, and verify:

- the filename is `astro_v2-astro_v2_primitive_collision-collisions.urdf`;
- status reports `47 MJCF geoms → 125 URDF collisions`;
- the downloaded XML contains 125 standard collision elements;
- a dirty collision draft triggers the saved-edition confirmation; and
- no repository file changes after either export.

- [ ] **Step 4: Commit the documentation**

```bash
git add README.md
git commit -m "docs: describe URDF collision export"
```

- [ ] **Step 5: Record final repository state**

```bash
git status --short
git log --oneline -4
```

Expected: a clean feature worktree with four scoped local commits and no remote changes.
