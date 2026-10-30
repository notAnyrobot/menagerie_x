# Compact palm collider correction

Baseline: `7a34149a15e8eb4fa5ccfce3e9147e686038e077`.
Branch: `codex/astro-palm-colliders`.
Scope: [accepted palm-only correction](design/astro-p2-simplified-collisions.md#accepted-palm-only-correction).

The maintainer rejected the full-hand envelope as too large. Both Astro hand
proxies now match the compact G1 box-feet hand reference: capsule radius
**0.05 m**, centerline **`0.05 0 0` to `0.10 0 0`**, in the wrist-yaw frame.
Total axial length is **0.15 m**, versus 0.22 m before. Extended fingers and
thumb are deliberately outside the palm-contact approximation. Full-hand
mesh containment is no longer a fitting or testing target.

Two subagents updated model/provenance and rendered/probed the scene. The main
session changed the goal-specific test, checked the diff and integrated docs.

## Scope and checks

- Robot XML comparison shows only the two hand geoms' `size` and `fromto`
  attributes changed. All other geometry, physical properties and visuals match.
- All **40 non-arm colliders**, forearm endpoint extensions, removed wrist-roll
  proxies, independent wrist joints and the 50-collider inventory remain intact.
- Scene XML is byte-identical to the baseline: **68 pairs** remain unchanged.
  All **111 protected existing Astro runtime/asset/source files** retain hashes.
- The palm probe is inside; an extended-finger probe is outside. Approximately
  51–53% of mesh vertices are inside, recorded only as characterization, not a
  completeness target. Native hand meshes and inertias were not changed.
- Reference plus fourteen wrist-bound/combined-pose probes forwarded and
  stepped without non-finite state or warnings. Positive palm-floor and
  palm-torso contacts work; lower-body ground contacts match the original in
  three leg poses. Folded elbows at 1.2 rad still produce selected palm/hip
  contact; this capsule is a coarse contact approximation, not calibration.
- `UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passed **17 test methods**,
  including standalone family loading. The corrected test now checks G1-size
  equivalence, palm inclusion and intentional fingertip exclusion.
- Both native 640×480 collider previews were refreshed and inspected. The
  [overlay](../astro_p2/astro_p2_wrist_hand_colliders.png) shows fingers extending
  beyond the smaller cap. Render transparency is temporary; saved visual
  materials and meshes are unchanged. No simulation stepping is used for images.
- `git diff --check` passed. No dependencies or packaging paths changed.

MJX runtime, controllers, Workbench and URDF compatibility remain deferred.
