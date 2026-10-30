# Canonical per-robot bundles: evolve Menagerie X or start from Menagerie?

> Scope update: the user subsequently prioritized close native Menagerie asset alignment and accepted Workbench/URDF incompatibilities. Application architecture and compatibility repairs discussed below are follow-up work, not requirements for this phase. See [ADR 0011](../adr/0011-upstream-asset-structure-first.md). MJX remains deferred.

Research date: 2026-10-30. Local implementation baseline, observed from
checkout HEAD: `27d9e7c0f3d58961f97af8cdb03acffa6b07a878`. It may not yet be
published remotely; local evidence links below use repository-relative paths
and inspected line anchors. Upstream source baseline:
[`f3b6013629c7b94f8ee93fd977b161fa8350f9bc`][U]. This is a proposal and
source investigation, not an implementation or approval to change branches.
Upstream files were read from the existing sparse checkout in
`/tmp/menagerie-upstream-research/checkout`; GitHub's fork documentation was
also retrieved. No shared browser was controlled. This route investigation
did not run model tests; existing tests are inspected evidence. Separately
delegated compatibility probes and upstream source findings are identified
below and do not imply that all upstream families were tested.

## Recommendation and what would change it

**Prefer evolving this repository to the accepted Menagerie structure, while
using pinned upstream source and checks as the reference.** The important
change is canonical model/scene ownership and a shared simulation interface,
not the ancestry of the Git repository. The current checkout already has
seven top-level families, family-local assets, ten robot MJCF entry points,
ten scenes, the upstream XML formatter, and adapted native checks. Its
remaining disagreement with the accepted design is substantive: most runtime
callers use nested MJCF sources and the browser assembles a different world.
Starting with upstream does not supply a replacement Workbench or remove
that adaptation work. Sources: [existing scaffold inventory][L-upstream],
[manifest][L-manifest], [native catalog][L-catalog],
[browser composition][L-browser-compose].

A clean pinned scaffold remains a defensible alternative when a **fresh
integration surface**, clearer ownership review, or an upstream-shaped
repository is worth the extra porting and history work. A literal GitHub fork
is justified when membership in the upstream fork network and contributing
changes back are product goals. Neither choice implies adopting upstream's
download package, release pipeline, all its robot models, MJX, or mjlab.
The report below compares these alternatives independently rather than
assuming that copying fewer old files means less work.

Accepted requirements are recorded in the local [glossary](../../GLOSSARY.md),
[ADR 0001](../adr/0001-canonical-per-robot-runtime-files.md),
[ADR 0002](../adr/0002-explicit-simulation-configurations.md),
[ADR 0003](../adr/0003-portable-robot-bundles.md), and
[decision log](../design/per-robot-design-decisions.md). They require directly
maintained family-root robot and scene files, the same authoritative files
for CLI and Workbench, an explicit model + scene + optional initial pose,
and independently portable runtime bundles. They do **not** settle metadata
placement, revision workflows, scene editing, URDF placement, compatibility
duration, or repository ancestry. Those remain proposals below.

The carried scope is seven families and 12 logical editions, retaining CLI,
Workbench, physical descriptions, controls, source evidence and provenance.
Astro 29 and P1 racket remain cataloged URDF-only descriptions unless a
separate decision changes that. MJX is deferred. There is no implicit mjlab
target. These constraints follow the [decision log](../design/per-robot-design-decisions.md)
and [current inventory][L-manifest].

## Four different meanings of “start from Menagerie”

| Route | Concrete meaning | History and upstream relationship | What it buys |
| --- | --- | --- | --- |
| A: evolve current repository | Migrate from the current commit on a new implementation branch, adopting the native paired structure | Preserve Menagerie X ancestry; retain pinned attribution for selected upstream files | Smallest integration delta and straightforward before/after review |
| B1: literal GitHub fork | Create a separate GitHub fork of upstream at the pin, prune unrelated working-tree content, then import the seven local bundles and application | Upstream ancestry and GitHub fork-network relationship; local history needs explicit preservation/import | Natural upstream comparison and contribution workflow; clean upstream starting tree |
| B2: pinned source scaffold | Copy an explicitly listed subset of upstream source into a clean staging tree or a replacement tree in the current repository, then integrate local bundles/tools | Attribution and pin retained; no GitHub fork relationship is implied | A deliberately small starting tree without inheriting release/package machinery |
| C: rewrite | Reimplement the catalog, CLI, Workbench and editing workflows against native bundles | New implementation regardless of whether its repository is a fork | Opportunity for a new product design, with the largest behavior-recreation burden |

A GitHub fork is a separate repository connected to upstream, with its own
settings and collaboration space; an ordinary branch remains in one
repository. Copying source files does not create that relationship. Source:
[GitHub fork reference][GH-forks]. Route B2 can preserve the current repository
history, so “clean source tree” and “discard history” are independent choices.
Route C is outside the recommended structural migration: preserving named
features while recreating them is more than moving to Menagerie's layout.

## Measured starting point and actual reusable material

Counts below were computed from `git ls-files` at the local baseline,
excluding symlink traversal and untracked work. Source-line counts are raw
physical lines, including comments and blank lines; they are **inventory, not
effort estimates or proof of quality**. Byte counts count tracked regular
files once, not transitive assets behind compatibility links.

| Local material | Measured inventory | Treatment in either route |
| --- | ---: | --- |
| Python implementation in `src/menagerie_x` | 20 files / 6,483 lines | Preserve behavior; reuse much implementation while replacing path, scene and metadata assumptions |
| Production browser JS/CSS/HTML | 14 files / 4,317 lines | Preserve rendering, editor and interaction behavior; redesign model/scene loading and initialization |
| Browser test files | 6 files / 363 lines | Retain applicable feature checks; add paired-scene and closure regressions |
| Python tests and fixtures | 19 files / 2,910 lines | Carry across behavior tests; replace assertions about obsolete paths and generated mirrors |
| Family regular files | 400 files / 190,788,936 bytes, about 182 MiB | Carry descriptions, meshes, licenses, provenance and review evidence; avoid substituting same-named upstream robots |
| Tracked authoring/scaffold scripts | 5 files / 617 lines | Remove the mirror generator after cutover; keep conversion/refinement/preview tools where their behavior is still wanted |
| Relative compatibility symlinks | 17 links | Evaluate separately from runtime portability and remove only after callers/packaging migrate |

The family inventory includes documentation and source/runtime copies, not
400 distinct physical descriptions. The manifest declares 12 logical
editions, ten with MJCF; nine of those MJCFs have a nested source plus a flat
generated copy, while Dex's source is already at the root. The separately
maintained Astro 29 conversion exists as a tracked file but is not a
cataloged MJCF. Sources: [manifest][L-manifest],
[catalog mapping][L-catalog], [generator][L-sync],
[Astro 29 MJCF notes][L-Astro29-mjcf].

The current upstream-derived substrate is small and already present:

| Upstream material | Current state | Marginal value of importing it again |
| --- | --- | --- |
| `format_xml.py` | 193 lines, byte-identical to the inspected pin (`cmp` succeeded) | None for a second identical copy; useful as the retained native XML formatter |
| `catalog.py` | Upstream 185 lines; local 64-line manifest adapter | Native category/preview shape is useful; neither the full upstream map nor the local source/mirror distinction is the desired authority |
| Native model/layout tests | Upstream two files, 208 lines; local adapted test 102 lines | Deterministic short stepping and layout checks already adopted; new paired-scene/portability checks still needed |
| Makefile/hooks/build CI | Local versions already integrate Python and browser checks | Clean upstream versions offer conventions, but need local application/dependency/test integration again |
| Scene pattern | Local generated scenes already include robot XML and add environment | Keep and maintain the resulting scenes directly; another template import is unnecessary |
| Upstream runtime package | Seven implementation files, 839 lines | Optional archive/cache/closure machinery; no Workbench, collision authoring, URDF renderer, or local provenance workflow |
| Other top-level Python tools | Upstream five files, 1,170 lines in total, including formatter, catalog, registry, gallery and aggregate licensing | Choose individually; gallery/release tooling is useful only if its corresponding product requirement is adopted |

Sources: [retained scaffold attribution][L-upstream],
[upstream formatter][U-format], [upstream catalog][U-catalog],
[model checks][U-model-test], [layout checks][U-layout-test],
[upstream package implementation][U-package], [upstream root][U].

This evidence does not imply that 10,800 application lines should remain
unchanged. It shows why an upstream reset is not a ready-made application
replacement. The strongest saving from Menagerie is **using its simple
portable file contract and proven native smoke-test pattern**, avoiding
inventing another public model format. Both routes obtain that saving.
Route B obtains a genuinely clean starting tree; Route A obtains the same
native contract with fewer files requiring re-integration.

## Upstream package, catalog and release coupling

The robot-folder contract is separable from upstream distribution machinery.
The upstream README describes robot XML + separate scene + local assets;
its Python package is a distinct consumer. Sources:
[upstream overview][U-readme], [package documentation][U-package-doc].

Copying the complete package and build pipeline would also inherit these
specific assumptions:

1. `build_registry.py` scans top-level XML that compiles, classifies a file as
   a scene when its stem contains `scene`, obtains default choices from
   `catalog.MODEL_MAP` and scene includes, and expects a detectable family
   `LICENSE`. It records family Git-tree object IDs, builds content-addressed
   archives, and refuses dirty model directories by default. It explicitly
   retains README, LICENSE, CHANGELOG and root patches beyond dependency
   closures. A bare URDF-only family does not become a robot registry entry
   through this XML discovery. Source: [registry builder][U-registry].
2. Runtime `Robot` metadata exposes entry points, one default model and one
   default scene, plus archive identity and size/checksum fields. This is not
   the local logical-edition/format/provenance/revision model, and does not
   encode the accepted full explicit simulation configuration with optional
   pose. Source: [registry module][U-runtime-registry].
3. The cache defaults to Google DeepMind's `releases/download/assets` URL;
   `MENAGERIE_ROOT` and `MENAGERIE_BASE_URL` permit local/alternative sources.
   The package metadata uses the `mujoco-menagerie` name, Google DeepMind
   identity and repository, and `mujoco>=3.2.0`, unlike the local pinned
   runtime. Sources: [cache module][U-cache], [package metadata][U-pyproject],
   [local package metadata][L-pyproject].
4. Release CI runs on main pushes, builds/uploads archives to a long-lived
   GitHub `assets` release, verifies downloads using that base URL, publishes
   to PyPI, and pushes version tags. The Makefile builds registries/archives
   and derives package version from the exact Git tag. Sources:
   [release workflow][U-release], [Makefile][U-make].
5. The layout checks require an exact family `LICENSE` filename and scenes
   for discovered model directories. Local licensing contains mixed source
   grants and unresolved records; preserving these facts needs a deliberate
   adaptation, not copying an unrelated grant or aggregate LICENSE. Sources:
   [layout tests][U-layout-test], [local licensing][L-licensing].

Therefore the minimal B scaffold should initially omit `python/`,
`build_registry.py`, `generate_gallery.py`, `regenerate_license.py`, upstream
release/live-preview workflows, gallery media, unrelated families and the
unrelated aggregate license. Retain license texts/headers for each actually
copied file. Retain upstream's native layout/test ideas, not a second
authoritative model registry. Selectively adopting its dependency-closure
implementation could be useful after checking its supported XML references;
it is a separate engineering choice, not a requirement to publish archives.

If remote archive delivery is later desired, budget a distinct design for
package naming, hosting, immutable archive identity, catalog compilation,
URDF/provenance inclusion, ownership of cached editable files, and releases.
That new distribution feature could change the value of upstream's package;
it is not already an agreed requirement.

## Shared target tree and ownership proposal

The accepted location for supported runtime robot/scene XML is the family
root. The following tree is one proposal consistent with that requirement;
the optional paths are not newly accepted policy.

```text
<family>/
  <existing-model-stem>.xml          # canonical supported robot MJCF
  <other-supported-model>.xml       # another logical edition when it has MJCF
  <shared-model-fragment>.xml       # optional maintained canonical include
  scene.xml                        # canonical default paired scene
  scene_<edition>.xml               # canonical other supported paired scene
  assets/                          # meshes, textures, height fields, etc.
  urdf/                            # supported URDFs where already conventional
  <existing-hhtools-model>.urdf      # retained root exception if chosen
  robot.yaml                       # HHTools descriptor where one exists
  joint-order.json                  # application mapping where one exists
  family.json                      # OPTIONAL local metadata authority
  SOURCE.json                      # provenance, or a referenced source record
  sources/<origin>/<pin-or-id>/     # immutable retained source evidence
    ...                            # original paths/bytes and snapshot manifest
  revisions/<edition>/<revision>/  # authoring output; not auto-supported
    model.xml
    provenance.json
  reviews/                         # optional relocation of existing QA evidence
  README.md
  CHANGELOG.md
  LICENSING.md
  LICENSE.* / NOTICE.*              # existing scope-specific grants/notices
```

There need not be an empty `urdf/`, `sources/`, `revisions/` or `assets/`
directory when it has no files. SOMA, for example, has primitive-only
geometry. Empty directory symmetry does not establish portability.
Physical description contents and logical edition IDs stay distinct from
directory conventions. The [existing local manifest][L-manifest] already
expresses both URDF-only and MJCF-only editions.

**Canonical descriptions:** root robot XMLs describe geometry, inertials,
kinematics, controls, sensors and intrinsic collision policy as currently
declared. Root scene XMLs include the selected model and maintain the
environment plus any scene-specific contacts/initialization. Full native
scenes remain ordinary MuJoCo entry points. Editing one model does not
regenerate or overwrite another runtime copy.

Shared local model/default/actuator fragments may be maintained as canonical
dependencies, as upstream Talos demonstrates; a supported root entry point
does not have to duplicate every included definition. Such a fragment is not
an immutable vendor snapshot. A declared pair should verify that the scene
includes the declared model, or explicitly describe its composition; selecting
an incompatible model/scene must not silently substitute a different include.
The exact compatibility policy is an interview decision.

**Source snapshots:** preserve the bytes actually retained today before
changing their authoring role. Record origin repository/commit separately
from original-source hash, packaged-source hash and canonical-runtime hash.
Do not invent a missing original vendor file from a transformed local copy.
For example, local G1 records both original and packaged retargeting URDF
hashes; that distinction must survive relocation. An archived source file
without its original full asset tree is an explicitly recorded file snapshot,
not a claim that the original upstream bundle has been reconstructed.
Source: [G1 provenance][L-manifest-G1].

**Supported descriptions versus revisions:** the 12 logical editions remain
explicit catalog choices. Saved authoring revisions must retain their own
identity and origin. Proposed `revisions/` keeps them out of root XML discovery
and ordinary supported scenes; promotion would name an explicit model + scene
pair and update metadata atomically. The choice between immediately usable
workspace revisions and explicit promotion is open. The current edition
module intentionally globs all valid XML in a managed directory, and Dex's
managed directory is its family root; blindly moving that policy to every
root would mix models, scenes, conversions and scratch files. Sources:
[discovery][L-editions], [Dex workspace declaration][L-manifest-Dex].

### Global versus per-family metadata

| Choice | Authoritative ownership | Advantages | Cost or risk |
| --- | --- | --- | --- |
| Keep one root manifest | Root owns family inventory, edition descriptions, simulation configurations and source records | Least metadata migration; existing writers/tests have one authority | Copying one folder carries runnable XML but not necessarily its catalog choices/provenance records unless explicitly exported |
| Family metadata plus root index | Family owns editions, paired simulation configurations, defaults, artifact provenance and revision references; root owns discovery/order/global defaults/aliases | Better locality; copy carries semantic description and provenance; editors can change one family independently | Move all writers/readers together, validate schema/duplicates, choose how a standalone folder is discovered |
| Family metadata compiled into root catalog | Family is source authority; root catalog is a generated read-only index | Fast global consumption and self-contained metadata | Adds generation/checking; must forbid editing the generated index and handle rebuilds after authoring |

**Recommendation for the interview:** family-owned semantic metadata plus a
small root discovery/default/alias index, with a loader that can accept either
a catalog root or one family. This would make the bundle a deep module:
callers learn a small interface for resolving a supported description and
simulation configuration; metadata layout and revision storage stay behind
that seam. It earns its depth only if CLI and Workbench actually share it.
Do not introduce both a mutable global manifest and mutable family catalog
for the same fields. Generating a metadata index is compatible with direct
canonical XML; generating another authoritative XML mirror is not.

An alternative is keeping the root manifest for this migration and relocating
metadata later. Runtime portability alone does not require a local metadata
file: native MuJoCo can load the copied scene directly. That staged choice
trades less immediate churn against completing semantic bundle locality later.
It must be an explicit user decision rather than an inference from ADR 0003.

### Concrete mappings for representative families

| Family | Supported model/scene mapping | Source and format handling |
| --- | --- | --- |
| `unitree_g1` | Root `unitree_g1_29dof_with_hand_rev_1_0.xml` + `scene.xml`; root `unitree_g1_29dof_box_feet.xml` + `scene_29dof_box_feet.xml` | Keep 43-DOF hand edition and 29-DOF box-feet reference distinct; retain Unitree and ProtoMotions snapshots, `urdf/for_retargeting/g1.urdf`, both license scopes and original/packaged hashes |
| `astro_p2` | Existing three root model stems; `scene.xml`, `scene_30dof_mesh_collision.xml`, `scene_30dof_primitive_collision_halfway.xml` | Preserve primitive, mesh and halfway descriptions; URDF exists for first two only. Preserve authorization/conversion evidence; do not regenerate reviewed MJCF from URDF as a layout step |
| `astro_p2_43dof_dex3_1` | Existing root model + `scene.xml`; an explicitly optional `fist` initial pose if selected | MJCF is already independently refined beyond its URDF. Preserve its reviewed collision edits, joint-order mapping, fist keyframe/evidence, sample mounting status and hand license. Source snapshot is evidence, not a competing editable runtime copy |
| `astro_p2_29dof` | Supported URDF remains selectable; no newly advertised canonical MJCF/scene pair | Keep root HHTools URDF, `robot.yaml`, mapping/calibration-related files and local mesh closure. Archive/classify the existing standalone conversion and experiments separately; native temporary URDF simulation must not silently promote the conversion to supported MJCF |

Sources: [manifest][L-manifest], [Dex refinement warning][L-Dex-mjcf],
[Dex README][L-Dex-readme], [Astro 29 descriptor][L-Astro29-yaml],
[Astro 29 conversion notes][L-Astro29-mjcf]. Exact spelling changes, if any,
need a migration map; the table intentionally uses existing stems/edition IDs.

## Feature preservation means adapting both routes

Current application behavior is the requirement to preserve, but its internal
file/path assumptions are replaceable. In particular, preserving features
does not require keeping `robots/` aliases, `meshes/` aliases, nested `mjcf/`
authority or JSON floor injection indefinitely. The following work is needed
whether code is edited in place or copied into an upstream-shaped tree.

| Existing capability | Current seam or assumption | Necessary adaptation in A and B |
| --- | --- | --- |
| Browse seven families/12 logical editions and select URDF or MJCF | `Edition`/`Variant` parsed from root manifest | Retain logical IDs, formats, default choices, dimensions/status and aliases; resolve canonical descriptions rather than generated mirrors |
| Native CLI exact-file loading and viewer launch | `commands/mujoco.py` loads selected `variant.mjcf` or `--mjcf`; no explicit scene/pose selection | Add shared simulation-configuration resolution while retaining an exact-file route; report the resolved model, scene and pose so selections are inspectable |
| Browser MuJoCo physics, controls, contacts, pushing and diagnostics | Browser edits XML, flattens mesh paths to basenames, appends its JSON-derived floor and resets spawn | Load the canonical selected scene/dependency closure and explicit pose; preserve scene contact settings and remove implicit world/pose reconstruction for that path |
| Three-based visualization and URDF view | Renderers operate on compiled arrays/URDF and receive catalog metadata | Reuse renderers with the selected configuration; avoid duplicate terrain or applying the robot pose twice |
| Collision editing, drafts, revision conflict protection, save-as/overwrite | Server resolves description source; stores edit revisions; managed editions assume a `mjcf/` directory or override | Resolve one explicit mutable canonical model or revision; keep original snapshot immutable; distinguish model versus scene save targets; preserve existing conflict/error behavior |
| Conversion, authorization and imported variants | Conversion authorization writes `mjcf/<candidate>.xml`; import code creates nested workspaces | Redirect successful promotion/import to the chosen canonical layout and metadata transaction; keep review evidence and already-reviewed manual deltas |
| URDF-only visualization and temporary physics/native launch | Temporary URDF runtime conversion adds a floating base and terrain, rewrites mesh paths | Preserve URDF capability through an explicit format adapter; make it consume the selected scene/pose where supported and leave authored URDF bytes unchanged |
| Collision URDF export, diagnostics, random pose and video recording | Implemented in existing editor/server/browser modules | Retain behavior and route it through the selected logical edition/configuration; maintain coordinate and revision identity during model reloads |
| Height/PD/Viser utilities | Some utilities still assume default P1 `mjcf/`/`meshes/` paths | Resolve descriptions/assets through shared metadata or a deliberate exact path; preserve computations and documentation edits |
| Checkout, sdist and code-only wheel use | Asset discovery and custom link-preserving sdist hook | Decide artifact contents explicitly; verify extracted/copied bundles and installed application lookup, rather than assuming a source checkout proves packaging |

Local evidence: [asset/edition data types and loader][L-assets],
[CLI command surface][L-cli], [native loader][L-native],
[browser composition and VFS loading][L-browser-compose],
[server format/source/editor routing][L-server],
[temporary URDF runtime][L-urdf-runtime],
[revision/import module][L-editions],
[candidate authorization][L-authorize],
[package policy][L-pyproject], [sdist hook][L-hatch].

Two particularly important constraints follow directly from inspected code:

- Browser loading currently inspects meshes in one XML and sends basenames
  to a VFS. A canonical scene's `include` graph, nested assets, same-named
  meshes in different directories, textures, or height fields are not solved
  by changing the manifest path alone. Serve a validated family-local
  dependency closure preserving relative identity, or use a proven equivalent
  compiler adapter. A closure transport is an implementation adapter, not a
  second editable model. Both native launch and browser compilation should
  identify the same file inputs. Source: [browser loader][L-browser-compose].
- Current root native scenes place the floor relative to the existing robot
  datum; Workbench resets robot spawn against a global flat floor. Switching
  to the canonical scene must preserve its actual coordinates and optional
  initialization rather than also applying the old spawn transform. Compare
  model + scene + pose outcomes, not just robot mass and joint counts.
  Sources: [scene generator][L-sync], [browser spawn/loading][L-browser-spawn].

This is why the shared simulation resolver is the valuable module. It hides
metadata location, validates the pairing/pose and paths, and returns a clear
configuration to both consumers. The UI, native launcher and dependency
transport are real adapters at that seam. A pass-through wrapper around each
old implicit floor/spawn implementation would leave the complexity spread
across callers and fail the intended locality improvement.

### Concrete native-compatibility evidence from the parallel investigations

The [upstream contract investigation](mujoco-upstream-contract.md) supplies
native examples beyond G1/T1: Talos has scene → actuator wrapper → shared
mechanism includes and distinct `assets/torso/base_link.stl` and
`assets/gripper/base_link.stl`; Stretch includes PNG-backed scene resources,
a scene-owned free object, tendons and coupled actuators; RBY1 scenes own
solver/integrator settings. Those examples were source-inspected in that
investigation, not all downloaded and compiled. They demonstrate why complete
relative paths, multiple model wrappers and scene-owned physics belong in
the design without adding any MJX requirement.

The separate [Workbench compatibility investigation](mujoco-workbench-compatibility.md)
produced native/WASM
MuJoCo 3.11.0 results under `/tmp/workbench-compat-probes/`. This route report
read `native-results.json`, `wasm-results.json` and `catalog-results.json`;
their detailed methodology belongs to that investigation. Its findings
materially affect **both** implementation routes:

| Reproduced observation | Consequence for the migration proposal |
| --- | --- |
| Path-preserving complete VFS loading compiled upstream G1, T1 and Go2 scenes and a synthetic nested-include/duplicate-basename/PNG fixture; declared keyframe control targets and 50-step finite-state checks were exercised. The current Workbench-style VFS failed to find included robot XML. | A browser adapter can consume native bundles without rewriting their physical descriptions. Complete dependency transport is feasible, but must replace the current direct-mesh-only mechanism. This is a small tested sample, not an all-Menagerie compatibility claim. |
| Current collision parsing raised `IndexError` for G1/Go2 model defaults; T1 had unnamed collisions that could be read but a no-op update rejected because names were empty; scene wrappers returned zero editable links/collisions. | Editing must resolve effective defaults and source ownership through includes; a compile/load success does not establish authoring support. Use stable editor identity without requiring source renaming merely to edit. |
| A synthetic no-op collision edit removed `material`, `friction` and `solref`, and rewrote `contype=2`/`conaffinity=4` to `1`/`1`. | The save path needs lossless, ownership-aware targeted edits. Reusing the existing editor unchanged would alter physics during a nominal structural migration. |
| Renderer probes represented an infinite plane with zero extent and an ellipsoid as a sphere. | Preserve native model geometry semantics in visualization; use a finite presentation extent for an infinite plane and correct ellipsoid dimensions. These are adapter repairs, not robot-model changes. |
| Catalog probes showed logical/revision identity ambiguity, and a scene import reported success despite its missing included robot failing native compilation. | Metadata/revision identity and import closure validation are real acceptance requirements; copying the catalog module without redesign would preserve the faults. |

The report's native smoke-test gates therefore include scene resources,
keyframe controls, source ownership, inherited defaults and non-destructive
editing. These are stronger reasons to redesign the adapters than the folder
layout alone. They also strengthen the effort comparison: upstream supplies
valid XML that exposes these assumptions, but no replacement Workbench editor.
Starting from its scaffold cannot remove this shared work.

## Route A: evolve the present repository

1. Freeze the accepted inventory and capture baselines/source hashes without
   modifying physical descriptions. Record every current logical edition,
   exact format path, scene, default, revision workspace and known external
   consumer path. Include user-local untracked work in a non-destructive
   migration inventory; it is not automatically a supported catalog model.
2. Resolve metadata/revision/save-target questions from the interview. Build
   the shared configuration resolver and family-local closure handling, then
   adapt CLI and Workbench against the accepted native contract. Existing
   backend assumptions are replaceable during this stage.
3. Promote the nine existing generated flat robot files to direct canonical
   ownership after comparing them to preserved source baselines. Dex remains
   canonical at root. Keep the ten scenes directly maintained, and stop
   regenerating them from global spawn metadata. Archive original nested
   source bytes separately, retaining their provenance and physical source
   context. Do not overwrite a newer Workbench edit with an older mirror.
4. Migrate edition/import/conversion/authoring operations and tests as one
   coherent change. Replace source-versus-copy tests with baseline semantics
   and same-configuration consumer tests. Update documentation, CI and
   packaging to the new authority.
5. Remove obsolete generator policies and aliases only after acceptance gates
   demonstrate that supported consumers no longer depend on them.

**Effort profile:** concentrated semantic migration of the loader/editor
paths; limited repository assembly. **Primary risks:** an old writer still
targets nested MJCF, old spawn logic runs after scene loading, revisions are
misclassified, or an authoritative source is mistaken for disposable output.
**Advantages:** behavior and asset provenance are already colocated; existing
tests provide a direct before/after harness; the native scaffold is already
available. None of these advantages excuses retaining the old backend model.

## Route B: clean pinned upstream scaffold, then integrate

1. Choose B1 versus B2 before any repository creation/history changes. Start
   from the exact upstream pin, retaining an untouched reference for source
   comparison. Define an allowlist of scaffold files rather than importing
   the complete runtime/release pipeline by default.
2. Remove unrelated model folders from the candidate working tree. Import
   the seven **local** family bundles, not upstream replacements. Upstream
   `unitree_g1/` collides by name with the local mixed Unitree/ProtoMotions
   family; remove the upstream candidate contents before importing the local
   family so unused model variants/assets/licenses cannot be blended silently.
   Do not add upstream G1 MJX or mjlab files as incidental baggage.
3. Bring across CLI/Workbench, behavior tests, required package/build metadata,
   source/provenance records, licenses and authoring tools by an explicit
   inventory. Copying the current application wholesale is a valid starting
   integration step, but at that instant it also copies its old assumptions.
   Apply the same shared resolver, dependency transport, model/scene/pose,
   editing and revision migration described for A.
4. Adapt upstream structural checks for the preserved URDF-only inventory and
   actual license scopes. Add the local feature tests rather than treating
   upstream's short native scene test as Workbench acceptance.
5. Remove unused package/gallery/release material, complete attribution,
   compare the candidate's supported assets and behavior to the original,
   and decide which repository/branch becomes authoritative only after all
   acceptance gates pass.

**Effort profile:** the same semantic loader/editor migration, plus explicit
assembly, inventory reconciliation and repository/package identity work.
**Primary risks:** silently omitting application behavior or source evidence,
same-name G1 replacement/blending, leaving upstream release endpoints/default
models in place, and losing history links. **Advantages:** stronger visual
separation between upstream scaffold and local additions; a clean candidate
tree can make ownership review easier; a literal fork makes upstream
contribution paths clearer. These are real benefits, but do not make missing
functionality free to port.

**When the scaffold reduces effort:** if the current native-layout work is
being intentionally discarded, or the user wants the upstream runtime
package/gallery/release features and accepts their adaptation, B has more
reusable upstream implementation. Under the current accepted scope, the
formatter/check patterns/layout are already present, so most B effort buys
clean assembly and repository lineage rather than new application capability.

### Does a literal fork make future merges automatic?

It provides shared ancestry for Git comparisons/merges and the GitHub fork
relationship; it does not promise conflict-free synchronization. A heavily
pruned fork has deleted many upstream model directories and replaced
catalog/package/build policies. Future upstream edits to deleted files can
conflict with deletions; new upstream families can enter through broad merges;
local shared-tool changes can conflict with upstream edits. This is a Git
integration consequence, not a defect in forking.

Proposed maintenance policy for either B1 or A/B2 with an upstream reference:
keep a pin and provenance allowlist, review selected upstream tool/test fixes,
apply them intentionally and record the new pin/treatment. A whole-upstream
merge is appropriate only if keeping that wider tree synchronized is a
deliberate goal. A literal fork adds contribution/discovery value, but pruning
alone does not create a low-maintenance automatic-update channel.

## Relative effort and risk matrix

These are comparative judgments about this scope, not person-day estimates.
“Shared substantial” means real engineering work in both routes; it does not
claim a rewrite is required.

| Work or risk | A: evolve current | B1/B2: clean scaffold | Evidence / reason |
| --- | --- | --- | --- |
| Native family layout and formatter | Mostly available | Available from upstream, then import local families | Existing scaffold already adopted |
| Canonical source/runtime ownership | Shared substantial | Shared substantial | Upstream does not classify local snapshots, reviews or drafts |
| Explicit model + scene + pose in CLI/Workbench | Shared substantial | Shared substantial | Existing browser and CLI have different scene/spawn paths |
| Portable include/asset closure in browser | Shared substantial | Shared substantial; optional upstream closure reuse | Native layout alone does not fix basename flattening |
| Logical editions, URDF-only and dual-format behavior | Adapt existing module | Import and adapt module, or recreate it | Upstream package models different metadata |
| Collision save/draft/import/promotion behavior | Adapt existing implementation | Import and adapt, with omission risk | Upstream has no equivalent Workbench |
| Model/mesh and provenance retention | Inventory and role change | Inventory, copy and reconcile | Seven families must survive both routes |
| CI, package/sdist and dependency integration | Update existing setup | Replace/adapt upstream setup plus restore browser setup | Different package/runtime/distribution models |
| Existing history and review continuity | Low additional cost | B2 can retain it; B1 needs migration strategy | Source tree and repository lineage are separate choices |
| Upstream contribution ergonomics | Reference pin/manual comparison | B1 strongest; B2 same selective-vendoring model as A | GitHub fork relation has concrete collaboration value |
| Risk of hidden legacy assumptions | Must deliberately remove them | They return if application is simply copied | Clean directory names do not alter loader semantics |
| Risk of incidental upstream scope | Small | Larger without allowlist/pruning review | Package/release/models are coupled to upstream identities |
| Clean ownership review surface | Achievable in staged PRs | Strong initial advantage | B can show exactly what is brought back |

There is no evidence for a reliable absolute schedule from source inventory
alone. The integration unknown with the largest impact is browser consumption
of full canonical scenes and drafts with preserved initialization. A small
later implementation proof against one include-heavy scene and one URDF-only
edition would retire that risk more effectively than debating line counts.
It should happen after the remaining design decisions, not as an unapproved
new implementation in this research step.

## Symlinks, URDF, HHTools and provenance

**Runtime portability:** a family copy must resolve every supported model,
scene and referenced runtime asset without sibling families, repository-global
terrain files, or installing Menagerie X. Internal relative includes and
assets satisfy the accepted contract. Native XML must compile after copying
the family to an unrelated temporary directory; testing only inside the
checkout can hide accidental dependencies. Source: [ADR 0003](../adr/0003-portable-robot-bundles.md).

**Symlinks:** current `meshes -> assets` aliases are family-local; current
`robots/<family> -> ../<family>` aliases serve old catalog paths. They have
different purposes. A native root model using `assets/` need not depend on
either alias. Existing URDF/HHTools references can still depend on `meshes/`.
The sdist hook reconstructs exactly these links because normal traversal had
suppressed repeated inodes. Sources: [compatibility policy][L-upstream],
[build hook][L-hatch].

Proposed policy: keep aliases only as a temporary compatibility adapter while
changing known callers, or retain the family-local mesh alias until its URDF
and HHTools contract is explicitly migrated. A dereferenced distribution
export is another option if symlinks are undesirable, but then asset
duplication and path rules must be tested. Native portability does not settle
Windows/link export behavior, nor require preserving every old physical path.
Choose the supported platforms/artifacts before deleting the hook or aliases.

**HHTools:** Astro 29's `robot.yaml` names a root URDF and `meshes` search path
and records application joint/retargeting configuration. Moving its URDF into
`urdf/` merely for symmetry would require descriptor, mesh-path and consumer
updates. The cleaner first migration can leave that root URDF as an explicit
exception while moving canonical MJCF ownership elsewhere. Dex's descriptor
is a sample asset description; its docs explicitly disclaim established hand
calibration/retargeting support. Folder cleanup must not strengthen those
claims. Sources: [Astro 29 descriptor][L-Astro29-yaml],
[Dex README][L-Dex-readme].

**URDF/MJCF independence:** Dex has intentional MJCF-only contact refinements
that a fresh URDF conversion would overwrite. P2 has reviewed primitive,
mesh and halfway choices; Atom and SOMA are MJCF-only. A universal
“regenerate MJCF from URDF” policy would lose real work. Declare artifact roles
individually: preserved source, generated candidate with inputs/tool/options,
independently maintained derivative, or workspace revision. Sources:
[Dex warning][L-Dex-mjcf], [manifest][L-manifest].

**Physical baseline:** preserve names, order, frames, masses/inertias, joint
limits, collision shapes/masks/pairs/exclusions, solver/control properties,
sensors, keyframes and already reviewed refinements. Moving a source floor
out of the canonical robot does not authorize changing its standing frame,
actuator configuration, self-contact policy or pose initialization. Existing
tests compare several compiled arrays and short warning-free stepping, but
do not cover every sensor/contact/actuator/keyframe field. Extend the baseline
comparisons where the migration touches semantics. Source:
[existing native regression checks][L-native-tests].

**Licenses and snapshots:** retain the existing source-scope notices and
unresolved grant records. A scaffold fork does not relicense Astro/Atom data
under Google's aggregate license; removing unrelated families should also
remove their unrelated aggregate license material from a source-copy
distribution. For B1, pruning the working tree does not erase upstream history
or its original notices. Sources: [local licensing][L-licensing],
[upstream attribution][L-upstream].

## Staged deletion list, acceptance and rollback

The following is a proposed migration sequence. No listed item was deleted
by this research.

| Stage | Replace/migrate first | Then remove or retire |
| --- | --- | --- |
| Authority | Preserve exact source snapshots; switch catalog and all writers to root canonical files | The nine nested files' role as active runtime authority; archive/move them only after path migration |
| Scene behavior | Shared selected scene/pose and closure loading in CLI/Workbench | Browser implicit floor injection and implicit spawn reset for canonical MJCF configurations; JSON as a competing MJCF world authority |
| Generation | Direct-maintained root XML checks and ownership docs | `scripts/sync-menagerie.py`, `make sync`, its hook/check target, and generated-mirror assertions/policies |
| Authoring | Explicit revision workspace, immutable snapshot policy, safe promotion transaction | Root/`mjcf/` catch-all discovery as the supported-edition authority; obsolete source-mutating defaults |
| Compatibility | Migrate known CLI utilities, URDF/HHTools references and packaging/export paths | Unneeded `robots/` aliases; later unnecessary `meshes/` aliases and link-only build hook logic |
| Evidence organization | Record relocation/provenance map and preserve meaningful review/conversion output | Stale path text and duplicate editable representations; do not delete retained source evidence or user experiments by pattern |
| Clean scaffold only | Integrate local package/CI and selected upstream tools | Unrelated families, remote registry/cache/release/gallery material and incorrect upstream package/repository identity |

Existing `UPSTREAM.md`, `CONTRIBUTING.md`, family READMEs, `Makefile`, hook,
package include lists and tests currently describe or enforce generated
mirrors. Update them in the same cutover so they cannot later instruct a
contributor to overwrite canonical edits. Sources: [upstream policy][L-upstream],
[contribution policy][L-contributing], [Makefile][L-make],
[package metadata][L-pyproject], [native tests][L-native-tests].

Acceptance gates for either route:

1. Inventory equivalence: seven families/12 logical editions, same format
   availability/defaults, no incidental upstream robot editions, no silent
   promotion of Astro 29 or racket MJCF.
2. Provenance preservation: every retained imported/source file has its
   pre-migration bytes/hash or an explicit source-to-packaged transformation
   record; licenses/notices and Dex/refinement evidence remain reachable.
3. Native portability: copy each family alone outside the checkout and
   compile each supported root model/scene from there, with assets resolved
   inside that copy. Apply the relevant URDF/HHTools mesh-resolution checks
   too. Missing catalog MJCF in a URDF-only edition is an expected capability,
   not a reason to manufacture a placeholder.
4. Physical/initialization equivalence: compare baseline model fields and
   selected configuration behavior, including names/order, actuators,
   sensors, collision policy, keyframes and optional pose/control targets;
   exercise short stepping. Document expected world-only changes explicitly.
5. Consumer agreement: the CLI and Workbench report the same selected model,
   scene, pose and source hashes; a scene-specific contact setting and a
   non-default pose survive both paths. Browser asset transport handles
   relative includes/resources without basename collisions or external
   dependencies. Exercise nested includes, duplicate mesh basenames and
   file-backed textures, plus a scene-owned free object/contact/solver option.
   No second implicit floor or spawn transform appears; a robot is not
   identified solely as whichever free joint happens to occur first.
6. Authoring agreement: edit/save/reload a model through Workbench and observe
   the same file through CLI; preserve draft conflict protection, save-as,
   URDF export and revision behavior. A model edit does not mutate a source
   snapshot or unintended scene; a scene edit has its own declared target.
   No-op edits preserve material/friction/solver/mask attributes and effective
   defaults; unnamed geoms are addressable; included model geoms resolve to
   their owned editable source. Import succeeds only with its runtime closure.
7. Product/packaging regression: existing applicable Python/browser feature
   checks pass; exercise URDF-only selection/native launch, collision tools,
   diagnostics/pushing, recording, import/conversion and utilities, including
   infinite-plane and ellipsoid presentation. Build and
   extract the supported distribution formats and repeat path/asset checks.

For rollback, preserve a clean base reference, a content/provenance migration
map and source baselines. Structure implementation commits around authority,
shared resolution, consumer adaptation and cleanup; do not remove old paths
before new consumers pass. Avoid shipping two editable authorities as a
fallback. Before cutover, rollback means reverting candidate commits; after
users create edits, first preserve those edits and their identities, then
apply a documented reverse mapping. A clean-scaffold candidate stays
non-authoritative until gates pass, so abandoning it does not disturb the
existing repository. No branch, tag, fork, remote or history was changed for
this report.

## Git-history and branch strategy options

- **Recommended for A:** later create `codex/<migration-name>` from the agreed
  current base. Preserve existing commits; use ordinary reviewed migration
  commits. An isolated worktree is appropriate because local untracked
  experiments exist, but its creation is implementation setup after the
  interview, not part of this report.
- **B2 inside current ancestry:** create a candidate branch with an explicitly
  assembled clean tree, then add retained product/data material in reviewable
  commits. This buys source-tree cleanup without sacrificing Menagerie X
  ancestry; it still needs source attribution and acceptance checks.
- **B1 in a new fork:** preserve the current project as an archival repository
  or import its history with deliberate provenance links, then integrate
  assets/application as separate commits. Choose whether upstream or local
  ancestry is primary before importing. An unrelated-history merge or history
  rewrite should not be an incidental cleanup technique.
- **Selective upstream updates for any route:** record the upstream pin and
  file treatment in `UPSTREAM.md`, review specific upstream changes and
  maintain the local adaptation deliberately. Branch ancestry does not decide
  source ownership, licensing, or supported variants.

None of these choices needs rewriting the existing branch or force-pushing
to achieve the accepted runtime structure. New GitHub repository/fork creation
also changes project identity/URLs and collaboration context; decide that
with the user rather than hiding it inside a file refactor.

## Questions for the remaining design interview

These are decisions still required, not requests already answered by the
three accepted ADRs. The recommendations make the tradeoffs concrete.

1. **Route and repository identity:** evolve this repository, assemble a clean
   source scaffold while keeping its history, or create a literal upstream
   fork? Recommendation: A unless upstream fork-network membership or a fresh
   candidate tree is itself desired. Which concrete upstream package or
   maintenance behavior is expected to become cheaper through a fork?
2. **Metadata authority:** root manifest for this migration, or family-owned
   editions/configurations/provenance plus root discovery/defaults? Recommend
   family locality if completing the portable semantic bundle now is worth
   migrating all metadata writers together.
3. **Supported choices versus revisions:** should saving a draft make it a
   selectable workspace revision immediately, and what explicit promotion
   makes it a supported model/scene configuration? Keep logical editions
   separate from file revisions in either policy.
4. **Save targets:** does a collision edit overwrite a canonical model after
   review, create a revision by default, or offer both? Which operations may
   edit scenes, and how is a scene-specific contact/pose edit distinguished
   from a robot edit? Preserve the feature while changing obsolete backend
   implementation freely.
5. **URDF and source placement:** keep root HHTools URDF/descriptor paths as
   explicit exceptions, or migrate them with consumers? Which retained files
   are original evidence versus independently maintained descriptions? Do not
   impose one universal URDF-to-MJCF derivation rule.
6. **Pose and pairing policy:** are poses selected from model/scene keyframes,
   family metadata, or both with one authority? How are available/compatible
   model-scene pairs declared, and what does omission of initial pose mean?
   Keep the existing robot coordinate convention until any transform change
   is separately approved.
7. **Compatibility and artifacts:** which old paths/commands require a
   migration period, and which can change immediately? Is the deliverable a
   source checkout + sdist + code-only wheel, or are standalone family exports
   and additional platforms required? Remote archive hosting is a separate
   optional distribution feature.

The proposed route does not require uniform controllers, collision redesign,
new hardware calibration, MJX validation, mjlab adapters, or replacing local
G1 with upstream G1. Those would be additional modeling/product work and need
their own decisions and evidence.

## Sources

Upstream implementation evidence is linked at its fixed commit. Local
implementation evidence identifies repository-relative files with inspected
line ranges at the local baseline; these are checkout observations and do not
claim the current commit is available on GitHub. Existing research reports
[Menagerie scaffold investigation](mujoco-menagerie.md) and
[per-robot structure investigation](mujoco-per-robot-structure.md) provide
additional upstream examples and model compilation findings; their earlier
recommendations do not override accepted ADRs.

[L-manifest]: ../../manifest.json#L11-L127
[L-manifest-Dex]: ../../manifest.json#L40-L76
[L-manifest-G1]: ../../manifest.json#L114-L125
[L-upstream]: ../../UPSTREAM.md#L1-L63
[L-catalog]: ../../catalog.py#L31-L64
[L-sync]: ../../scripts/sync-menagerie.py#L19-L79
[L-assets]: ../../src/menagerie_x/assets/__init__.py#L14-L228
[L-editions]: ../../src/menagerie_x/assets/editions.py#L65-L438
[L-cli]: ../../src/menagerie_x/cli.py#L20-L131
[L-native]: ../../src/menagerie_x/commands/mujoco.py#L30-L104
[L-server]: ../../src/menagerie_x/workbench/server.py#L494-L555
[L-browser-compose]: ../../src/menagerie_x/workbench/web/app.js#L2160-L2222
[L-browser-spawn]: ../../src/menagerie_x/workbench/web/app.js#L2098-L2113
[L-urdf-runtime]: ../../src/menagerie_x/workbench/urdf_runtime.py#L53-L164
[L-authorize]: ../../src/menagerie_x/commands/mjcf.py#L580-L617
[L-pyproject]: ../../pyproject.toml#L1-L47
[L-hatch]: ../../hatch_build.py#L1-L61
[L-native-tests]: ../../tests/test_menagerie_models.py#L46-L97
[L-Dex-mjcf]: ../../astro_p2_43dof_dex3_1/MJCF.md#L16-L64
[L-Dex-readme]: ../../astro_p2_43dof_dex3_1/README.md#L14-L74
[L-Astro29-yaml]: ../../astro_p2_29dof/robot.yaml#L1-L12
[L-Astro29-mjcf]: ../../astro_p2_29dof/MJCF.md
[L-licensing]: ../../LICENSING.md#L1-L19
[L-contributing]: ../../CONTRIBUTING.md#L1-L49
[L-make]: ../../Makefile#L1-L30
[U]: https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc
[U-readme]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/README.md#overview
[U-format]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/format_xml.py
[U-catalog]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/catalog.py
[U-model-test]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/test/model_test.py
[U-layout-test]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/test/model_dir_test.py#L24-L79
[U-package]: https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/python/src/mujoco_menagerie
[U-package-doc]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/python/DOC.md
[U-runtime-registry]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/python/src/mujoco_menagerie/_registry.py#L36-L173
[U-registry]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/build_registry.py#L40-L232
[U-cache]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/python/src/mujoco_menagerie/_cache.py#L49-L152
[U-pyproject]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/python/pyproject.toml#L1-L20
[U-release]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/.github/workflows/release.yml#L1-L91
[U-make]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/Makefile#L31-L49
[GH-forks]: https://docs.github.com/en/pull-requests/reference/forks
