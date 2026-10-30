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
import hashlib
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

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
                # Some retained descriptions use a family-local relative mesh alias.
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
        # Retained imports remain evidence, not editable native inputs.
        # Astro variants are checked explicitly below against their common body.
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


class G1PrimitiveTests(unittest.TestCase):
    def test_upstream_sources_and_assets_are_preserved(self):
        family = ROOT / "unitree_g1"
        record = json.loads((family / "provenance/menagerie_mjx.json").read_text())
        for item in record["files"] + record["assets"]:
            with self.subTest(path=item["file"]):
                payload = (family / item["file"]).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), item["sha256"])

    def test_primitive_colliders_and_complete_scene_contacts(self):
        robot = mujoco.MjModel.from_xml_path(str(ROOT / "unitree_g1/g1_mjx.xml"))
        scene = mujoco.MjModel.from_xml_path(str(ROOT / "unitree_g1/scene_mjx.xml"))
        self.assertEqual((robot.nq, robot.nv, robot.nu), (36, 35, 29))
        visuals = robot.geom_group == 2
        colliders = np.isin(robot.geom_group, [3, 4])
        self.assertEqual(int(visuals.sum()), 35)
        self.assertTrue(np.all(robot.geom_type[visuals] == mujoco.mjtGeom.mjGEOM_MESH))
        self.assertEqual(int(colliders.sum()), 27)
        for kind, count in ((mujoco.mjtGeom.mjGEOM_CAPSULE, 23),
                            (mujoco.mjtGeom.mjGEOM_SPHERE, 2),
                            (mujoco.mjtGeom.mjGEOM_BOX, 2)):
            self.assertEqual(int((robot.geom_type[colliders] == kind).sum()), count)
        self.assertFalse(np.any(robot.geom_contype))
        self.assertFalse(np.any(robot.geom_conaffinity))
        self.assertEqual(robot.npair, 0)
        self.assertEqual(scene.npair, 49)
        floor = scene.geom("floor").id
        floor_pairs = (scene.pair_geom1 == floor) | (scene.pair_geom2 == floor)
        self.assertEqual(int(floor_pairs.sum()), 23)
        self.assertTrue(np.all(scene.pair_dim[floor_pairs] == 3))
        self.assertEqual(int((~floor_pairs).sum()), 26)
        self.assertTrue(np.all(scene.pair_dim[~floor_pairs] == 1))
        self.assertEqual(robot.nkey, 0)
        self.assertEqual([scene.key(i).name for i in range(scene.nkey)], ["home", "knees_bent"])
        self.assertAlmostEqual(robot.opt.timestep, 0.004)
        # Position-servo feedback distinguishes this variant from the retained
        # torque-motor models even though they share 29 body joint names.
        self.assertTrue(np.all(robot.actuator_biastype == mujoco.mjtBias.mjBIAS_AFFINE))
        np.testing.assert_array_equal(robot.actuator_biasprm[:, 1], -robot.actuator_gainprm[:, 0])
        np.testing.assert_array_equal(robot.actuator_biasprm[:, 2], np.full(robot.nu, -2.0))


class AstroP2SimplifiedTests(unittest.TestCase):
    def test_body_joints_options_and_visuals_match_default(self):
        base = mujoco.MjModel.from_xml_path(str(ROOT / "astro_p2/astro_p2.xml"))
        simple = mujoco.MjModel.from_xml_path(str(ROOT / "astro_p2/astro_p2_simplified.xml"))
        self.assertEqual((simple.nq, simple.nv, simple.nu, simple.nbody),
                         (base.nq, base.nv, base.nu, base.nbody))
        self.assertEqual(simple.nu, 0)
        for attribute in ("body_parentid", "body_pos", "body_quat", "body_mass", "body_inertia",
                          "body_ipos", "body_iquat", "jnt_type", "jnt_pos", "jnt_axis", "jnt_range",
                          "jnt_limited", "jnt_stiffness", "jnt_actfrcrange", "dof_damping",
                          "dof_armature", "dof_frictionloss", "qpos0"):
            np.testing.assert_array_equal(getattr(simple, attribute), getattr(base, attribute))
        for attribute in ("timestep", "integrator", "solver", "iterations", "ls_iterations",
                          "disableflags", "enableflags", "gravity"):
            np.testing.assert_array_equal(getattr(simple.opt, attribute), getattr(base.opt, attribute))
        visuals = np.flatnonzero(base.geom_group == 1)
        self.assertEqual(len(visuals), 37)
        self.assertEqual(int((simple.geom_group == 1).sum()), len(visuals))
        for i in visuals:
            old = base.geom(int(i))
            new = simple.geom(old.name)
            for attribute in ("bodyid", "type", "dataid", "pos", "quat", "size", "rgba", "matid",
                              "group", "contype", "conaffinity"):
                np.testing.assert_array_equal(getattr(new, attribute), getattr(old, attribute))

    def test_support_and_selected_self_contacts_are_active(self):
        scene = mujoco.MjModel.from_xml_path(str(ROOT / "astro_p2/scene_simplified.xml"))
        data = mujoco.MjData(scene)
        mujoco.mj_forward(scene, data)
        self.assertEqual(data.ncon, 0)
        # Preserve the source reference pose; ground it only for this probe.
        data.qpos[2] -= 0.1051
        mujoco.mj_forward(scene, data)
        floor = scene.geom("menagerie_floor").id
        supported = set()
        for contact in data.contact:
            if floor in (contact.geom1, contact.geom2):
                other = contact.geom2 if contact.geom1 == floor else contact.geom1
                supported.add(scene.geom(int(other)).name)
                self.assertEqual(contact.dim, 3)
        self.assertEqual(supported, {f"{side}_foot{i}_collision"
                                     for side in ("left", "right") for i in (1, 2, 3)})
        mujoco.mj_resetData(scene, data)
        # A bounded arm pose that exercises the declared hand/torso contact.
        pose = {"shoulder_pitch": -0.0525, "shoulder_roll": 0.0724,
                "shoulder_yaw": -1.6345, "elbow": 0.1660,
                "wrist_pitch": 0.0470, "wrist_yaw": -0.9371}
        for name, value in pose.items():
            joint = scene.joint(f"left_{name}_joint")
            self.assertTrue(joint.range[0] <= value <= joint.range[1])
            data.qpos[joint.qposadr[0]] = value
        mujoco.mj_forward(scene, data)
        selected = {scene.geom("left_hand_collision").id, scene.geom("torso_collision").id}
        self.assertTrue(any({contact.geom1, contact.geom2} == selected and contact.dim == 1
                            for contact in data.contact))
        self.assertFalse(np.any(data.warning.number))

    def test_compact_geometry_and_explicit_contact_policy(self):
        robot = mujoco.MjModel.from_xml_path(str(ROOT / "astro_p2/astro_p2_simplified.xml"))
        scene = mujoco.MjModel.from_xml_path(str(ROOT / "astro_p2/scene_simplified.xml"))
        colliders = np.isin(robot.geom_group, [3, 4])
        self.assertEqual(int(colliders.sum()), 27)
        for kind, count in ((mujoco.mjtGeom.mjGEOM_CAPSULE, 23),
                            (mujoco.mjtGeom.mjGEOM_SPHERE, 2),
                            (mujoco.mjtGeom.mjGEOM_BOX, 2)):
            self.assertEqual(int((robot.geom_type[colliders] == kind).sum()), count)
        self.assertFalse(np.any(robot.geom_contype))
        self.assertFalse(np.any(robot.geom_conaffinity))
        self.assertEqual(robot.npair, 0)
        self.assertEqual(scene.npair, 49)
        floor = scene.geom("menagerie_floor").id
        np.testing.assert_array_equal(scene.geom_pos[floor], [0, 0, -0.75])
        floor_pairs = (scene.pair_geom1 == floor) | (scene.pair_geom2 == floor)
        self.assertEqual(int(floor_pairs.sum()), 23)
        self.assertTrue(np.all(scene.pair_dim[floor_pairs] == 3))
        self.assertTrue(np.all(scene.pair_dim[~floor_pairs] == 1))
        pairs = {frozenset((int(a), int(b))) for a, b in zip(scene.pair_geom1, scene.pair_geom2)}
        self.assertEqual(len(pairs), scene.npair)
        referenced = set(map(int, np.concatenate((scene.pair_geom1, scene.pair_geom2))))
        self.assertEqual({scene.geom(i).name for i in referenced - {floor}},
                         {robot.geom(int(i)).name for i in np.flatnonzero(colliders)})
        for side in ("left", "right"):
            box = scene.geom(f"{side}_foot_box_collision").id
            self.assertNotIn(frozenset((box, floor)), pairs)
            for number in (1, 2, 3):
                capsule = scene.geom(f"{side}_foot{number}_collision").id
                self.assertIn(frozenset((capsule, floor)), pairs)


class AstroP2VariantTests(unittest.TestCase):
    def setUp(self):
        self.rubber = mujoco.MjModel.from_xml_path(str(ROOT / "astro_p2/astro_p2.xml"))
        self.dex = mujoco.MjModel.from_xml_path(str(ROOT / "astro_p2/astro_p2_with_hands.xml"))

    def test_fixed_head_and_hand_dof_inventory(self):
        self.assertEqual((self.rubber.nq, self.rubber.nv, self.rubber.nu), (36, 35, 0))
        self.assertEqual((self.dex.nq, self.dex.nv, self.dex.nu), (50, 49, 0))
        for model in (self.rubber, self.dex):
            self.assertEqual(sum(model.jnt_type == mujoco.mjtJoint.mjJNT_FREE), 1)
            self.assertEqual(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "head_joint"), -1)
        rubber_joints = {self.rubber.joint(i).name for i in range(self.rubber.njnt)}
        dex_joints = {self.dex.joint(i).name for i in range(self.dex.njnt)}
        self.assertTrue(rubber_joints.issubset(dex_joints))
        self.assertEqual(len(dex_joints - rubber_joints), 14)
        self.assertTrue(all("hand" in name for name in dex_joints - rubber_joints))
        self.assertEqual(self.rubber.nkey, 0)
        self.assertGreaterEqual(mujoco.mj_name2id(self.dex, mujoco.mjtObj.mjOBJ_KEY, "fist"), 0)

    def test_both_variants_share_the_refined_body(self):
        rubber, dex = self.rubber, self.dex
        # Hands are intentionally different; retained hand attachment frames
        # still have exactly the same poses in their wrist-yaw frames.
        for i in range(rubber.nbody):
            body = rubber.body(i)
            other = dex.body(body.name) if body.name else dex.body(0)
            for attribute in ("pos", "quat"):
                np.testing.assert_array_equal(getattr(body, attribute), getattr(other, attribute))
            if body.name not in {"left_hand_link", "right_hand_link"}:
                for attribute in ("mass", "inertia", "ipos", "iquat"):
                    np.testing.assert_array_equal(getattr(body, attribute), getattr(other, attribute))
        for i in range(rubber.njnt):
            joint = rubber.joint(i)
            other = dex.joint(joint.name)
            for attribute in ("type", "pos", "axis", "range", "limited", "stiffness"):
                np.testing.assert_array_equal(getattr(joint, attribute), getattr(other, attribute))
            # Map damping/armature by named joint; deleting fingers shifts IDs.
            count = 6 if joint.type[0] == mujoco.mjtJoint.mjJNT_FREE else 1
            for attribute in ("dof_damping", "dof_armature", "dof_frictionloss"):
                a, b = int(joint.dofadr[0]), int(other.dofadr[0])
                np.testing.assert_array_equal(getattr(rubber, attribute)[a:a+count],
                                              getattr(dex, attribute)[b:b+count])
        for i in range(rubber.ngeom):
            geom = rubber.geom(i)
            if "rubber_hand" in geom.name:
                continue
            other = dex.geom(geom.name)
            for attribute in ("type", "size", "pos", "quat", "friction", "contype", "conaffinity"):
                np.testing.assert_array_equal(getattr(geom, attribute), getattr(other, attribute))

    def test_native_rubber_meshes_and_inertias_match_astro_sources(self):
        record = json.loads((ROOT / "astro_p2/provenance/rubber_hands.json").read_text())
        xml = ET.parse(ROOT / "astro_p2/astro_p2.xml")
        vendor = ROOT / "astro_p2" / record["source_urdf_local"]
        self.assertEqual(hashlib.sha256(vendor.read_bytes()).hexdigest(), record["source_urdf_sha256"])
        vendor_xml = ET.parse(vendor)
        for side, source in record["hands"].items():
            path = ROOT / "astro_p2" / source["mesh"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["mesh_sha256"])
            original = vendor_xml.find(f"link[@name='{side}_hand_link']")
            original_inertial = original.find("inertial")
            self.assertEqual(source["mass_kg"], float(original_inertial.find("mass").get("value")))
            self.assertEqual(source["inertia_hand_frame_kg_m2"],
                             {k: float(v) for k, v in original_inertial.find("inertia").attrib.items()})
            original_mesh = Path(original.find("visual/geometry/mesh").get("filename")).name
            self.assertEqual(path.name, original_mesh)
            hand = self.rubber.body(f"{side}_hand_link")
            self.assertAlmostEqual(float(hand.mass[0]), source["mass_kg"], places=12)
            np.testing.assert_allclose(hand.ipos, source["com_hand_frame_m"], rtol=0, atol=1e-12)
            np.testing.assert_allclose(hand.pos, source["astro_mount_xyz_m"], rtol=0, atol=1e-12)
            inertial = xml.find(f".//body[@name='{side}_hand_link']/inertial")
            tensor = source["inertia_hand_frame_kg_m2"]
            expected = [tensor[key] for key in ("ixx", "iyy", "izz", "ixy", "ixz", "iyz")]
            np.testing.assert_allclose(np.fromstring(inertial.get("fullinertia"), sep=" "),
                                       expected, rtol=0, atol=1e-15)
            capsule = xml.find(f".//geom[@name='{side}_rubber_hand_collision']")
            self.assertEqual(capsule.get("type"), "capsule")
            self.assertEqual(float(capsule.get("size")), source["collision_radius_m"])
            np.testing.assert_allclose(np.fromstring(capsule.get("fromto"), sep=" "),
                                       source["collision_fromto_hand_frame_m"], rtol=0, atol=1e-12)
        self.assertAlmostEqual(float(self.rubber.body_mass.sum()), 40.58255359, places=9)
        self.assertAlmostEqual(float(self.dex.body_mass.sum()), 41.69666115, places=9)
