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

"""Curated native models, following MuJoCo Menagerie's root catalog.

Active and legacy entries are separate. Native runtime setup lives in XML;
the application manifest is not the authority for model behavior.
"""

import enum
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class ModelType(int, enum.Enum):
    HUMANOID = 7


MODEL_MAP = {
    "astro_p2/astro_p2": ModelType.HUMANOID,
    "astro_p2/astro_p2_with_hands": ModelType.HUMANOID,
    "atom_p3/atom_p3_27dof": ModelType.HUMANOID,
    "soma23/soma23_free_base": ModelType.HUMANOID,
    "unitree_g1/unitree_g1_29dof_with_hand_rev_1_0": ModelType.HUMANOID,
    "unitree_g1/unitree_g1_29dof_box_feet": ModelType.HUMANOID,
    "unitree_g1/g1_mjx": ModelType.HUMANOID,
}

# Retained for native loading checks; these models are scheduled for retirement.
LEGACY_MODEL_MAP = {
    "astro_p1/astro_p1_30dof": ModelType.HUMANOID,
    "astro_p1/astro_p1_27dof": ModelType.HUMANOID,
}

PREVIEW_OVERRIDES = {
    "astro_p2/astro_p2_with_hands": "astro_p2/scene_with_hands.xml",
    "astro_p1/astro_p1_27dof": "astro_p1/scene_27dof.xml",
    "unitree_g1/unitree_g1_29dof_box_feet": "unitree_g1/scene_29dof_box_feet.xml",
    "unitree_g1/g1_mjx": "unitree_g1/scene_mjx.xml",
}


def preview_path(robot, robot_maker):
    return PREVIEW_OVERRIDES.get(robot, f"{robot_maker}/scene.xml")


def display_name(robot):
    return robot.split("/")[-1].replace("_", " ")


def model_entries(root=ROOT, include_legacy=True):
    """Yield declared pairs, including retained legacy models for verification."""
    root = Path(root)
    models = dict(MODEL_MAP)
    if include_legacy:
        models.update(LEGACY_MODEL_MAP)
    for robot in models:
        family = robot.split("/")[0]
        yield {
            "family": family,
            "model": root / f"{robot}.xml",
            "scene": root / preview_path(robot, family),
        }
