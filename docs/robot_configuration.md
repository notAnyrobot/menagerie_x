# Astro Robot Configuration

This document describes the detailed control configuration, joint layout, key assets, and simulator settings for the **Astro** humanoid robot.

## Joint Order (30 DOFs)

The canonical joint order follows the MJCF body-tree depth-first traversal. URDF and MJCF variants share this same ordering.

| DOF | Joint Name (regex) | Group |
|----:|---|---|
| 0 | `left_hip_pitch_joint` | L Leg |
| 1 | `left_hip_roll_joint` | L Leg |
| 2 | `left_hip_yaw_joint` | L Leg |
| 3 | `left_knee_joint` | L Leg |
| 4 | `left_ankle_pitch_joint` | L Leg |
| 5 | `left_ankle_roll_joint` | L Leg |
| 6 | `right_hip_pitch_joint` | R Leg |
| 7 | `right_hip_roll_joint` | R Leg |
| 8 | `right_hip_yaw_joint` | R Leg |
| 9 | `right_knee_joint` | R Leg |
| 10 | `right_ankle_pitch_joint` | R Leg |
| 11 | `right_ankle_roll_joint` | R Leg |
| 12 | `waist_yaw_joint` | Torso |
| 13 | `waist_pitch_joint` | Torso |
| 14 | `waist_roll_joint` | Torso |
| 15 | `head_yaw_joint` | Head |
| 16 | `left_shoulder_pitch_joint` | L Arm |
| 17 | `left_shoulder_roll_joint` | L Arm |
| 18 | `left_shoulder_yaw_joint` | L Arm |
| 19 | `left_elbow_joint` | L Arm |
| 20 | `left_wrist_roll_joint` | L Arm |
| 21 | `left_wrist_pitch_joint` | L Arm |
| 22 | `left_wrist_yaw_joint` | L Arm |
| 23 | `right_shoulder_pitch_joint` | R Arm |
| 24 | `right_shoulder_roll_joint` | R Arm |
| 25 | `right_shoulder_yaw_joint` | R Arm |
| 26 | `right_elbow_joint` | R Arm |
| 27 | `right_wrist_roll_joint` | R Arm |
| 28 | `right_wrist_pitch_joint` | R Arm |
| 29 | `right_wrist_yaw_joint` | R Arm |

Regex patterns used in the config to match joint groups:

| Pattern | Matches |
|---|---|
| `.*_hip_(pitch\|roll\|yaw)_joint` | DOFs 0-2, 6-8 (all hip joints) |
| `.*_knee_joint` | DOFs 3, 9 |
| `.*_ankle_pitch_joint` | DOFs 4, 10 |
| `.*_ankle_roll_joint` | DOFs 5, 11 |
| `waist_yaw_joint` | DOF 12 |
| `waist_pitch_joint` | DOF 13 |
| `waist_roll_joint` | DOF 14 |
| `head_yaw_joint` | DOF 15 |
| `.*_(shoulder_(pitch\|roll\|yaw)\|elbow\|wrist_roll)_joint` | DOFs 16-20, 23-27 |
| `.*_wrist_(pitch\|yaw)_joint` | DOFs 21-22, 28-29 |

## Actuator Types

Three motor types are used, identified by their armature constants:

| Motor ID | Constant | Armature ($\text{kg} \cdot \text{m}^2$) | Joints |
|---|---|---|---|
| 8514-25 | `ARMATURE_8514_25` | 0.081431 | Hip (pitch/roll/yaw), knee, waist yaw |
| 5016-25 | `ARMATURE_5016_25` | 0.008811 | Waist pitch/roll, shoulder, elbow, wrist roll, ankle pitch/roll |
| 3907-36 | `ARMATURE_3907_36` | 0.002387 | Head yaw, wrist pitch/yaw |

> [!NOTE]
> Some joints apply a **multiplier** to the base armature for effective armature computation. For example, `waist_pitch_joint` uses `ARMATURE_5016_25 x 2.0 = 0.017622`.

## PD Control Parameters

Control mode: **`BUILT_IN_PD`** (simulator-native PD controller).

### Stiffness & Damping Formulas

Stiffness and damping are computed from the armature using the following formulas:

$$
K_p = \text{armature} \times \text{multiplier} \times \omega^2
$$

$$
K_d = 2 \times \zeta \times \text{armature} \times \text{multiplier} \times \omega
$$

where $\omega = 2\pi \times f$ (angular frequency), $f$ is the natural frequency in Hz, and $\zeta$ is the damping ratio.

**Global defaults:** $f = 10.0 \text{ Hz}$, $\zeta = 2.0$

### Local Parameter Tool

This checkout includes a browser tool for tuning PD parameters and inspecting preset keyframe heights.

```bash
uv run menagerie_x pd-tool
```

For a terminal-only launch that prints the URL without opening a browser:

```bash
uv run menagerie_x pd-tool --no-browser
```

The PD table panel loads the `Joint Parameters` table below. Adjust natural frequency `f` and damping ratio per joint group, then preview and apply changes to this document.

The `Keyframe Heights` panel loads preset poses from `src/menagerie_x/assets/astro_v1/constants.py` and uses the legacy V1 MuJoCo model to compute ground-aligned heights for:

| Body | Source link |
|---|---|
| Pelvis | `pelvis` |
| Torso | `torso_link` |
| Left shoulder pitch | `left_shoulder_pitch_link` |
| Right shoulder pitch | `right_shoulder_pitch_link` |

The panel also renders a MuJoCo snapshot for the selected keyframe. Available keyframes are `zero`, `home`, `t_pose`, and `knees_bent`.

For command-line height checks:

```bash
uv run menagerie_x heights --config knees_bent
```

### Joint Parameters

| # | Joint Pattern | Motor | Mult | $f$ (Hz) | Damping Ratio | $K_p$ | $K_d$ | Action Scale | Effort ($\text{N}\cdot\text{m}$) | Vel ($\text{rad/s}$) |
|--:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `.*_hip_(pitch\|roll\|yaw)_joint` | 8514-25 | 1.0 | 8.0 | 2.5 | 205.745 | 20.466 | 0.1580 | 130.0 | 18.85 |
| 2 | `.*_knee_joint` | 8514-25 | 1.0 | 9.0 | 2.8 | 260.396 | 25.787 | 0.1248 | 130.0 | 18.85 |
| 3 | `.*_ankle_pitch_joint` | 5016-25 | 2.0 | 8.0 | 2.5 | 44.524 | 4.429 | 0.3369 | 60.0 | 26.18 |
| 4 | `.*_ankle_roll_joint` | 5016-25 | 1.5 | 8.0 | 2.5 | 33.393 | 3.322 | 0.3369 | 45.0 | 26.18 |
| 5 | `waist_yaw_joint` | 8514-25 | 1.0 | 8.0 | 2.5 | 205.745 | 20.466 | 0.1580 | 130.0 | 18.85 |
| 6 | `waist_pitch_joint` | 5016-25 | 2.0 | 8.0 | 3.0 | 44.524 | 5.315 | 0.3369 | 60.0 | 26.18 |
| 7 | `waist_roll_joint` | 5016-25 | 1.66 | 8.0 | 3.0 | 36.955 | 4.411 | 0.3382 | 50.0 | 26.18 |
| 8 | `.*_(shoulder_*\|elbow\|wrist_roll)_joint` | 5016-25 | 1.0 | 10.0 | 2.5 | 34.784 | 2.768 | 0.2156 | 30.0 | 26.18 |
| 9 | `.*_wrist_(pitch\|yaw)_joint` | 3907-36 | 1.0 | 10.0 | 3.0 | 9.423 | 0.900 | 0.2653 | 10.0 | 20.94 |
| 10 | `head_yaw_joint` | 3907-36 | 1.0 | 10.0 | 3.0 | 9.423 | 0.900 | 0.2653 | 10.0 | 20.94 |

> [!TIP]
> **Action Scale** = $0.25 \times \text{effort\_limit} \;/\; K_p$. This follows the BeyondMimic convention where the scale factor bounds policy outputs to +/-25% of maximum torque equivalent displacement.

### Comparison with Atom Robot

For reference, the Dobot Atom robot uses a similar joint layout but different actuator parameters.

| Joint Group | Astro $K_p$ | Atom $K_p$ | Astro $K_d$ | Atom $K_d$ |
|---|---:|---:|---:|---:|
| `.*_hip_pitch_joint` | 205.745 | 234.502 | 16.373 | 24.881 |
| `.*_hip_roll_joint` | 205.745 | 152.071 | 16.372 | 16.135 |
| `.*_hip_yaw_joint` | 205.745 | 89.537 | 16.372 | 9.500 |
| `.*_knee_joint` | 205.745 | 169.126 | 16.372 | 17.945 |
| `.*_ankle_pitch_joint` | 69.569 | 29.846 | 4.429 | 3.167 |
| `.*_ankle_roll_joint` | 52.177 | 29.846 | 3.322 | 3.167 |
| `waist_yaw_joint` | 205.745 | 284.245 | 16.372 | 30.159 |
| `waist_pitch_joint` | 69.569 | 29.846 | 4.429 | 3.167 |
| `head_yaw_joint` | 13.570 | 100.000 | 0.720 | 5.000 |
| `.*_shoulder_pitch_joint` | 34.784 | 100.000 | 2.214 | 5.000 |
| `.*_elbow_joint` | 34.784 | 50.000 | 2.214 | 2.000 |
| `.*_wrist_roll_joint` | 34.784 | 100.000 | 2.214 | 5.000 |
| `.*_wrist_pitch_joint` | 13.570 | 100.000 | 0.720 | 5.000 |
| `.*_wrist_yaw_joint` | 13.570 | 100.000 | 0.720 | 5.000 |

## Default Joint Positions

| Joint Pattern | Position (rad) |
|---|---:|
| `.*_hip_pitch_joint` | -0.312 |
| `.*_knee_joint` | 0.669 |
| `.*_ankle_pitch_joint` | -0.363 |
| `.*_elbow_joint` | 0.2 |
| `left_shoulder_roll_joint` | 0.2 |
| `left_shoulder_pitch_joint` | 0.2 |
| `right_shoulder_roll_joint` | -0.2 |
| `right_shoulder_pitch_joint` | 0.2 |

All other joints default to 0.0.

## Body Mapping

| Semantic Name | Link |
|---|---|
| Left foot | `left_ankle_roll_link` |
| Right foot | `right_ankle_roll_link` |
| Left hand | `left_wrist_yaw_link` |
| Right hand | `right_wrist_yaw_link` |
| Head | `head_link` |
| Torso (anchor) | `torso_link` |

Default root height: **0.75 m**

## Asset Files

| Purpose | File |
|---|---|
| Simulation (legacy MJCF) | `src/menagerie_x/assets/astro_v1/legacy/mjcf/astro_v1.xml` |
| Retargeting (URDF) | `src/menagerie_x/assets/astro_v1/urdf/astro_v1.urdf` |
| Racket variant (URDF) | `src/menagerie_x/assets/astro_v1/urdf/astro_with_racket.urdf` |

## URDF Capsule Collision Extension

Standard URDF geometry does not define a capsule primitive. This package supports an Astro-specific extension tag for consumers that can read capsule collision data directly:

```xml
<collision name="left_knee_collision">
  <geometry>
    <capsule radius="0.055" fromto="0.01 0 -0.2 0.01 0 -0.0" format="astro-extension-v1" />
  </geometry>
</collision>
```

Generate an extended URDF from the MJCF capsule geoms:

```bash
uv run menagerie_x urdf-capsules --output /tmp/astro_v1_capsules.urdf
```

The generator keeps the existing URDF content and appends extension capsule collision elements to matching links. Use the generated file only with tools that explicitly support `format="astro-extension-v1"`; keep `src/menagerie_x/assets/astro_v1/urdf/astro_v1.urdf` as the standard mesh-collision URDF.

## Simulator Parameters

| Simulator | FPS | Decimation | Substeps | Position Iters | Velocity Iters |
|---|---:|---:|---:|---:|---:|
| IsaacGym | 100 | 2 | 2 | 8 | 4 |
| IsaacLab | 200 | 4 | - | 8 | 4 |
| Genesis | 100 | 2 | 2 | - | - |
| Newton | 200 | 4 | - | - | - |
