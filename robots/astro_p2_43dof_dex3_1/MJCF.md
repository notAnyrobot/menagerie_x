# MJCF sample edition

`astro_p2_43dof_dex3_1.xml` corresponds to the sibling URDF: floating base,
29 Astro body hinges, 14 Dex3-1 finger hinges, no actuators (`nq=50`, `nv=49`).
Visual meshes are collision-disabled in group 1; collisions are group 3.
All collision geoms are primitives: 53 native capsules (39 body + 14 finger), 11 cylinders,
4 boxes (two feet + two palms), and one sphere. Source explicit
inertias are retained with inference disabled. Fixed frames remain named.

Read [README.md](README.md) for sample mounting assumptions, joint-order mapping,
source licensing, mass accounting, regeneration and validation. Relative mesh
paths are self-contained; keep `meshes/` next to the XML. No floor, initial
standing offset, actuator, controller, hand calibration or retargeting is added.
`mjcf-conversion.json` includes hashes and the source-to-capsule mapping.
