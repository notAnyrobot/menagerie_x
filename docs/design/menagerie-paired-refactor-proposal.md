---
status: implemented
---

# Align Menagerie X with MuJoCo Menagerie's native asset structure

This implemented outline follows the user's 2026-10-30 scope clarification
and [ADR 0011](../adr/0011-upstream-asset-structure-first.md). The primary goal
is close native asset alignment. Workbench and URDF incompatibilities are
acceptable during this refactor. MJX remains deferred.

## Target structure

Use the ordinary upstream pattern for the seven existing robot families:

```text
<robot-family>/
  <model>.xml
  <alternate-model>.xml       # where an existing model choice needs it
  scene.xml
  scene_<choice>.xml          # where an additional scene is useful
  assets/                    # actual relative mesh/texture dependencies
  README.md
  CHANGELOG.md
  LICENSE* / LICENSING.md     # retained actual notices and provenance status
  ...                        # retained URDFs/source records where present
```

The maintained model and scene XML are the actual runtime inputs. A scene
includes its model; shared local XML fragments are permitted when useful.
Model variants share local assets. Native MuJoCo can load the folder without
Menagerie X's application, global manifest, or a custom per-family schema.
Keep current model filenames where practical; preserving the physical model
and clear native entry points matters more than renaming files for symmetry.

Do not add `family.json`. Upstream G1/T1 use XML and documentation for per-robot
setup; upstream root `catalog.py` supplies curated catalog metadata, and
package tooling derives its registry. Existing Menagerie X application
metadata can remain legacy material or receive minimal updates where useful;
it does not become the authority for native XML behavior.

## Implementation outline

1. Create a dedicated branch from the current checkout, following the already
   selected current-repository route. Use upstream revision
   `f3b6013629c7b94f8ee93fd977b161fa8350f9bc` as the reference.
2. Inventory the current seven families, runtime models, source records, and
   user-local files. Preserve physical parameters, original evidence, notices,
   and user work.
3. Make directly maintained family-root model/scene XML canonical. Remove the
   requirement to regenerate flat mirrors from nested editable MJCF sources;
   preserve the previous source material separately where needed.
4. Make each declared native model/scene dependency set portable and relative.
   Keep robot and environment ownership clear, preserving actual model-specific
   contacts, solver settings, controls, and keyframes.
5. Apply upstream XML/documentation conventions and native model/scene checks.
   Update small catalog/tooling pieces only when needed for this asset target.
6. Record known Workbench, URDF, and old-path incompatibilities. Preserve their
   existing files and code; repair the consumers in a separate follow-up.

The G1/T1 investigations are references for organization and native ownership,
not permission to substitute their gains, inertias, contacts, or control
interfaces for the local models. Astro 29's existing separate MJCF conversion
and URDF-only catalog status must be inventoried explicitly; avoid deleting
or silently replacing either artifact during migration.

## Native validation and review

- Enumerate the retained robot/model choices and confirm no unrelated upstream
  production robots were added.
- Load every declared native model and scene with the pinned native MuJoCo
  runtime; run upstream-style short simulation checks for scenes.
- Copy each family elsewhere and compile its entry points without another
  family or the Menagerie X application.
- Compare robot physics against the preserved baseline; account explicitly
  for model/scene environment separation and documented pose selection.
- Review XML, documentation, licenses/provenance, and any intended path changes.
- Review the implementation branch before merging.

Workbench/browser parity, lossless authoring overlays, promotion systems,
reproducible revision storage, URDF preview frameworks, and native/WASM parity
are not acceptance gates for this phase. Existing URDF/application material is
preserved, not promised to remain compatible and not discarded.

## Research references

- [Upstream native contract](../research/mujoco-upstream-contract.md).
- [Detailed G1/T1 setup](../research/mujoco-per-robot-structure.md).
- [Route comparison](../research/mujoco-refactor-options.md).
- [Known application incompatibilities](../research/mujoco-workbench-compatibility.md).

The earlier application-heavy proposal has been superseded by this outline.
Remaining discussion should concern genuine ambiguities in the native robot
asset structure, not new requirements for deferred application compatibility.

## Implemented disposition

The maintained root XML files are now the native authority. All existing XML
and asset bytes were retained; nested imports are documented as snapshots and
the regeneration script is removed. Root `catalog.py` explicitly curates the
11 existing MJCFs and scenes, including Astro 29's separately maintained
conversion. Its new scene does not change the legacy URDF-only app entry.
Native tests live under `test/`; `tests/` retains deferred application tests.
See [verification](../native-refactor-verification.md).
