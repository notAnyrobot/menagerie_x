"""Regression coverage for the official Unitree G1 Menagerie import."""

from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from menagerie_x.assets import get_variant, inspect_variant, list_mjcf_editions, validate_assets
from menagerie_x.commands.mjcf import list_managed_candidates
from menagerie_x.commands.mujoco import check_mujoco
from menagerie_x.workbench.server import WorkbenchRequestHandler


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "menagerie_x" / "assets"
G1_URDF = ASSETS / "unitree_g1" / "urdf" / "g1_29dof_with_hand_rev_1_0.urdf"
RETARGETING_URDF = ASSETS / "unitree_g1" / "urdf" / "for_retargeting" / "g1.urdf"
RETARGETING_MJCF = ASSETS / "unitree_g1" / "mjcf" / "protomotions_g1_retargeting_box_feet.xml"

BASE_29_DOF = [
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint",
    "left_knee_joint", "left_ankle_pitch_joint", "left_ankle_roll_joint",
    "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint",
    "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint",
    "waist_yaw_joint", "waist_roll_joint", "waist_pitch_joint",
    "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint",
    "left_elbow_joint", "left_wrist_roll_joint", "left_wrist_pitch_joint",
    "left_wrist_yaw_joint", "right_shoulder_pitch_joint", "right_shoulder_roll_joint",
    "right_shoulder_yaw_joint", "right_elbow_joint", "right_wrist_roll_joint",
    "right_wrist_pitch_joint", "right_wrist_yaw_joint",
]


class UnitreeG1ImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.variant = get_variant("unitree_g1", ASSETS)

    def test_catalogued_official_variant_has_a_selectable_mjcf_edition(self) -> None:
        self.assertEqual(self.variant.dof, 43)
        self.assertEqual(self.variant.urdf, G1_URDF)
        editions = list_mjcf_editions(self.variant, ASSETS)
        self.assertEqual(
            [edition["id"] for edition in editions],
            ["g1_29dof_with_hand_rev_1_0", "protomotions_g1_retargeting_box_feet"],
        )
        self.assertTrue(editions[0]["default"])
        self.assertEqual(editions[0]["validation"], "valid")
        self.assertEqual(editions[0]["kind"], "official")
        self.assertEqual(editions[0]["source_revision"], self.variant.mjcf_provenance["source_revision"])
        self.assertIsInstance(editions[0]["modified_at"], int)
        self.assertLess(editions[0]["modified_at"], 10**13)  # Unix milliseconds, safe for browser Date.
        self.assertFalse(editions[1]["default"])
        self.assertEqual(editions[1]["kind"], "retargeting-reference")
        self.assertEqual(validate_assets(ASSETS), [])

    def test_protomotions_retargeting_edition_is_selectable_and_self_contained(self) -> None:
        editions = {edition["id"]: edition for edition in list_mjcf_editions(self.variant, ASSETS)}
        reference = editions["protomotions_g1_retargeting_box_feet"]
        self.assertEqual(reference["validation"], "valid")
        self.assertEqual(reference["provenance"]["source_role"], "kinematic model selected when ProtoMotions converts retargeted G1 CSV files")
        self.assertEqual(reference["provenance"]["source_path"], "protomotions/data/assets/mjcf/g1_bm_box_feet.xml")
        self.assertTrue(RETARGETING_MJCF.is_file())
        self.assertTrue((ASSETS / "unitree_g1" / "LICENSE.ProtoMotions").is_file())
        self.assertTrue((ASSETS / "unitree_g1" / "NOTICE.ProtoMotions").is_file())
        self.assertEqual(list_managed_candidates("unitree_g1", ASSETS), [])

        resolver = object.__new__(WorkbenchRequestHandler)
        resolver.asset_root = ASSETS
        record, source = resolver._edition(self.variant, reference["id"])
        self.assertEqual(record["id"], reference["id"])
        self.assertEqual(source, RETARGETING_MJCF)

    def test_protomotions_retargeting_urdf_is_kept_separate_from_the_official_default(self) -> None:
        self.assertEqual(self.variant.urdf, G1_URDF)
        self.assertTrue(RETARGETING_URDF.is_file())
        root = ET.parse(RETARGETING_URDF).getroot()
        mesh_filenames = [mesh.get("filename") for mesh in root.findall(".//mesh") if mesh.get("filename")]
        resolved_meshes = [(RETARGETING_URDF.parent / str(filename)).resolve() for filename in mesh_filenames]
        self.assertTrue(all(path.is_relative_to((ASSETS / "unitree_g1" / "meshes").resolve()) for path in resolved_meshes))
        self.assertTrue(all(path.is_file() for path in resolved_meshes))

        manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
        provenance = manifest["variants"]["unitree_g1"]["source_provenance"]["retargeting_urdf"]
        self.assertEqual(provenance["packaged_path"], "urdf/for_retargeting/g1.urdf")
        self.assertEqual(provenance["source_path"], "protomotions/data/assets/urdf/for_retargeting/g1.urdf")
        self.assertEqual(provenance["packaged_sha256"], hashlib.sha256(RETARGETING_URDF.read_bytes()).hexdigest())
        self.assertEqual(provenance["source_sha256"], "bd199a00d2bd38f17b47ecf896c3891605af658ebc76d8954b6c2060af071c8e")

    def test_retargeting_edition_keeps_the_29_body_joint_schema_and_box_foot_contacts(self) -> None:
        root = ET.parse(RETARGETING_MJCF).getroot()
        joints = [joint.get("name") for joint in root.findall(".//joint") if joint.get("name")]
        self.assertEqual(joints[0], "floating_base_joint")
        self.assertEqual(joints[1:], BASE_29_DOF)
        self.assertFalse(any("hand" in joint for joint in joints))
        self.assertGreaterEqual(len([geom for geom in root.findall(".//geom") if geom.get("type") == "box"]), 2)
        self.assertEqual(root.find(".//site[@name='imu']").get("pos"), "-0.03959 -0.00224 0.14792")

        mesh_files = [mesh.get("file") for mesh in root.findall(".//asset/mesh") if mesh.get("file")]
        self.assertTrue(all((ASSETS / "unitree_g1" / "meshes" / str(filename)).is_file() for filename in mesh_files))

    def test_every_official_urdf_mesh_resolves_inside_the_packaged_workspace(self) -> None:
        root = ET.parse(G1_URDF).getroot()
        mesh_filenames = [
            mesh.get("filename")
            for mesh in root.findall(".//mesh")
            if mesh.get("filename")
        ]
        self.assertGreater(len(mesh_filenames), 0)
        self.assertTrue(all(filename.startswith("../meshes/") for filename in mesh_filenames))
        meshes_dir = ASSETS / "unitree_g1" / "meshes"
        resolved_meshes = [(G1_URDF.parent / filename).resolve() for filename in mesh_filenames]
        self.assertTrue(all(path.is_relative_to(meshes_dir.resolve()) for path in resolved_meshes))
        self.assertTrue(all(path.is_file() for path in resolved_meshes))

        inspection = inspect_variant(self.variant)
        self.assertFalse([issue for issue in inspection.issues if issue.code == "mesh-missing"])
        self.assertFalse([issue for issue in inspection.issues if issue.severity == "error"])
        self.assertEqual(
            [issue.element for issue in inspection.issues if issue.code == "inertial-missing"],
            ["imu_in_torso", "imu_in_pelvis", "d435_link", "mid360_link"],
        )

    def test_joint_identity_preserves_the_g1_body_sequence_and_adds_hands(self) -> None:
        root = ET.parse(G1_URDF).getroot()
        joints = [joint.get("name") for joint in root.findall("joint") if joint.get("type") != "fixed"]
        self.assertEqual(len(joints), 43)
        self.assertEqual([name for name in joints if name in BASE_29_DOF], BASE_29_DOF)
        hand_joints = [name for name in joints if name and "_hand_" in name]
        self.assertEqual(len(hand_joints), 14)

    def test_provenance_keeps_the_official_source_and_license(self) -> None:
        manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
        provenance = manifest["variants"]["unitree_g1"]["source_provenance"]
        self.assertEqual(provenance["repository"], "https://github.com/unitreerobotics/unitree_ros")
        self.assertEqual(provenance["source_path"], "robots/g1_description/g1_29dof_with_hand_rev_1_0.urdf")
        self.assertEqual(
            manifest["variants"]["unitree_g1"]["mjcf_provenance"]["source_revision"],
            provenance["sha256"],
        )
        self.assertNotEqual(provenance["sha256"], hashlib.sha256(G1_URDF.read_bytes()).hexdigest())
        self.assertTrue((ASSETS / "unitree_g1" / provenance["license_file"]).is_file())

    @unittest.skipUnless(importlib.util.find_spec("mujoco"), "mujoco is not installed")
    def test_mujoco_compiles_the_packaged_mjcf(self) -> None:
        result = check_mujoco("unitree_g1", ASSETS)
        self.assertEqual(result["variant"], "unitree_g1")
        self.assertGreater(int(result["nq"]), 0)
        reference = check_mujoco(mjcf_path=RETARGETING_MJCF)
        self.assertIsNone(reference["variant"])
        self.assertGreater(int(reference["nq"]), 0)
