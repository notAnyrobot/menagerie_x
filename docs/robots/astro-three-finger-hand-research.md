# G1 three-finger hand source review

Reviewed 2026-10-22. This note records source evidence for the sample Astro hand variant; it does not establish mechanical compatibility with Astro.

## Identity

Unitree explicitly identifies G1's optional three-finger hand as **Dex3-1**, with seven active joints per hand: three for the thumb and two each for the index and middle fingers. Tactile arrays are optional on G1. [Unitree G1 product specifications](https://www.unitree.com/g1/)

The Dex3-1 product page advertises 710 g mass and 175 × 88 × 77 mm dimensions in the flat state. It reports thumb motion of −60…60°, −35…60°, and 0…100°, and two finger flexion ranges of 0…90° and 0…100°. These are physical motion descriptions; signed model coordinates differ by side. [Unitree Dex3-1 specifications](https://www.unitree.com/mobile/Dex3-1/)

## Official model assets and reuse

The official `unitreerobotics/unitree_ros` repository publishes separate [left URDF](https://github.com/unitreerobotics/unitree_ros/blob/5994d4faef0a9cadd3287f8de0199a67eeb2a259/robots/dexterous_hand_description/dex3_1/dex3_1_l.urdf), [right URDF](https://github.com/unitreerobotics/unitree_ros/blob/5994d4faef0a9cadd3287f8de0199a67eeb2a259/robots/dexterous_hand_description/dex3_1/dex3_1_r.urdf), and [16 STL meshes](https://github.com/unitreerobotics/unitree_ros/tree/5994d4faef0a9cadd3287f8de0199a67eeb2a259/robots/dexterous_hand_description/dex3_1/meshes). Pin: `5994d4faef0a9cadd3287f8de0199a67eeb2a259`.

The repository's [BSD 3-Clause license](https://github.com/unitreerobotics/unitree_ros/blob/5994d4faef0a9cadd3287f8de0199a67eeb2a259/LICENSE) permits redistribution/modification subject to retaining its copyright, conditions, and disclaimer, and prohibits using contributor names for endorsement without permission. No nested license or asset-specific override was present in the pinned repository tree. Retain a verbatim copy beside redistributed assets and record the upstream paths and hashes.

## Model inspection

Each standalone URDF has eight links, seven independent revolute joints, eight mesh visuals, seven mesh collisions and one thumb-proximal box collision, and explicit per-link inertials. There are no mimic joints. The palm is the root; its local +X direction extends along the fingers. Joint names and limits below are copied from the pinned URDFs, in radians:

| Suffix after `left_hand_` / `right_hand_` | Axis | Left range | Right range |
|---|---|---|---|
| `thumb_0_joint` | +Y | −1.04719755…1.04719755 | −1.04719755…1.04719755 |
| `thumb_1_joint` | +Z | −0.61086523…1.04719755 | −1.04719755…0.61086523 |
| `thumb_2_joint` | +Z | 0…1.74532925 | −1.74532925…0 |
| `middle_0_joint` | +Z | −1.57079632…0 | 0…1.57079632 |
| `middle_1_joint` | +Z | −1.74532925…0 | 0…1.74532925 |
| `index_0_joint` | +Z | −1.57079632…0 | 0…1.57079632 |
| `index_1_joint` | +Z | −1.74532925…0 | 0…1.74532925 |

Thumb joint 0 has URDF effort 2.45 N·m and velocity 3.14 rad/s; the other joints have 1.4 N·m and 12 rad/s. These are the published model fields, not independently verified hardware limits or a controller configuration. [Left](https://github.com/unitreerobotics/unitree_ros/blob/5994d4faef0a9cadd3287f8de0199a67eeb2a259/robots/dexterous_hand_description/dex3_1/dex3_1_l.urdf), [right](https://github.com/unitreerobotics/unitree_ros/blob/5994d4faef0a9cadd3287f8de0199a67eeb2a259/robots/dexterous_hand_description/dex3_1/dex3_1_r.urdf)

Summing each URDF's eight mass fields gives **0.69654599 kg per hand**: palm 0.37283854 kg; thumb base 0.08623657 kg; three proximal links 0.05885070 kg each; three distal links 0.02030626 kg each. This is 0.01345401 kg below the advertised 0.710 kg. The model does not explain the difference; use the supplied inertials consistently rather than silently rescaling them to the product mass. [Official URDF inertials](https://github.com/unitreerobotics/unitree_ros/blob/5994d4faef0a9cadd3287f8de0199a67eeb2a259/robots/dexterous_hand_description/dex3_1/dex3_1_l.urdf)

## Attachment evidence and limitations

The official full-body G1 model fixes each palm to its wrist-yaw link at translation `(0.0415, +0.003, 0)` m for the left and `(0.0415, −0.003, 0)` m for the right, with zero relative RPY. This describes G1's existing mount, not an Astro mounting drawing. [G1 model with Dex3-1 hands](https://github.com/unitreerobotics/unitree_ros/blob/5994d4faef0a9cadd3287f8de0199a67eeb2a259/robots/g1_description/g1_29dof_with_hand_rev_1_0.urdf)

An Astro adapter therefore requires an explicitly labeled sample transform and a hardware adapter whose geometry and mass remain to be measured. The source assets establish hand geometry and internal kinematics; they do not establish Astro bolt patterns, cable clearances, structural strength, hand calibration, hardware communication, retargeting, or safe contact parameters. Simplified collision shapes in an assembled sample must be distinguished from the upstream mesh collision assets.
