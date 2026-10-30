# Astro folded-elbow contact stops

Historical receipt before the maintainer shortened the left upper arm. Current
left contact uses the [actual forearm capsule](astro-left-elbow-direct-contact.md)
instead of the original internal sphere; the right setup remains unchanged.

The maintainer requested actual forearm/upper-arm collision near the folded
elbow limit after shaft consolidation. This refines only `astro_p2.xml`, on
the existing `codex/astro-palm-colliders` branch. No commit, merge or push was
performed.

## Implementation

For this model, folding farther approaches the **lower** elbow limit,
−0.52 rad (−29.79°), from the reference q=0 configuration. The +1.66 rad end
of the range extends the elbow in the opposite direction.

The continuous upper-arm shaft overlaps the broad forearm hinge envelope even
at q=0. Directly pairing the full capsules would therefore create permanent
contact. Instead, each elbow body gets one **radius-0.01 m sphere** named
`{side}_elbow_stop_collision`, wholly inside its existing forearm capsule.
Local centers are x=0.052311955 m left and x=0.054703143 m right, y=z=0.
The different positions compensate for the manually tuned upper-arm radii.

Both spheres have density=0, contype=conaffinity=0 and collide only through
two explicit `condim=1` pairs with their corresponding existing upper-arm
shaft. These pairs bypass the adjacent-body filter for the small stop proxies
while leaving the permanently overlapping large hinge envelopes filtered.
They use the existing default contact solver parameters; no global settings,
native ranges, joint margins, controllers or gains were changed.

The onset target is −0.47 rad, giving 0.05 rad (2.86°) before the native lower
limit. For upper-arm distal endpoint L=0.0295 m above the elbow pivot, combined
radius R=(upper-arm radius + stop radius), and folding angle a=0.47 rad, the
forearm sphere center is:

`x = L sin(a) + sqrt(R² − (L cos(a))²)`.

This selects contact at the upper-arm's rounded distal end. The force acts on
the forearm body and creates resisting elbow torque; this is a native contact
constraint, not a visualization-only marker or a change to the angle limits.

## Preservation

All **52 existing collider definitions and body attachments remain exact**.
Only two stop spheres and their two contact pairs were added, bringing the
default inventory to **54 colliders / 2 explicit pairs / 2 existing body
exclusions**. All other XML structure and attributes, meshes, inertia, body
physics and numerical options are unchanged. Both the simplified and
articulated-hand model XML files remain byte-identical to starting snapshots.

Default XML SHA-256 before:
`0347731e4c0c99cf8c9551cc6a22a6a2712bf74a489fdada7ca480d65ac21832`.
After:
`8c32e723bed8e3d52d747ad3b26eb7c4622815ed8bd84a4c21f062c51edce510`.

## Native verification

MuJoCo 3.11.0 signed distances and actual generated contacts agree. Both
stops begin contact at approximately **−0.470000 rad**. At q=0 their clearances
are 13.06/13.15 mm. At q=−0.46 rad they remain separated by about 0.293 mm.
No stop contact is present through the rest of the range up to +1.66 rad.

| Static elbow angle | Left / right penetration | Left / right normal force | Left / right resisting torque |
|---|---|---|---|
| −0.48 rad | 0.293 / 0.294 mm | 6.13 / 6.13 N | +0.180 / +0.180 Nm |
| −0.50 rad | 0.880 / 0.882 mm | 26.49 / 26.50 N | +0.778 / +0.780 Nm |
| −0.52 rad | 1.467 / 1.471 mm | 44.88 / 44.87 N | +1.320 / +1.322 Nm |

These are gravity-on full-model static probes. The native elbow angle limit
is not active at −0.48/−0.50 rad: the restoring torque comes from contact.
Positive torque opposes the negative folding direction.

An independent sweep checked **657 poses per side**: 219 elbow angles across
the full range and shoulder yaw −1.92/0/+1.92 rad. All contacts unrelated to
the new spheres retained identical pairs and distances versus the pre-edit
snapshot. The default reference pose is contact-free. Regression checks also
confirm that the spheres remain enclosed by their original forearm capsules.

Four 0.2 s diagnostic folding probes started at q=−0.4 rad with velocity −1 or
−3 rad/s, one side at a time. Gravity was disabled only in memory to isolate
the stop response; no controller or kinematic fixture was added. Each probe
generated actual contact force and reversed its elbow velocity before the
native lower angle limit became active:

| Initial speed | Minimum left angle | Minimum right angle |
|---|---:|---:|
| −1 rad/s | −0.484389 rad | −0.484348 rad |
| −3 rad/s | −0.505436 rad | −0.505345 rad |

All states stayed finite with no warnings. These are compliant stops; the
probes do not establish a hard angle clamp under arbitrary powered loads.

`UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passes **22 test methods**:
2 layout/style checks and 20 model methods, including native model/scene
loading and stepping, standalone family copies, knee checks and the new
contact-activation, containment and dynamic resistance regressions.

A native collision preview at q=−0.50 rad with abducted shoulders shows both
selected elbow contacts and contact-force arrows. It was rendered without
stepping or changing saved poses/materials. MJX runtime, Workbench, URDF
compatibility and controllers remain deferred.
