# MJCF sample edition

`astro_p2_43dof_dex3_1.xml` corresponds to the sibling URDF: floating base,
29 Astro body hinges, 14 Dex3-1 finger hinges, no actuators (`nq=50`, `nv=49`).
Visual meshes are collision-disabled in group 1; collisions are group 3.
All collision geoms are primitives: 57 native capsules (43 body + 14 finger), 12 cylinders,
6 boxes (two feet + two per palm), and one sphere. Source explicit
inertias are retained with inference disabled. Fixed frames remain named.

Read [README.md](README.md) for sample mounting assumptions, joint-order mapping,
source licensing, mass accounting, regeneration and validation. Relative mesh
paths are self-contained; keep `meshes/` next to the XML. No floor, initial
standing offset, actuator, controller, hand calibration or retargeting is added.
`mjcf-conversion.json` includes hashes and the source-to-capsule mapping.

## MJCF-only contact refinement

The MJCF now intentionally differs from the URDF collision geometry:
- Each shin capsule's lower endpoint is raised from -0.260 to -0.230 m in the knee frame, retaining its 53 mm radius and upper endpoint.
- Each palm uses two simple boxes, leaving a notch at the thumb-side rear corner. The full-width front box spans X=52–86.7 mm; the narrower rear box spans X=0–52 mm.
- Proximal thumb capsules use a 12 mm radius and begin 18 mm along the thumb segment, removing the oversized root overlap. Their distal center remains at 41.175 mm.

All sole/foot-side shapes, distal finger capsules, visual geometry, inertias and joints are unchanged. No contact exclusions or collision masks were changed.

`mjcf-refinement.json` records the pre-pelvis-refinement hash and checks: zero contacts in the zero pose, a 315-pose ankle pitch/roll grid, and a 315-pose thumb-root joint grid. Other joints were zero; these are static contact checks, not whole-body or dynamic validation.

The original `mjcf-conversion.json` describes the pre-refinement URDF conversion. Running the URDF converter again will overwrite these intentional MJCF-only edits; preserve/reapply them if rebuilding. The URDF comparison in the viewer therefore shows the earlier collision geometry.

## MJCF-only torso and arm refinement

Four added native capsules cover the lower upper arms and wrist-roll housings
(one per side on each segment). Wrist-yaw cylinders use radius 29 mm, half-length
21 mm and center X=47 mm. The head-adjacent upper-back capsule was removed at the
user's request; the head sphere and three neck-handle capsules are retained.

The torso was subsequently adjusted to eliminate 18 newly introduced arm-contact
cases. The upper capsule returns to its original radius 90 mm and Y endpoints
+/-44.5 mm at Z=250 mm. The middle capsule uses radius 93 mm and Y endpoints
+/-18 mm, centered at X=2 mm, Z=160 mm. The lower capsule is unchanged. The shorter
middle capsule gives arms more side clearance while retaining slightly more depth
than the original 90 mm radius. No exclusions or masks were changed.

With 10,000 fixed-seed visual-surface samples per mesh, torso 95th-percentile
outside distance is 19.7 mm versus 18.8 mm before the torso/arm refinement; maximum
sampled distance remains 32.2 mm. This is a modest coverage tradeoff for clearance,
not an exact mesh envelope. All other current per-link metrics are recorded in
`mjcf-refinement.json`.

## Motion checks after torso and wrist clearance adjustments

- All 18 previously recorded new contact cases now have zero contacts.
- All 43 joint limits remain unchanged. Individual full-range sweeps (2,623 poses)
  produce no newly colliding poses; 142 poses already collided in the baseline.
- The original 6,000 combined arm samples have no newly colliding poses.
- An additional 20,000 combined arm samples have no newly colliding poses. These
  expanded samples informed tuning. The saved wrist-to-hip case and its mirrored
  right-arm configuration are both clear after reducing the wrist cylinder radius
  from 30 to 29 mm; length and center are retained.
- The previous 630 ankle/thumb regression poses remain clear. Two thousand sampled
  combined hand configurations retain their prior clear/contact classifications,
  and all 1,000 combined waist configurations are clear.

`mjcf-mobility-review.json` records the original suite, and
`mjcf-torso-clearance-review.json` records all 18 resolved configurations and the
expanded sample results, including the resolved wrist-to-hip configuration.
These are static `mj_forward` contact checks against the pre-upper-body-refinement
baseline, not dynamic stepping or proof of clearance for every possible motion.
Visuals, inertias, joints, hands, feet, shin refinements, and URDF are unchanged.

## Pelvis/root refinement

The root's horizontal cylinder and vertical capsule are retained. A single
shallow vertical cylinder (`pelvis_upper_shell_collision`) covers the upper shell
rim: radius 57 mm, half-height 14 mm, centered at Z=86 mm in the pelvis frame.
It ends at Z=100 mm, below the waist-yaw origin at 112.3 mm. The cylinder fills
coverage lost where the existing capsule tapers; it does not enlarge the lower
hip-joint envelope. Hip and waist link collision shapes are unchanged.

In the same 10,000-sample neutral visual-surface check, pelvis outside distance
improves from 10.0 to 6.1 mm at the 95th percentile and from 15.6 to 12.0 mm at
the sampled maximum. Surface samples more than 10 mm outside fall from 4.97% to
0.81%. This is an approximate primitive fit, not complete mesh coverage.

`mjcf-pelvis-review.json` records the pelvis refinement revision;
earlier JSON reviews retain the hashes of the revisions they originally tested.
Compared with the immediately preceding model, no existing element, mass,
inertia, joint range, collision mask, or exclusion changes. Static regression
checks cover individual joints, combined hip/knee/ankle configurations, arms,
hands, waist, and previously resolved cases; see the report for counts and limits.

Final pelvis regression: no newly colliding poses across 26,000 arm samples,
10,000 leg samples, 1,000 waist samples, 2,000 hand samples and 2,623 single-joint
poses. The 19 saved torso/wrist cases and 630 ankle/thumb regression poses remain
clear. These sample sets were used for tuning and are not independent validation.

## Fist default and palm refinement

`fist-pose.json` defines the viewer's default hand pose; the MJCF includes a `fist`
keyframe with the same values. Thumb opposition (`thumb_0`) is zero on both sides;
left thumb bend joints are +0.9 and +1.3 radians, right thumb bend joints are
-0.9 and -1.3. Index and middle fingers use -1.55/-1.70 radians on the left and
+1.55/+1.70 on the right. The linked hand-closure control scales these values
from open to fist. Individual joint sliders can override this preset.

The right-thumb axes and ranges match the pinned official source URDF. The
annotated asymmetric pose used right opposition=-1.047 rad with right bend_1=0,
versus left opposition=0 and bend_1=+1.047 rad. Correct matching closure requires
opposite bend signs, not reversing the model's joint axes. No axes, limits or
joint reference angles have been changed. Maximum thumb bend is deliberately
avoided: the old palm collider reported about 20 mm penetration at both maxima.

Palms retain two simple boxes per hand. The front box now spans X=52–85 mm,
Y=-13–19 mm on the left (mirrored on the right), and Z=+/-41 mm. The rear spans
X=0–52 mm, Y=-6–18 mm on the left (mirrored on the right), Z=+/-35 mm. These trim
the broad-box corners and preserve the thumb-side root notch. Each box is a
subset of its prior envelope. Fingers, including distal capsules, are unchanged.

`mjcf-fist-review.json` is the latest model hash and validation record. All 101
open-to-fist samples are contact-free; left/right thumb origins mirror within
1e-8 m in palm coordinates. Repeated zero-hand motion suites introduce no new
colliding poses across 26,000 arm, 10,000 leg, 2,000 hand, 1,000 waist and 2,623
individual-joint configurations. The 630 ankle/thumb and 19 saved torso/wrist
regression configurations remain clear. This does not certify arbitrary body
motion with closed hands, dynamic grasping or hardware calibration.

The viewer explicitly loads the `fist` keyframe at startup. Other MuJoCo consumers
must select that keyframe to use this default; ordinary `mj_resetData` still uses
the unchanged zero-joint configuration. The URDF remains unchanged. Rebuilding
from URDF overwrites these MJCF-only collision edits and the fist keyframe.
