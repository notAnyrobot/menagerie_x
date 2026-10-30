# Menagerie X

Terms for the robot collection, its descriptions, and simulation configurations.

## Language

**Robot variant**:
A named robot asset family whose supported descriptions are maintained together, such as `astro_p1`, `astro_p2`, or `unitree_g1`.

**Robot edition**:
A named robot-description configuration within a variant, such as `30dof_primitive_collision`. An edition may provide URDF, MJCF, or both.

**Description format**:
The serialization of a robot description, such as URDF or MJCF.

**Robot model**:
A description of one robot configuration, including its geometry, kinematics, dynamics, and any declared controls and sensors.

**Scene**:
A simulation environment and task configuration used with a robot model. It may include terrain, contact configuration, and poses.

**Simulation configuration**:
An explicit pairing of a robot model and scene, with an optional initial pose. It identifies what to instantiate and how to initialize it.

**Initial pose**:
A specified starting configuration of the robot, with associated control targets when provided.

**Canonical description**:
A maintained robot or scene description that is the authority for simulation and authoring.

**Source snapshot**:
An original description or source material preserved as evidence of an asset's origin.

**Portable robot bundle**:
A robot's descriptions and runtime dependencies that can be used independently of the surrounding catalog and authoring tools.

**Workbench revision**:
A saved authoring state that can be previewed and edited separately from supported catalog choices.

**Promotion**:
The explicit publication of an authoring revision into a supported robot model or simulation configuration.
