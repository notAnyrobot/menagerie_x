# CLI and Workbench compatibility with canonical MuJoCo bundles

> Scope update: the user subsequently prioritized close native Menagerie asset alignment and accepted Workbench/URDF incompatibilities. Application architecture and compatibility repairs discussed below are follow-up work, not requirements for this phase. See [ADR 0011](../adr/0011-upstream-asset-structure-first.md). MJX remains deferred.

Research date: 2026-10-30. Local code citations below identify files and line numbers in the inspected checkout; its commit may be unpushed, so these are repository-relative evidence links rather than claims of remotely verified GitHub pages. Implementation inspected: `27d9e7c0f3d58961f97af8cdb03acffa6b07a878`. Upstream examples: Menagerie `f3b6013629c7b94f8ee93fd977b161fa8350f9bc`. This is a proposal and reproducible compatibility investigation, not an implementation. The accepted target is directly maintained family-root robot and scene XMLs, explicit model + scene + optional initial pose, shared authority between CLI and Workbench, and independently portable families. Keep the seven current families and supported CLI/Workbench features. MJX compatibility is deferred. Other downstream frameworks are not implicit requirements. See the [accepted decisions](../design/per-robot-design-decisions.md).

## Finding

**The engine already supports the paired source structure; Workbench's transport, initialization, editor, and file-management assumptions are the obstacles.** Native MuJoCo and the installed JavaScript WASM engine are both **3.11.0**. Giving WASM complete relative-path bundles loaded real G1, T1, and Go2 scenes with the same dimensions as native MuJoCo. No conversion to the current flat, explicit-attribute editor dialect was necessary. Conversely, today's browser loader cannot open those scenes, the collision editor fails on their normal inherited/unnamed geometry, and its existing materialization can change unrelated physics during an unchanged draft save. These are observed failures, not hypothetical consequences of a version upgrade. [Dependency pins][L-deps] [Browser pin][L-webdeps] [Loader][L-load] [Editor parser][L-editor-parse] [Editor writer][L-editor-write]

The recommended seam is a **source bundle and simulation configuration module**, shared by the CLI, server, and browser: resolve authoritative source files and dependencies once; let native/WASM adapters compile them; initialize the declared pose once; keep an explicit source location for edits. Rendering and collision editing should consume resolved engine semantics without treating a compiled serialization as the new canonical source. This is a proposal, subject to the open ownership and metadata decisions below.

## Method and concrete results

Read the actual CLI, catalog, server, renderers, collision stores, URDF conversion/export, diagnostics, recording, and their tests. Retrieved current MuJoCo documentation through Context7, then used the installed 3.11.0 bindings for probes. No browser was navigated, no server was restarted, no branch changed, and no implementation files were edited. The pre-existing test suite was inspected, not rerun; results below are separate executable probes, not claims that the repository suite passes.

Temporary prototypes and machine-readable results are under `/tmp/workbench-compat-probes/`:

| Prototype | What it actually exercises | Output |
| --- | --- | --- |
| `probe.py` | Native upstream model/scene compilation, reference/keyframe state, existing collision-document loader and unchanged draft update, a two-file multi-section scene, unchanged explicit collider rewrite | `native-results.json` |
| `probe.mjs` | Actual installed `@mujoco/mujoco` 3.11.0, path-preserving VFS versus current scene loader's empty dependency set, keyframe reset, 50 simulation steps; actual `mjcf-renderer.js` imported with only module URLs adapted for Node | `wasm-results.json` |
| `nested-fixture.py` | Small synthetic bundle: nested includes, `assetdir`, two different `base.obj` files in separate directories, file-backed PNG texture | `nested-native.json`, `nested/` |
| `catalog-probe.py` | Existing import and legacy edition mutation functions against an isolated temporary catalog | `catalog-results.json`, `catalog/` |

Run from the checkout with `.venv/bin/python /tmp/workbench-compat-probes/probe.py`, `.venv/bin/python /tmp/workbench-compat-probes/nested-fixture.py`, `node /tmp/workbench-compat-probes/probe.mjs`, and `.venv/bin/python /tmp/workbench-compat-probes/catalog-probe.py`. The Python and Node prototypes use the existing environment and package dependencies; they do not install or amend packages. `/tmp` files are session artifacts rather than permanent test fixtures; the inputs, expected outcomes, and necessary future acceptance cases are recorded here.

### Native and WASM compile the real paired scenes

The WASM prototype registers every local XML/mesh/PNG in a family's VFS under its **unchanged family-relative path**, then calls `MjModel.from_xml_path("scene.xml", vfs)`. This method and VFS buffers are present in the installed bindings; the official wrapper also offers named-path XML loading. A named entry point avoids the `from_xml_string` wrapper's internal `model.xml` name and preserves directory context. [Official WASM binding source][M-wasm]

| Native CPU scene | Native and WASM `nq/nv/nu` | `nbody/ngeom/nmesh` | `ntex/nmat/nkey` | WASM result after declared first keyframe + 50 steps |
| --- | --- | --- | --- | --- |
| `unitree_g1/scene.xml` | 36 / 35 / 29 | 31 / 72 / 35 | 2 / 3 / 1 | finite qpos |
| `booster_t1/scene.xml` | 30 / 29 / 23 | 25 / 37 / 24 | 2 / 3 / 1 | finite qpos |
| `unitree_go2/scene.xml` | 19 / 18 / 12 | 14 / 57 / 16 | 2 / 5 / 1 | finite qpos |
| Synthetic `nested/scene.xml` | 0 / 0 / 0 | 3 / 3 / 2 | 1 / 1 / 0 | finite state; no keyframe |

The synthetic bundle has `scene.xml → robot.xml → parts/body.xml → parts/child.xml`, `assetdir="assets"`, `a/base.obj`, `b/base.obj`, and `wood.png`. Native retains distinct mesh vertex norms 1.5 and 3.0; WASM compiles both meshes and the PNG. This proves the transport approach for these dependency classes, not universal support for every Menagerie model/plugin or visual feature. Real scene source: [G1][U-g1-scene], [T1][U-t1-scene], [Go2][U-go2-scene].

For each real scene, the current browser-equivalent VFS contains **no files**: these scene documents reference sibling robot XMLs and procedural textures, with meshes declared in the included robot. Actual WASM `from_xml_string(sceneSource, emptyVfs)` fails respectively with `Error opening file 'g1.xml'`, `'t1.xml'`, and `'go2.xml'`. Current `prepareSimulationSource` does not expand includes; it gathers only direct `mesh[file]` descendants and fetches their basenames. Adding a generic floor does not repair the missing includes. The existing `/runtime?format=mjcf` endpoint returns the same unexpanded source. [Browser loader][L-load] [Runtime/source/files routes][L-routes]

### Collision authoring fails before physics is involved

| Raw authoritative source passed to today's editor | Observed result |
| --- | --- |
| Upstream `unitree_g1/g1.xml` and `g1_with_hands.xml` | `IndexError: list index out of range` |
| Upstream `unitree_go2/go2.xml` | Same `IndexError` |
| Upstream `booster_t1/t1.xml` | 24 body links, 12 collisions, all 12 unnamed; unchanged update rejects `primitive must have a link and non-empty name` |
| Any of the three upstream `scene.xml` files | Zero links and zero editor collisions, despite native scenes containing robot geoms |

G1/Go2 use foot classes with inherited sizes. `_default_geom_attributes` copies only the directly declared geom attributes of named classes. `_is_contact` consults that shallow mask dictionary, while `_geom_geometry` ignores it completely and reads `type`/`size` from the geom alone. Parent default inheritance, a body's `childclass`, and include expansion are not resolved. Thus the size-less foot reaches `size[0]`. The editor enumerates only literal named `<body>` elements, not the compiled source graph. T1's unnamed geoms are valid MuJoCo, but editor validation requires every primitive name to be nonempty. [Parser, exact lines 284–397][L-editor-parse] [Validation, lines 400–449][L-editor-validate] [G1 source][U-g1] [Go2 source][U-go2] [T1 source][U-t1]

A named one-geom fixture proves a separate save problem. Original sphere attributes include `material="body" friction=".9 .04 .05" solref=".01 1" contype="2" conaffinity="4"`. Creating a draft and sending its **unchanged** primitive list through `update` produces a replacement with `contype="1" conaffinity="1" group="3"`, position/quaternion/size, and no material, friction, or solref. The surrounding default has friction `.7 .02 .03`, so the effective friction changes too. `_materialize` removes all represented primitive nodes and recreates them from the editor's narrow schema. This must be adapted before authoritative robot-file overwrite is safe for upstream-style source. [Writer, lines 463–506][L-editor-write]

### Multiple sections are legal engine input

The synthetic scene includes a robot with its own asset, worldbody, contact exclusion, and keyframe, then adds another asset/worldbody/contact/keyframe section. Native compiles **two materials, two geoms, one explicit pair, one exclusion, two keyframes**. A second native string probe with repeated top-level default/asset/worldbody/contact/keyframe sections also compiles: two named default classes, two materials, two bodies/geoms, two exclusions, two keys. MuJoCo expands includes before normal MJCF parsing. Therefore a source adapter cannot keep only `find("worldbody")`, the first asset block, or a single keyframe/contact section. These probes preserve normal CPU semantics; they do not require MJX. [Include semantics and asset resolution][M-xml]

## Feature inventory and compatibility disposition

“Preserve” retains user-visible capability, sometimes through a small path adapter. “Adapt” means the capability stays but its existing assumptions must change. “Defer” below is limited to explicitly out-of-scope support; it is not permission to remove existing functionality.

| Current capability and owning code | Disposition | Necessary behavior at the proposed seam |
| --- | --- | --- |
| `manifest`, `variants`, `validate`; seven family/edition catalog | **Preserve + adapt metadata** | Resolve explicit robot/scene/pose entries; retain format and edition identity; validate dependency closure and bundle portability instead of requiring only a `meshes/` directory. [CLI][L-cli] [Catalog][L-assets] |
| `mujoco --mjcf PATH --check`, native viewer, `--seconds` | **Preserve** | Exact-path loading already preserves includes and compiler-relative assets. Add a configuration selection path and initialize its pose; retain arbitrary exact XML entry-point inspection. [Native loader][L-native] |
| Workbench variant → format → logical edition selection | **Preserve + adapt** | Retain current descriptions and IDs; add explicit simulation configuration selection where one model has several scenes/poses. Do not equate filename, model, revision, and configuration. [Selection][L-select] |
| Workbench MJCF loading and physics pause/play/reset | **Adapt** | Compile the selected scene entry and complete closure, without stripping directories or adding an undeclared floor; reset the declared initial state identically in native/WASM. [Loader][L-load] [Reset/step][L-reset] |
| Mesh and primitive visual geometry, opacity, collision overlay, picking | **Preserve + adapt renderer** | Keep compiled geom world transforms. Support the native infinite-plane convention and classify presentation independently of collision filtering. Preserve current box/sphere/cylinder/capsule/mesh support. [Renderer][L-renderer] |
| Contact-point visualization, diagnostic draft contacts | **Preserve + adapt** | Compile the complete selected scene including pairs/exclusions/defaults. Keep contact visualization driven by engine output; compile a draft overlay in the same scene/configuration. [Draft compile][L-diagnostic-load] [Contact module][L-contacts] |
| Mouse pushing, follow camera, frame robot | **Preserve + adapt IDs** | Continue applying force/torque to compiled body IDs. Distinguish robot bodies from additional scene props/free bodies; do not select the first free joint as robot identity. [Push][L-push] [Root selection][L-load] |
| Joint sliders and random pose | **Preserve** | They currently use each compiled hinge/slide's `qposadr`, not joint index; retain this correct mapping and current kinematic nature. Re-resolve IDs after compile. [Joint UI][L-joints] |
| Named poses and actuator targets | **Adapt / add explicit initialization** | Use declared keyframe semantics, or reference reset when absent; preserve ctrl/act/qvel/mocap state when supplied. Never assume joint order equals actuator/control order. [Pose code][L-reset] [Engine reset][M-sim] |
| Body frames, center of mass, hinge/slide axis diagnostics | **Preserve** | Existing compiled body `ipos`, `xpos/xmat`, joint `xanchor/xaxis` are appropriate; use runtime-owned ID mappings and selected edition data. [Diagnostics][L-diagnostics] |
| Collision primitive add/edit/reassign/delete/snap, mesh retention/removal | **Adapt authoring** | Read resolved geometry; edit identified source nodes while preserving every unrelated attribute/default/contact; retain temporary draft ownership and explicit export/overwrite. [Editor UI][L-editor-ui] [Editor store][L-editor-store] |
| Left/right collision mirror | **Preserve with scoped capability** | Keep the current validated `left_`/`right_` named-body workflow. Obtain resolved zero-pose frames from MuJoCo; offer an explicit mapping before extending beyond those names. Unsupported symmetry must be reported, not guessed. [Mirror][L-mirror] |
| Draft expiration/discard/stale detection/export/overwrite | **Preserve + adapt ownership** | Keep server-owned sessions and optimistic concurrency; bind them to source file/node locations plus configuration and closure digest. Hashing only the top scene misses included robot edits. [Draft store][L-editor-store] |
| Import, duplicate, rename, delete, set default | **Adapt** | Separate logical edition/configuration operations from authoring revision-file operations; copy dependency closures, update references, protect referenced files, and keep default configuration identity explicit. [Management][L-editions] |
| URDF inspection/physics/native viewer and collision editing | **Preserve + adapt path/runtime modules** | Continue disposable native compilation, retain authored URDF bytes, matching edition selection, supported package paths, fixed/free base choice, and fallback visual inspection. Feed selected scene/configuration through one adapter. [URDF runtime][L-urdf-runtime] [URDF browser][L-urdf-browser] |
| Download/preview URDF with saved MJCF collisions | **Preserve bounded export** | Resolve the selected edition's URDF, export robot colliders, and retain fail-closed frame/shape validation. A scene's floor/props are not URDF robot collisions. [Export][L-urdf-export] |
| Reload selected description; native-viewer status/error/one owned process; restart | **Preserve + adapt configuration** | Reload closure and metadata while retaining selected configuration/view; native viewer receives the same scene/pose; restart retains current deliberate draft-loss behavior. [Reload/restart][L-reload] [Native process][L-process] |
| Canvas recording and local rendering upload | **Preserve** | Existing stream/MP4/WebM/upload lifecycle is independent of source layout. Include configuration identity in filename or metadata and verify the rendered scene is correct. [Recording][L-recording] [Upload][L-upload] |
| Legacy Viser mesh browser, height calculator, PD document editor, capsule-extension utility | **Preserve scoped adapters** | Update hardcoded source paths where needed. These are existing specialized tools, not promises of all-family generalized control/retargeting. [CLI][L-cli] [Viser][L-viser] [Heights][L-heights] [Capsules][L-capsules] |
| MJX, mjlab/Isaac/hardware compatibility; broad arbitrary-plugin support | **Defer** | Do not infer support from native compilation or from siblings shipped upstream. Preserve source when copying an accepted bundle; add validation only if explicitly requested. |

## Initialization, scene ownership, and runtime fidelity

### Current native and browser initialization differ

Native `load_model` correctly delegates file/include/asset semantics to `MjModel.from_xml_path`. Its fallback is limited to legacy manifest models missing `meshdir`. Native `launch_mujoco` then constructs `MjData` with no named keyframe selection, no catalog spawn, and no JSON scene-floor injection. Workbench constructs `MjData`, calls reset, replaces the **first free joint's** seven qpos values with catalog spawn, zeros velocities, and calls forward. Neither MJCF path restores a selected keyframe's controls. Browser stepping never writes a controller target itself. [Native, lines 40–104][L-native] [Reset, lines 834–859][L-reset] [Root search, lines 2230–2238][L-load]

Observed native reference/keyframe differences:

| Native robot | Reference root Z; ctrl norm | First named keyframe root Z; ctrl norm |
| --- | --- | --- |
| G1 | .793; 0 | `stand`: .79; 1.8538608362 |
| G1 with hands | .793; 0 | `stand`: .79; 2.3752473555 |
| T1 | .7; 0 | `home`: .665; 2.1725560982 |
| Go2 | .445; 0 | `home`: .27; 4.0249223595 |

The successful WASM keyframe-reset probe reproduces these control norms. This does not show stable standing: only finite state after 50 steps was checked. A general initializer must use named compiled keyframe lookup plus `mj_resetDataKeyframe`, including targets/state, rather than selecting a pose by filename, assigning a qpos vector alone, or universally setting `ctrl=qpos`. Existing sliders/random pose explicitly change qpos and call forward; preserving them as kinematic inspection avoids pretending they implement motor/position/tendon controllers. [Engine keyframe/reset semantics][M-sim] [Slider/random-pose implementation][L-pose]

| Input/runtime route today | Floor and root behavior | Canonical-pair proposal |
| --- | --- | --- |
| CLI exact bare robot XML | Robot reference pose; robot-only geoms | Preserve exact-path behavior; configuration launch uses declared scene/pose |
| CLI exact paired scene XML | Native included robot plus scene floor/contact/options; reference pose unless initialized | Compile same entry point; apply optional declared initial pose |
| Workbench selected current robot XML | Adds first colliding JSON plane; replaces first free root with catalog spawn | Migrate the equivalent existing placement into the declared configuration; do not silently change physical state |
| Workbench paired scene XML today | Fails missing include; if transport alone is fixed, current preparation also adds generic floor to existing scene | Remove generic floor injection on canonical scene route; exactly one scene-owned environment |
| Workbench URDF runtime | Generates temporary MJCF, writes JSON gravity/root placement and first colliding plane | Preserve temporary conversion; compose explicitly selected environment without modifying authored URDF |

The local generated `astro_p2/scene.xml` already has an infinite plane at Z=-.75, whereas the browser uses the manifest JSON environment and spawn at Z=.75. These are different entry routes with their own placement convention, not duplicate canonical authorities to retain. Preserve each existing supported configuration's effective geometry/state during migration and make any desired origin/standing change a separate decision. Simply switching the CLI or browser to the other entry changes what is simulated. [Local paired scene][L-astro-scene] [Current catalog spawn][L-manifest] [JSON scene resolver][L-scenes]

### Rendering is not native MuJoCo visual equivalence

The current renderer's **primitive box visual works**: a compiled collision-disabled group-2 box of half-size `.1 .2 .3` produces a visible Three `BoxGeometry` with full extents `.2 .4 .6`. So “all visuals must be meshes” would be a false restriction. However, a valid native infinite plane `size="0 0 .1"` becomes `PlaneGeometry(0,0)` with zero extents. This is the floor convention in the real upstream and local paired scenes. An ellipsoid `.1 .2 .3` falls through to a sphere of radius `.1`, measured extents `.2 .2 .2`. These are proven renderer gaps, separate from compilation. [Renderer, lines 13–29][L-renderer] [G1 floor][U-g1-scene] [Local floor][L-astro-scene]

Presentation currently classifies geoms by nonzero contact masks, not `geom_group`: all contacting robot geoms get the uniform translucent collision material and start hidden; all world geoms get the `scene-terrain` layer. This is correct for the inspected G1/T1/Go2 visual/collision conventions, but group and collision semantics are different things. Preserve existing toggles while identifying robot visuals/collisions and scene objects explicitly; explicit contact pairs must remain physical even for masks-zero geoms. The actual material constructor reads `geom.rgba` alone; it does not read `matid`, material RGBA, texture/UV arrays, scene lights, cameras, or visual settings. The app uses fixed Three lights/camera/background. Thus successful native/WASM compilation preserves those engine inputs but does not prove faithful checker textures, material colors, haze, or scene viewpoints in browser output. Do not promise native-renderer parity; fix the concrete plane problem and choose a declared visual fidelity scope. [Material/classification][L-renderer] [Fixed app presentation][L-app-presentation]

## Source ownership and file lifecycle

### Compiled runtime is a view, not an editable source replacement

Keep compiled arrays for resolved geometry/frames/contact diagnostics, and keep the authored source graph for writes. `mj_saveLastXML` is already useful inside the **disposable URDF runtime**: it writes a compiled/canonicalized MJCF and is then augmented in a temporary file. It does not preserve include file ownership, original factorization, or source formatting for direct authoring. The existing collision writer instead reparses raw XML but reconstructs represented primitive geoms, causing the proven field loss. Neither is a complete source-editing solution. [URDF runtime, lines 111–164][L-urdf-runtime] [Editor writer][L-editor-write] [MuJoCo XML saving semantics][M-sim]

Proposal: resolve includes while recording each source node's owning path and structural identity; compile this same bundle; map runtime objects to source handles. Names can help, but valid unnamed geoms need handles such as `(relative source path, element path, source digest)`, rather than forced renaming of vendor files. Resolve inherited values with the engine for display; change only attributes necessary for the requested edit on the owning geom. Material/default/contact and untouched attributes remain in source. A no-op save should not rewrite any bytes. A draft can carry replacements in a temporary VFS/overlay at original relative paths; compile the complete selected scene before export/overwrite.

Keep existing server-owned draft sessions, TTL, format isolation, explicit save/export, and stale-write conflict behavior. Expand the revision from the selected XML's SHA to the referenced XML/dependency set used for compilation. A scene wrapper's SHA alone cannot detect an externally changed included robot. Default edit scope should identify robot geometry and its canonical robot file; scene geometry/contact editing needs its own explicit owner/scope rather than treating a scene worldbody as a robot link. Whether one save may update multiple source files remains a decision. [Sessions and stale check][L-editor-store] [Explicit overwrite route][L-overwrite]

### Current edition/revision management cannot directly become configuration management

The primary browser selects manifest logical edition IDs, but legacy `edition_path` resolves **discovered filename stems**, only in `mjcf_workspace` or a nested `mjcf/`. Nondefault canonical description paths are deliberately excluded from that discovery. The UI mutation buttons pass the active logical ID. Consequently many real logical editions cannot be duplicated/renamed/deleted through these handlers; putting authoritative files at the family root alone does not repair the identity mismatch. [Discovery/resolution][L-editions] [Mutation UI][L-mutate]

The isolated catalog proves it: logical `stable → robot.xml` rejects `duplicate_mjcf_edition("alpha", "stable", "copy")` with `MJCF edition 'stable' does not exist for alpha`. An unregistered `revision.xml` can be chosen by `set_default_mjcf_edition`; this changes **`editions.stable.mjcf` to `revision.xml` while `default_edition` remains `stable`**. That is revision promotion within an edition, not changing the default edition. Duplicate copies one XML; rename only conditionally updates the default model pointer; delete protects only that default pointer. These operations have no dependency/reference graph for scenes/configurations, so rename/delete must be adapted before use on authoritative paired bundles. [Exact operations, lines 203–438][L-editions]

Import is similarly one-file oriented: `_copy_referenced_meshes` copies direct mesh assets only, then copies the XML verbatim into a different folder. It does not copy included XML or file textures, and validation counts literal nodes without compiling the graph. The synthetic paired `scene.xml` imports successfully as a new family with reported zero bodies/one geom, but native loading the installed XML immediately fails `Error opening file 'robot.xml'`. This is a proven incomplete import, not a reason to flatten all incoming models. Import should accept a bundle and explicit entry points, copy the portable dependency closure with paths intact, compile it, and then register logical descriptions/configurations. On asset path collisions, compare content or keep separate namespaces rather than silently keeping existing bytes. [Import and validation][L-editions]

Exported MJCF drafts currently copy only the temporary XML, plus candidate metadata; a moved include-bearing source does not take its closure with it. The browser then attempts `selectEdition(exportedFilenameStem)`, although primary selection only accepts manifest logical editions. Preserve export as an authoring revision without silently adding a new logical robot edition; supply an explicit revision-preview path or registration action. [Draft export][L-editor-store] [Export UI][L-export-ui] [Primary selection][L-select]

### URDF compatibility stays a separate adapter

Authored URDF inspection, temporary MJCF physics, and collision transfer are three distinct existing capabilities. Preserve the current STL support and fixed/free-base declarations. The browser's URDF resolver supports packaged STL paths only; the server runtime rewrites meshes under the family `meshes` root, falling back to basename. These rules need the same portable bundle path resolver when URDF layout moves; a generic MuJoCo asset transport does not by itself extend URDF/Collada support. [URDF paths][L-urdf-paths] [Native rewrite][L-urdf-runtime]

The URDF collision exporter is deliberately bounded: it starts with the canonical URDF, replaces only collision elements, supports boxes/spheres/cylinders and capsule expansion, validates robot-frame correspondence, and refuses unrepresentable cases. It rejects includes, mesh collisions, world geoms, unnamed/unmapped bodies, and frame mismatch. Preserve this fail-closed behavior; feed it the selected **robot model**, not the paired scene with floor/props. Its current function takes `variant.urdf` (the default edition's URDF), while its server action selects an MJCF edition separately. Change the interface to explicit matching edition URDF + robot MJCF; otherwise nondefault export may use the default URDF. Full MJCF→URDF round-trip fidelity, solver/contact/actuator equivalence, or export for MJCF-only families is not an existing guarantee to create. [Exporter, lines 263–410][L-urdf-export] [Server export route][L-routes]

## Proposed implementation dependencies and acceptance gates

Use a small deep module interface; the complexity belongs behind it, rather than repeated in CLI, source endpoints, draft compilation, and browser loading:

1. `resolve(configuration) → source bundle`: authoritative robot/scene paths, optional pose, exact family-relative bytes/asset paths, source handles, dependency digest. Validate containment within the portable family. An exact XML file can resolve to an anonymous entry for existing CLI usage.
2. `compile(bundle, native|wasm) → runtime`: named entry point and path-preserving dependency access, compiled indices/names, capabilities, precise errors. These are already two real adapters; do not build a speculative universal simulator abstraction.
3. `initialize(runtime, initial_pose?)`: reference reset when absent; declared keyframe/state when present; shared semantics for CLI, browser, draft diagnostics, reset, and native launch.
4. `edit(draft, source_handle, operation)` and explicit export/overwrite: preservation-aware source edits, closure concurrency check, complete scene validation, clear destination. Keep this an authoring interface separate from runtime arrays.

Implement in that dependency order: identity/configuration resolution → portable closure and native/WASM parity → initialization → compiled/source mapping → ownership-preserving edits and file lifecycle → rendering/UI/compatibility-path migration. Import and rename depend on closure resolution; safe overwrite depends on source mapping and compile validation; contacts/diagnostics/pushing depend on runtime IDs and the chosen scene. The final family-root move depends on these adapters, not vice versa.

| Acceptance gate | Required evidence |
| --- | --- |
| Seven-family preservation | Enumerate all current manifest descriptions, aliases, URDF-only and MJCF-only entries; same supported descriptions remain selectable/loadable; existing command entry points remain usable |
| Paired authority | Editing a canonical robot is visible through both CLI and browser after reload; no sync/generated sibling silently overwrites it; native launch uses selected scene and optional pose |
| Dependency semantics | G1/T1/Go2 scenes match native/WASM dimensions, geom/body names, options, masks/pairs/exclusions, keyframe counts; nested fixture preserves both duplicate-basename meshes and PNG; repeated section fixture retains all entries |
| Source portability | Copy each supported family to an unrelated temporary directory; load every declared scene/model without catalog, repository symlinks, or sibling-family access |
| Initial state | Compare qpos, qvel, ctrl, act, mocap and time for reference reset and selected pose across native/WASM/draft reset; missing pose is an error, no implicit home/stand selection; robot identity works when scene has another free body |
| Joint/control mapping | Existing scalar sliders use qpos addresses after a free base; ball/free joints are not scalar sliders; reordered joints/actuators and a non-joint actuator fixture cannot receive positional ctrl by accidental index |
| Physics/contacts/push | Check scene solver/timestep/gravity/pairs survive; same short deterministic smoke under each adapter; contact markers reference current runtime; pushing maps to selected compiled body and clears force on reset/disposal |
| Collision display/edit semantics | Defaults/childclass/inherited foot sizes work; unnamed colliders are editable via source handles; masks-zero explicit-pair geoms remain accounted for; visual group classification does not alter physics |
| Source preservation | No-op draft/save is byte-identical; one size change preserves material/friction/solref/contype/conaffinity/group/default class/inertial/contact/keyframe data; compile edited configuration before canonical overwrite |
| Ownership/concurrency | Included-file changes cause stale conflict; editing one configuration with shared robot explains affected configurations; scene props are not silently written into robot; export preserves valid closure and does not create a logical edition implicitly |
| File lifecycle | Logical default change differs from revision promotion; rename updates every declared reference or refuses; referenced model/scene deletion refuses; import failure leaves no partial registration; closure-preserving import compiles |
| URDF | Existing STL and fixed/free runtime features remain; authored URDF hashes unchanged by physics; matching-edition collision export keeps unrelated URDF nodes; unsupported shapes/frames fail with existing reports |
| Presentation | Primitive box visual remains visible; native `size=0 0 ...` plane is visible at declared pose; declared ellipsoid behavior is accurate or explicitly unsupported; record browser scene after floor fix, not compilation success alone |
| Reload/native/restart/recording | Same-ID reload invalidates included XML/asset caches and retains configuration/view; stale runtime is disposed on failure; native viewer one-process/status/error behavior preserved; recordings upload and are playable; restart closes owned resources as today |

Only short finite-state simulation, dimensions, and selected geometric/editor behaviors were measured here. Native GUI launch, browser GPU rendering, actual contact markers/pointer gestures, video encoding, broad performance, hardware behavior, and all upstream bundles were not executed. These gates specify what the subsequent implementation must demonstrate, rather than claiming that a source-layout choice already guarantees them.

### Durable minimal reproduction

The following snippets reconstruct the central probes even if `/tmp/workbench-compat-probes` has been removed. Run from this repository. `UPSTREAM`/the Node argument must point to a checkout of the pinned upstream commit with G1/T1/Go2 assets available. Each sample uses the existing installed dependencies.

```python
# .venv/bin/python, from the repository root
from pathlib import Path
from tempfile import TemporaryDirectory
import mujoco
from menagerie_x.workbench.mjcf_collisions import (
    MjcfCollisionDraftStore, load_mjcf_collision_document,
)
UPSTREAM = Path('/tmp/menagerie-upstream-research/checkout')
for family, robot in [('unitree_g1', 'g1.xml'),
                      ('booster_t1', 't1.xml'), ('unitree_go2', 'go2.xml')]:
    for name in [robot, 'scene.xml']:
        source = UPSTREAM / family / name
        m = mujoco.MjModel.from_xml_path(str(source))
        print(source, m.nq, m.nv, m.nu, m.nbody, m.ngeom)
        try:
            doc = load_mjcf_collision_document(source)
            print('editor', len(doc.links), len(doc.collisions))
        except Exception as exc:
            print(type(exc).__name__, str(exc))
with TemporaryDirectory() as directory:
    source = Path(directory) / 'robot.xml'
    source.write_text('''<mujoco><default><geom friction=".7 .02 .03"/></default>
      <worldbody><body name="b"><geom name="g" type="sphere" size=".1"
      friction=".9 .04 .05" solref=".01 1" contype="2" conaffinity="4"/>
      </body></worldbody></mujoco>''')
    store = MjcfCollisionDraftStore()
    try:
        session = store.create(source)
        store.update(session.identifier, source, session.document.revision,
                     session.primitives, sorted(session.retained_mesh_ids))
        before = mujoco.MjModel.from_xml_path(str(source))
        after = mujoco.MjModel.from_xml_path(str(session.temporary))
        print('before/after friction', before.geom_friction, after.geom_friction)
        print('before/after masks', before.geom_contype, after.geom_contype,
              before.geom_conaffinity, after.geom_conaffinity)
    finally:
        store.close()
```

Expected sphere output: friction `[.9, .04, .05] → [.7, .02, .03]`; masks `2/4 → 1/1`. For WASM save the following as `/tmp/bundle-compile.mjs`, then run `node /tmp/bundle-compile.mjs /path/to/pinned/upstream/unitree_g1` (repeat for T1 and Go2):

```javascript
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const { default: load } = await import(pathToFileURL(path.resolve(
  'src/menagerie_x/workbench/web/node_modules/@mujoco/mujoco/mujoco.js')));
const mj = await load();
const directory = path.resolve(process.argv[2]);
function walk(dir, prefix = '') {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const name = path.join(prefix, entry.name);
    return entry.isDirectory() ? walk(path.join(dir, entry.name), name) : [name];
  });
}
const vfs = new mj.MjVFS();
for (const name of walk(directory))
  vfs.addBuffer(name, new Uint8Array(fs.readFileSync(path.join(directory, name))));
const model = mj.MjModel.from_xml_path('scene.xml', vfs);
const data = new mj.MjData(model);
if (model.nkey) mj.mj_resetDataKeyframe(model, data, 0);
for (let i = 0; i < 50; i++) mj.mj_step(model, data);
console.log(mj.mj_versionString(), model.nq, model.nv, model.nu,
            model.nbody, model.ngeom, [...data.qpos].every(Number.isFinite));
data.delete(); model.delete(); vfs.delete();
const empty = new mj.MjVFS();
try {
  const unexpected = mj.MjModel.from_xml_string(
    fs.readFileSync(path.join(directory, 'scene.xml'), 'utf8'), empty);
  unexpected.delete();
} catch (error) { console.log('current dependency-set failure:', error.message); }
finally { empty.delete(); }
```

## Decisions to resolve before implementation

- Where explicit configurations/default configuration are recorded, and how they relate to existing logical editions and authoring revisions.
- Whether no initial pose means reference reset (recommended) and which existing configurations explicitly select a keyframe versus preserving their present spawn convention.
- Whether collision saves target only canonical robot geometry, and how scene-owned geometry/contact edits are requested; whether any operation may change multiple shared source files.
- Whether revision export is a complete portable bundle, a family-local sibling using existing assets, or both explicit options; how revisions are previewed without becoming editions.
- The browser's declared visual fidelity scope beyond correcting the proven infinite-plane failure; retaining current Three presentation is compatible with engine correctness only if it is described accurately.
- URDF placement and derivation/provenance policy, while retaining current authored URDF and bounded collision export capabilities.

[L-deps]: ../../pyproject.toml#L1-L16
[L-webdeps]: ../../src/menagerie_x/workbench/web/package.json#L1-L10
[L-cli]: ../../src/menagerie_x/cli.py#L20-L158
[L-assets]: ../../src/menagerie_x/assets/__init__.py#L157-L334
[L-native]: ../../src/menagerie_x/commands/mujoco.py#L40-L104
[L-load]: ../../src/menagerie_x/workbench/web/app.js#L2160-L2276
[L-routes]: ../../src/menagerie_x/workbench/server.py#L671-L733
[L-select]: ../../src/menagerie_x/workbench/web/app.js#L2521-L2616
[L-reset]: ../../src/menagerie_x/workbench/web/app.js#L834-L891
[L-joints]: ../../src/menagerie_x/workbench/web/app.js#L1157-L1261
[L-pose]: ../../src/menagerie_x/workbench/web/app.js#L900-L995
[L-push]: ../../src/menagerie_x/workbench/web/app.js#L1007-L1085
[L-renderer]: ../../src/menagerie_x/workbench/web/mjcf-renderer.js#L13-L145
[L-app-presentation]: ../../src/menagerie_x/workbench/web/app.js#L93-L115
[L-editor-parse]: ../../src/menagerie_x/workbench/mjcf_collisions.py#L284-L397
[L-editor-validate]: ../../src/menagerie_x/workbench/mjcf_collisions.py#L400-L449
[L-editor-write]: ../../src/menagerie_x/workbench/mjcf_collisions.py#L463-L506
[L-editor-store]: ../../src/menagerie_x/workbench/mjcf_collisions.py#L534-L721
[L-editor-ui]: ../../src/menagerie_x/workbench/web/app.js#L1363-L2072
[L-mirror]: ../../src/menagerie_x/workbench/mjcf_collisions.py#L169-L281
[L-overwrite]: ../../src/menagerie_x/workbench/server.py#L953-L972
[L-diagnostic-load]: ../../src/menagerie_x/workbench/web/app.js#L2098-L2158
[L-diagnostics]: ../../src/menagerie_x/workbench/web/diagnostics.js#L198-L254
[L-contacts]: ../../src/menagerie_x/workbench/web/contact-visualizer.js
[L-editions]: ../../src/menagerie_x/assets/editions.py#L65-L438
[L-mutate]: ../../src/menagerie_x/workbench/web/app.js#L2387-L2455
[L-export-ui]: ../../src/menagerie_x/workbench/web/app.js#L2022-L2072
[L-urdf-runtime]: ../../src/menagerie_x/workbench/urdf_runtime.py#L55-L164
[L-urdf-browser]: ../../src/menagerie_x/workbench/web/app.js#L2278-L2365
[L-urdf-paths]: ../../src/menagerie_x/workbench/web/urdf-utils.js#L1-L9
[L-urdf-export]: ../../src/menagerie_x/assets/urdf_collision_export.py#L263-L414
[L-reload]: ../../src/menagerie_x/workbench/web/app.js#L2617-L2697
[L-process]: ../../src/menagerie_x/workbench/server.py#L112-L243
[L-recording]: ../../src/menagerie_x/workbench/web/scene-recording.js
[L-upload]: ../../src/menagerie_x/workbench/server.py#L394-L441
[L-viser]: ../../src/menagerie_x/commands/viser.py#L18-L38
[L-heights]: ../../src/menagerie_x/tools/calc_heights.py#L126-L144
[L-capsules]: ../../src/menagerie_x/commands/urdf_capsules.py
[L-astro-scene]: ../../astro_p2/scene.xml#L1-L21
[L-manifest]: ../../manifest.json
[L-scenes]: ../../src/menagerie_x/assets/scenes.py#L215-L245
[U-g1]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1.xml
[U-t1]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/booster_t1/t1.xml
[U-go2]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_go2/go2.xml
[U-g1-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/scene.xml
[U-t1-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/booster_t1/scene.xml
[U-go2-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_go2/scene.xml
[M-xml]: https://github.com/google-deepmind/mujoco/blob/b85fdca54f0e0038b804af146a0b4e94199e00d0/doc/XMLreference.rst
[M-sim]: https://github.com/google-deepmind/mujoco/blob/b85fdca54f0e0038b804af146a0b4e94199e00d0/doc/programming/simulation.rst
[M-wasm]: https://github.com/google-deepmind/mujoco/blob/b85fdca54f0e0038b804af146a0b4e94199e00d0/wasm/codegen/templates/bindings.cc
