# Menagerie robot-description conventions

This document turns the packaged Unitree G1 hand-model import into a
**Menagerie convention**, without relabelling Menagerie or MuJoCo adaptations as
vendor rules.  It is the baseline for new imported or authored robot variants.
It does not replace a vendor's source description: preserve the vendor file and
provenance, then make any workbench representation an explicit edition.

## Evidence, terminology, and scope

The reference import is the `unitree_g1` variant in the asset manifest.  It
declares the official G1 URDF and default MJCF, 43 movable DoFs, its spawn pose,
and upstream provenance.  The manifest identifies Unitree's `unitree_ros`
revision and original URDF path, while retaining the BSD-3-Clause license.
([manifest](../../src/menagerie_x/assets/manifest.json#L131-L175),
[license](../../src/menagerie_x/assets/unitree_g1/LICENSE.Unitree#L1-L18)).
The repository README records that the paired default MJCF is packaged from the
official description and only has its relative `meshdir` changed.
([README](../../README.md#L104-L113)).

Claims in this guide are labelled as follows:

| Label | Meaning |
| --- | --- |
| **Unitree observation** | What the pinned G1 source itself does; useful evidence, not a universal requirement. |
| **MJCF rule** | A MuJoCo language/runtime constraint or an intentional MJCF representation convention. |
| **Menagerie rule** | The reusable packaging/authoring policy proposed here. |

The ProtoMotions G1 files are a separate retargeting reference, not the
production template.  Their candidate metadata, licence and source role say so
explicitly. ([reference MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/protomotions_g1_retargeting_box_feet.xml#L1-L3),
[notice](../../src/menagerie_x/assets/unitree_g1/NOTICE.ProtoMotions#L1-L12)).
In particular, they simplify the feet, omit hands, and use a different URDF
name/path convention; do not copy those choices into an official import unless
the variant's purpose is retargeting.

## 1. Variant package layout

### Reference layout

```text
src/menagerie_x/assets/<robot_version>/
  urdf/
    <official-description>.urdf
    for_retargeting/                 # only for a distinct retargeting source
      <retargeting-description>.urdf
  mjcf/
    <default-edition>.xml
    <optional-non-default-edition>.xml
  meshes/
  LICENSE.<source>
  NOTICE.<source>                    # when required by a second source
```

**Menagerie rule — mandatory.** Give every robot family/version one asset
directory and keep source formats and reusable meshes in sibling directories.
The README documents this family/version structure, and the G1 package follows
it. ([README](../../README.md#L117-L144)).  The manifest selects one default
URDF/MJCF pair for the variant; additional MJCF files are selectable editions,
not replacement defaults. ([manifest](../../src/menagerie_x/assets/manifest.json#L131-L175),
[README](../../README.md#L95-L102)).

**Menagerie rule — mandatory.** Record the source repository, immutable
revision, original path, licence file, and any local path adaptation in the
manifest.  Keep assets from another supplier in a separately identified
edition and retain its own licence/notice.  G1 separates the Unitree default
provenance from the ProtoMotions retargeting URDF provenance and states that
the latter changes only mesh paths. ([manifest](../../src/menagerie_x/assets/manifest.json#L141-L159)).

**Menagerie rule — recommended.** Put purpose-specific source URDFs under a
purpose subdirectory such as `urdf/for_retargeting/`; do not overwrite the
official default.  G1 does exactly this for the ProtoMotions source, and the
tests require it to remain separate. ([retargeting URDF](../../src/menagerie_x/assets/unitree_g1/urdf/for_retargeting/g1.urdf#L1-L20),
[test](../../tests/test_unitree_g1.py#L77-L91)).

## 2. Names and deterministic identity

### Names

**Unitree observation.** The source uses lowercase `snake_case` names:

- physical links end in `_link`, for example `left_hip_pitch_link`;
- articulations end in `_joint`, for example `left_hip_pitch_joint`;
- laterality is the first token (`left_` or `right_`), then region and axis;
- sensor/accessory frames use descriptive names such as `imu_in_torso` and
  pair with a fixed `*_joint` when represented as a URDF link.

The root materials and the first pelvis/leg links show the naming and
link-then-content pattern. ([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L1-L86)).
The accessory frames demonstrate the fixed-frame names.
([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L492-L576)).
Mesh logical names normally equal their link names, but a vendor revision
suffix is retained in the file where it is semantically meaningful, such as
`waist_yaw_link_rev_1_0.STL`. ([MJCF asset list](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L5-L24)).

**Menagerie rule — mandatory.** Use unique lowercase `snake_case` identifiers.
For a robot with conventional limbs, use `<side>_<region>_<axis>_link` and the
matching `_joint`; preserve a vendor's established names rather than silently
renaming them.  For authored models, use `*_visual` and `*_collision` only for
named alternate geoms, never to rename a body or actuated joint.  This makes
body lookup, collision editing, motion mapping, and left/right pairing
unambiguous.

### Ordering is an interface

**Menagerie rule — mandatory.** Treat the ordered actuated joint list as API
data, not an incidental formatting choice.  Store it in a test or metadata
contract, and use the same order for motion mapping and MJCF motors.  The G1
regression test establishes the body-29 order and checks that the complete
official import has 43 movable joints plus fourteen hand joints.
([test](../../tests/test_unitree_g1.py#L24-L35),
[test](../../tests/test_unitree_g1.py#L127-L133)).

The G1 body-29 sequence is:

1. left leg: hip `pitch`, `roll`, `yaw`, knee, ankle `pitch`, `roll`;
2. right leg in the same order;
3. waist: `yaw`, `roll`, `pitch`;
4. left arm: shoulder `pitch`, `roll`, `yaw`, elbow, wrist `roll`, `pitch`,
   `yaw`;
5. right arm in the same order.

The fourteen hand DoFs follow: left thumb `0..2`, middle `0..1`, index `0..1`,
then the same right-side sequence.  The URDF's anatomy-grouped declarations
are legs, torso, fixed accessories, left arm/hand, right arm/hand.
([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L59-L84),
[URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L421-L578),
[URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L579-L982)).

**Important G1-specific exception.** The source's textual link/joint order is
not completely uniform: some wrist joints occur immediately before their child
link.  Do not write a formatter or importer that assumes every link must be
declared before its joint.  Build order from the explicit declared joint list
and parent/child topology instead. ([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L680-L748)).

## 3. URDF source convention

### Per-link contents

**Unitree observation.** For a normal physical link, the source orders child
elements as `<inertial>`, `<visual>`, then `<collision>`; each visual/collision
declares its local `<origin>` and `<geometry>`, and the visual then gives a
material.  The left hip pitch link is a compact canonical example.
([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L60-L86)).
The visual and collision may reuse one vendor mesh, but that is a source choice
rather than a requirement.  The same source also uses primitive collision
geometry on the ankle. ([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L195-L233)).

**Menagerie rule — mandatory for authored physical links.** Use this readable
source order:

```xml
<link name="<name>_link">
  <inertial>…mass and inertia in the link frame…</inertial>
  <visual>…display geometry…</visual>
  <collision>…physical geometry…</collision>
</link>
<joint name="<name>_joint" type="revolute|continuous|fixed">
  <origin …/>
  <parent link="…"/>
  <child link="…"/>
  <axis …/>                 <!-- movable joint -->
  <limit …/>                <!-- bounded movable joint -->
</joint>
```

This is a Menagerie authoring convention, **not** a claim that every valid
URDF must have every child.  Visual-only cosmetic links and intentionally empty
sensor frames are legitimate exceptions: G1's pelvis is visual-only
([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L20-L33)),
while its IMU/camera/LiDAR frames are empty fixed links.
([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L547-L576)).

**Menagerie rule — mandatory.** A visual mesh is never a substitute for a
collision contract.  Declare collision geometry separately, even if it
temporarily references the same mesh.  Prefer simple capsules, boxes, spheres,
or carefully reviewed primitives for physical interaction; record why a
render mesh is also used for collision when that is unavoidable.

### Frames, units, and base choice

**Unitree observation.** Origins use `xyz` in metres and `rpy` in radians,
with local joint axes explicitly declared; G1's lower-body axes alternate as
expected by the joint name (`pitch` Y, `roll` X, `yaw` Z).
([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L80-L139)).
The source intentionally leaves a world link and floating joint commented out
for MuJoCo conversion. ([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L13-L18)).

**Menagerie rule — mandatory.** Keep an imported vendor URDF's frame choices
and units intact.  Do not add a free root to the source URDF merely because a
simulation edition needs one.  State the chosen root/body convention in the
variant manifest and add a free root only in the MJCF edition when the robot is
meant to be dynamic.  In MJCF, a `free` joint has six DoFs and can only be on a
body directly under `worldbody`; it cannot share that body with other joints.
([MuJoCo XML reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html#body-joint),
[G1 root](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L57-L64)).

### Mesh paths

**Menagerie rule — mandatory.** Resolve every URDF mesh relative to the URDF,
inside that version's `meshes/` directory.  The official packaged G1 URDF uses
`../meshes/<file>.STL`, and the regression test requires every mesh to resolve
there. ([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L26-L31),
[test](../../tests/test_unitree_g1.py#L105-L125)).  The separate retargeting
URDF is one directory deeper and therefore uses `../../meshes/`; that is a
layout-derived adaptation, not a different mesh policy.
([retargeting URDF](../../src/menagerie_x/assets/unitree_g1/urdf/for_retargeting/g1.urdf#L1-L4)).

## 4. MJCF edition convention

### Structure

**MJCF rule.** An MJCF model is a kinematic tree rooted at `worldbody`; dynamic
bodies are nested below it, while the world body itself cannot have an inertial
or joint. ([MuJoCo XML reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html#body)).

**Menagerie rule — mandatory.** Use this top-level order for authored MJCF
editions when each section is needed:

```xml
<mujoco model="<edition-id>">
  <compiler angle="radian" meshdir="../meshes"/>
  <default>…shared classes only when they eliminate real duplication…</default>
  <asset>…named meshes/materials/textures…</asset>
  <worldbody>…robot body tree and optional scene bodies…</worldbody>
  <actuator>…one explicitly ordered actuator per actuated joint…</actuator>
  <sensor>…named sensors bound to sites…</sensor>
  <visual>…camera/render defaults…</visual>
</mujoco>
```

G1 demonstrates `compiler`, asset mesh aliases, a nested pelvis-rooted robot
tree, ordered motors, site-based IMU sensors, and scene rendering/floor
configuration. ([MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L1-L64),
[actuators and sensors](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L339-L390),
[scene](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L393-L408)).
`<default>` and `<include>` are valid MJCF facilities but are not present in
this compact G1 edition; use them only to make a larger model clearer, never as
a requirement inferred from G1.

### Kinematic hierarchy

**Unitree observation.** The official G1 MJCF uses a dynamic floating
`pelvis` root directly below `worldbody`.  The left and right leg chains branch
from that pelvis, as does the serial trunk
`waist_yaw_link` → `waist_roll_link` → `torso_link`.
([MJCF root and lower-body branches](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L57-L151)).
Both arm chains then branch from the same final `torso_link`: shoulder pitch,
shoulder roll, shoulder yaw, elbow, wrist roll/pitch/yaw, and optional hand
subtrees.
([left arm](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L151-L246),
[right arm](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L247-L335)).

**Menagerie rule — mandatory.** Preserve that explicit hierarchy for the G1
edition: one named dynamic floating pelvis root; left/right legs branching
from the pelvis; one serial waist/trunk ending at `torso_link`; and both serial
arm chains branching from that final torso body before shoulder pitch/roll/yaw,
elbow, wrist, and optional hands.  Every future bilateral robot must likewise
declare a named root, a serial trunk, and the explicit common parent from which
the paired upper limbs branch.  Document any intentional deviation in the
variant or edition metadata, including multiple torso bodies or independent
shoulder girdles, so consumers do not have to infer the topology from textual
element order.

### Body, visual, and collision representation

**Unitree/MJCF observation.** Each dynamic G1 body places `<inertial>` first,
its named joint second, then geoms.  The first mesh geom is render-only via
`contype="0" conaffinity="0" group="1" density="0"`; the next geom omits the
collision-exclusion flags and therefore serves as a physical collision geom.
([MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L65-L80)).
The ankle adds physical primitive contact points after its render mesh.
([MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L90-L98)).

**Menagerie rule — mandatory.** Preserve this semantic separation in every
editable edition:

- visual geoms: disable contact with `contype="0" conaffinity="0"`, use the
  workbench's visual group, and set `density="0"` when they are display-only;
- collision geoms: omit the display-only contact exclusions and use reviewed
  primitive/mesh geometry;
- a body must map both representations back to the same body identity so
  collision editing and force picking affect the physical body, not a render
  mesh.

Use a `*_visual`/`*_collision` geom name when an edition needs stable
per-geometry references.  The default G1 edition leaves most geoms unnamed;
the ProtoMotions reference names its visual/collision geoms, which is useful
evidence for that optional naming convention but not an upstream Unitree rule.
([ProtoMotions MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/protomotions_g1_retargeting_box_feet.xml#L44-L80)).

### Motors and sensors

**Menagerie rule — mandatory.** List motors in the declared actuated-joint
order and give every motor a name equal to its `joint` target unless a real
transmission requires an explicit mapping.  The G1 edition has 43 motors in
the body-29, left-hand-7, right-hand-7 order.  Note that its right-hand body
tree puts middle before index, whereas the motor list puts index before middle;
the motor list is the control-vector contract. ([MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L339-L383)).

**Menagerie rule — recommended.** Give sensor sites stable semantic names and
sensor names of `<site-or-frame>-<measurement>`.  G1's torso/pelvis gyro and
accelerometer pairs bind to `imu_in_torso` and `imu_in_pelvis` sites.
([MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L60-L64),
[sensors](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L385-L390)).

## 5. Authoring checklist

### Mandatory before a new variant is registered

- [ ] Create `urdf/`, `mjcf/`, and `meshes/` under one `<robot_version>`
      package; retain source licences/notices and provenance.
- [ ] Register one manifest variant with its `robot_version`, source format,
      URDF path, optional default MJCF path, DoF count, spawn pose, status, and
      source provenance.
- [ ] Keep the official or canonical source description byte-identifiable;
      document every local change, including path-only rewrites.
- [ ] Use unique lowercase snake_case link/joint/body/mesh/site names and a
      deterministic movable-joint list.
- [ ] For every physical URDF link, provide mass/inertia, a visual
      representation, and intentional collision geometry; document exceptions.
- [ ] Resolve every mesh under the package's `meshes/` directory; never use a
      checkout-absolute path or a path outside the robot package.
- [ ] In every dynamic MJCF edition, use one explicit free root only when the
      model is intended to float; place it on a direct `worldbody` child.
- [ ] For a bilateral robot, declare the named root, serial trunk, and explicit
      common upper-limb branch parent; document any topology deviation.
- [ ] Separate render-only from collision geoms and retain body identity for
      both.
- [ ] Make every MJCF actuator refer to exactly one existing actuated joint in
      the declared control order.

### Recommended for maintainability

- [ ] Group source declarations anatomically: root, left/right lower limbs,
      torso, accessory frames, left/right upper limbs, hands/end effectors.
- [ ] Put URDF contents in inertial → visual → collision order and make visual
      geometry precede collision geometry in the corresponding MJCF body.
- [ ] Give deliberately simplified retargeting/learning editions a purpose
      subfolder and a non-default manifest/edition identity.
- [ ] Use named `*_visual` / `*_collision` MJCF geoms where tools need
      geometry-level references.
- [ ] Bind sensors to named sites rather than unnamed coordinates, and keep
      scene cosmetics after robot definition.

## 6. Validation gates and common pitfalls

| Gate | What to verify | G1 evidence / failure avoided |
| --- | --- | --- |
| Paths | Every manifest path exists; every URDF/MJCF mesh resolves inside the package mesh directory. | G1 tests resolve each source mesh and reject missing meshes. ([test](../../tests/test_unitree_g1.py#L105-L125)) |
| Provenance | Default source and non-default reference editions have distinct supplier, revision, licence, and purpose metadata. | Unitree and ProtoMotions records are separate. ([manifest](../../src/menagerie_x/assets/manifest.json#L141-L159)) |
| Joint contract | Count movable joints; compare the exact ordered list with the declared robot/motion profile; confirm one actuator per control joint. | 43 total = body-29 plus hands-14; 43 motors. ([test](../../tests/test_unitree_g1.py#L127-L133), [MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L339-L383)) |
| Free-root policy | Dynamic edition has exactly one free root; fixed source URDF has no accidental world joint. | The G1 source comments conversion scaffolding, while MJCF adds the free root. ([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L13-L18), [MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L57-L64)) |
| Kinematic hierarchy | Resolve the named root, serial trunk, and explicit common upper-limb branch parent; compare bilateral chain order and record deviations. | G1 branches both legs and its serial waist from `pelvis`, then both arms from the final `torso_link`. ([MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L57-L161), [MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L247-L335)) |
| Collision semantics | Toggle visual-only/collision-only views and verify both select the same physical body; run the model under gravity/contact. | Render-only geoms are explicitly contact-disabled; ankle primitives supply physical contacts. ([MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L65-L98)) |
| Compile | Run asset validation and a native MuJoCo compile for each selectable MJCF edition. | The G1 test exercises both the default and retargeting editions when MuJoCo is available. ([test](../../tests/test_unitree_g1.py#L147-L154)) |

Two pitfalls deserve special treatment:

1. **Sensor frames without inertia.** G1 intentionally has four empty fixed
   frame links (`imu_in_torso`, `imu_in_pelvis`, `d435_link`, `mid360_link`).
   The workbench reports them as `inertial-missing`, while the regression test
   confirms they are the only such warnings and that there are no errors.
   Treat these as documented sensor-frame exceptions, not as a licence to omit
   inertia from moving or collision-bearing links.
   ([URDF](../../src/menagerie_x/assets/unitree_g1/urdf/g1_29dof_with_hand_rev_1_0.urdf#L547-L576),
   [test](../../tests/test_unitree_g1.py#L119-L125)).
2. **Assuming a visual mesh is physics.** Render meshes may be contact-disabled
   or lack a useful collision hull.  Keep collision geometry explicit, and
   test the collision-only viewer path.  The G1 default's contact-disabled
   visual geoms and primitive foot contacts are the direct counterexample.
   ([MJCF](../../src/menagerie_x/assets/unitree_g1/mjcf/g1_29dof_with_hand_rev_1_0.xml#L65-L98)).

## Decision summary

Use Unitree G1 as the naming, anatomical ordering, and source-link-layout
example.  Use MJCF's explicit body/geom/actuator semantics for the simulation
edition.  Use Menagerie policy for per-version packaging, provenance,
deterministic joint contracts, collision editing, and validation.  Keeping
those three layers separate is what lets future vendor imports retain their
authentic descriptions while still behaving consistently in Menagerie.
