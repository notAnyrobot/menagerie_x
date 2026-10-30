# Astro wrist redundancy and rounded hand refinement

Historical receipt: the full-hand envelope below was rejected as too large.
The current accepted collider is palm-only, with fingers/thumb intentionally
outside; see [the palm correction](design/astro-p2-simplified-collisions.md#accepted-palm-only-correction).
Current checks are recorded in [the compact palm receipt](astro-palm-collision-verification.md).

Implementation: `4716da7`, branch `codex/astro-wrist-hand-refinement`.
Baseline: `10fcf7edccd61611679601274064f034887baca6`.
Scope: [accepted wrist/hand refinement](design/astro-p2-simplified-collisions.md#accepted-wrist-and-hand-refinement).
Robot geometry and scene/previews were implemented by separate subagents.

## Geometry changes

- Removed both standalone wrist-roll collision capsules. The forearm endpoint
  extends from local x=0.075 to 0.09 m, keeping radius 0.054 m. Together with
  the wrist-pitch capsule's proximal sphere, it covers the removed shell
  independently of wrist rotation. An axial cross-section check gives a minimum
  union margin of **0.218 mm**; twelve articulated-pose checks also passed.
- Wrist joints and independent pitch/yaw motion remain intact. The hand proxy
  stays on wrist yaw; no independently moving links were welded together.
- Replaced the thin hand shaft with a rounder capsule inspired by G1 box-feet's
  hand shape, fitted to Astro rather than copying G1 dimensions. Radius is
  **0.06 m**, centerline x=0.065–0.165 m, z=0.014 m, and mirrored y=±0.004 m.
- The centerline shortens from 118 to 100 mm. Overall axial extent grows from
  178 to 220 mm because the original proxy missed actual fingers and thumb.
  All **4,611 left / 4,914 right hand mesh vertices** are now inside the proxy,
  compared with 54.96% / 53.79% before. Minimum vertex margin is approximately
  **1.65 mm**. This is a geometric fit, not hardware-contact calibration.

The model now has **50 colliders: 40 unchanged non-arm shapes and 10 arm
capsules**. Only six robot geoms were removed/edited: two wrist-roll removals,
two forearm endpoint changes, and two hand fits. All other XML definitions,
37 visual geoms, 21 compiled physical/mesh arrays and 29 option fields match
the preserved source. Mass remains 40.58255359 kg; `nq=36`, `nv=35`, `nu=0`.
All 111 protected existing Astro runtime/asset/source files retain their hashes.

## Contacts and native verification

Removed exactly ten scene pairs referring to the deleted wrist-roll geoms.
All remaining pair attributes are unchanged: **68 pairs, 10 arm-floor and
58 selected self-contact**. Original non-arm automatic contacts, detailed feet,
floor datum and contact parameters remain intact.

Reference and tested wrist/mixed poses had zero contacts. A positive selected
hand/torso probe, explicit hand-floor probe and disabled unlisted hand/foot
overlap check passed. Ground-contact parity with the original model held in
three leg poses; grounded native stepping stayed finite without warnings.

The fuller hand envelope intentionally changes some folded-arm contacts:
elbows at 1.2 rad produce selected hand/hip contacts, approximately 3.38 mm deep,
that the earlier under-covering proxy missed. This is documented in the family
README rather than hidden by dropping those pairs. Controllers and complete
trajectory equivalence are not claimed.

`UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passed **17 test methods**.
The added checks cover removed-shell union coverage across wrist pitch and
containment of actual hand mesh vertices. After the review's test-only helper
cleanup, all **seven arm collision tests** passed again. No model/scene changes
followed the full native acceptance run.

Updated and inspected the native whole-body collider preview and a new
[wrist/hand overlay](../astro_p2/provenance/retired_simplified/astro_p2_wrist_hand_colliders.png). The overlay
uses temporary transparency to show the unchanged hand mesh inside its collider;
render settings do not change saved materials or physics. Images use reference
initialization without simulation stepping. Checked 72 local document/image
links and `git diff --check` successfully.

## Source archive

`/tmp/menagerie-x-astro-wrist-hand-dist/menagerie_x-0.1.0.tar.gz`
(69,351,540 bytes) was built before the test-only review cleanup and this note.
All **20 native model/scene entry points** loaded from a fresh extraction.
Revised XML, provenance and both collider previews matched checkout bytes;
local experiment archives and floating scratch XML were excluded.

SHA-256:

```text
926e06c5c0d3d71d08354b9045c7d90ffb904244d4b6be5c5e99197eec18d1fa
```

## Standards

Initial review found no hard violations and one P3 judgment call: duplicated
point-to-capsule distance calculations in the two new tests. Extracted the
shared private `_capsule_surface_distances` helper; the reviewer confirmed
both call sites preserve the original calculations/tolerance and the finding
is resolved. Native XML/provenance repetition follows repository conventions.

Standards: **0 remaining findings**; worst remaining issue: none.

## Spec

No actionable Spec findings. Independent review confirmed the intended geometry
changes, preservation of physical/visual definitions, removal of only the ten
obsolete contact pairs, accepted scope and close-up evidence.

Spec: **0 findings**; worst issue: none.

Review summary: Standards **0 remaining**, worst **none**; Spec **0**, worst
**none**. MJX runtime, controller work, Workbench and URDF compatibility remain
deferred. No runtime speedup is claimed from shape-count reduction alone.
