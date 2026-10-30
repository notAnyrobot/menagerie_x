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

"""Local Menagerie entry points, derived from the existing edition manifest.

Adapted from MuJoCo Menagerie's catalog.py. No second robot registry is kept.
URDF-only editions remain in manifest.json and have no simulated scene here.
"""

import enum
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class ModelType(int, enum.Enum):
    HUMANOID = 7


def model_entries(root=ROOT):
    """Yield each declared MJCF's source, top-level model, and scene paths."""
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for family, raw in sorted(manifest["variants"].items()):
        for edition, description in raw["editions"].items():
            source = description.get("mjcf")
            if not source:
                continue
            scene = "scene.xml" if edition == raw["default_edition"] else f"scene_{edition}.xml"
            yield {
                "family": family,
                "edition": edition,
                "source": root / family / source,
                "model": root / family / Path(source).name,
                "scene": root / family / scene,
                "spawn_z": float(raw.get("spawn", {}).get("xyz", [0, 0, 0])[2]),
            }


MODEL_MAP = {f"{entry['family']}/{entry['model'].stem}": ModelType.HUMANOID for entry in model_entries()}
PREVIEW_OVERRIDES = {f"{entry['family']}/{entry['model'].stem}": str(entry["scene"].relative_to(ROOT)) for entry in model_entries()}


def preview_path(robot, robot_maker):
    return PREVIEW_OVERRIDES.get(robot, f"{robot_maker}/scene.xml")


def display_name(robot):
    return robot.split("/")[-1].replace("_", " ")
