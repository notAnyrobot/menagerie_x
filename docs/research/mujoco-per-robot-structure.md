# Per-robot structure in MuJoCo Menagerie

Research date: 2026-10-30. Scope: `unitree_g1`, `booster_t1`, and the implications for the existing seven Menagerie X families. This is evidence for a design interview, not an approved migration or a physics change.

## Revisions and method

Upstream `HEAD` was checked with `git ls-remote` and remains **`f3b6013629c7b94f8ee93fd977b161fa8350f9bc`**, committed 2026-10-23. Both user-provided `main` URLs were opened in the web tool, but the rendered G1 listing omitted `g1_mjlab.xml`; the pinned Git tree and files below are authoritative for this report. The sparse checkout at `/tmp/menagerie-upstream-research/checkout` was extended with T1, without fetching the other robot families. Local comparisons use **`27d9e7c0f3d58961f97af8cdb03acffa6b07a878`**. Sources: [upstream revision][U], [G1 tree][G1-tree], [T1 tree][T1-tree], [local revision][L].

Source inspection was supplemented by compiling all **nine** XMLs in these two upstream directories using the existing local **MuJoCo 3.11.0** installation. All four `scene*.xml` files then completed 0.1 seconds with the upstream deterministic Halton control perturbation and zero MuJoCo warnings. These are native MuJoCo checks, not MJX or mjlab integration tests, sustained standing tests, or hardware validation. The smoke-test procedure comes from [upstream `model_test.py`][U-model-test]; per-file results appear below.

Current MuJoCo semantics were retrieved through Context7. To keep the supporting source immutable, API explanations below cite MuJoCo **3.11.0**, whose tag resolves to `b85fdca54f0e0038b804af146a0b4e94199e00d0`: [XML reference source][M-xml], [simulation documentation source][M-sim].

## The useful shared structure

Both families are small, portable description bundles: a family directory, flat complete robot XMLs, scene XMLs that include a sibling robot, local `assets/`, a README, a changelog, a license, and preview images. **Neither inspected family contains a nested `mjcf/`, `urdf/`, `source/`, `generated/`, hand subpackage, or specialized backend subdirectory.** G1's hands, MJX, and mjlab variants are sibling XMLs sharing the same asset directory. Exact filenames, including all assets, are recorded in the appendix. Sources: [G1 tree][G1-tree], [T1 tree][T1-tree].

The strongest finding for Menagerie X is **one directly maintained, runnable MJCF per supported model choice**, with descriptive sibling filenames and shared assets. Upstream does not retain both an editable nested MJCF and a rewritten flat copy of the same MJCF in these families. It also does not attempt to generate every model from a common robot schema. This is an observation about these examples, not a requirement imposed on all Menagerie contributors. Sources: [G1 files][G1-tree], [T1 files][T1-tree], [derivation notes][G1-readme], [T1 derivation notes][T1-readme].

### Actual entry points

Counts below are observations from the pinned XML and the native compilation described above. “Internal DOF” excludes the free base; `nq` and `nv` include it. Sensor count means sensor elements, not scalar output dimensions.

| Robot file | Internal DOF; `nq/nv/nu` | Scene | Contacts and poses | Evidence |
| --- | --- | --- | --- | --- |
| `g1.xml` | 29; `36/35/29` | `scene.xml` | Normal contact masks; robot owns `stand` | [robot][G1-model], [scene][G1-scene] |
| `g1_with_hands.xml` | 43; `50/49/43` | `scene_with_hands.xml` | Adds 14 finger hinges; robot owns `stand` | [robot][G1-hands], [scene][G1-hands-scene] |
| `g1_mjx.xml` | 29; `36/35/29` | `scene_mjx.xml` | Robot disables dynamic contacts; scene owns 49 explicit pairs plus `home`/`knees_bent` | [robot][G1-mjx], [scene][G1-mjx-scene] |
| `g1_mjlab.xml` | 29; `36/35/0` | None shipped | Active collision masks, four body exclusions; no actuators, solver options, or keyframes | [robot][G1-mjlab], [purpose in changelog][G1-changelog] |
| `t1.xml` | 23; `30/29/23` | `scene.xml` | Normal contact masks; robot owns `home` | [robot][T1-model], [scene][T1-scene] |

The catalog registers only `unitree_g1/g1` and `booster_t1/t1` as their gallery entries. This does **not** mean the other complete G1 XMLs are disposable revisions: the package registry builder considers every compilable top-level XML as an entry point, while the gallery chooses a primary model and preview. “Default gallery entry,” “shipped model variant,” and “tested scene” are different concepts. Sources: [catalog][U-catalog], [registry discovery/defaults][U-registry], [scene test discovery][U-model-test].

## What each XML owns

### Compiler, defaults, assets, and kinematics

Every robot XML uses `angle="radian"` and `meshdir="assets"`; T1 and mjlab also explicitly set `autolimits="true"`. Assets are file-backed STL meshes and local materials. G1's normal model declares 35 meshes, its hand model 49, and T1 24. G1's family directory has 51 STL files across its variants; T1 has 24. Mesh declaration names may differ from filenames, for example `torso_link` refers to `torso_link_rev_1_0.STL`. Preserve these references rather than inferring model identity solely from filenames. Sources: [G1 model][G1-model], [hands model][G1-hands], [mjlab model][G1-mjlab], [T1 model][T1-model], [G1 asset tree][G1-assets], [T1 asset tree][T1-assets].

G1 uses a parent `g1` default class and `childclass="g1"` on the pelvis, with nested `visual`, `collision`, and `foot` classes. Its base and hand models keep most axes, limits, inertials, and per-joint force ranges on individual elements. MJX additionally factors anatomical joint/actuator settings into classes such as `hip_pitch`, `knee`, `ankle`, and `wrist`. T1 instead uses a compact `t1` class with `visual`/`collision` children; most physical variation remains explicit. These are different levels of factoring, not evidence for one universal class hierarchy. Sources: [G1 defaults and joints][G1-model], [MJX defaults][G1-mjx], [T1 defaults and joints][T1-model].

G1's floating root is `pelvis` at `(0,0,0.793)`, with named `floating_base_joint`. Tree order is left leg, right leg, waist, then left/right arms; the hand version adds thumb/index/middle chains at each wrist. T1's root is `Trunk` at `(0,0,0.7)` with an unnamed free joint; it orders head, arms, then waist and legs. G1 has 30 explicit body inertials, the hand variant 44, and T1 24: all bodies in these robot trees have explicit inertials. Inertial frames include per-link positions, quaternion orientations, masses, and diagonal inertia tensors. Their detailed values, naming, axes, and traversal order belong to the particular robot. Sources: [G1 body tree][G1-model], [hands body tree][G1-hands], [T1 body tree][T1-model].

**Implication:** preserve original body/joint names and physics; use named mappings when application order differs from XML traversal. Local Dex already documents that exact distinction in `joint-order.json` and its README. Defaults can improve readability, but a layout migration is not permission to change inertia inference, actuator force limits, joint axes, or physical constants. Sources: [local Dex README][L-Dex-readme], [local joint order][L-Dex-order], [MuJoCo inertia semantics][M-xml].

### Visuals, collisions, and controls

The standard G1 models put collision-disabled visual meshes in group 2, collision geoms in group 3, and sites in group 5. G1 mixes mesh and primitive collision geometry, with four 5 mm sphere contacts per foot. T1 also uses visual group 2/collision group 3/site group 5, but its colliders are simplified boxes, cylinders, and a head sphere, including one box per foot. Matching visual/collision group conventions therefore does not imply matching contact approximations. Sources: [G1 defaults/feet][G1-model], [G1 hands][G1-hands], [T1 defaults/geoms][T1-model].

MJX uses manually designed capsule/sphere body colliders, foot capsules, and additional foot boxes in group 4. Its parent geom default sets `contype="0" conaffinity="0"`; the scene explicitly selects allowed contacts. Mjlab changes this to active collision masks, seven foot capsules per foot, four exclusions, and no foot boxes. These are physical/backend adaptations, not formatting differences. Sources: [MJX robot][G1-mjx], [MJX contact pairs][G1-mjx-scene], [mjlab robot][G1-mjlab], [G1 changelog][G1-changelog].

A geom's `group` mainly controls rendering and can affect inferred inertias at compilation; it does **not** select collision filtering at runtime. Collision masks and explicit pairs have different semantics. Thus reassigning groups can affect a viewer and potentially mass inference, while copying masks or pair lists can change physics. Source: [MuJoCo geom group, contact masks, and compiler inertia documentation][M-xml].

G1's base and hand files have one position actuator per hinge, names matching joint names, with parent settings `kp=500`, `dampratio=1`, `inheritrange=1`, joint armature `0.01`, and friction loss `0.3`. MJX uses lower gains (`kp=75`, `kv=2`, with ankle/wrist overrides to `kp=20`), per-anatomy armatures, timestep `0.004`, five solver iterations, and eight line-search iterations. T1 uses `kp=75`, `kv=5`, joint armature `0.005`, and friction loss `0.1`; per-joint actuator-force limits remain explicit. These are examples to document, not defaults to impose locally. Sources: [base G1][G1-model], [hands][G1-hands], [MJX][G1-mjx], [T1][T1-model].

Sensor interfaces differ too: base/hand G1 have torso and pelvis gyro/accelerometer pairs (four sensors); MJX has fourteen sensors spanning local/global velocities, accelerations, orientations, and up vectors; mjlab has five pelvis/root sensors including subtree angular momentum; T1 has three IMU sensors at its trunk site. There is no shared mandatory sensor schema in these examples. Sources: [G1 sensors][G1-model], [MJX sensors][G1-mjx], [mjlab sensors][G1-mjlab], [T1 sensors][T1-model].

### Scene ownership and origin conventions

The normal scenes include the sibling robot and own the floor, procedural ground/sky textures, haze, headlight, and camera viewing parameters. Both families put the floor at world Z=0. The robot XMLs themselves retain lights; MJX and mjlab also retain tracking cameras. T1's scene adds another light. Therefore “all illumination must move to scenes” is a possible local policy, not a rule these upstream examples consistently follow. Sources: [G1 robot][G1-model], [G1 scene][G1-scene], [T1 robot][T1-model], [T1 scene][T1-scene], [MJX][G1-mjx], [mjlab][G1-mjlab].

The important exception is `scene_mjx.xml`: it owns **all 49 explicit contact pairs**, including self-contacts as well as robot–floor contacts, and its two keyframes. The standalone `g1_mjx.xml` compiles but does not by itself provide these contacts or poses. A future scene composer must deliberately carry this configuration when reusing that robot. Conversely, mjlab places its four robot self-collision exclusions inside the robot file and expects actuators/options to be specified programmatically. “Robot XML compiles” is a weaker promise than “robot XML contains a complete ready-to-run task configuration.” Sources: [MJX robot][G1-mjx], [MJX scene][G1-mjx-scene], [mjlab intent][G1-changelog], [mjlab exclusions][G1-mjlab].

Reference configuration and named poses are also separate:

| Model | Root Z in the robot/reference configuration | Named pose root Z | Owner |
| --- | --- | --- | --- |
| Standard/hand G1 | 0.793 | `stand`: 0.79 | Robot |
| MJX G1 | 0.793 | `home`: 0.783675; `knees_bent`: 0.755 | Scene |
| Mjlab G1 | 0.793 | None shipped | — |
| T1 | 0.7 | `home`: 0.665 | Robot |

Sources: [standard G1][G1-model], [hands][G1-hands], [MJX robot][G1-mjx], [MJX scene][G1-mjx-scene], [mjlab][G1-mjlab], [T1][T1-model]. These pose vectors also set joint angles and, where actuators exist, matching control targets. A pose called `home` or `stand` is not automatically selected merely by loading the XML: normal reset uses `qpos0` and zero controls; an application must select the keyframe explicitly. Sources: [MuJoCo reset semantics][M-sim], [keyframe semantics][M-xml].

Do not infer a new requirement that every local robot's root be translated to a standing pelvis height or that every model acquire a `home` keyframe. Local scenes currently preserve source root frames by lowering their floor by `initial_root_z - manifest_spawn_z`; this is an intentional existing convention and differs from these upstream Z=0 scenes. Source: [local scene generator][L-sync], [compatibility rationale][L-upstream].

## Sources, dependencies, and maintenance

G1's README starts from Unitree's MJCF, describes manual default factoring, adds a standing pose and position actuators, and applies similar work to the hand model. Its changelog records the 2024 model update against Unitree revision **`c20ca8f1fe5e519474c6c8d10b1ce5c719dd7a65`**, then separately records MJX and mjlab adaptations. The vendor revision is historical provenance, not the Menagerie revision; the README's source links themselves target a moving branch. Sources: [README][G1-readme], [changelog][G1-changelog].

T1 starts from Booster's `T1_serial.urdf`: the documented recipe adds MuJoCo import compiler settings, imports and saves MJCF, adds a free base and IMU, adds a home pose, adds stabilization terms, and switches to `implicitfast` plus position controls. The checked-in runtime compiler need not repeat URDF conversion settings. The family ships neither that source URDF nor a conversion program nor a source commit/hash ledger. Its source link points to a moving branch, so an exact original Booster revision cannot be established from these files alone. Sources: [README][T1-readme], [runtime XML][T1-model], [complete tree][T1-tree].

G1 keeps its BSD-3-Clause text at exactly `LICENSE`; T1 keeps Apache-2.0 there. Upstream layout checks explicitly require the exact `LICENSE` filename, README, changelog, and at least one `scene*.xml` per robot directory. The contribution guide says to ship `scene.xml`, while the test permits other `scene*.xml` names and documented exemptions. These checks do not mandate a scene for **every** sibling model, as the scene-less mjlab file demonstrates. Sources: [G1 license][G1-license], [T1 license][T1-license], [layout test][U-layout-test], [contribution guide][U-contributing], [G1 tree][G1-tree].

All referenced robot assets in these examples live inside their family; no external sibling family, absolute mesh path, symlink, or network download is required by these XMLs. The only file includes are the scenes' sibling robot includes; the robot files are complete MJCFs. Their colocated layout avoids path rewriting when switching between model and scene. MuJoCo's include and compiler mesh-directory rules depend on the main XML file's location, so moving a scene to another directory is not mechanically equivalent. Sources: [G1 XMLs][G1-tree], [T1 XMLs][T1-tree], [MuJoCo include/meshdir semantics][M-xml].

The upstream registry discovers compilable flat XMLs, collects their file dependency closures, copies those closures into a temporary family directory, and recompiles entry points before packaging. It retains README/license/changelog and patches, but does not retain arbitrary authoring material or preview images by default. Menagerie X should preserve its URDFs and provenance records explicitly if it ever adopts such packaging; copying that builder unchanged would not preserve the local product's full workspace. Source: [registry builder][U-registry].

Upstream asks for model-specific changelog entries, shared-tool changes in the root changelog, and XML formatting/default factoring. CI compiles and steps top-level `scene*.xml` for 0.1 seconds under deterministic controls; it separately derives/tests its package registry, while pre-commit checks XML/style and license aggregation. This does not validate every robot-only file dynamically, select every keyframe, establish long-term standing, or test MJX execution. Sources: [contribution guide][U-contributing], [model tests][U-model-test], [build workflow][U-build], [hooks][U-hooks].

Do not copy documentation uncritically: T1's changelog title currently names Crazyflie rather than T1, and both READMEs advertise MuJoCo 2.3.4. Their current XMLs use control attributes such as `inheritrange`, `dampratio`, and `kv`; this research verified 3.11.0, **not** whether every current attribute works at the advertised minimum. Sources: [T1 changelog][T1-changelog], [T1 README][T1-readme], [G1 README][G1-readme], [current actuator syntax in G1][G1-model] and [T1][T1-model].

## Shared contract versus choices to keep local

| Category | Evidence-backed common contract or practice | What remains robot/application specific |
| --- | --- | --- |
| Family bundle | Portable relative dependencies, docs, license, changelog, usable scene | Exact model filenames, asset naming, source-record depth |
| Entry points | Complete sibling MJCFs; default scene includes one | How many supported variants, whether a backend file has a scene |
| MJCF organization | Compiler/defaults/assets/body tree plus needed interfaces; defaults reduce repetition | Exact section order (T1 places assets before defaults), class hierarchy |
| Body description | Explicit source-informed kinematics/inertials | Root body/name/height, axes, traversal order, tensors, DOF count |
| Collision presentation | Clear visual/contact roles | Geom groups, shapes, masks, pairs, self-contact policy |
| Controls/sensors | Document the interface that exists | Presence, mode, names, gains, sensors, programmatic configuration |
| Poses | Named poses where useful | Names, placement in robot vs scene, selected application default |
| Validation | Compilation, dependency completeness, short warning-free scene stepping | Longer/contact/hardware/backend checks required by specific changes |

The table synthesizes [G1 model][G1-model], [MJX model][G1-mjx]/[scene][G1-mjx-scene], [mjlab][G1-mjlab], [T1 model][T1-model]/[scene][T1-scene], [layout tests][U-layout-test], and [simulation tests][U-model-test]. It is not a proposal to homogenize the robots' physical descriptions.

## Precise gaps and decisions for Menagerie X

The earlier refactor already provides the seven top-level families, shared `assets/`, docs, flat native model/scene entry points, and compatibility links. The manifest remains the sole catalog authority: 12 logical editions, ten cataloged MJCFs; Astro 29 and the racket edition remain cataloged URDF-only. This investigation does not reopen those agreed boundaries or replace the CLI/Workbench. Sources: [manifest][L-manifest], [catalog][L-catalog], [existing compatibility choices][L-upstream], [inventory tests][L-tests].

### 1. Decide canonical file ownership first

For P1, P2, G1, Atom, and SOMA, the manifest and runtime still point to nested `mjcf/` sources; `sync-menagerie.py` rewrites flat sibling copies with `meshdir="assets"` and removes source world planes. Dex already has its authoritative MJCF at the family root, so its model entry point is the source itself. Editing a generated flat copy in other families is lost on the next sync. Upstream's inspected bundles have no such dual editable location. Sources: [manifest][L-manifest], [catalog][L-catalog], [sync generator][L-sync], [local G1 explanation][L-G1-readme], [upstream trees][G1-tree].

**Recommendation for the interview:** prefer flat, directly maintained runtime MJCFs for supported models, while retaining vendor snapshots separately as immutable references. This offers the upstream browsing/editing experience and one clear Workbench save target. The alternative is retaining nested authority and generated public copies, which preserves current source bytes but requires unmistakable generated-file markers, deterministic regeneration, and consistent editor routing. Converting those sources to new canonical runtime files must preserve original snapshot hashes as **source hashes**, and record separate runtime artifact hashes; it is not license to erase provenance. This recommendation follows the ownership contrast above, not an upstream mandate.

### 2. Separate supported model choices from saved work

Local logical editions already represent actual choices: P2 primitive/mesh/halfway colliders, G1 hands/box-feet reference, P1 30/27/racket. However, Workbench's `list_mjcf_editions` also discovers valid XMLs in its managed workspace, while native catalog scenes come only from manifest editions. `mjcf_workspace` points Dex at its family root. Root globs would therefore risk treating scratch conversions, drafts, generated scenes, and saved revisions as the same kind of supported model. Sources: [manifest][L-manifest], [edition discovery][L-editions], [catalog][L-catalog].

**Recommendation:** keep explicit supported edition IDs/defaults in the manifest; store provenance snapshots and draft/review revisions in clearly distinct places. Decide whether user-created Workbench revisions become visible immediately as workspace choices or require promotion to a supported catalog model. Upstream's `g1_mjx.xml` and `g1_mjlab.xml` show meaningful application variants with the same 29 DOF; hardware DOF alone is not a sufficient variant identity. Sources: [G1 changelog][G1-changelog], [MJX][G1-mjx], [mjlab][G1-mjlab].

### 3. Define independent versus derived URDF/MJCF ownership

Dex's MJCF has intentional collision refinements and a `fist` pose beyond its URDF; its documentation explicitly warns that the converter overwrites those changes. Astro 29's root conversion is separately maintained despite not being a cataloged MJCF. Imported Atom and SOMA have no local URDF source. A blanket “URDF is canonical and regenerates everything” rule would lose legitimate work. Sources: [Dex MJCF notes][L-Dex-mjcf], [Astro 29 MJCF notes][L-Astro29-mjcf], [manifest][L-manifest].

**Recommendation:** declare derivation per artifact: imported snapshot, reproducibly generated output, independently maintained MJCF derivative, or workspace draft. Capture input hashes, tool/version/options, output hash, and known manual delta where those facts exist. Do not make `source_revision` ambiguously mean both a Git commit and a content SHA-256; the current manifest already contains both kinds of provenance. Source: [manifest provenance records][L-manifest].

### 4. Decide scene semantics without changing coordinates silently

Current native scenes supply a floor using manifest standing height while source roots remain unchanged. CLI/Workbench still obtain models from the manifest source path, and Workbench has its own scene composition. Decide whether the flat scene is a presentation artifact, the supported native simulation entry point, or a reusable task configuration with contacts/poses. G1 MJX proves that these promises can diverge. Sources: [local sync][L-sync], [native loader][L-loader], [Workbench server][L-workbench], [MJX scene][G1-mjx-scene].

**Recommendation:** let robot geometry, inertials, joints, controls, and intrinsic exclusions stay with the model; let terrain/environment contacts and task poses stay with scenes when needed. If self-contact pairs or initial poses live in a scene, explicitly document that dependency. Preserve source coordinate frames now; any new Z=0 ground convention should be a separately agreed transform contract with keyframes/spawn metadata checked together.

### 5. Keep physics/interface normalization out of the structural change

Local P1 has position actuators, G1 has its imported actuators, SOMA has 66 motor-actuated internal DOF, while P2, Dex, and Atom currently have no actuators. Visual/collision groups also differ: P1/P2/Dex use 1/3, Atom uses 0/3, local G1 uses visual 1 with default-group collision geoms, and SOMA uses default-group primitive geoms. Dex's `fist` is a specific application pose. These differences are not directory defects. Sources: [P1][L-P1], [P2][L-P2], [Atom][L-Atom], [SOMA][L-SOMA], [local G1][L-G1], [Dex notes][L-Dex-mjcf].

**Recommendation:** document existing capabilities and preserve names, indices, masks, groups, gains, inertials, and keyframes during ownership/path changes. If a consistent viewer group scheme is wanted, decide that separately and check visibility plus inertia inference; do not introduce standard actuators or `home` poses merely to resemble G1/T1.

### 6. Define the finished family bundle and checks

The local README/changelog/license-scope pattern already exists, including unresolved licensing records and mixed-source notices. Preserve it: adopting the upstream exact `LICENSE` filename cannot manufacture a missing grant. Preview images, URDFs, retargeting configuration, vendor snapshots, and review JSONs serve different purposes; decide which belong in a portable consumer bundle and which remain authoring evidence. Sources: [local licensing][L-licensing], [compatibility choices][L-upstream], [local Dex README][L-Dex-readme], [upstream registry retention][U-registry].

Existing local tests already verify seven families/12 editions, source/generated physics equality, exactly one scene floor, deterministic sync, and 0.1-second no-warning stepping. If canonical ownership changes, replace the source-vs-copy assertion with a preserved baseline/signature check rather than losing that guarantee. The current comparison covers important body/geom/joint arrays but does not exhaustively compare sensors, contact-pair settings, all actuator dynamics, joint-name order, and keyframes. Select additional comparisons according to the changes actually made. Source: [current layout/model tests][L-tests].

For the interview, resolve these in order: **(1)** canonical runtime location, **(2)** supported variants versus workspace revisions, **(3)** imported/generated/independent derivation rules, **(4)** scene/spawn/pose promises, **(5)** portable bundle/provenance contents. Uniform controllers, collision redesign, robot-frame changes, new MJX variants, and backend adapters are separate modeling work.

## Limits

This report establishes the structure of two pinned upstream families and their contrast with the pinned local project. It does not establish a universal convention for every Menagerie robot, an exact original T1 vendor revision, the READMEs' minimum-version claims, long-term dynamic stability, mechanical fidelity, or hardware transferability. All nine selected native XMLs compiled; all four scenes passed the described short native smoke check. No local robot, asset, manifest, source hash, branch, or test file was changed. Untracked local experimental XMLs and retargeting output were observed and left untouched.

## Complete inspected family trees

These exact inventories come from `git ls-tree -r --name-only` at the upstream pin; they include files rather than only selected entry points. Sources: [G1 pinned tree][G1-tree], [T1 pinned tree][T1-tree].

```text
unitree_g1/
  CHANGELOG.md
  LICENSE
  README.md
  assets/
    head_link.STL
    left_ankle_pitch_link.STL
    left_ankle_roll_link.STL
    left_elbow_link.STL
    left_hand_index_0_link.STL
    left_hand_index_1_link.STL
    left_hand_middle_0_link.STL
    left_hand_middle_1_link.STL
    left_hand_palm_link.STL
    left_hand_thumb_0_link.STL
    left_hand_thumb_1_link.STL
    left_hand_thumb_2_link.STL
    left_hip_pitch_link.STL
    left_hip_roll_link.STL
    left_hip_yaw_link.STL
    left_knee_link.STL
    left_rubber_hand.STL
    left_shoulder_pitch_link.STL
    left_shoulder_roll_link.STL
    left_shoulder_yaw_link.STL
    left_wrist_pitch_link.STL
    left_wrist_roll_link.STL
    left_wrist_yaw_link.STL
    logo_link.STL
    pelvis.STL
    pelvis_contour_link.STL
    right_ankle_pitch_link.STL
    right_ankle_roll_link.STL
    right_elbow_link.STL
    right_hand_index_0_link.STL
    right_hand_index_1_link.STL
    right_hand_middle_0_link.STL
    right_hand_middle_1_link.STL
    right_hand_palm_link.STL
    right_hand_thumb_0_link.STL
    right_hand_thumb_1_link.STL
    right_hand_thumb_2_link.STL
    right_hip_pitch_link.STL
    right_hip_roll_link.STL
    right_hip_yaw_link.STL
    right_knee_link.STL
    right_rubber_hand.STL
    right_shoulder_pitch_link.STL
    right_shoulder_roll_link.STL
    right_shoulder_yaw_link.STL
    right_wrist_pitch_link.STL
    right_wrist_roll_link.STL
    right_wrist_yaw_link.STL
    torso_link_rev_1_0.STL
    waist_roll_link_rev_1_0.STL
    waist_yaw_link_rev_1_0.STL
  g1.png
  g1.xml
  g1_mjlab.xml
  g1_mjx.xml
  g1_mjx_colliders.png
  g1_with_hands.png
  g1_with_hands.xml
  scene.xml
  scene_mjx.xml
  scene_with_hands.xml
```

```text
booster_t1/
  CHANGELOG.md
  LICENSE
  README.md
  assets/
    AL1.stl
    AL2.stl
    AL3.stl
    AR1.stl
    AR2.stl
    AR3.stl
    Ankle_Cross_Left.stl
    Ankle_Cross_Right.stl
    H1.stl
    H2.stl
    Hip_Pitch_Left.stl
    Hip_Pitch_Right.stl
    Hip_Roll_Left.stl
    Hip_Roll_Right.stl
    Hip_Yaw_Left.stl
    Hip_Yaw_Right.stl
    Shank_Left.stl
    Shank_Right.stl
    Trunk.stl
    Waist.stl
    left_foot_link.stl
    left_hand_link.stl
    right_foot_link.stl
    right_hand_link.stl
  scene.xml
  t1.png
  t1.xml
```

[U]: https://github.com/google-deepmind/mujoco_menagerie/commit/f3b6013629c7b94f8ee93fd977b161fa8350f9bc
[G1-tree]: https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1
[G1-assets]: https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/assets
[G1-model]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1.xml
[G1-hands]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1_with_hands.xml
[G1-mjx]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1_mjx.xml
[G1-mjlab]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1_mjlab.xml
[G1-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/scene.xml
[G1-hands-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/scene_with_hands.xml
[G1-mjx-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/scene_mjx.xml
[G1-readme]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/README.md
[G1-changelog]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/CHANGELOG.md
[G1-license]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/LICENSE
[T1-tree]: https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/booster_t1
[T1-assets]: https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/booster_t1/assets
[T1-model]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/booster_t1/t1.xml
[T1-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/booster_t1/scene.xml
[T1-readme]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/booster_t1/README.md
[T1-changelog]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/booster_t1/CHANGELOG.md
[T1-license]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/booster_t1/LICENSE
[U-model-test]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/test/model_test.py
[U-layout-test]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/test/model_dir_test.py
[U-catalog]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/catalog.py
[U-registry]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/build_registry.py
[U-contributing]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/CONTRIBUTING.md
[U-build]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/.github/workflows/build.yml
[U-hooks]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/.pre-commit-config.yaml
[M-xml]: https://github.com/google-deepmind/mujoco/blob/b85fdca54f0e0038b804af146a0b4e94199e00d0/doc/XMLreference.rst
[M-sim]: https://github.com/google-deepmind/mujoco/blob/b85fdca54f0e0038b804af146a0b4e94199e00d0/doc/programming/simulation.rst
[L]: https://github.com/notAnyrobot/menagerie_x/commit/27d9e7c0f3d58961f97af8cdb03acffa6b07a878
[L-manifest]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/manifest.json
[L-catalog]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/catalog.py
[L-sync]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/scripts/sync-menagerie.py
[L-upstream]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/UPSTREAM.md
[L-tests]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/tests/test_menagerie_models.py
[L-editions]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/src/menagerie_x/assets/editions.py
[L-loader]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/src/menagerie_x/commands/mujoco.py
[L-workbench]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/src/menagerie_x/workbench/server.py
[L-G1-readme]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/unitree_g1/README.md
[L-Dex-readme]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/astro_p2_43dof_dex3_1/README.md
[L-Dex-order]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/astro_p2_43dof_dex3_1/joint-order.json
[L-Dex-mjcf]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/astro_p2_43dof_dex3_1/MJCF.md
[L-Astro29-mjcf]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/astro_p2_29dof/MJCF.md
[L-licensing]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/LICENSING.md
[L-P1]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/astro_p1/mjcf/astro_p1_30dof.xml
[L-P2]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/astro_p2/mjcf/astro_p2_30dof_primitive_collision.xml
[L-Atom]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/atom_p3/mjcf/atom_p3_27dof.xml
[L-SOMA]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/soma23/mjcf/soma23_free_base.xml
[L-G1]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/unitree_g1/mjcf/unitree_g1_29dof_with_hand_rev_1_0.xml
