# Menagerie X domain glossary

## Robot variant

A distinct robot asset family stored in one directory beneath `assets`, excluding scene and terrain data. Examples include `astro_p1`, `astro_p2`, and `unitree_g1`.

## Description format

The serialization used by a robot description: URDF or MJCF. A variant may offer either format or both.

## Robot edition

A named robot-description choice within a variant and format, such as `30dof_primitive_collision`. Availability is format-specific; an edition is not required to exist in both URDF and MJCF.
