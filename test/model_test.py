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
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from catalog import model_entries

ROOT = Path(__file__).resolve().parents[1]


def parse_mjcf(path):
    """Inspect the compiled MJCF tree, including attached child models."""
    spec = mujoco.MjSpec.from_file(str(path))
    spec.compile()
    return ET.fromstring(spec.to_xml())


def shared_foot_geom_name(name):
    # The retained articulated model numbers symmetric sole rows in reverse.
    return {"right_foot_2_capsule_collision": "right_foot_4_capsule_collision",
            "right_foot_3_capsule_collision": "right_foot_5_capsule_collision",
            "right_foot_4_capsule_collision": "right_foot_2_capsule_collision",
            "right_foot_5_capsule_collision": "right_foot_3_capsule_collision"}.get(name, name)


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
                runtime_paths = {entry[k] for entry in entries if entry["family"] == family
                                 for k in ("model", "scene")}
                paths = set(runtime_paths)
                pending = list(paths)
                while pending:
                    path = pending.pop()
                    xml = ET.parse(path).getroot()
                    for include in [*xml.iter("include"), *xml.findall("asset/model")]:
                        dependency = ROOT / family / include.get("file")
                        if dependency not in paths:
                            paths.add(dependency)
                            pending.append(dependency)
                for path in paths:
                    destination = bundle / path.relative_to(ROOT / family)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, destination)
                for path in runtime_paths:
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


class AstroP2CollisionTests(unittest.TestCase):
    def test_relative_scene_paths_resolve_collision_models(self):
        script = """
import mujoco
import sys
for path, ngeom in ((sys.argv[1], 89), (sys.argv[2], 90)):
    model = mujoco.MjModel.from_xml_path(path)
    assert model.ngeom == ngeom
    for side in ('left', 'right'):
        assert model.body(f'{side}_foot_link').id > 0
    for name in ('waist_roll_link_4_capsule_collision', 'neck_handle_left_support_capsule',
                 'neck_handle_right_support_capsule'):
        assert model.body(int(model.geom(name).bodyid[0])).name == 'waist_roll_link'
"""
        for directory in (ROOT, ROOT.parent, ROOT / "astro_p2"):
            paths = [str((ROOT / "astro_p2" / name).relative_to(directory))
                     for name in ("astro_p2.xml", "scene.xml")]
            with self.subTest(directory=str(directory)):
                result = subprocess.run([sys.executable, "-c", script, *paths], cwd=directory,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shared_foot_model_preserves_attachments_and_geometry(self):
        template = mujoco.MjModel.from_xml_path(str(ROOT / "astro_p2/foot_collisions.xml"))
        robot = mujoco.MjModel.from_xml_path(str(ROOT / "astro_p2/astro_p2.xml"))
        self.assertEqual(template.ngeom, 11)
        for side in ("left", "right"):
            foot = robot.body(f"{side}_foot_link")
            self.assertEqual(robot.body(int(robot.body_parentid[foot.id])).name, f"{side}_ankle_roll_link")
            self.assertEqual(float(foot.mass[0]), 0)
            self.assertEqual(int((robot.geom_bodyid == foot.id).sum()), template.ngeom)
            for i in range(template.ngeom):
                source = template.geom(i)
                attached = robot.geom(f"{side}_{source.name}")
                self.assertEqual(int(attached.bodyid[0]), foot.id)
                for attribute in ("type", "size", "pos", "quat", "group", "contype", "conaffinity",
                                  "condim", "friction", "solref", "solimp"):
                    np.testing.assert_array_equal(getattr(attached, attribute), getattr(source, attribute))

    @staticmethod
    def _non_arm_colliders(path):
        root = parse_mjcf(path)
        arm_bodies = set()
        for side in ("left", "right"):
            shoulder = root.find(f".//body[@name='{side}_shoulder_pitch_link']")
            arm_bodies.update(body.get("name") for body in shoulder.iter("body"))
        return {geom.get("name"): (body.get("name"), dict(geom.attrib))
                for body in root.iter("body") if body.get("name") not in arm_bodies
                for geom in body.findall("geom") if geom.get("group") == "3"}

    def test_knee_extension_stop_preserves_flexion_contacts(self):
        path = ROOT / "astro_p2/astro_p2.xml"
        current = mujoco.MjModel.from_xml_path(str(path))
        # Counterfactual preserves every manual edit except the 3 mm knee stop.
        spec = mujoco.MjSpec.from_file(str(path))
        for side in ("left", "right"):
            spec.geom(f"{side}_knee_link_1_capsule_collision").fromto = [0.015, 0, -0.24, 0.015, 0, 0]
        before = spec.compile()
        for side in ("left", "right"):
            pair = {current.geom(f"{side}_hip_roll_link_1_capsule_collision").id,
                    current.geom(f"{side}_knee_link_1_capsule_collision").id}
            joint = current.joint(f"{side}_knee_joint")
            self.assertTrue(joint.limited[0])
            for angle, expected_contact in ((0, False), (-0.06, False),
                                            (-0.08, True), (-0.09, True)):
                data = mujoco.MjData(current)
                data.qpos[joint.qposadr[0]] = angle
                mujoco.mj_forward(current, data)
                self.assertEqual(any({c.geom1, c.geom2} == pair for c in data.contact),
                                 expected_contact)
            for yaw in (-0.5, 0, 0.5):
                for angle in np.linspace(0, 2.44, 123):
                    records = []
                    for model in (current, before):
                        data = mujoco.MjData(model)
                        data.qpos[model.joint(f"{side}_knee_joint").qposadr[0]] = angle
                        data.qpos[model.joint(f"{side}_hip_yaw_joint").qposadr[0]] = yaw
                        mujoco.mj_forward(model, data)
                        records.append(sorted((min(c.geom1, c.geom2), max(c.geom1, c.geom2),
                                               c.dim, c.dist) for c in data.contact))
                    # Existing deep-flexion contacts must not appear earlier or deepen.
                    self.assertEqual(len(records[0]), len(records[1]))
                    np.testing.assert_allclose(records[0], records[1], rtol=0, atol=1e-10)

    def test_lower_body_ground_contacts_match_original(self):
        retained = set(self._non_arm_colliders(ROOT / "astro_p2/astro_p2.xml"))
        retained.add("menagerie_floor")
        for pose in ({}, {"left_knee_joint": 0.45, "left_ankle_pitch_joint": -0.2}):
            records = []
            for filename in ("scene_with_hands.xml", "scene.xml"):
                model = mujoco.MjModel.from_xml_path(str(ROOT / "astro_p2" / filename))
                data = mujoco.MjData(model)
                data.qpos[2] -= 0.1051
                for name, value in pose.items():
                    data.qpos[model.joint(name).qposadr[0]] = value
                mujoco.mj_forward(model, data)
                contacts = []
                for contact in data.contact:
                    names = tuple(sorted((model.geom(int(contact.geom1)).name,
                                          model.geom(int(contact.geom2)).name)))
                    if filename == "scene_with_hands.xml":
                        names = tuple(sorted(shared_foot_geom_name(name) for name in names))
                    if set(names).issubset(retained):
                        values = np.concatenate(([contact.dist], contact.pos, contact.friction,
                                                 contact.solref, contact.solimp))
                        contacts.append((names, int(contact.dim), values))
                # Canonical endpoint ordering avoids sub-picometer roundoff
                # changing the order of otherwise equivalent capsule contacts.
                records.append(sorted(contacts, key=lambda item: (item[0], tuple(np.round(item[2], 10)))))
            self.assertGreater(len(records[0]), 0)
            self.assertEqual(len(records[0]), len(records[1]))
            for old, new in zip(*records):
                self.assertEqual(old[:2], new[:2])
                np.testing.assert_allclose(old[2], new[2], rtol=0, atol=1e-12)


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
        calibrated = {"pelvis_upper_shell_collision", "right_elbow_link_1_capsule_collision"} | {
            f"{side}_{role}" for side in ("left", "right")
            for role in ("knee_link_1_capsule_collision", "wrist_pitch_link_1_capsule_collision",
                         "upper_arm_capsule_collision", "elbow_stop_collision")}
        for i in range(rubber.ngeom):
            geom = rubber.geom(i)
            if "rubber_hand" in geom.name or geom.name in calibrated:
                continue
            other = dex.geom(shared_foot_geom_name(geom.name))
            for attribute in ("type", "size", "pos", "quat", "friction", "contype", "conaffinity"):
                if attribute == "quat":
                    if geom.name.startswith("right_foot_"):
                        # Reversing a symmetric sole capsule's endpoints leaves
                        # its shape intact, but flips its quaternion axis.
                        np.testing.assert_allclose(np.abs(geom.quat), np.abs(other.quat), rtol=0, atol=1e-11)
                        continue
                    # Manual cleanup of near-zero fromto coordinates changes the
                    # compiled capsule quaternion by about 2e-12, not its shape.
                    np.testing.assert_allclose(geom.quat, other.quat, rtol=0, atol=1e-11)
                else:
                    np.testing.assert_array_equal(getattr(geom, attribute), getattr(other, attribute))

    def test_default_collision_inventory_and_reference(self):
        default = self.rubber
        self.assertEqual(int((default.geom_group == 3).sum()), 52)
        self.assertEqual(default.nexclude, 2)
        self.assertEqual(default.npair, 0)
        self.assertEqual(int((default.geom_group == 1).sum()), 37)
        colliders = default.geom_group == 3
        self.assertTrue(np.all(default.geom_contype[colliders] == 1))
        self.assertTrue(np.all(default.geom_conaffinity[colliders] == 1))
        visuals = default.geom_group == 1
        self.assertTrue(np.all(default.geom_contype[visuals] == 0))
        self.assertTrue(np.all(default.geom_conaffinity[visuals] == 0))
        state = mujoco.MjData(default)
        mujoco.mj_forward(default, state)
        self.assertEqual(state.ncon, 0)
        scene = mujoco.MjModel.from_xml_path(str(ROOT / "astro_p2/scene.xml"))
        for side in ("left", "right"):
            for angle, expected_contact in ((0, False), (-0.08, True), (2.3, False), (2.44, True)):
                state = mujoco.MjData(scene)
                state.qpos[scene.joint(f"{side}_knee_joint").qposadr[0]] = angle
                mujoco.mj_forward(scene, state)
                pair = {scene.geom(f"{side}_hip_roll_link_1_capsule_collision").id,
                        scene.geom(f"{side}_knee_link_1_capsule_collision").id}
                self.assertEqual(any({c.geom1, c.geom2} == pair for c in state.contact), expected_contact)

    def test_default_upper_arm_shafts_are_continuous_through_yaw(self):
        model = self.rubber
        data = mujoco.MjData(model)
        for side, radius in (("left", 0.037), ("right", 0.039)):
            shaft = model.geom(f"{side}_upper_arm_capsule_collision")
            self.assertEqual(model.body(int(shaft.bodyid[0])).name, f"{side}_shoulder_roll_link")
            self.assertAlmostEqual(shaft.size[0], radius)
            self.assertEqual(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM,
                                              f"{side}_shoulder_roll_link_1_capsule_collision"), -1)
            # Separate transverse housing remains; axial shaft must be invariant
            # under shoulder yaw, while following shoulder pitch and roll.
            self.assertEqual(model.geom(f"{side}_shoulder_roll_link_2_capsule_collision").type[0],
                             mujoco.mjtGeom.mjGEOM_CAPSULE)
            for pitch, roll in ((0, 0), (-1, 0.2), (1, -0.2)):
                for yaw in np.linspace(-1.92, 1.92, 9):
                    mujoco.mj_resetData(model, data)
                    for role, angle in (("pitch", pitch), ("roll", roll), ("yaw", yaw)):
                        data.qpos[model.joint(f"{side}_shoulder_{role}_joint").qposadr[0]] = angle
                    mujoco.mj_forward(model, data)
                    body = model.body(f"{side}_shoulder_roll_link").id
                    frame = data.xmat[body].reshape(3, 3)
                    half_length = 0.06
                    expected_center = data.xpos[body] + frame @ np.array([0, 0, -half_length])
                    np.testing.assert_allclose(data.geom_xpos[shaft.id], expected_center, atol=1e-12)
                    axis = data.geom_xmat[shaft.id].reshape(3, 3)[:, 2]
                    np.testing.assert_allclose(np.abs(axis @ frame[:, 2]), 1, atol=1e-12)
                    self.assertAlmostEqual(shaft.size[1], half_length)
            joint = model.joint(f"{side}_elbow_joint")
            self.assertTrue(joint.limited[0])
            np.testing.assert_array_equal(joint.range, [-0.52, 1.66])

    def test_default_automatic_elbow_contacts(self):
        model = self.rubber
        self.assertEqual(model.npair, 0)
        for side in ("left", "right"):
            upper = model.geom(f"{side}_upper_arm_capsule_collision")
            forearm = model.geom(f"{side}_elbow_link_1_capsule_collision")
            joint = model.joint(f"{side}_elbow_joint")
            body = int(forearm.bodyid[0])
            self.assertEqual(model.body_parentid[model.body_parentid[body]], upper.bodyid[0])
            self.assertEqual((upper.contype[0], upper.conaffinity[0]), (1, 1))
            selected = {forearm.id, upper.id}
            self.assertEqual(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM,
                                              f"{side}_elbow_stop_collision"), -1)
            for yaw in (-1.92, 0, 1.92):
                for angle, contact_expected in ((1.66, False), (0, False), (-0.15, False),
                                                 (-0.28, False), (-0.35, False),
                                                 (-0.4, side == "right"),
                                                 (-0.48, side == "right"), (-0.5, True), (-0.52, True)):
                    data = mujoco.MjData(model)
                    data.qpos[joint.qposadr[0]] = angle
                    data.qpos[model.joint(f"{side}_shoulder_yaw_joint").qposadr[0]] = yaw
                    mujoco.mj_forward(model, data)
                    contacts = [c for c in data.contact if {c.geom1, c.geom2} == selected]
                    self.assertEqual(bool(contacts), contact_expected)
                    self.assertTrue(all(c.dim == 3 for c in contacts))
                    if angle == -0.5:
                        # Native angle limit is not active here: contact must provide resistance.
                        self.assertGreater(data.qfrc_constraint[joint.dofadr[0]], 0)

    def test_default_elbow_stop_resists_folding_motion(self):
        model = self.rubber
        # Diagnostic only: no gravity or controller; native model file is untouched.
        model.opt.gravity[:] = 0
        for side in ("left", "right"):
            joint = model.joint(f"{side}_elbow_joint")
            for speed in (-1, -3):
                data = mujoco.MjData(model)
                data.qpos[joint.qposadr[0]] = -0.3
                data.qvel[joint.dofadr[0]] = speed
                minimum = 0
                contacted = False
                reversed_motion = False
                target = f"{side}_elbow_link_1_capsule_collision"
                selected = {model.geom(target).id,
                            model.geom(f"{side}_upper_arm_capsule_collision").id}
                for _ in range(150):
                    mujoco.mj_forward(model, data)
                    minimum = min(minimum, float(data.qpos[joint.qposadr[0]]))
                    reversed_motion |= data.qvel[joint.dofadr[0]] > 0
                    contacted |= any({c.geom1, c.geom2} == selected for c in data.contact)
                    mujoco.mj_step(model, data)
                self.assertTrue(contacted)
                self.assertGreater(minimum, joint.range[0])
                self.assertTrue(reversed_motion)
                self.assertTrue(np.isfinite(data.qpos).all())
                self.assertTrue(np.isfinite(data.qvel).all())
                self.assertFalse(np.any(data.warning.number))

    def test_left_overlapping_capsules_generate_actual_contact(self):
        model = self.rubber
        data = mujoco.MjData(model)
        joint = model.joint("left_elbow_joint")
        data.qpos[joint.qposadr[0]] = -0.5
        mujoco.mj_forward(model, data)
        upper = model.geom("left_upper_arm_capsule_collision").id
        forearm = model.geom("left_elbow_link_1_capsule_collision").id
        self.assertLess(mujoco.mj_geomDistance(model, data, upper, forearm, 1, None), 0)
        self.assertTrue(any({c.geom1, c.geom2} == {upper, forearm} for c in data.contact))
        self.assertGreater(data.qfrc_constraint[joint.dofadr[0]], 0)
        self.assertEqual(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM,
                                          "left_elbow_stop_collision"), -1)

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
