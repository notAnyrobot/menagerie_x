# Simplified native refactor verification

Baseline: `27d9e7c0f3d58961f97af8cdb03acffa6b07a878` (local `main`).
Implementation branch: `codex/native-menagerie-refactor`.
Reference: MuJoCo Menagerie `f3b6013629c7b94f8ee93fd977b161fa8350f9bc`.
Scope: the simplified native target in ADR 0011. Workbench, URDF compatibility,
and MJX are deferred.

## Acceptance evidence

Verified on 2026-10-30 with native MuJoCo 3.11.0 (local CPython 3.13.12;
CI is configured for Python 3.12):

- `UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all`: native layout/style checks
  and load/simulation/portability checks pass.
- All 11 declared robot models and all 11 scenes compile. Each steps for at
  least 0.1 seconds with deterministic Halton actuator inputs, finite positions
  and velocities, and no MuJoCo warnings. Existing scene keyframes reset and
  forward successfully; keyframes are selected explicitly.
- All seven family runtime folders load when copied into temporary directories
  containing only their declared XML, assets, and local mesh alias. No legacy
  manifest, application code, source snapshots, or other families are copied.
- SHA-256 comparison against the pre-edit branch baseline confirms **377
  existing family asset/source files are unchanged**, including every original
  XML, URDF, mesh, image, JSON/YAML provenance record, and license notice.
- All **5,302 compiled NumPy arrays across the 11 native robot models** exactly
  match the pre-edit native baseline. No physical parameter or keyframe was
  changed. The permanent suite also compares nine canonical models with the
  retained import snapshots, excluding the legacy G1 presentation plane.
- `git diff --check` passes. Native source-distribution contents and relative
  runtime links also passed the source-archive check below.

The temporary hash/compiled-array snapshots are validation artifacts under
`/tmp`, not a new runtime metadata or revision system.

## Deliberate changes and limits

The new Astro 29 scene includes its existing MJCF unchanged, with one floor at
`z=-0.75`. The separate legacy application manifest remains URDF-only for that
edition. The native catalog is now an explicit upstream-style model/preview map,
independent of that manifest. Nested imports are retained as source evidence;
the mirror generator and tests for its removed behavior are retired.

Native tests live under `test/`. Application code and the remaining application
tests under `tests/` are preserved but are not this phase's merge gate. Browser
include/mesh loading, editor save targets, URDF parity, and MJX were not certified
by these native checks. Short stepping is not a stable controller, hardware
fidelity, or exhaustive contact-quality test.

## Source archive

`UV_CACHE_DIR=/tmp/menagerie-x-uv-cache uv build --sdist --out-dir
/tmp/menagerie-x-native-dist` succeeds. The extracted source archive loads all
22 native model/scene entry points. Relative runtime aliases are retained;
local floating-MJCF files, `.local/`, and `retargeting/` experiments are excluded.

## Branch review

Reviewed commit: `93f884c` on `codex/native-menagerie-refactor`.
Fixed baseline: `27d9e7c0f3d58961f97af8cdb03acffa6b07a878`.
Diff command: `git diff 27d9e7c0f3d58961f97af8cdb03acffa6b07a878...HEAD`.
The originating spec is ADR 0011 and the simplified implementation outline.
Two independent fresh-context subagents used
[Matt's code-review skill](/home/android/.codex/plugins/cache/mattpocock/mattpocock-skills/1.3.2/skills/engineering/code-review/SKILL.md).
Both axes found no actionable issues, so no corrective code change was needed.
The review did not reinstate any deferred compatibility requirement.

## Standards

No actionable Standards findings.

The diff follows `CONTRIBUTING.md` and `UPSTREAM.md`: native XML is directly
maintained, scenes include sibling models, original assets/source XML remain
unchanged, family changelogs document the migration, and native validation is
independent of deferred application compatibility.

No baseline smells warrant changes. Explicit catalog maps and repeated family
documentation follow the repository's stated upstream alignment and
standalone-family conventions.

Read-only verification: inspected the implementation, removed generator/tests,
family documentation, and pinned upstream catalog structure;
`git diff --check` passes.

Standards: **0 documented-standard violations; 0 actionable judgement-call
findings.**

## Spec

No actionable Spec findings.

The diff implements the simplified target: directly maintained family-root XML,
explicit upstream-style native catalog, independent scene includes, relative
family-local dependencies, and retirement of mirror regeneration. Astro 29's
existing MJCF is explicitly inventoried with a new scene; its legacy URDF-only
manifest entry remains unchanged.

The reviewer independently ran
`UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all`: all five tests passed,
covering all 11 models and 11 scenes, short simulation, keyframe reset,
copied-family portability, and comparisons against retained imports. The family
diff confirms existing XML, meshes, URDFs, provenance, and notices remain
unchanged. Application code and the legacy manifest are unchanged; Workbench,
URDF compatibility, and MJX remain deferred.

No missing or partial requirements, unasked scope expansion, or incorrectly
implemented requirements identified.

Review totals: **Standards 0 findings (worst: none); Spec 0 findings (worst: none).**
