# Astro arm-only collision revision

Implementation: `cc31426`, branch `codex/astro-arm-collisions`.
Baseline: `1fcf365c105b10776db158a0f68d0245c2057296`.
Scope: [the accepted arm-only revision](design/astro-p2-simplified-collisions.md#accepted-revision-preserve-the-body-optimize-arms-only).

The maintainer rejected the whole-body coarse envelope and marked the original
arms/hands for optimization. This revision replaces that alternative in place;
`astro_p2_simplified.xml` and `scene_simplified.xml` retain their paths. The public
label is **Astro P2 with optimized arm collisions**. Two subagents implemented
the robot and scene/previews; the main session integrated tests and documents.

## Geometry and preservation

- **40 non-arm colliders are restored exactly from `astro_p2.xml`**: pelvis,
  hips, legs, complete feet, torso/neck and head. Names, parent frames, shapes,
  placement, groups/colors and all contact attributes/masks match the source.
- Arms/hands reduce **20 → 12 shapes**, six capsules per side. The complete
  model has **52 colliders**, rather than a target of 27 for the whole body.
- Per arm: shoulder housing, upper-arm shaft, forearm, wrist-roll shell,
  wrist-pitch housing, and a combined fixed wrist-yaw/hand envelope.
- The long upper-arm shaft is rotationally symmetric about shoulder yaw;
  merging the collinear source shafts onto the shoulder-roll frame preserves
  their yaw-dependent envelope. Wrist roll and pitch retain independent frames;
  the final wrist/hand proxy follows wrist yaw because the hand is fixed to it.
- Some merged capsules broaden the old narrow shaft areas to retain their joint
  housing envelope. No exhaustive visual-mesh fit or runtime speedup is claimed.
  The original hand collision envelope itself excludes some visual mesh detail.

Removing only old/new arm collision geoms and normalizing model name/comments
leaves the complete source/revised XML tree identical. Compared 21 compiled
physical/mesh arrays, all 37 visual geoms and 29 numerical option fields with
the default model. Mass remains **40.58255359 kg**, `nq=36`, `nv=35`, `nu=0`.
Default/articulated models, scenes, previews, assets and imported evidence
remain unchanged: **111 protected preexisting Astro files** retain their hashes.

Arm-envelope checks covered twelve deterministic poses, including independent
joint bounds and a combined extreme pose. Source capsule envelopes and sampled
wrist-cylinder rims remained inside the revised proxies (maximum numerical
excess approximately `7.35e-14 m`). This checks those collision envelopes and
poses, not every visual-mesh vertex or hardware configuration.

## Hybrid contact policy and native behavior

Original non-arm geoms retain automatic contacts and source parameters. Only
the optimized arm geoms have zero masks. The scene contains **78 explicit arm
pairs**: 12 arm-floor and 66 selected self-contact pairs. Every explicit pair
includes an optimized arm; none overrides retained lower-body/body pairs or
their floor contacts. Arm-floor friction/solver defaults match the original
(`condim=3`, friction `1 1 .005 .0001 .0001`, `solref=.02 1`), rather than the
earlier copied G1 foot tuning. Selected arm self-contacts use `condim=1`.

At identical straight, asymmetric-knee and bent-leg poses, source/revised
non-arm contact names, positions, distances, frames, friction and solver
parameters matched to `1e-13`. The grounded straight pose has **32 contact
points across the original 16 sole capsules**. Pose grounding was temporary;
the original floor at z=-0.75 and reference configuration were not changed.

Reference and six elbow/wrist probes had no unintended contacts. A bounded arm
pose generated the selected wrist/hand-to-torso contact; a controlled unlisted
wrist/hand-to-foot overlap generated no contact. Three grounded states stepped
0.1 s with finite state and no warnings. Later trajectories can differ because
the arm collision approximation and selected interactions intentionally change.

`UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passed **15 test methods**:
two layout/style and thirteen model methods, covering ten native pairs. Five
arm-revision methods guard body/visual preservation, exact non-arm geometry and
parameters, lower-body contact equivalence, wrist frames/selected self-contact,
and the hybrid pair policy. Standalone family loading remains covered.

Both reference previews were regenerated and inspected. The visual PNG is
byte-identical to its previous version; the collider PNG now shows the original
detailed body and feet with optimized arms. Neither preview advances simulation.
Checked 87 local document/image links and `git diff --check` successfully.

## Source archive

Built `/tmp/menagerie-x-astro-arm-dist/menagerie_x-0.1.0.tar.gz`
(69,242,651 bytes) before this final verification note. A fresh extraction loaded
all **20 native model/scene entry points**. Revised model, scene, provenance and
collider preview matched the checkout; local experiment archives were excluded.

SHA-256:

```text
c58fb97c95e16cfecd5b3938d16337325d8e240cb62720765eaf29db88111bf3
```

## Standards

No actionable documented-standard breaches or Fowler baseline smells found.
Native XML repetition follows the repository's direct-authoring/preservation
conventions. Reviewed `git diff 1fcf365...HEAD` at implementation `cc31426`.

Standards: **0 findings**; worst issue: none.

## Spec

No actionable Spec findings against the accepted arm-only correction.
Independent review confirmed exact preservation of all 40 non-arm colliders
and the complete non-collision XML tree; all five arm collision tests passed.

Spec: **0 findings**; worst issue: none.

Review summary: Standards **0**, worst **none**; Spec **0**, worst **none**.
No runtime changes followed review. MJX execution, controllers, Workbench,
URDF compatibility and performance benchmarking remain deferred.
