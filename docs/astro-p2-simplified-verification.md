# Simplified Astro P2 collision variant: verification

Implementation: `99937dc`, branch `codex/astro-p2-simplified-collisions`.
Baseline: `20ad78c0c1c661f9200094b51395f7c85e9861e2`.
Scope: [accepted design](design/astro-p2-simplified-collisions.md).

Geometry design, robot XML, and scene/docs/previews were delegated to separate
subagents. The main session integrated the catalog, root documentation, tests
and source-archive verification.

## Configuration and geometry decisions

The additional pair is `astro_p2/astro_p2_simplified.xml` and
`astro_p2/scene_simplified.xml`, labeled **Astro P2 with simplified collisions**.
Its robot collision count is **27 instead of 60**: 23 capsules, two spheres and
two boxes. All 37 visual meshes and their appearance remain the default Astro.
Dimensions and attachments are recorded in
[the derivation receipt](../astro_p2/provenance/simplified_collisions.json).

The 27 roles follow the compact G1 arrangement, using Astro-specific dimensions:

- Central envelope: pelvis sphere (radius 0.08 m), torso capsule (radius
  0.12 m, spanning local z=0.07–0.24), and the existing head sphere (0.075 m).
- Each leg: hip, thigh, shin and ankle-bridge capsules, three sole capsules,
  and a foot box used for selected self-contacts.
- Each arm: shoulder, elbow/forearm, wrist and original fixed-hand capsules.
  Longer capsules replace several neighboring shell/housing primitives.

The retained G1-style geom role `linkage_brace_collision` covers Astro's ankle
bridge; it does not assert that Astro has G1's mechanism. Similarly, shoulder
and elbow role names do not introduce new joints or change Astro's joint axes.

Each sole retains radius 0.012 m and local bottom z=-0.051. Three continuous
capsules replace eight smaller capsules. They preserve main heel/toe extents
and support width while filling some fine sole-outline gaps. The foot box
approximately bounds the old toe/heel side cylinders and bridge, and is not
paired with the floor. The torso becomes one broad envelope: small handles and
supports are omitted; some front/back space broadens and maximum upper-chest
lateral coverage decreases. These are deliberate approximations, not measured
mesh containment or hardware fitting.

## Contact selection and licensing

The robot has zero automatic contact masks and no explicit pairs. Its scene
supplies **49 selected pairs**: 26 frictionless self-contact pairs (`condim=1`)
and 23 floor-contact pairs (`condim=3`). Six sole-floor pairs use friction
`1 1` and `solref="0.008 1"`. Pair attributes match G1's pattern after adapting
the floor name. Other interactions are omitted by design; a new environment
must supply its own intended pairs.

Astro robot/mesh material remains Apache-2.0. Adapted Menagerie scene contact
definitions retain the actual BSD-3-Clause notice in
[LICENSE.Menagerie](../astro_p2/LICENSE.Menagerie), byte-identical to the pinned
upstream notice. [Family licensing](../astro_p2/LICENSING.md) separates the scope.

## Preservation and native checks

- Both preexisting Astro models, scenes, previews, meshes and imported evidence
  remain unchanged: **111 existing runtime/asset/provenance files** retain their
  hashes and **964 compiled arrays** from the two existing models match.
- Removing collision geoms/comments and normalizing only the new model name
  leaves source and simplified robot XML canonically identical.
- Compared 21 compiled physical/mesh arrays, all 37 visual geoms and 29 option
  fields against the default model. Body tree, inertias, joints, passive
  parameters, force limits, reference state, visual placements and numerical
  options match. Mass remains **40.58255359 kg**, `nq=36`, `nv=35`, `nu=0`.
- No gains, actuators, controller, standing keyframe or solver retuning were
  added. Timestep remains 0.002 s with the native Euler integrator.
- Reference pose retains its approximately 0.105 m sole-to-floor gap; the scene
  floor stays at z=-0.75. Grounding was done only in temporary verification data.
- Grounded probes generated all six sole-floor interactions: 12 contact points
  at the sampled states, with no foot-box/floor contacts or self-contacts.
- Five selected reference/bent poses had no unintended self-contact. A valid
  left-arm pose generated the declared hand/torso `condim=1` contact. Controlled
  overlap probes also generated a selected torso/hand contact and no unlisted
  pelvis/hand contact. These are targeted checks, not all-pose certification.
- Native 0.1-second stepping from reference and grounded states remained finite
  with zero MuJoCo warnings. Both visual and collider-only 640×480 previews were
  rendered without stepping and inspected; rendering options do not alter XML.

`UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passed **13 test methods**:
two directory/style methods and eleven model methods, with subtests for all
ten native pairs (eight active and two legacy). This includes standalone family
copies, old-source physics, and the new collision/contact/preservation checks.
Checked 92 local documentation/image links and `git diff --check` successfully.

## Source distribution

Built `/tmp/menagerie-x-astro-simplified-dist/menagerie_x-0.1.0.tar.gz`
(69,227,648 bytes) from the implementation before final documentation additions.
A fresh extraction loaded all **20 native model/scene entry points**. The new
Astro model, scene, provenance, notice and both previews matched checkout bytes.
Local experiment archives and floating-model scratch files were excluded.

SHA-256:

```text
d420e9d4f643687512a12028c59d60958b9a2e3726642f0661ec9523c17a96c8
```

MJX/JAX/Warp execution, training, backend throughput, hardware fidelity,
Workbench and URDF compatibility remain deferred. Fewer primitives do not by
themselves establish a performance improvement or a stable standing controller.

## Standards

No actionable documented-standard breaches or baseline Fowler smells found in
`git diff 20ad78c...HEAD` (`20ad78c` → `99937dc`).

The review checked `CONTRIBUTING.md`, `UPSTREAM.md`, `CONTEXT.md`, root and Astro
READMEs/licensing, and the accepted native-first ADR. Directly maintained XML,
self-contained assets, notices, preserved imports, catalog registration and
deferred compatibility follow those conventions. Native XML repetition follows
the explicit authoring/preservation policy and is not an actionable smell.

Standards: **0 actionable findings**; worst issue: none.

## Spec

No actionable Spec findings against
[the accepted scope](design/astro-p2-simplified-collisions.md).

Independent checks confirmed preservation of non-collision model definitions
and existing Astro assets, correct six-capsule support contacts, and disabled
contacts against an undeclared floor. All 13 native tests passed.

Spec: **0 findings**; worst issue: none.

Review summary: Standards **0**, worst **none**; Spec **0**, worst **none**.
No runtime changes followed independent review.
