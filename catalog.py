# Copyright 2026 DeepMind Technologies Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Curated native entry points, following MuJoCo Menagerie's root catalog.

Keys are <family>/<model XML stem>. Runtime setup lives in the XML files;
the legacy application's manifest.json is independent of this native catalog.
"""

import enum
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class ModelType(int, enum.Enum):
    HUMANOID = 7


MODEL_MAP = {
    "astro_p1/astro_p1_30dof": ModelType.HUMANOID,
    "astro_p1/astro_p1_27dof": ModelType.HUMANOID,
    "astro_p2/astro_p2_30dof_primitive_collision": ModelType.HUMANOID,
    "astro_p2/astro_p2_30dof_mesh_collision": ModelType.HUMANOID,
    "astro_p2/astro_p2_30dof_primitive_collision_halfway": ModelType.HUMANOID,
    "astro_p2_29dof/astro_p2_29dof": ModelType.HUMANOID,
    "astro_p2_43dof_dex3_1/astro_p2_43dof_dex3_1": ModelType.HUMANOID,
    "atom_p3/atom_p3_27dof": ModelType.HUMANOID,
    "soma23/soma23_free_base": ModelType.HUMANOID,
    "unitree_g1/unitree_g1_29dof_with_hand_rev_1_0": ModelType.HUMANOID,
    "unitree_g1/unitree_g1_29dof_box_feet": ModelType.HUMANOID,
}

PREVIEW_OVERRIDES = {
    "astro_p1/astro_p1_27dof": "astro_p1/scene_27dof.xml",
    "astro_p2/astro_p2_30dof_mesh_collision": "astro_p2/scene_30dof_mesh_collision.xml",
    "astro_p2/astro_p2_30dof_primitive_collision_halfway": "astro_p2/scene_30dof_primitive_collision_halfway.xml",
    "unitree_g1/unitree_g1_29dof_box_feet": "unitree_g1/scene_29dof_box_feet.xml",
}


def preview_path(robot, robot_maker):
    return PREVIEW_OVERRIDES.get(robot, f"{robot_maker}/scene.xml")


def display_name(robot):
    return robot.split("/")[-1].replace("_", " ")


def model_entries(root=ROOT):
    """Yield the declared native models and scenes, without scanning local drafts."""
    root = Path(root)
    for robot in MODEL_MAP:
        family = robot.split("/")[0]
        yield {
            "family": family,
            "model": root / f"{robot}.xml",
            "scene": root / preview_path(robot, family),
        }
