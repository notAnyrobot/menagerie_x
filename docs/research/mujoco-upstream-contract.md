# MuJoCo Menagerie: the portable asset and runtime contract

> Scope update: the user subsequently prioritized close native Menagerie asset alignment and accepted Workbench/URDF incompatibilities. Application architecture and compatibility repairs discussed below are follow-up work, not requirements for this phase. See [ADR 0011](../adr/0011-upstream-asset-structure-first.md). MJX remains deferred.

Research date: **2026-10-30**. This report extends the earlier [collection survey](mujoco-menagerie.md) and [G1/T1 study](mujoco-per-robot-structure.md) with repository contracts and representative **native MuJoCo** exceptions. It informs the accepted [per-robot decisions](../design/per-robot-design-decisions.md); it does not implement them. MJX compatibility remains deferred. No mjlab integration requirement follows from this investigation.

## Revisions, method, and limits

- Upstream checkout: **`f3b6013629c7b94f8ee93fd977b161fa8350f9bc`**, committed **2026-10-23**. `git ls-remote origin refs/heads/main` independently returned this same SHA on the research date. The public GitHub repository was also opened in the browser; its rendered listing is less authoritative than the pinned Git tree. [Pinned upstream revision][U]
- Implemented local baseline: **`27d9e7c0f3d58961f97af8cdb03acffa6b07a878`**. Accepted decisions recorded after that baseline are target requirements, not implemented runtime behavior. [Local baseline][L]
- Read contribution/style rules, structural and simulation tests, catalog, registry builder, package APIs, dependency closure code, and release workflow. Read source XML/README files for Panda, FR3/FR3 v2, Stretch/Stretch 3, Talos, Shadow Hand, RealSense D435i, ALOHA and RBY1. A source-only census of **91 top-level `scene*.xml` files whose filenames lack `mjx`** located additional scene-owned contact/pose cases; this filename filter is not a backend-compatibility certification. XML/README inspection did not require downloading all mesh directories.
- Retrieved current MuJoCo documentation through Context7, then pinned API evidence to **MuJoCo 3.11.0**, tag SHA **`b85fdca54f0e0038b804af146a0b4e94199e00d0`**, verified with `git ls-remote`. [XML reference][M-xml], [simulation reference][M-sim], [official WASM source][M-wasm]
- One additional native check downloaded D435i's actual dependency closure (10 XML/OBJ files; 45,995,621 bytes), compiled it using the existing **MuJoCo 3.11.0**, and stepped 0.1 seconds. It returned `nq=nv=nu=0`, `ngeom=10`, `nsensor=0`, and zero warnings. The other newly inspected families were **source-inspected**, not fully asset-downloaded or compile-tested here. Earlier G1/T1 native checks are documented separately. No all-collection WASM, hardware-fidelity, or sustained-control claim is made.

## What pairing with Menagerie should mean

The useful compatibility boundary is **a directly loadable, editable MJCF entry point plus its family-local dependency closure**. A robot file identifies the mechanism; a scene includes the robot and provides its environment. Users can load files from disk without a Python catalog, or parse the same files into `MjSpec` before compiling. A bundle can expose several complete model choices and scenes. The family directory is the unit of asset distribution; a particular model or scene is the unit of loading. This interpretation follows both the collection's published organization and its current package API. [Upstream overview][U-readme], [package documentation][U-doc], [package registry API][U-registry]

For Menagerie X, the accepted canonical root files should therefore be the files that the CLI and Workbench actually load and edit. Directory shape alone is insufficient if a consumer rewrites paths, reconstructs the ground, substitutes spawn state, or silently changes the selected scene before compiling. This is a proposed operational meaning of the accepted decisions, not a new upstream rule. [Accepted local decisions](../design/per-robot-design-decisions.md)

## Enforced contracts versus useful conventions

| Concern | Evidence at the pinned revision | Implication for Menagerie X |
| --- | --- | --- |
| Family identification | Structural discovery considers visible top-level directories containing top-level XML; it does not require all directories to be robots. [Structural test][U-layout] | Keep the seven supported families explicit in local metadata; avoid promoting every authoring file automatically. |
| Required documentation | Structural tests require `README.md`, exact `LICENSE`, and `CHANGELOG.md`. [Structural test][U-layout] | Preserve per-family provenance and licensing. A preview image or `assets/` directory is not a universal structural test requirement. |
| Scenes | Tests require **any `scene*.xml`**, with an explicit D435i exception. Contribution prose says to ship `scene.xml`. [Structural test][U-layout], [contribution rules][U-contrib] | A default `scene.xml` is a good local standard; do not mistake the stronger prose recommendation for a universal exact-filename invariant. |
| Entry points | The builder tries compiling every top-level XML and registers the successful ones. Files that are only include fragments need not be standalone entry points. [Registry builder][U-build] | Separate supported public model/scene entries from helper fragments and experiments. Do not equate all XML files with selectable editions. |
| Defaults | Catalog keys identify directory/model-stem entries. Preview overrides handle alternate scene names or standalone end effectors. The builder uses `scene.xml` first, then a declared preview or an unambiguous sole scene, and rejects unresolved multiple-scene defaults. [Catalog][U-catalog], [builder][U-build] | Explicit local model + scene + optional pose metadata is compatible with upstream and is clearer than importing its filename/default inference. |
| Portability | The builder follows file dependencies, copies them under a temporary family directory, and recompiles every entry from that copy. Closure resolution rejects files outside the family. [Builder][U-build], [closure code][U-closure] | Test relocation of each local family. A sibling repository, absolute path, or catalog-only resource is outside this portable-bundle contract. |
| Numerical smoke test | Tests compile top-level `scene*.xml`, step 0.1 seconds under deterministic Halton control perturbations scaled to actuator ranges, and reject warnings. They do not select a named keyframe first. [Model test][U-test] | Adopt a comparable load/step baseline, then validate declared initial poses separately. Passing it does not establish standing, walking, or physically accurate control. |
| Style/tooling | XML formatting and license aggregation run through pre-commit; the CI build additionally derives the registry and runs package tests. `make all` combines the checks. [Contribution rules][U-contrib], [hooks][U-hooks], [Makefile][U-make], [CI][U-ci] | XML style and portable-runtime tests are separable from adopting the upstream Python package or release infrastructure. |

There is no inspected universal requirement for one free base, one actuator per joint, a fixed joint-name vocabulary, an IMU, a `home` keyframe, identical solver settings, a single default scene, or a physically meaningful policy interface. The examples below provide concrete counterexamples; the inspected structural tests do not enforce those capabilities. [Structural tests][U-layout], [Panda][P-model], [Stretch][S-model], [D435i][D-model]

## Representative native patterns beyond G1/T1

| Family / entry | Real structure and ownership | Consequence |
| --- | --- | --- |
| Panda | `scene.xml → panda.xml`; sibling `panda_nohand.xml` and `hand.xml` share assets. The full arm owns `home`, finger tendon/equality coupling and a gripper control range of 0–255. `hand.xml` is previewed directly by a catalog override. [Family tree][P-tree], [full model][P-model], [catalog][U-catalog] | Multi-model families and standalone end effectors are legitimate. Actuator controls cannot all be interpreted as joint angles. A separate scene for every alternative is not guaranteed upstream. |
| FR3 / FR3 v2 | Each is its own family with a root model and scene. FR3 exposes `attachment_site`, position actuators, robot-owned contact exclusions and `home`. FR3 v2 has a separately maintained model file and differs in model contents. [FR3][F-model], [FR3 v2][F2-model] | Similar product names do not imply interchangeable definitions. Preserve each supported mechanism and its gains rather than collapsing variants solely by names. |
| Talos | `scene_position.xml → talos_position.xml → talos.xml`; the motor scene follows the parallel motor wrapper. Shared core owns mechanism/options/contact/equality; wrappers own actuator mode and pose. The position wrapper calls its key `walk_pose`; the motor wrapper has an unnamed key. There is no `scene.xml`; catalog selects `scene_position.xml`. [Core][T-core], [position wrapper][T-pos], [motor wrapper][T-motor], [position scene][T-scene], [catalog][U-catalog] | Root canonical files may include shared local files. “Directly maintained canonical model” need not mean duplicating the whole mechanism into each actuator variant. Never infer pose name from family type. |
| Stretch | `scene.xml → stretch.xml`; the model uses `assetdir="assets"`, mixed OBJ/STL and image assets, a floating base, wheel/telescope tendons, equality couplings and mixed motor/general/position actuators. The scene adds a table, a free object, and file-backed `wood.png`. No keyframe is declared in these two files. [Robot][S-model], [scene][S-scene] | A scene can change `nq`/`nv` independently of the robot and include additional free joints. A loader cannot select “the first free joint” as a universal robot or spawn interface. Runtime dependencies include scene textures. |
| ALOHA | `scene.xml → aloha.xml → joint_position_actuators.xml + keyframe_ctrl.xml`. Its scene supplies additional STL/OBJ table/frame meshes and a PNG texture; the pose lives in a separate included fragment. Other actuator/pose fragments also exist. [Robot][A-model], [scene][A-scene], [actuator fragment][A-act], [pose fragment][A-key] | Recursive includes are a real native pattern, not an MJX complication. Compiling only the immediately fetched XML or scanning its direct meshes is incomplete. |
| Shadow Hand | Left/right root models have `scene_left.xml` / `scene_right.xml`, and the right scene introduces a free ellipsoid with scene-specific friction/contact dimension. A separate `keyframes.xml` exists, but the inspected hand/scene files do not include it. [Tree][H-tree], [right scene][H-scene] | File presence does not imply use. Dependency reachability and declared entry points determine runtime assets; a spare pose file must not be auto-applied. |
| RealSense D435i | One model XML, no scene; explicitly exempt from the scene structural requirement. Its native compile has no joints, actuators, or MuJoCo sensor elements. [Structure test][U-layout], [model][D-model], [README][D-readme] | A camera-shaped model is not evidence of an implemented depth-camera/sensor simulation. Catalog membership does not imply controllable robotics. |

The end-effector convention is useful but scoped: upstream FAQ recommends `attachment_site` on arms; Panda's **no-hand** model and FR3 expose it, while the combined Panda already embeds its gripper. The FAQ also handles keyframe expansion when attaching a hand, and the package documentation warns that a composed parent should match an attached arm's integrator. An attachment marker is an interface convention, not proof that arbitrary model pairs compose without coordinate, naming, pose-dimension, or solver decisions. [FAQ][U-faq], [Panda no-hand][P-nohand], [FR3][F-model], [package composition examples][U-doc]

## Scene options, contacts, and initial poses are runtime content

Non-MJX examples settle this without relying on deferred backend variants:

- **RBY1** scenes declare timestep, Newton solver, iteration/tolerance, integrator, cone and impedance settings. Dropping the scene drops its simulation configuration. [Native RBY1 scene][R-scene]
- **Apollo** scene sets timestep/integrator/iterations and explicitly pairs soles with the scene floor, plus selected self-contact pairs. These are not reproduced by creating an arbitrary new floor beside the robot. [Apollo scene][AP-scene]
- **ToddlerBot 2XC** scene defines many explicit floor/robot contact pairs. Scene ownership is not restricted to camera and lighting decoration. [ToddlerBot scene][TB-scene]
- **H1** scene owns its `home` pose. **SO101 `scene_box.xml`** owns a `pickup` key including the additional object's state, velocities and controls. A robot-only pose and a scene-sized pose are not interchangeable. [H1 scene][H1-scene], [SO101 scene][SO-scene]

These observations support the accepted **explicit model + scene + optional initial pose** design. Proposal: preserve each declared scene as the compile target; validate that its intended robot dependency is present; resolve a selected pose against the **compiled scene**, and apply it explicitly. No pose selection should mean normal MuJoCo initialization, not an invented `home`, automatic first key, blanket zero controls, or replacement free-base spawn. If an override mode is needed, define its precedence separately. MuJoCo documents keyframe reset and `mj_forward` as explicit operations; key `qpos` is copied when state is set to that keyframe. [MuJoCo keyframe reference][M-xml], [reset API][M-header], [forward reference][M-api]

Keep ownership intentional rather than imposing one rule across all physical parameters: mechanism-relative inertials, gains, actuator transmission, local self-contact exclusions and default classes can stay with the robot; floor-dependent pairs and task object poses naturally belong to the scene. Upstream demonstrates both robot-owned and scene-owned options and keys. Moving values across that boundary requires preserving the resulting compiled model, not merely producing visually similar XML. [Panda model][P-model], [Stretch model][S-model], [Apollo scene][AP-scene], [SO101 scene][SO-scene]

## Paths, assets, and editing

MuJoCo resolves ordinary included files relative to the **main MJCF directory**. `meshdir` and `texturedir` affect their asset types; `assetdir` supplies both unless individually overridden. Attached model specs have their own main-file directory. Preserve these distinctions when constructing a closure; resolving every file relative to whichever included XML mentioned it is not a generally correct replacement for engine semantics. [Pinned XML path rules][M-xml], [upstream closure implementation][U-closure]

Talos uses nested asset paths, including **`assets/torso/base_link.stl` and `assets/gripper/base_link.stl`**. Their MJCF mesh names distinguish them. Flattening to basenames destroys information. Upstream's Python `assets()` deliberately detects repeated case-folded basenames and rejects that in-memory path for Talos, OP3 and Lite6, recommending disk `model()` / `spec()` instead. This is a limitation of that convenience path, not a collection-wide unique-basename rule. [Talos assets][T-core], [package file API note][U-doc], [collision detection][U-closure]

Proposal: the family root is the runtime namespace, with relative subpaths preserved. Closure discovery must follow includes and file-backed meshes, textures and any other referenced resources; preserve case, mesh scales and explicit asset names. Test the actual compiler on the relocated closure. A narrow implementation can support the seven local families first, but must describe unsupported resource kinds honestly instead of silently dropping them. [Portability verification][U-build], [closure][U-closure]

For editing, load the chosen canonical robot or scene from disk/its equivalent VFS and retain its source path. `MjSpec` is a supported editable parse of the same entry, but compiling and saving a model is not evidence that comments, includes, class organization, or original source layout survive intact. The next editor design must explicitly choose whether an edit targets a robot file, scene file, or included helper. The upstream package exposes both file paths and editable specs; it does not define Menagerie X's collision-editor save policy. [Package API][U-registry], [local accepted canonical-file decision](../adr/0001-canonical-per-robot-runtime-files.md)

## Minimum native CPU and WASM contract

**Native CPU:** a compatible MuJoCo version, the declared entry XML and complete family-local closure, then compile/data initialization/optional explicit keyframe/forward/step. No gallery service, package registry, policy library, or MJX environment is needed to load a checked-out XML. Version floors are **per model**: inspected READMEs state Panda 2.3.3, FR3 3.1.3, Stretch 3.3.0, D435i 2.2.2; the Python package dependency `mujoco>=3.2.0` is not a proof that every latest model works at 3.2.0. Keep the existing local 3.11.0 pin during structural migration unless a separate reason changes it. [Panda README][P-readme], [FR3 README][F-readme], [Stretch README][S-readme], [D435i README][D-readme], [package project][U-pyproject], [local project][L-project]

**WASM:** the official `@mujoco/mujoco` engine plus served `.wasm`, enough memory, a browser-compatible binding build, and the same XML/assets supplied in a path-preserving VFS. MuJoCo 3.11 provides `MjVFS.addBuffer` and a named-file `mj_loadXML(filename, vfs)` wrapper. Its `from_xml_string` helper temporarily names the entry **`model.xml`**; code using that helper must account for entry-directory semantics and name collisions. Prefer evaluating the named-entry API for canonical-file loading. Match native/WASM versions and validate observable compiled properties and reset state in both; a collection entry's native smoke test is not a browser certification. [Official bindings template][M-bindings], [VFS wrapper][M-vfs], [WASM README][M-wasm]

The default single-thread WASM build does not require cross-origin-isolation headers; the optional multithread build does. This should not be turned into an unnecessary prerequisite for the existing Workbench. Rendering meshes/materials/textures and scene objects correctly is an additional viewer responsibility beyond successful engine compilation. The official binding documentation treats APIs and browser support as evolving; use the pinned tested surface. [WASM threading/API documentation][M-wasm]

At local baseline, `loadMujocoModel()` fetches one source XML, enumerates only direct mesh elements, removes `meshdir`, reduces mesh paths to basenames, creates a replacement terrain, and compiles an XML string. Those assumptions conflict with Talos, ALOHA and Stretch's observed asset/scene patterns. The separate Workbench compatibility investigation should determine the concrete repair and renderer coverage; this report establishes the upstream cases that the design must not erase. [Local loader][L-app], [Talos][T-core], [ALOHA][A-model], [Stretch scene][S-scene]

## Safe standardization and remaining choices

Standardize **entry discovery, declared defaults/configurations, family-local dependencies, canonical save targets, provenance, formatting, relocation checks and runtime verification**. Retain descriptive root XML names, optional shared include fragments, and local asset subdirectories when needed. Requiring one directly maintained canonical file per supported choice is compatible with upstream; requiring every choice to be a duplicated monolith is not necessary. [Builder][U-build], [Talos wrappers][T-pos], [ALOHA includes][A-model]

Do not standardize dynamics by copying reference robots: gains, damping, friction, mass/inertia, actuator ranges/transmissions, contact masks/pairs, geom groups, solver settings and poses express model-specific decisions. Panda's 0–255 tendon gripper, Stretch's mixed transmissions and Apollo's scene contacts explain why uniform numeric defaults would change behavior. Preserve existing seven-family physics and provenance during the structural refactor; intentional physics improvements need their own decisions and evidence. [Panda][P-model], [Stretch][S-model], [Apollo][AP-scene], [accepted scope](../design/per-robot-design-decisions.md)

The new upstream Python package is useful evidence but optional infrastructure: it derives a registry from the checkout, records the repository commit and model-directory tree IDs, publishes content-addressed per-family archives, and lazily resolves them from a shared GitHub release/cache. `MENAGERIE_ROOT` redirects asset resolution to a checkout while the installed registry still supplies entry metadata. Reusing that provider requires registry/build/release decisions; keeping Menagerie X's own manifest and shipping portable canonical files does not. [Builder][U-build], [registry][U-registry], [cache][U-cache], [release workflow][U-release]

Remaining design questions are local: how to name/select supported configurations, which authoring revisions stay outside them, where initial-pose policy is stored, which editor writes each include/scene, and whether to retain or replace the local package metadata path. None is settled by upstream convention alone. The research supports the three accepted decisions without expanding scope to MJX, mjlab, arbitrary upstream robots, hosted release integration, or a universal robot-control abstraction.

## Primary source index

All upstream Menagerie links below are immutable at `f3b6013629c7b94f8ee93fd977b161fa8350f9bc`; MuJoCo links use the verified 3.11.0 SHA. Local baseline links use `27d9e7c0f3d58961f97af8cdb03acffa6b07a878`.

[U]: https://github.com/google-deepmind/mujoco_menagerie/commit/f3b6013629c7b94f8ee93fd977b161fa8350f9bc
[U-readme]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/README.md
[U-contrib]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/CONTRIBUTING.md
[U-layout]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/test/model_dir_test.py
[U-test]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/test/model_test.py
[U-build]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/build_registry.py
[U-catalog]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/catalog.py
[U-closure]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/python/src/mujoco_menagerie/_closure.py
[U-registry]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/python/src/mujoco_menagerie/_registry.py
[U-doc]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/python/DOC.md
[U-pyproject]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/python/pyproject.toml
[U-cache]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/python/src/mujoco_menagerie/_cache.py
[U-release]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/.github/workflows/release.yml
[U-hooks]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/.pre-commit-config.yaml
[U-make]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/Makefile
[U-ci]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/.github/workflows/build.yml
[U-faq]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/FAQ.md
[P-tree]: https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/franka_emika_panda
[P-model]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/franka_emika_panda/panda.xml
[P-nohand]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/franka_emika_panda/panda_nohand.xml
[P-readme]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/franka_emika_panda/README.md
[F-model]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/franka_fr3/fr3.xml
[F-readme]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/franka_fr3/README.md
[F2-model]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/franka_fr3_v2/fr3v2.xml
[T-core]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/pal_talos/talos.xml
[T-pos]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/pal_talos/talos_position.xml
[T-motor]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/pal_talos/talos_motor.xml
[T-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/pal_talos/scene_position.xml
[S-model]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/hello_robot_stretch/stretch.xml
[S-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/hello_robot_stretch/scene.xml
[S-readme]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/hello_robot_stretch/README.md
[A-model]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/aloha/aloha.xml
[A-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/aloha/scene.xml
[A-act]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/aloha/joint_position_actuators.xml
[A-key]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/aloha/keyframe_ctrl.xml
[H-tree]: https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/shadow_hand
[H-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/shadow_hand/scene_right.xml
[D-model]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/realsense_d435i/d435i.xml
[D-readme]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/realsense_d435i/README.md
[R-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/rainbow_robotics_rby1/scene_rby1a_1.2.xml
[AP-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/apptronik_apollo/scene.xml
[TB-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/toddlerbot_2xc/scene.xml
[H1-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_h1/scene.xml
[SO-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/robotstudio_so101/scene_box.xml
[M-xml]: https://github.com/google-deepmind/mujoco/blob/b85fdca54f0e0038b804af146a0b4e94199e00d0/doc/XMLreference.rst
[M-sim]: https://github.com/google-deepmind/mujoco/blob/b85fdca54f0e0038b804af146a0b4e94199e00d0/doc/programming/simulation.rst
[M-api]: https://github.com/google-deepmind/mujoco/blob/b85fdca54f0e0038b804af146a0b4e94199e00d0/doc/APIreference/functions_override.rst
[M-header]: https://github.com/google-deepmind/mujoco/blob/b85fdca54f0e0038b804af146a0b4e94199e00d0/include/mujoco/mujoco.h
[M-wasm]: https://github.com/google-deepmind/mujoco/blob/b85fdca54f0e0038b804af146a0b4e94199e00d0/wasm/README.md
[M-bindings]: https://github.com/google-deepmind/mujoco/blob/b85fdca54f0e0038b804af146a0b4e94199e00d0/wasm/codegen/templates/bindings.cc
[M-vfs]: https://github.com/google-deepmind/mujoco/blob/b85fdca54f0e0038b804af146a0b4e94199e00d0/wasm/codegen/templates/bindings.h
[L]: https://github.com/notAnyrobot/menagerie_x/commit/27d9e7c0f3d58961f97af8cdb03acffa6b07a878
[L-project]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/pyproject.toml
[L-app]: https://github.com/notAnyrobot/menagerie_x/blob/27d9e7c0f3d58961f97af8cdb03acffa6b07a878/src/menagerie_x/workbench/web/app.js
