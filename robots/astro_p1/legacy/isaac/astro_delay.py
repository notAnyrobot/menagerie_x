
import isaaclab.sim as sim_utils
# from isaaclab.actuators import ImplicitActuatorCfg
from rl_lab.actuator.actuator import DelayedImplicitActuatorCfg
from isaaclab.assets.articulation import ArticulationCfg

from rl_lab_assets import ROBOT_ASSETS_DATA_DIR

ARMATURE_3907_36 = 0.002387232
ARMATURE_5016_25 = 0.008810606409825
ARMATURE_8514_25 = 0.08143145775

NATURAL_FREQ_HZ = 6
NATURAL_FREQ = NATURAL_FREQ_HZ * 2.0 * 3.1415926535   # 转换为角频率 (rad/s)
DAMPING_RATIO = 2.0


# 计算刚度 (Stiffness = Armature * ω²)
STIFFNESS_3907_36 = ARMATURE_3907_36 * NATURAL_FREQ**2
STIFFNESS_5016_25 = ARMATURE_5016_25 * NATURAL_FREQ**2
STIFFNESS_8514_25 = ARMATURE_8514_25 * NATURAL_FREQ**2


# 计算阻尼 (Damping = 2 * ζ * Armature * ω)
DAMPING_3907_36 = 2.0 * DAMPING_RATIO * ARMATURE_3907_36 * NATURAL_FREQ
DAMPING_5016_25 = 2.0 * DAMPING_RATIO * ARMATURE_5016_25 * NATURAL_FREQ
DAMPING_8514_25 = 2.0 * DAMPING_RATIO * ARMATURE_8514_25 * NATURAL_FREQ


ASTRO_DELAY_CFG = ArticulationCfg(
    spawn=sim_utils.UrdfFileCfg(
        fix_base=False,
        replace_cylinders_with_capsules=True,
        asset_path=f"{ROBOT_ASSETS_DATA_DIR}/astro/astro_v1.urdf",
        activate_contact_sensors=True,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            disable_gravity=False,
            retain_accelerations=False,
            linear_damping=0.0,
            angular_damping=0.0,
            max_linear_velocity=1000.0,
            max_angular_velocity=1000.0,
            max_depenetration_velocity=1.0,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False, solver_position_iteration_count=8, solver_velocity_iteration_count=4
        ),
        joint_drive=sim_utils.UrdfConverterCfg.JointDriveCfg(
            gains=sim_utils.UrdfConverterCfg.JointDriveCfg.PDGainsCfg(stiffness=0, damping=0)
        ),
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        pos=(0.0, 0.0, 0.75),
        joint_pos={
            ".*_hip_pitch_joint": -0.312,
            ".*_knee_joint": 0.669,
            ".*_ankle_pitch_joint": -0.363,
            ".*_elbow_joint": 0.2,
            "left_shoulder_roll_joint": 0.2,
            "left_shoulder_pitch_joint": 0.2,
            "right_shoulder_roll_joint": -0.2,
            "right_shoulder_pitch_joint": 0.2,
        },
        joint_vel={".*": 0.0},
    ),
    soft_joint_pos_limit_factor=0.9,
    actuators={
        "legs": DelayedImplicitActuatorCfg(
            joint_names_expr=[
                ".*_hip_.*",
                ".*_knee_joint",
            ],
            effort_limit_sim={
                ".*_hip_.*": 130,
                ".*_knee_joint": 130,
            },
            velocity_limit_sim={
                ".*_hip_.*": 18.850,
                ".*_knee_joint": 18.850,
            },
            stiffness={
                ".*_hip_.*": STIFFNESS_8514_25,
                ".*_knee_joint": STIFFNESS_8514_25,
            },
            damping={
                ".*_hip_.*": DAMPING_8514_25,
                ".*_knee_joint": DAMPING_8514_25,
            },
            armature={
                ".*_hip_.*": ARMATURE_8514_25,
                ".*_knee_joint": ARMATURE_8514_25,
            },
            min_delay=0,
            max_delay=3,
            # delay_hold_prob=0.2,
            # delay_update_period=4,
            delay_per_env_phase=True,
        ),
        "feet": DelayedImplicitActuatorCfg(
            joint_names_expr=[
                ".*_ankle_pitch_joint", 
                ".*_ankle_roll_joint",
            ],
            effort_limit_sim={
                ".*_ankle_pitch_joint": 60.0,
                ".*_ankle_roll_joint": 45.0,
            },
            velocity_limit_sim={
                ".*_ankle_pitch_joint": 26.180,
                ".*_ankle_roll_joint": 26.180,
            },
            stiffness=2.0 * STIFFNESS_5016_25,
            damping=2.0 * DAMPING_5016_25,
            armature=2.0 * ARMATURE_5016_25,
            min_delay=0,
            max_delay=3,
        ),
        "waist": DelayedImplicitActuatorCfg(
            joint_names_expr=["waist_roll_joint", "waist_pitch_joint"],
            effort_limit_sim={
                "waist_pitch_joint": 60.0,
                "waist_roll_joint": 50.0,
            },
            velocity_limit_sim={
                "waist_pitch_joint": 26.180,
                "waist_roll_joint": 26.180,
            },
            stiffness=2.0 * STIFFNESS_5016_25,
            damping=2.0 * DAMPING_5016_25,
            armature=2.0 * ARMATURE_5016_25,
            min_delay=0,
            max_delay=3,
        ),
        "waist_yaw": DelayedImplicitActuatorCfg(
            effort_limit_sim=130.0,
            velocity_limit_sim=18.850,
            joint_names_expr=["waist_yaw_joint"],
            stiffness=STIFFNESS_8514_25,
            damping=DAMPING_8514_25,
            armature=ARMATURE_8514_25,
            min_delay=0,
            max_delay=3,
        ),
        "arms": DelayedImplicitActuatorCfg(
            joint_names_expr=[
                ".*_shoulder_pitch_joint",
                ".*_shoulder_roll_joint",
                ".*_shoulder_yaw_joint",
                ".*_elbow_.*",
                ".*_wrist_.*",
            ],
            effort_limit_sim={
                ".*_shoulder_pitch_joint": 30,
                ".*_shoulder_roll_joint": 30,
                ".*_shoulder_yaw_joint": 30, 
                ".*_elbow_.*": 30,
                ".*_wrist_roll_joint": 30,
                ".*_wrist_pitch_joint": 10,
                ".*_wrist_yaw_joint": 10,
            },
            velocity_limit_sim = {
                ".*_shoulder_pitch_joint": 26.180,
                ".*_shoulder_roll_joint": 26.180,
                ".*_shoulder_yaw_joint": 26.180, 
                ".*_elbow_.*": 26.180,
                ".*_wrist_roll_joint": 26.180,
                ".*_wrist_pitch_joint": 20.940,
                ".*_wrist_yaw_joint": 20.940,
            },
            stiffness={
                ".*_shoulder_pitch_joint": STIFFNESS_5016_25,
                ".*_shoulder_roll_joint": STIFFNESS_5016_25,
                ".*_shoulder_yaw_joint": STIFFNESS_5016_25, 
                ".*_elbow_.*": STIFFNESS_5016_25,
                ".*_wrist_roll_joint": STIFFNESS_5016_25,
                ".*_wrist_pitch_joint": STIFFNESS_3907_36,
                ".*_wrist_yaw_joint": STIFFNESS_3907_36,
            },
            damping={
                ".*_shoulder_pitch_joint": DAMPING_5016_25,
                ".*_shoulder_roll_joint": DAMPING_5016_25,
                ".*_shoulder_yaw_joint": DAMPING_5016_25, 
                ".*_elbow_.*": DAMPING_5016_25,
                ".*_wrist_roll_joint": DAMPING_5016_25,
                ".*_wrist_pitch_joint": DAMPING_3907_36,
                ".*_wrist_yaw_joint": DAMPING_3907_36,
            },
            armature={
                ".*_shoulder_pitch_joint": ARMATURE_5016_25,
                ".*_shoulder_roll_joint": ARMATURE_5016_25,
                ".*_shoulder_yaw_joint": ARMATURE_5016_25,
                ".*_elbow_.*": ARMATURE_5016_25,
                ".*_wrist_roll_joint": ARMATURE_3907_36,
                ".*_wrist_pitch_joint": ARMATURE_3907_36,
                ".*_wrist_yaw_joint": ARMATURE_3907_36,
            },
            min_delay=0,
            max_delay=3,
        ),
    },
)

ASTRO_DELAY_ACTION_SCALE = {}
for a in ASTRO_DELAY_CFG.actuators.values():
    e = a.effort_limit_sim
    s = a.stiffness
    names = a.joint_names_expr
    if not isinstance(e, dict):
        e = {n: e for n in names}
    if not isinstance(s, dict):
        s = {n: s for n in names}
    for n in names:
        if n in e and n in s and s[n]:
            ASTRO_DELAY_ACTION_SCALE[n] = 0.25 * e[n] / s[n]
