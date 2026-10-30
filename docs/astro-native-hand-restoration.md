# Restore Astro P2 native rubber hands

The user rejected the G1 rubber-hand fit and requested the original Astro hands.
Branch: `codex/astro-native-rubber-hands`, from `899a43f`.

## Source and scope

Original meshes and inertias are restored from repository revision
`fcbb3f222359df8b275fee1bc79d47721efdd2ec`, using
`astro_p2/assets/{left,right}_hand_link.stl` and
`astro_p2/urdf/astro_p2_30dof_primitive_collision.urdf`. The source URDF is retained
verbatim under `astro_p2/provenance/rubber_hand_sources/`; this is source evidence,
not a maintained 30-DoF model. The native model still has a fixed head and 29 DoFs.

The original meshes, source visual color, fixed-joint transforms, hand masses,
COMs, and full inertia tensors are restored. The original wrist-local hand
cylinder (radius 0.027 m, length 0.08 m) plus two matching end spheres becomes
an equivalent native capsule expressed in the existing hand frame. The refined
wrist housing collisions remain unchanged. The older 54 mm sphere-hand stand-ins
are not used. No G1 hand or wrist dynamics remains in the default Astro model.

`provenance/rubber_hands.json` records the exact revision, source/mesh hashes,
transforms, inertias, and collision capsule endpoints. The rejected G1 trial's
record and notices remain historical provenance. G1 models and assets themselves
are unchanged.

## Verification

The expected model has `nq=36`, `nv=35`, `nu=0`, and mass **40.58255359 kg**.
Tests compare native hand meshes/inertias with original Astro source records,
and compare the refined body by named bodies, joints, and geoms against the
unchanged Dex3-1 alternative. Native model/scene load-and-step and standalone
family checks remain the acceptance gate. The preview is regenerated from the
restored native scene. Workbench, URDF compatibility, and MJX remain deferred.

Verified: `make all` passes all eight native test methods; all sixteen model/scene
entry points load from the extracted source archive. Non-hand XML is structurally
identical to the prior model; Dex model, scene, and preview are byte-identical.
All 40 retained source records and 501 preexisting local files remain unchanged.
Original Astro meshes are byte-identical to their source Git blobs. The updated
preview was visually inspected, and 75 active-document links/anchors resolve.
