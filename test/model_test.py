# Copyright 2022 DeepMind Technologies Limited
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

"""Native load/step and portability checks adapted from upstream model_test.py."""

from pathlib import Path
import shutil
import tempfile
import unittest

import mujoco
import numpy as np

from catalog import model_entries

ROOT = Path(__file__).resolve().parents[1]


def step_scene(model, data):
    # Upstream's deterministic Halton control perturbation, for 0.1 seconds.
    for i in range(int(np.ceil(0.1 / model.opt.timestep))):
        for j in range(model.nu):
            if model.actuator_ctrllimited[j]:
                low, high = model.actuator_ctrlrange[j]
                center, radius = 0.5 * (high + low), 0.5 * (high - low)
            else:
                center, radius = 0.0, 1.0
            data.ctrl[j] = center + radius * (2 * mujoco.mju_Halton(i, j + 2) - 1)
        mujoco.mj_step(model, data)


class ModelTests(unittest.TestCase):
    def test_models_and_scenes_load_and_step(self):
        for entry in model_entries():
            with self.subTest(model=str(entry["model"].relative_to(ROOT))):
                robot = mujoco.MjModel.from_xml_path(str(entry["model"]))
                scene = mujoco.MjModel.from_xml_path(str(entry["scene"]))
                self.assertFalse(np.any(robot.geom_type == mujoco.mjtGeom.mjGEOM_PLANE))
                self.assertEqual(sum(scene.geom_type == mujoco.mjtGeom.mjGEOM_PLANE), 1)
                self.assertEqual((robot.nq, robot.nv, robot.nu, robot.nbody),
                                 (scene.nq, scene.nv, scene.nu, scene.nbody))
                for model in (robot, scene):
                    data = mujoco.MjData(model)
                    step_scene(model, data)
                    self.assertTrue(np.isfinite(data.qpos).all())
                    self.assertTrue(np.isfinite(data.qvel).all())
                    self.assertFalse(np.any(data.warning.number), str(data.warning.number))
                # Model-owned keyframes remain usable without an app pose system.
                for key in range(scene.nkey):
                    data = mujoco.MjData(scene)
                    mujoco.mj_resetDataKeyframe(scene, data, key)
                    mujoco.mj_forward(scene, data)
                    self.assertTrue(np.isfinite(data.qpos).all())
                    self.assertFalse(np.any(data.warning.number))

    def test_family_runtime_is_standalone(self):
        entries = list(model_entries())
        for family in sorted({entry["family"] for entry in entries}):
            with self.subTest(family=family), tempfile.TemporaryDirectory() as temporary:
                bundle = Path(temporary) / family
                bundle.mkdir()
                # Only canonical runtime XML and assets: no legacy manifest,
                # nested MJCF snapshots, other families, or application package.
                shutil.copytree(ROOT / family / "assets", bundle / "assets")
                # Two preserved HHTools XMLs retain the original relative mesh alias.
                if (ROOT / family / "meshes").is_symlink():
                    (bundle / "meshes").symlink_to("assets", target_is_directory=True)
                paths = {entry[k] for entry in entries if entry["family"] == family
                         for k in ("model", "scene")}
                for path in paths:
                    shutil.copy2(path, bundle / path.name)
                for path in paths:
                    with self.subTest(path=path.name):
                        model = mujoco.MjModel.from_xml_path(str(bundle / path.name))
                        self.assertGreater(model.nq, 0)

    def test_robot_physics_matches_retained_imports(self):
        # These nine old snapshots remain evidence, not editable native inputs.
        # HHTools models were already at the family root and stay byte-identical.
        for entry in model_entries():
            source = entry["model"].parent / "mjcf" / entry["model"].name
            if not source.is_file():
                continue
            with self.subTest(model=str(entry["model"].relative_to(ROOT))):
                source_model = mujoco.MjModel.from_xml_path(str(source))
                model = mujoco.MjModel.from_xml_path(str(entry["model"]))
                self.assertEqual((model.nq, model.nv, model.nu, model.nbody),
                                 (source_model.nq, source_model.nv, source_model.nu, source_model.nbody))
                for attribute in ("body_mass", "body_inertia", "body_pos", "body_quat", "jnt_range",
                                  "dof_damping", "actuator_gear", "qpos0"):
                    np.testing.assert_array_equal(getattr(model, attribute), getattr(source_model, attribute))
                robot_geoms = source_model.geom_type != mujoco.mjtGeom.mjGEOM_PLANE
                for attribute in ("geom_type", "geom_size", "geom_pos", "geom_quat", "geom_friction",
                                  "geom_contype", "geom_conaffinity"):
                    np.testing.assert_array_equal(getattr(model, attribute), getattr(source_model, attribute)[robot_geoms])
