# Astro hand presentation and G1 primitive configuration

Accepted implementation scope from the maintainer's 2026-10-30 request.
Baseline: `main` at `ff684bc863f0089f76671fd1c25f6e12c0bb9b97`.
Implementation branch: `codex/astro-silver-hands-g1-primitives`.

## Astro P2 with hands

- Public gallery, family README and application edition labels say **Astro P2
  with hands**, retaining Dex3-1 identity in technical provenance and licensing.
- The 16 articulated hand visual meshes use neutral silver, consistent with
  Astro's silver parts. Keep the gold torso and other body colors.
- Preserve mesh bytes, hand mounts, dynamics, collision shapes, joint limits,
  keyframes, default Astro model and all imported source evidence.
- Refresh the native preview at the reference pose. This is a material/color
  edit in MJCF, not a change to geometry or a recoloring of historical sources.

## Additional G1 configuration

- Add `unitree_g1/g1_mjx.xml` and `scene_mjx.xml`, matching MuJoCo Menagerie
  revision `f3b6013629c7b94f8ee93fd977b161fa8350f9bc`.
- Preserve the complete upstream configuration: 29 body joints/actuators,
  27 robot collision primitives (23 capsules, two spheres, two boxes), 35 visual
  meshes, position servos, joint/solver settings, sensors, 49 scene contact
  pairs, and the scene's `home` / `knees_bent` poses.
- Copy required assets and the actual upstream BSD-3-Clause notice, recording
  source revision/hashes. Do not replace or retune either existing G1 variant.
- Register the new pair in the native catalog and gallery. Label it **Unitree
  G1 with primitive collisions**, keeping upstream filenames for close pairing.
- The preview uses `home`, without simulation stepping. Loading the scene is
  essential: the robot file disables automatic contacts and declares no pairs.
- Verify native model/scene loading, stepping, keyframes, standalone family and
  source-distribution loading, and compiled equivalence to the pinned source.
- MJX/JAX/Warp device execution, Workbench and URDF compatibility stay deferred.
  No new dependencies, compatibility layer or metadata framework is required.

The preceding [research](../research/unitree-g1-native-and-mjx.md) explains the
source contract and why native validation does not certify MJX runtime support.
