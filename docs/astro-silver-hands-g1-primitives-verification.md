# Astro silver hands and G1 primitive configuration: verification

Implementation: `2d10cd5` on `codex/astro-silver-hands-g1-primitives`.
Baseline: `main` at `ff684bc863f0089f76671fd1c25f6e12c0bb9b97`.
Scope: [accepted implementation](design/astro-silver-hands-g1-primitives.md).
Two subagents implemented the Astro and G1 changes independently; the main
session integrated catalog, gallery, metadata, tests and documentation.

## Astro presentation

- Public label and image alt text: **Astro P2 with hands**. Dex3-1 remains
  identified in technical provenance and licensing.
- All 16 articulated hand visual geoms use silver RGBA
  `0.69804 0.69804 0.69804 1`. The gold torso and other body colors are retained.
- Compared 482 compiled arrays for the articulated Astro model before/after:
  only `geom_rgba` changed, exactly 16 hand visual rows. Mesh bytes, physics,
  contacts, keyframes and default Astro model remain unchanged.
- Refreshed and inspected the native 640×480 reference-pose preview. Collision
  overlays are hidden and no simulation stepping is used for the image.

## G1 equivalence and preservation

- `g1_mjx.xml`, `scene_mjx.xml`, `LICENSE.Menagerie` and all 35 referenced mesh
  assets match MuJoCo Menagerie revision
  `f3b6013629c7b94f8ee93fd977b161fa8350f9bc` byte-for-byte. Source/asset hashes
  are recorded in [family provenance](../unitree_g1/provenance/menagerie_mjx.json).
- Both model and scene match 481 compiled NumPy arrays and 29 option fields
  each against the pinned upstream checkout under MuJoCo 3.11.0.
- Robot: `nq=36`, `nv=35`, `nu=29`; 35 visual mesh geoms and 27 collision
  primitives (23 capsules, two spheres, two boxes).
- Scene: 49 explicit pairs (26 self-contact, 23 floor-contact), with `home` and
  `knees_bent` keyframes. Robot-only XML has zero contact masks and no pairs;
  use the scene for the complete interaction setup.
- Preserved upstream servos, physical parameters, solver settings and sensors.
  Neither existing G1 model was replaced or retuned. The two required uppercase
  rubber-hand asset filenames were added; existing lowercase assets remain.
- The native 640×480 preview uses `home` without stepping and was inspected.

Across all four preexisting Astro/G1 runtime models, 1,928 compiled arrays were
compared: only the articulated Astro visual RGBA array changed. All 307
preexisting tracked asset/provenance/nested-MJCF/URDF files retain their hashes.

## Native acceptance and source archive

`UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passed **10 test methods**:
two layout/style methods and eight model methods, including subtests for all
nine declared native pairs (seven active plus two legacy P1). Checks cover
loading, deterministic 0.1-second stepping without warnings, keyframe reset,
standalone family copies, retained-source physics, Astro source fidelity and
the new G1 primitive/contact/source-hash contract.

Additional G1 stepping probes checked default initialization and both scene
keyframes. Its family also loaded from a standalone runtime-only copy.

Built `/tmp/menagerie-x-g1-primitive-dist/menagerie_x-0.1.0.tar.gz`
(68,989,766 bytes). A fresh extraction loaded all **18 model/scene entry points**.
New G1 XML, notices, provenance, case-sensitive hand assets and preview, plus
the Astro XML/preview, matched the checkout bytes. Local experiment archives
and floating-model scratch files were excluded. This artifact was built from
the implementation before this verification note and the README count fix.

Archive SHA-256:

```text
c93d7244f265005cf5775aa7b77e10699fd0bec2c624ff1523a591fa947bc51a
```

Both previews were rendered by native MuJoCo with software EGL. Temporary
render options select visual geom groups and suppress software-driver shadow
artifacts; they do not modify saved model physics. Checked 103 local
documentation/image links and `git diff --check` successfully.

MJX/JAX/Warp device execution, throughput, training and hardware performance
were not tested. No new runtime dependency or Workbench/URDF compatibility
path was introduced. MJX runtime support remains deferred.

## Standards

No actionable documented-standard violations or baseline Fowler smells found
in `git diff main...HEAD` (`ff684bc` → `2d10cd5`).

Standards reviewed: `CONTRIBUTING.md`, `UPSTREAM.md`, `CONTEXT.md`, root
`README.md` / `LICENSING.md`, the Astro P2 and Unitree G1 family
READMEs/licensing records, and applicable ADRs including
`docs/adr/0011-upstream-asset-structure-first.md`. The native family layout,
local assets, preserved source evidence/notices, catalog entries, and family
changelogs follow those rules. Imported XML duplication/naming follows the
documented upstream-preservation policy and is therefore not a baseline-smell
finding. G1 robot, scene and notice match the pinned upstream bytes.

Standards: **0 findings** (0 hard violations, 0 judgment calls); worst issue: none.

## Spec

No missing or partial requirements, unrequested scope creep, or incorrect
implementation behavior found against the accepted implementation scope.
The reviewer independently confirmed exact upstream XML/license/35 asset
bytes, compiled model equivalence, and Astro XML edits restricted to silver
RGBA on 16 hand visuals. Both previews were inspected.

Spec: **0 findings**; worst issue: none.

The main session corrected the root README's unchanged introduction from six
to seven active models after the review flagged it separately. No runtime
changes followed native acceptance or independent review.

Review summary: Standards **0**, worst **none**; Spec **0**, worst **none**.
