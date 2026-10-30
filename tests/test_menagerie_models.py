# Copyright 2022 DeepMind Technologies Limited
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

"""Scene/layout checks adapted from upstream test/model{,_dir}_test.py."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

import mujoco
import numpy as np

from catalog import MODEL_MAP, model_entries
from menagerie_x.assets import get_asset_paths, get_variant, list_mjcf_editions, validate_assets

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FAMILIES = {"astro_p1", "astro_p2", "astro_p2_29dof", "astro_p2_43dof_dex3_1", "atom_p3", "soma23", "unitree_g1"}


def _pseudorandom_ctrlnoise(model, data, i):
    # Upstream's deterministic Halton control perturbation.
    for j in range(model.nu):
        ctrlrange = model.actuator_ctrlrange[j]
        if model.actuator_ctrllimited[j]:
            center = 0.5 * (ctrlrange[1] + ctrlrange[0])
            radius = 0.5 * (ctrlrange[1] - ctrlrange[0])
        else:
            center, radius = 0.0, 1.0
        data.ctrl[j] = center + radius * (2 * mujoco.mju_Halton(i, j + 2) - 1)


class MenagerieLayoutTests(unittest.TestCase):
    def test_inventory_contains_only_the_original_families(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        self.assertEqual(set(manifest["variants"]), EXPECTED_FAMILIES)
        self.assertEqual(sum(len(v["editions"]) for v in manifest["variants"].values()), 12)
        self.assertEqual(len(MODEL_MAP), 10)
        for family in EXPECTED_FAMILIES:
            with self.subTest(family=family):
                for name in ("README.md", "CHANGELOG.md", "LICENSING.md"):
                    self.assertTrue((ROOT / family / name).is_file(), f"{family}/{name}")
                self.assertTrue((ROOT / family / "assets").is_dir())
                self.assertEqual((ROOT / "robots" / family).resolve(), ROOT / family)
        self.assertFalse((ROOT / "astro_p2_29dof" / "scene.xml").exists())

    def test_legacy_catalog_path_resolves_to_the_checkout(self):
        self.assertEqual(get_asset_paths(ROOT / "robots").root, ROOT)
        self.assertEqual(validate_assets(ROOT), [])

    def test_generated_entrypoints_match_the_manifest_and_sources(self):
        subprocess.run([sys.executable, str(ROOT / "scripts/sync-menagerie.py"), "--check"], check=True)

    def test_presentation_scenes_are_not_editable_editions(self):
        variant = get_variant("astro_p2_43dof_dex3_1", ROOT)
        self.assertFalse(any(record["id"].startswith("scene") for record in list_mjcf_editions(variant, ROOT)))


class MenagerieModelTests(unittest.TestCase):
    def test_flat_entrypoints_preserve_robot_physics(self):
        for entry in model_entries():
            with self.subTest(model=entry["model"].name):
                source = mujoco.MjModel.from_xml_path(str(entry["source"]))
                model = mujoco.MjModel.from_xml_path(str(entry["model"]))
                self.assertEqual((model.nq, model.nv, model.nu, model.nbody), (source.nq, source.nv, source.nu, source.nbody))
                for attribute in ("body_mass", "body_inertia", "body_pos", "body_quat", "jnt_range", "dof_damping", "actuator_gear", "qpos0"):
                    np.testing.assert_allclose(getattr(model, attribute), getattr(source, attribute), rtol=0, atol=0)
                self.assertFalse(any(model.geom_type[g] == mujoco.mjtGeom.mjGEOM_PLANE for g in range(model.ngeom)))
                robot_geoms = source.geom_type != mujoco.mjtGeom.mjGEOM_PLANE
                for attribute in ("geom_type", "geom_size", "geom_pos", "geom_quat", "geom_friction", "geom_contype", "geom_conaffinity"):
                    np.testing.assert_allclose(getattr(model, attribute), getattr(source, attribute)[robot_geoms], rtol=0, atol=0)

    def test_scenes_compile_and_step_without_warnings(self):
        for entry in model_entries():
            with self.subTest(scene=str(entry["scene"].relative_to(ROOT))):
                model = mujoco.MjModel.from_xml_path(str(entry["scene"]))
                self.assertEqual(sum(model.geom_type == mujoco.mjtGeom.mjGEOM_PLANE), 1)
                data = mujoco.MjData(model)
                i = 0
                while data.time < 0.1:
                    _pseudorandom_ctrlnoise(model, data, i)
                    mujoco.mj_step(model, data)
                    i += 1
                self.assertTrue(all(data.warning.number == 0), str(data.warning.number))
                self.assertTrue(np.isfinite(data.qpos).all())


if __name__ == "__main__":
    unittest.main()
