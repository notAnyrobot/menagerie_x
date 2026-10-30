# Approved Astro P2 collision design and simplified-variant retirement

On 2026-10-31 the maintainer approved the current `astro_p2/astro_p2.xml`,
requested committing it, retiring the separate simplified model and pushing
changes to origin. Implementation remains on `codex/astro-palm-colliders`.

## Approved default

The default XML is preserved byte-for-byte from the approved working tree.
SHA-256: `c492062c5b1c71874a7b7ef825c32493560065fbe6891a78727a497a42840ef9`.
Its latest manual upper-arm centerlines are `0 0 0 0 0 -0.12` in the
shoulder-roll frames, superseding the previous 0.124 m trial. Radii remain
0.037 m left / 0.039 m right. All default assets, meshes, inertia, joint
ranges, timestep and numerical settings are unchanged during retirement.
The articulated-hand model is also byte-identical to its starting snapshot.

The approved default has 52 collision primitives, 37 visual meshes, no explicit
pairs and two existing elbow/wrist-pitch body exclusions. All collision geoms
use ordinary automatic masks. The shaft-owning shoulder-roll body is the
forearm body's grandparent, enabling automatic elbow contacts. Reference
initialization has no contacts. Final geometry gives onset near −0.481659 rad
(−27.60°) left and −0.364978 rad (−20.91°) right, versus the native −0.52 rad
folded limit. Both shins retain the maintainer's 3 mm proximal extension;
knee extension and existing deep-flexion contacts remain covered by regressions.
No powered-controller or exact hard-stop behavior is claimed.

## Retirement

The simplified robot, sibling scene, three previews and derivation JSON moved
to `astro_p2/provenance/retired_simplified/`. Every moved file retains its exact
pre-retirement bytes. `snapshots.json` records original paths and SHA-256 hashes.
The archive preserves original embedded relative paths as historical evidence;
it is not a maintained runtime entry point. Shared assets and license notices
are preserved.

The retired variant was removed from `catalog.py`, preview overrides, active
README tables and root layout examples. It was not added as another legacy
runtime model. The collection now contains seven active models plus two
legacy Astro P1 models, for nine maintained model/scene pairs. Astro P2 has
only its default and articulated-hand pairs. The family README describes the
approved default and a newly rendered native collision preview.

## Verification

`UV_CACHE_DIR=/tmp/menagerie-x-uv-cache make all` passes **17 methods**:
2 layout/style and 15 native model tests. Native tests compile and step all
nine model/scene pairs, verify keyframes and load standalone family copies.
Default collision checks cover automatic elbow detection through yaw motion,
reference clearance, passive folding resistance, current shaft-frame geometry,
knee extension/deep bending, ground contacts, hand provenance and unchanged
body physics. Six checks specific to the retired alternative were removed;
useful knee/ground checks now exercise the maintained default.

The default XML and articulated model were independently compared byte-for-byte
with pre-retirement snapshots. All six archived files were hash-verified.
Current README links and `git diff --check` pass. The collision preview uses
native reference initialization without stepping or saved-material changes.

Historical iteration reports remain as dated evidence; this receipt supersedes
old runtime counts, shaft dimensions, explicit pair policies and test totals.
Workbench, URDF compatibility and MJX runtime remain deferred. This task pushes
the current branch only; it does not merge into main.
