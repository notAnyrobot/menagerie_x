# Astro P2 consolidation verification

Baseline: `fcbb3f222359df8b275fee1bc79d47721efdd2ec`.
Branch: `codex/astro-p2-variants`.
Scope: [Astro P2 variants](design/astro-p2-variants.md).

## Delegated work

The rubber-hand agent verified official Unitree sources, produced the new
native model, and recorded [source findings](research/astro-g1-rubber-hand-adoption.md).
A separate consolidation agent moved tracked sources and deduplicated meshes.
An independent inventory agent checked the native catalog, packaging, retirement
boundary, and verification requirements. Main integrated the findings and tests.

## Native checks

On 2026-10-30, `UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passes with
MuJoCo 3.11.0: eight test methods cover eight model/scene pairs (six active and
two legacy P1). All models/scenes compile and step for 0.1 seconds with finite
positions/velocities and no warnings. Existing keyframes reset and forward.
All five retained family runtime bundles load independently after copying only
the declared native XML, assets, and local mesh alias.

The rubber variant has `nq=36`, `nv=35`, `nu=0`, mass **40.64356917 kg**.
The Dex3-1 variant has `nq=50`, `nv=49`, `nu=0`, mass **41.69666115 kg**.
Named common-body comparisons preserve 38 non-hand bodies, 93 non-hand geoms,
and all 30 body joints including the free base. Damping, armature, and friction
remain unchanged for all 35 body velocity coordinates. Finger count, fixed head,
source mesh hashes, full hand inertia/COM, collision capsule transforms, and
hand mass accounting are checked explicitly.

The consolidated Dex model exactly preserves all 476 non-name compiled arrays
from the pre-consolidation source, including its finger definitions and `fist`
keyframe. Only model-label/name-address metadata changes with its new name.

## Source and user-work preservation

All 40 files in `astro_p2/provenance/migration.json` match their original SHA-256.
Shared mesh names were deduplicated only after verifying identical bytes; there
were no conflicting mesh names. Original source documents retain their bytes
and historical paths rather than pretending to be current runtime models.

SHA-256 comparison confirms all **501 preexisting untracked user files remain
unchanged**. Old Astro directories may remain on disk because those experiments
were preserved. They are outside the tracked native inventory and archive.
Active documentation checks validate **119 local links and anchors**. Both
new Astro previews were rendered from native scenes and visually inspected.
`git diff --check` passes.

## Source archive

The rebuilt source archive loads all sixteen retained native model/scene
entry points after extraction. All preview images, source hashes, and family
mesh aliases are intact. The old Astro roots, retired 30-DoF models, and local
floating-model experiments are absent. The archive is approximately 65.3 MiB.

## Independent branch review

Two fresh-context agents used Matt's code-review skill against baseline
`fcbb3f222359df8b275fee1bc79d47721efdd2ec`, reviewing commits `1ec1122` and
`23a35fc`. Diff command:
`git diff fcbb3f222359df8b275fee1bc79d47721efdd2ec...HEAD`.
Standards sources were CONTRIBUTING.md, UPSTREAM.md, README.md, and CONTEXT.md;
the originating spec was `docs/design/astro-p2-variants.md` and the user's request.
No actionable findings required code corrections.

## Standards

No actionable Standards findings.

The diff follows CONTRIBUTING.md's family-local runtime layout, direct XML
ownership, separate scenes, source preservation, and changelog requirements.
Catalog changes retain legacy P1 verification while separating the active
collection. License notices and provenance remain present.

No baseline code smells warrant a finding. The duplicated Astro body XML
follows the documented sibling-model convention in UPSTREAM.md; extracting a
shared generator would conflict with the repository's direct-maintenance
approach. Historical provenance paths and the narrow vendor CRLF exception
are intentional.

Standards: **0 findings**.

## Spec

No actionable Spec findings.

Missing or partial requirements: none found. Astro P1 remains legacy with both
native entries; all three 30-DoF P2 choices are retired; the consolidated family
provides the requested 29-body-DoF rubber-hand and 29+14-DoF Dex3-1 variants.

Unrequested behavior or scope creep: none found. Workbench, URDF compatibility,
and MJX remain deferred. The sample hand attachment is explicitly documented.

Incorrect implementation: none found. Independently checked all 16 native
model/scene XMLs compile and step without warnings; 40 retained source files
match baseline bytes; all 501 recorded untracked files remain unchanged;
rubber-hand mass, COM, and all six inertia components match the retained vendor
URDF. Dex compiled physical arrays match the baseline; the observed
size-metadata change corresponds to the renamed model.

Spec: **0 findings**.

Workbench, URDF compatibility, and MJX remain deferred. The sample hand mount
is explicit; these checks do not certify hardware fit, rubber deformation,
controller stability, or exhaustive dynamic contact quality.

Review totals: **Standards 0 findings (worst: none); Spec 0 findings (worst: none).**
