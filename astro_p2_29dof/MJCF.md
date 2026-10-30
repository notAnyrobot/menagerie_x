# Astro P2 29 DOF — MJCF edition

`astro_p2_29dof.xml` is generated from the sibling canonical URDF. All mesh paths
are relative to this bundle; keep `meshes/` beside the XML.

- 29 hinge joints and one floating base (`nq=36`, `nv=35`).
- Visuals remain in group 1 with collision disabled. Collisions are in group 3.
- 39 cylinder-plus-two-sphere assemblies become native capsule geoms. Matching
  requires equal radii and sphere centers at the cylinder endpoints on the same
  link; ordinary cylinders and standalone spheres are retained.
- Each foot has eight native sole capsules, two side-perimeter cylinders and one
  connecting box. This is the same geometry as its 27 URDF collision elements.
- All fixed frames, original explicit masses and inertias are retained. Inertia
  inference is disabled: the fixed foot collision frames add no mass beyond the
  ankle-roll inertias. A raw MuJoCo URDF import would otherwise infer extra mass.
- No ground plane, actuators, control gains or initial standing-height offset is
  added. The root starts at the URDF origin; place it appropriately in a scene.

Regenerate from the repository root:

```sh
.venv/bin/python scripts/build-astro-mjcf.py
```

The generator compiles the result, checks mass and joint counts, verifies foot
shape counts, and compares body poses and joint limits with the URDF import at
three joint configurations. `mjcf-conversion.json` records hashes and the full
source-to-capsule mapping. Conversion was checked with MuJoCo 3.11.0; it is not a
retargeting, controller or dynamic-contact quality validation.
