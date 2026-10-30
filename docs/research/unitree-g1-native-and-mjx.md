# MuJoCo Menagerie G1: simplified MJCF and MJX

Investigated on 2026-10-30 against upstream HEAD
`f3b6013629c7b94f8ee93fd977b161fa8350f9bc` (2026-10-23), verified with
`git ls-remote`. Local comparison baseline:
`ff684bc863f0089f76671fd1c25f6e12c0bb9b97`. Two independent background
investigations covered native model derivation and MJX changes; the main session
also loaded and stepped every relevant upstream model/scene.

This is research, not adoption. Existing robot files, dependencies, catalog and
controller interfaces were not changed. Workbench, URDF compatibility and MJX
implementation remain deferred.

Follow-up: the 27-primitive configuration was subsequently added as native XML
under [the implementation scope](../design/astro-silver-hands-g1-primitives.md).
The findings below describe the preceding investigation; MJX backend execution
remains deferred.

## Main findings

1. Upstream's **simplified description retains all 29 body joints**. It is a
   curated MJCF with shared defaults, separate scenes, position servos and a
   standing keyframe. Visual meshes and many mesh collision geoms remain.
2. Its **MJX variant uses the same MJCF format and 29-joint rigid-body model**,
   with hand-designed primitive colliders, selected contact pairs, different
   actuator/joint parameters and cheaper numerical settings. It is a distinct
   simulation configuration, not a file-format conversion or a reduced-joint
   robot.
3. **`scene_mjx.xml` is essential to the intended MJX configuration.** The robot
   file disables automatic contacts and contains no explicit pairs; the scene
   supplies 49 pairs and both initial-pose keyframes.
4. Menagerie X currently preserves Unitree and ProtoMotions variants. Matching
   Menagerie more closely would change control semantics and contact behavior,
   even where meshes, rigid-body inertias and kinematics already match.

Sources: [upstream overview and derivation][overview], [native defaults][native-defaults],
[MJX defaults][mjx-defaults], [MJX scene][mjx-scene], and the compiled comparisons below.

## Upstream files and responsibilities

| Robot XML | Scene XML | Internal DoFs / actuators | Collision representation | Initial poses |
| --- | --- | ---: | --- | --- |
| `g1.xml` | `scene.xml` | 29 / 29 | 24 mesh geoms, 4 cylinders, 8 foot spheres | `stand`, in robot XML |
| `g1_with_hands.xml` | `scene_with_hands.xml` | 43 / 43 | 37 mesh geoms, 4 cylinders, 8 spheres, 2 thumb boxes | `stand`, in robot XML |
| `g1_mjx.xml` | `scene_mjx.xml` | 29 / 29 | 27 primitive colliders; explicit scene contact pairs | `home`, `knees_bent`, in scene XML |

Counts exclude the floating base. The 43-joint version adds 14 finger joints
to the same 29-joint body. The ordinary 29-joint and MJX variants retain fixed
rubber-hand visuals. Robot and scene files share family-local `assets/`.
The family retains BSD-3-Clause terms. [Source files][family], [license][license].

There is also a newer `g1_mjlab.xml`, added on 2026-10-19. The changelog identifies
it as a derivative with capsule feet, active self-collisions, and actuators/solver
options removed for programmatic specification. It is a separate variant,
outside these two research questions. [Changelog][changelog].

## What “simplified” means in the native model

The documented derivation starts from Unitree's public MJCF, extracts common
properties into nested `<default>` classes, adds position actuators and a
`stand` keyframe, and applies similar edits to the hand variant. The changelog
pins the model update to Unitree revision
`c20ca8f1fe5e519474c6c8d10b1ce5c719dd7a65`. This is not a claim that the STL
meshes were decimated or joints removed. [Derivation][overview], [history][changelog].

- **Visual/collision split:** visuals use group 2, zero collision masks and zero
  density; collision geoms use group 3. Most body collision geoms are meshes.
  Each foot has four radius-0.005 m spheres, friction 0.6, priority 1 and
  `condim=3`. Four shoulder cylinders supplement the meshes.
  [Native defaults][native-defaults], [foot construction][native-foot].
- **Control:** all joints use position actuators, with common `kp=500`,
  `dampratio=1`, and `inheritrange=1`. Joint armature is 0.01 and friction loss
  is 0.3. `implicitfast` is selected; the compiled default timestep is 0.002 s.
  The upstream README explicitly says actuator tuning is needed.
  [Defaults][native-defaults], [derivation][overview].
- **Initialization/sensing:** `stand` includes both `qpos` and matching actuator
  targets. Four IMU sensors provide two gyros and two accelerometers at torso
  and pelvis sites. A named keyframe must be selected by the caller; compiling
  XML does not automatically reset to it. [Sensors/keyframe][native-tail].

The hand variant's `stand` keyframe has thumb targets of ±1.05 rad, slightly
beyond the corresponding ±1.0472 joint endpoints (0.0028 rad). Native loading
succeeds. Exact upstream adoption should record this detail; changing it is a
deliberate local correction rather than a faithful copy. [Hand limits and
keyframe][hands-source].

Compared by joint/body name under MuJoCo 3.11.0, upstream
`g1_with_hands.xml` and our
`unitree_g1/unitree_g1_29dof_with_hand_rev_1_0.xml` have matching body transforms,
inertial values, joint axes/ranges, joint actuator force limits and default
`qpos0`. All 49 upstream hand-model mesh files match local mesh bytes. However:

| Concern | Current Menagerie X hand model | Upstream Menagerie hand model |
| --- | --- | --- |
| Actuators | 43 torque motors | 43 position servos |
| Native integration | Default Euler | `implicitfast` |
| Joint armature / friction loss | 0 / 0 | 0.01 / 0.3 |
| Foot contacts | Existing Unitree values | Menagerie friction, priority and `condim` settings |
| Geometry inventory | 101 robot geoms | 100; redundant logo collision removed |
| Reset pose | No standing keyframe | Named `stand` pose and targets |

These are local compiled/source comparisons, not a claim that the complete
physics is identical. In particular, motor controls represent torques while
position-servo controls represent target joint angles; existing control arrays
cannot be reused with the same interpretation.
[Local torque actuators and sensors][local-hands], [upstream source][hands-source].

For the fixed-hand model, upstream filenames are `left_rubber_hand.STL` and
`right_rubber_hand.STL`; our equivalent meshes use lowercase `.stl`. Bytes match,
but case-sensitive filename resolution must be preserved when importing. The
upstream license notice also differs from our retained snapshot, so importing
requires its actual notice rather than assuming the local copy is identical.

Our `unitree_g1_29dof_box_feet.xml` is a ProtoMotions description, not upstream
Menagerie's `g1.xml` or `g1_mjx.xml`. Its presence must not be used to infer an
upstream MJX configuration. Local provenance is recorded in
[the family README](../../unitree_g1/README.md) and
[licensing notes](../../unitree_g1/LICENSING.md).

## What changes in the MJX model

Native compiled comparisons show that `g1.xml` and `g1_mjx.xml` retain matching
rigid-body topology, transforms, inertias, joint axes/ranges, actuator
transmissions/control ranges, and total mass **33.341142 kg**. Both have
`nq=36`, `nv=35`, `nu=29`. Joint regularization, contacts, sensing and servo
parameters differ, so their trajectories should not be expected to match.

| Setting | Ordinary `g1.xml` | `g1_mjx.xml` / `scene_mjx.xml` |
| --- | --- | --- |
| Robot visual meshes | 35 | Same 35 |
| Robot collision geoms | 36, mostly meshes | 27 primitives: 23 capsules, 2 spheres, 2 boxes |
| Contact selection | Automatic masks | Robot masks zero; 49 explicit scene pairs |
| Timestep | 0.002 s | 0.004 s |
| Integrator | `implicitfast` | `implicitfast` |
| Solver iterations / line-search iterations | 100 / 50 (defaults) | 5 / 8 |
| Euler damping flag | Enabled | Disabled |
| Position gains | `kp=500`, damping from `dampratio=1` | `kp=75`, `kv=2`; ankles/wrists `kp=20`, `kv=2` |
| Joint friction loss | 0.3 | 0.1 |
| Armature | Uniform 0.01 | Joint-specific values |
| Joint-limit `solref` | 0.02, 1 (default) | 0.008, 1 |
| Joint-limit `solimp` | 0.9, 0.95, 0.001, 0.5, 2 (default) | 0, 0.99, 0.01, 0.5, 2 |
| Sensors / output scalars | 4 / 12 | 14 / 44 |
| Keyframes | `stand` in robot | `home`, `knees_bent` in scene |

Source: [MJX options/defaults][mjx-defaults], [MJX actuators/sensors][mjx-tail],
[scene contacts/keyframes][mjx-scene]; geometry and dimension counts were
independently compiled locally. Neither configuration contains custom numeric
fields used as a hidden runtime contract.

`dampratio=1` is a damping ratio, not `kv=1`: compiled native servo damping
coefficients span approximately 4.553–43.011, compared with MJX's fixed 2.
MJX armature ranges from 0.003609725 to 0.025101925, changing generalized
inertia even though rigid-body inertias match. The `eulerdamp` flag concerns
Euler joint-damping integration; it does not disable servo velocity feedback,
and both models still select `implicitfast`. [MJX joint classes][mjx-defaults],
[position-actuator semantics][position-docs], [Euler damping flag][eulerdamp-docs].

The MJX contact design is more specific than “primitive feet”:

- Each foot has three capsule colliders for floor contacts and a box used in
  selected self-collision pairs. This is different from using a single foot box
  for every interaction.
- The scene has **23 floor pairs with `condim=3`** and **26 self pairs with
  `condim=1`**. Six foot-floor pairs specify friction `1 1` and `solref="0.008 1"`.
  Other pairs cover chosen hand, hip, thigh, shin, torso, shoulder, elbow and
  wrist interactions. The masks prevent unlisted automatic interactions.
- Loading `g1_mjx.xml` alone succeeds, but yields zero contact pairs with all
  robot masks zero. A new environment must explicitly supply the intended
  contacts; merely adding a floor does not reproduce `scene_mjx.xml`.

[Contact definitions and poses][mjx-scene]. These choices bound collision work
and alter physical interaction coverage. The intent is performance and useful
training behavior; no speedup was measured in this investigation. Upstream
reports hardware transfer through MuJoCo Playground, which is evidence about
that upstream training setup, not certification of a future Menagerie X import.
[Upstream MJX notes][overview].

MJX also changes observation reference frames: foot sites move to local
`(0.04, 0, -0.037)` and palm sites are added at `(0.08, 0, 0)`. IMU positions
stay fixed, but sensor names, order and output dimensions change. Consumers
must not assume the native sensor layout or the old foot-site origin.
[Foot and palm sites][mjx-sites], [sensor definitions][mjx-tail].

## MJX format, backend and verification boundary

MJX consumes a normal compiled MuJoCo model: load MJCF as `mujoco.MjModel`, then
transfer it using `mjx.put_model` and step with the MJX API. There is no separate
MJX XML language. MuJoCo 3.11 documents both MJX-JAX and MJX-Warp, whose feature
support and hardware/performance tradeoffs differ. Unsupported model features
can fail during transfer to the selected backend.
[MuJoCo 3.11 MJX overview and example][mjx-docs], [feature parity][mjx-parity].

Official documentation was checked through Context7 and the versioned MuJoCo
3.11 page. This environment has native MuJoCo 3.11.0, but no `jax`, `mujoco.mjx`
or `warp`. No packages were installed. **Native loading below does not establish
MJX device compatibility, compilation time, throughput, training quality or
sim-to-real performance.** A future adoption should choose its backend/version
explicitly and test that runtime separately.

## Native verification performed

Using the existing repository `.venv` (Python 3.13.12 / MuJoCo 3.11.0), each
upstream entry point compiled, forwarded, and stepped for 0.1 s from default
initialization and every available keyframe. All **12 initialization probes**
had finite state and zero MuJoCo warnings. This checks loading and short native
execution, not standing stability or controller quality.

Both research agents checked this combined report against their findings;
neither found a material factual issue. A foot-geometry citation was corrected
during that review.

| Entry point | `nq` / `nv` / `nu` | Geoms | Explicit pairs | Keyframes |
| --- | --- | ---: | ---: | --- |
| `g1.xml` | 36 / 35 / 29 | 71 | 0 | `stand` |
| `scene.xml` | 36 / 35 / 29 | 72 | 0 | `stand` |
| `g1_with_hands.xml` | 50 / 49 / 43 | 100 | 0 | `stand` |
| `scene_with_hands.xml` | 50 / 49 / 43 | 101 | 0 | `stand` |
| `g1_mjx.xml` | 36 / 35 / 29 | 62 | 0 | None |
| `scene_mjx.xml` | 36 / 35 / 29 | 63 | 49 | `home`, `knees_bent` |

## Proposal for a later adoption

To pursue the accepted goal of close Menagerie pairing, use pinned upstream
`g1.xml` / `scene.xml` and `g1_with_hands.xml` / `scene_with_hands.xml` as the
prospective canonical pair, with the actual upstream assets and notices. Keep
the current Unitree/ProtoMotions sources as explicit historical evidence rather
than silently changing their control contract. Decide separately whether the
ProtoMotions box-feet runtime remains an extra maintained variant.

Keep `g1_mjx.xml` and `scene_mjx.xml` together as a separately named optional
configuration if adopted later. Preserve the scene's explicit contacts and
poses; do not merge its lower gains, numerical settings or contact coverage
into the ordinary model. Test native loading first, then selected MJX backend
transfer/stepping and performance with documented versions. No compatibility
layer or metadata framework is needed for this file structure.

These are recommendations, not accepted implementation decisions. No G1 model
was replaced and MJX support was not enabled by this research.

[family]: https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1
[overview]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/README.md#L10-L42
[changelog]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/CHANGELOG.md#L5-L24
[license]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/LICENSE
[native-defaults]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1.xml#L1-L19
[native-foot]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1.xml#L103-L112
[native-tail]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1.xml#L339-L350
[hands-source]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1_with_hands.xml#L238-L499
[local-hands]: https://github.com/notAnyrobot/menagerie_x/blob/ff684bc863f0089f76671fd1c25f6e12c0bb9b97/unitree_g1/unitree_g1_29dof_with_hand_rev_1_0.xml#L477-L544
[mjx-defaults]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1_mjx.xml#L1-L90
[mjx-tail]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1_mjx.xml#L366-L418
[mjx-sites]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1_mjx.xml#L174-L304
[mjx-scene]: https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/scene_mjx.xml#L1-L144
[mjx-docs]: https://mujoco.readthedocs.io/en/3.11.0/mjx.html#minimal-example
[mjx-parity]: https://mujoco.readthedocs.io/en/3.11.0/mjx.html#feature-parity
[position-docs]: https://mujoco.readthedocs.io/en/3.11.0/XMLreference.html#actuator-position
[eulerdamp-docs]: https://mujoco.readthedocs.io/en/3.11.0/XMLreference.html#option-flag-eulerdamp
