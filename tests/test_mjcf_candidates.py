import json
import pathlib
import shutil
import tempfile
import unittest
from xml.etree import ElementTree as ET

from menagerie_x.assets import get_variant
from menagerie_x.commands.mjcf import (
    MjcfCandidateError,
    authorize_candidate,
    convert_variant_to_candidate,
    create_managed_candidate,
    discard_managed_candidate,
    list_managed_candidates,
    managed_candidate_path,
    validate_candidate,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "menagerie_x" / "assets"


class MjcfCandidateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.assets = pathlib.Path(self.directory.name) / "assets"
        shutil.copytree(ASSETS, self.assets)
        manifest_path = self.assets / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["variants"]["astro_v2"]["mjcf"] = None
        manifest["variants"]["astro_v2"].pop("mjcf_provenance", None)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        shutil.rmtree(self.assets / "astro_v2" / "mjcf", ignore_errors=True)

    def tearDown(self):
        self.directory.cleanup()

    def test_convert_creates_reviewable_portable_candidate_without_registering_it(self):
        candidate = pathlib.Path(self.directory.name) / "candidate.xml"
        result = convert_variant_to_candidate("astro_v2", "v2-review", candidate, self.assets)

        self.assertTrue(candidate.is_file())
        self.assertIn("menagerie_x_candidate", candidate.read_text(encoding="utf-8"))
        self.assertFalse((candidate.parent / "candidate.json").exists())
        self.assertEqual(result["report"]["free_root_count"], 1)
        self.assertGreater(result["report"]["model"]["ngeom"], 1)
        self.assertTrue(result["report"]["fixed_link_frame_sites"])
        self.assertNotIn(str(self.assets), candidate.read_text(encoding="utf-8"))
        self.assertIsNone(get_variant("astro_v2", self.assets).mjcf)

    def test_convert_refuses_nonempty_output_and_authorize_updates_only_target(self):
        candidate = pathlib.Path(self.directory.name) / "candidate.xml"
        candidate.write_text("review me", encoding="utf-8")
        with self.assertRaises(MjcfCandidateError):
            convert_variant_to_candidate("astro_v2", "v2-review", candidate, self.assets)
        candidate.unlink()
        convert_variant_to_candidate("astro_v2", "v2-review", candidate, self.assets)

        checked = validate_candidate(candidate, get_variant("astro_v2", self.assets))
        self.assertIsNone(checked["source_drift_warning"])
        installed = authorize_candidate(candidate, "astro_v2", self.assets)
        self.assertTrue(pathlib.Path(installed["installed_mjcf"]).is_file())
        manifest = json.loads((self.assets / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["variants"]["astro_v2"]["mjcf"], "mjcf/v2-review.xml")
        self.assertIsNone(manifest["variants"]["astro_with_racket"]["mjcf"])
        with self.assertRaises(MjcfCandidateError):
            authorize_candidate(candidate, "astro_v2", self.assets)

    def test_managed_candidate_lifecycle_never_accepts_arbitrary_paths(self):
        result = create_managed_candidate("astro_v2", "v2-review", self.assets)
        candidate = managed_candidate_path("astro_v2", "v2-review", self.assets)

        self.assertEqual(pathlib.Path(result["output"]), candidate)
        listed = list_managed_candidates("astro_v2", self.assets)
        self.assertEqual([item["id"] for item in listed], ["v2-review"])
        self.assertTrue(listed[0]["valid"])
        with self.assertRaises(MjcfCandidateError):
            managed_candidate_path("astro_v2", "../outside", self.assets)

        discard_managed_candidate("astro_v2", "v2-review", self.assets)
        self.assertFalse(candidate.exists())

    def test_manually_renamed_mjcf_is_listed_as_a_selectable_manual_edition(self):
        original = self.assets / "astro_v2" / "mjcf" / "v2-review.xml"
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ASSETS / "astro_v2" / "mjcf" / "astro_v2_mesh_collision.xml", original)
        manual = original.with_name("astro_v2_primitive_collision.xml")
        source = original.read_text(encoding="utf-8")
        comment_start = source.index("<!-- menagerie_x_candidate:")
        comment_end = source.index("-->", comment_start) + 3
        manual.write_text(source[:comment_start] + source[comment_end:], encoding="utf-8")
        original.unlink()

        listed = list_managed_candidates("astro_v2", self.assets)
        record = next(item for item in listed if item["id"] == "astro_v2_primitive_collision")

        self.assertTrue(record["valid"])
        self.assertTrue(record["manual"])
        self.assertGreater(record["model"]["nbody"], 1)
        self.assertEqual(managed_candidate_path("astro_v2", "astro_v2_primitive_collision", self.assets), manual)

    def test_managed_candidate_generation_stays_available_after_authorization(self):
        create_managed_candidate("astro_v2", "v2-review", self.assets)
        authorized = authorize_candidate(
            managed_candidate_path("astro_v2", "v2-review", self.assets),
            "astro_v2",
            self.assets,
        )

        follow_up = create_managed_candidate("astro_v2", "v2-second-review", self.assets)

        self.assertTrue(pathlib.Path(follow_up["output"]).is_file())
        self.assertTrue(pathlib.Path(authorized["installed_mjcf"]).is_file())
        manifest = json.loads((self.assets / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["variants"]["astro_v2"]["mjcf"], "mjcf/v2-review.xml")

    def test_compiled_visual_mesh_pose_already_contains_mesh_alignment(self):
        import mujoco
        import numpy as np

        source = ASSETS / "astro_v1" / "mjcf" / "astro_v1.xml"
        root = ET.fromstring(source.read_text(encoding="utf-8"))
        root.find("compiler").set("meshdir", str((ASSETS / "astro_v1" / "meshes").resolve()))
        model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))
        visual_mesh_ids = [
            geom_id
            for geom_id in range(model.ngeom)
            if int(model.geom_type[geom_id]) == int(mujoco.mjtGeom.mjGEOM_MESH)
            and int(model.geom_contype[geom_id]) == 0
        ]

        self.assertTrue(visual_mesh_ids)
        # The first pelvis visual has no additional authored geom transform, so
        # its compiled geom transform demonstrates where MuJoCo stores mesh
        # centering/alignment. Other geoms may add their own local offset.
        geom_id = visual_mesh_ids[0]
        mesh_id = int(model.geom_dataid[geom_id])
        np.testing.assert_allclose(model.geom_pos[geom_id], model.mesh_pos[mesh_id])
        np.testing.assert_allclose(model.geom_quat[geom_id], model.mesh_quat[mesh_id])
