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
  runtime links are checked separately below.

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

## Branch review

Matt's code-review skill will review the committed branch against the fixed
baseline on independent Standards and Spec axes. Findings and fixes must be
recorded here before the local merge.
