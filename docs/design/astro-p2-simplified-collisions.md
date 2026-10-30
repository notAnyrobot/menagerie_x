# Additional simplified Astro P2 collision variant

Maintainer request, 2026-10-30: create a simplified Astro P2 collision variant
following G1 MJX's approach, with fewer primitives and explicit contact pairs;
preserve existing variants, keep MJX runtime deferred, delegate implementation.

Baseline: `20ad78c` on `codex/astro-silver-hands-g1-primitives`.
Implementation branch: `codex/astro-p2-simplified-collisions`.

## Accepted revision: preserve the body, optimize arms only

The maintainer rejected the whole-body 27-primitive result and marked both arms
and hands in the original detailed-model screenshot. The current scope
supersedes the whole-body shape target and all-zero mask policy below:

- Revise the existing `astro_p2_simplified.xml` / `scene_simplified.xml` pair;
  label it **Astro P2 with optimized arm collisions**. Do not add another model.
- Restore all original non-arm colliders from `astro_p2.xml`, including pelvis,
  hips, legs, feet, torso/neck and head. Preserve their exact dimensions,
  attachments, names, groups, colors and contact parameters/masks.
- Simplify only the collision geoms below the left/right shoulder subtrees.
  Reduce redundant housing shapes while respecting independent elbow/wrist
  joints. A fixed hand and its wrist-yaw housing may share one proxy because
  their relative transform is fixed; independently rotating links must retain
  appropriate separate proxies.
- Preserve all existing variants and every body/joint/inertial/visual/option
  property. No actuators, controller tuning or MJX runtime work is introduced.
- Use a hybrid contact policy: original non-arm collisions remain automatic;
  optimized arm masks are zero and the scene explicitly selects their floor,
  torso/body and opposite-arm interactions. Do not override the preserved
  lower-body contact parameters with explicit pairs.
- Keep the original floor and reference pose. Compare lower-body contact sets
  and parameters against the default model, and check bent elbow/wrist poses.
  Refresh previews and add guards for exact non-arm preservation.
- Fewer total shapes is useful, but there is no required 27-shape target.
  Geometry and articulation take precedence over minimizing the count.

Revision branch: `codex/astro-arm-collisions`, baseline `1fcf365`.

## Accepted wrist and hand refinement

The next maintainer review identifies the small wrist-roll collider between
the forearm and wrist-pitch capsules as redundant, and requests a hand envelope
closer to the rounded G1 hand collider. Current implementation scope:

- Refine the same arm-optimized variant; preserve all 40 non-arm colliders,
  all shoulder/upper-arm shapes, existing variants, visuals and body properties.
- Remove the small wrist-roll proxy once its coverage is retained by the
  neighboring envelopes across wrist articulation. A small forearm endpoint
  adjustment is allowed; preserve separate independently moving pitch/hand
  frames rather than welding them together.
- Replace the long thin wrist/hand capsule with a shorter-axis, rounder proxy
  inspired by the G1 box-feet hand collider, fitted to Astro's native hand.
  Do not import G1 hand meshes or mechanically reuse its dimensions.
- Remove scene pairs for deleted geoms while preserving all other pair
  parameters and the original non-arm automatic contact behavior.
- Check reference, bent and wrist-limit poses, native loading/stepping, source
  preservation and archive closure. Render a wrist/hand close-up for review.
- The old requirement to contain the previous long hand capsule is superseded
  by the new shape fit; record any approximation honestly. Native hand mesh,
  mass/inertia, wrist joints and MJX deferral remain unchanged.

Revision branch: `codex/astro-wrist-hand-refinement`, baseline `10fcf7e`.

## Accepted palm-only correction

The maintainer rejected the full-hand envelope as too large: matching the G1
example and covering only the palm is sufficient. This supersedes the preceding
full-mesh containment goal:

- Use the G1 box-feet hand capsule's compact geometry in Astro's wrist-yaw
  frame: radius 0.05 m, centerline `(0.05, 0, 0)` to `(0.10, 0, 0)`.
- Do not enlarge the collider to include extended fingers or thumb. Those
  regions intentionally remain outside this palm-contact approximation.
- Change only the two hand geoms and their documentation/provenance/previews.
  Keep the wrist redundancy cleanup, all other arm/body shapes and all 68
  contact pairs unchanged. No mesh, physical property or MJX runtime changes.
- Replace the whole-hand coverage test with palm containment and fingertip
  exclusion checks. Inspect a native overlay to confirm the smaller shape.

Revision branch: `codex/astro-palm-colliders`, baseline `7a34149`.

## Original scope and ownership (superseded where noted above)

- Add `astro_p2/astro_p2_simplified.xml` and `scene_simplified.xml` as a third
  native Astro configuration. Label it **Astro P2 with simplified collisions**.
- Base it on the default 29-DoF Astro model with its original fixed hands.
  Keep the two existing Astro models, scenes, previews and imported sources
  byte-identical. No additional articulated-hand collision variant is requested.
- Preserve the base model's body tree, masses/inertias, all 29 joints and free
  base, passive parameters, joint force limits, reference configuration, all 37
  visual meshes/materials, and native options. Astro remains unactuated (`nu=0`);
  do not copy G1 PD servos, gains, timestep, solver tuning or keyframes.
- Author a compact envelope fitted to Astro's own link frames and existing
  shapes. Target 27 primitives rather than the default model's 60: pelvis/head
  spheres, a torso capsule, four capsules per arm, and eight shapes per leg
  including three sole capsules and one self-contact foot box.
- Disable automatic contacts on the new robot. Its sibling scene supplies an
  explicit list of selected self-contacts and floor contacts, modeled on G1's
  26 self / 23 floor pair pattern, with one floor at Astro's existing `z=-0.75`.
  Keep self contacts frictionless (`condim=1`); floor pairs use tangential
  friction (`condim=3`). Foot boxes serve selected self-contacts rather than
  duplicating sole support contacts.
- These are deliberate coarse collision approximations. Preserve the existing
  detailed model for finer surface coverage. Do not claim exhaustive mesh
  coverage, calibrated contacts, faster performance or a standing controller.
- Preserve actual license notices for adapted Menagerie contact definitions;
  Astro-origin model/mesh material retains Apache-2.0. Record derivation and
  geometry decisions without adding a generator or metadata framework.

## Verification and delivery

- Use subagents for geometry design, robot XML, and scene/docs/previews.
- Register the pair in the native catalog and gallery. Provide native visual
  and collider-only previews, explicitly documenting their initialization.
- Check source preservation, equal compiled rigid-body/joint/visual properties,
  fewer collision primitives, zero automatic masks, valid explicit pairs, and
  contact behavior (support contacts, selected self-contacts and excluded pairs).
- Run native load/short-step, standalone family and extracted source archive
  checks. Keep the existing models in the test inventory. Review the completed
  diff independently before finalizing the branch.
- MJX/JAX/Warp runtime, Workbench, URDF compatibility, controller development
  and performance benchmarking remain deferred. No new dependency is needed.
