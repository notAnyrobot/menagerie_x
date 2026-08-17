import pathlib
import json
import os
import shutil
import tempfile
import unittest

from menagerie_x.commands.mjcf import read_candidate_metadata_file
from menagerie_x.workbench.collisions import StaleCollisionDocumentError
from menagerie_x.workbench.mjcf_collisions import (
    MjcfCollisionDraftStore,
    _body_frames,
    _matrix_multiply,
    _quat_to_matrix,
    _rpy_to_quat,
    load_mjcf_collision_document,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "menagerie_x" / "assets" / "astro_v1" / "mjcf" / "astro_v1.xml"
CANDIDATE = ROOT / "src" / "menagerie_x" / "assets" / "astro_v2" / "mjcf" / "astro_v2-review.xml"
HALFWAY = ROOT / "src" / "menagerie_x" / "assets" / "astro_v2" / "mjcf" / "astro_v2_primitive_collision_halfway.xml"


class MjcfCollisionDraftTests(unittest.TestCase):
    def test_halfway_fixture_mirrors_both_directions_without_touching_center_collisions(self):
        directory = tempfile.TemporaryDirectory()
        fixture_root = pathlib.Path(directory.name) / "astro_v2"
        source = fixture_root / "mjcf" / "astro_v2_primitive_collision_halfway.xml"
        source.parent.mkdir(parents=True)
        os.symlink(HALFWAY.parents[1] / "meshes", fixture_root / "meshes", target_is_directory=True)
        shutil.copyfile(HALFWAY, source)
        original = load_mjcf_collision_document(source)
        original_by_name = {(item["link"], item["name"]): item for item in original.collisions}
        center_keys = [key for key in original_by_name if key[0] in {"pelvis", "waist_roll_link", "head_link"}]
        center_before = {key: original_by_name[key] for key in center_keys}
        store = MjcfCollisionDraftStore()
        try:
            session = store.create(source)
            preview = store.mirror_preview(session.identifier, source, session.document.revision, "left-to-right")
            self.assertEqual(preview["sagittal_plane"], "y=0")
            self.assertEqual(preview["source_side"], "left")
            self.assertEqual(preview["target_side"], "right")
            self.assertGreater(preview["replaced_target_meshes"], 0)
            self.assertTrue(preview["affected"])
            self.assertTrue(all(record["source_link"].startswith("left_") and record["target_link"].startswith("right_") for record in preview["affected"]))
            self.assertFalse(any(record["target_link"] in {"pelvis", "waist_roll_link", "head_link"} for record in preview["affected"]))

            session, _ = store.mirror(session.identifier, source, session.document.revision, "left-to-right")
            mirrored = load_mjcf_collision_document(session.temporary)
            mirrored_by_name = {(item["link"], item["name"]): item for item in mirrored.collisions}
            self.assertFalse(any(item["link"].startswith("right_") and item["geometry"]["type"] == "mesh" for item in mirrored.collisions))
            source_frames = _body_frames(source)
            draft_frames = _body_frames(session.temporary)
            reflection = [[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0]]
            for record in preview["affected"]:
                original_collision = original_by_name[(record["source_link"], record["source_name"])]
                mirrored_collision = mirrored_by_name[(record["target_link"], record["target_name"])]
                self.assertEqual(mirrored_collision["geometry"], original_collision["geometry"])
                source_position, source_rotation = source_frames[record["source_link"]]
                target_position, target_rotation = draft_frames[record["target_link"]]
                source_world = [source_position[index] + sum(source_rotation[index][column] * original_collision["origin"]["xyz"][column] for column in range(3)) for index in range(3)]
                target_world = [target_position[index] + sum(target_rotation[index][column] * mirrored_collision["origin"]["xyz"][column] for column in range(3)) for index in range(3)]
                self.assertAlmostEqual(target_world[0], source_world[0], places=9)
                self.assertAlmostEqual(target_world[1], -source_world[1], places=9)
                self.assertAlmostEqual(target_world[2], source_world[2], places=9)
                source_orientation = _matrix_multiply(source_rotation, _quat_to_matrix(_rpy_to_quat(original_collision["origin"]["rpy"])))
                target_orientation = _matrix_multiply(target_rotation, _quat_to_matrix(_rpy_to_quat(mirrored_collision["origin"]["rpy"])))
                expected_orientation = _matrix_multiply(_matrix_multiply(reflection, source_orientation), reflection)
                for row in range(3):
                    for column in range(3):
                        self.assertAlmostEqual(target_orientation[row][column], expected_orientation[row][column], places=9)

            store.overwrite(session.identifier, source, session.document.revision)
            persisted = load_mjcf_collision_document(source)
            persisted_by_name = {(item["link"], item["name"]): item for item in persisted.collisions}
            self.assertEqual({key: persisted_by_name[key] for key in center_keys}, center_before)

            reverse = store.create(source)
            reverse_preview = store.mirror_preview(reverse.identifier, source, reverse.document.revision, "right-to-left")
            self.assertEqual(reverse_preview["sagittal_plane"], "y=0")
            self.assertTrue(reverse_preview["affected"])
            reverse, _ = store.mirror(reverse.identifier, source, reverse.document.revision, "right-to-left")
            store.overwrite(reverse.identifier, source, reverse.document.revision)
            reloaded = load_mjcf_collision_document(source)
            reloaded_by_name = {(item["link"], item["name"]): item for item in reloaded.collisions}
            self.assertEqual({key: reloaded_by_name[key] for key in center_keys}, center_before)
            import mujoco

            model = mujoco.MjModel.from_xml_path(str(source))
            self.assertGreater(model.ngeom, 0)
        finally:
            store.close()
            directory.cleanup()

    def test_projects_named_capsules_and_exports_unregistered_candidate(self):
        document = load_mjcf_collision_document(SOURCE)
        capsule = next(item for item in document.collisions if item["geometry"]["type"] == "capsule")
        self.assertTrue(capsule["editable"])
        self.assertGreater(capsule["geometry"]["length"], 0)

        store = MjcfCollisionDraftStore()
        try:
            session = store.create(SOURCE)
            self.assertTrue(session.temporary.is_file())
            self.assertEqual(store.source_bytes(session.identifier, SOURCE), SOURCE.read_bytes())
            output = store.export(session.identifier, SOURCE, session.document.revision, source_variant="astro_v1")
            self.assertTrue(output.is_file())
            self.assertIn("menagerie_x_candidate", output.read_text(encoding="utf-8"))
            output.unlink()
        finally:
            store.close()

    def test_overwrite_replaces_only_the_draft_source_atomically_and_rejects_stale_source(self):
        directory = tempfile.TemporaryDirectory()
        source = pathlib.Path(directory.name) / "review.xml"
        shutil.copyfile(CANDIDATE, source)
        store = MjcfCollisionDraftStore()
        try:
            session = store.create(source)
            store.update(session.identifier, source, session.document.revision, session.primitives, sorted(session.retained_mesh_ids))
            metadata = read_candidate_metadata_file(source)
            self.assertEqual(
                store.overwrite(session.identifier, source, session.document.revision, metadata),
                source,
            )
            updated = read_candidate_metadata_file(source)
            self.assertEqual(updated["candidate_id"], metadata["candidate_id"])
            self.assertEqual(updated["source_variant"], metadata["source_variant"])
            self.assertEqual(updated["created_at"], metadata["created_at"])
            self.assertIn("modified_at", updated)
            source.write_bytes(source.read_bytes() + b"<!-- external change -->\n")
            with self.assertRaises(StaleCollisionDocumentError):
                store.overwrite(session.identifier, source, session.document.revision)
        finally:
            store.close()
            directory.cleanup()

    def test_overwrite_updates_legacy_candidate_sidecar_without_changing_its_identity(self):
        directory = tempfile.TemporaryDirectory()
        candidate = pathlib.Path(directory.name) / "candidate"
        candidate.mkdir()
        source = candidate / "model.xml"
        shutil.copyfile(CANDIDATE, source)
        metadata = read_candidate_metadata_file(source)
        source.write_bytes(source.read_bytes().replace(b"<!-- menagerie_x_candidate:", b"<!-- retained candidate:\"", 1))
        # Folder candidates keep their review metadata in candidate.json rather
        # than an XML comment.  The model stays a normal editable MJCF file.
        sidecar = candidate / "candidate.json"
        sidecar.write_text(json.dumps(metadata), encoding="utf-8")
        store = MjcfCollisionDraftStore()
        try:
            session = store.create(source)
            store.update(session.identifier, source, session.document.revision, session.primitives, sorted(session.retained_mesh_ids))
            store.overwrite(session.identifier, source, session.document.revision, metadata, sidecar)
            updated = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(updated["candidate_id"], metadata["candidate_id"])
            self.assertEqual(updated["created_at"], metadata["created_at"])
            self.assertIn("modified_at", updated)
        finally:
            store.close()
            directory.cleanup()
