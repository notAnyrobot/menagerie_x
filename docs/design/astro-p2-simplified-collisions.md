# Additional simplified Astro P2 collision variant

Maintainer request, 2026-10-30: create a simplified Astro P2 collision variant
following G1 MJX's approach, with fewer primitives and explicit contact pairs;
preserve existing variants, keep MJX runtime deferred, delegate implementation.

Baseline: `20ad78c` on `codex/astro-silver-hands-g1-primitives`.
Implementation branch: `codex/astro-p2-simplified-collisions`.

## Scope and ownership

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
