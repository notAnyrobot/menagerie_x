import datetime as dt
import pathlib
import tempfile
import unittest
import xml.etree.ElementTree as ET

from menagerie_x.workbench.collisions import (
    CollisionDraftNotFoundError,
    CollisionDraftStore,
    CollisionDocumentError,
    StaleCollisionDocumentError,
    export_collision_copy,
    load_collision_document,
)


SOURCE = """<?xml version=\"1.0\"?>
<robot name=\"test\">
  <!-- preserve this comment -->
  <link name=\"base\">
    <collision name=\"base_mesh\"><geometry><mesh filename=\"base.stl\"/></geometry></collision>
    <collision name=\"base_box\"><origin xyz=\"1 2 3\" rpy=\"0 0 0\"/><geometry><box size=\"1 2 3\"/></geometry></collision>
  </link>
  <link name=\"arm\"/>
  <joint name=\"fixed\" type=\"fixed\"><parent link=\"base\"/><child link=\"arm\"/></joint>
</robot>
"""


class CollisionDocumentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.source = pathlib.Path(self.directory.name) / "robot.urdf"
        self.source.write_text(SOURCE, encoding="utf-8")

    def tearDown(self):
        self.directory.cleanup()

    def test_projection_distinguishes_editable_primitives_from_meshes(self):
        document = load_collision_document(self.source)

        self.assertEqual(document.links, ("base", "arm"))
        self.assertEqual([item["id"] for item in document.collisions], ["collision-0-0", "collision-0-1"])
        self.assertFalse(document.collisions[0]["editable"])
        self.assertTrue(document.collisions[1]["editable"])
        self.assertEqual(document.collisions[1]["geometry"], {"type": "box", "size": [1.0, 2.0, 3.0]})

    def test_export_edits_primitives_preserves_meshes_comments_and_source(self):
        document = load_collision_document(self.source)
        source_before = self.source.read_bytes()
        draft = [
            {
                "id": "collision-0-1",
                "link": "arm",
                "name": "arm_box",
                "origin": {"xyz": [0.1, 0.2, 0.3], "rpy": [0.0, 0.0, 0.5]},
                "geometry": {"type": "box", "size": [0.4, 0.5, 0.6]},
            },
            {
                "id": f"{document.new_id_prefix}sphere",
                "link": "base",
                "name": "base_sphere",
                "origin": {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]},
                "geometry": {"type": "sphere", "radius": 0.2},
            },
        ]

        output = export_collision_copy(self.source, document.revision, draft, dt.datetime(2026, 8, 13, 1, 2, 3, tzinfo=dt.UTC))

        self.assertEqual(self.source.read_bytes(), source_before)
        self.assertEqual(output.name, "robot_collision_edited_20260813T010203Z.urdf")
        result = output.read_text(encoding="utf-8")
        self.assertIn("<!-- preserve this comment -->", result)
        root = ET.fromstring(result)
        self.assertEqual(root.find("./link[@name='base']/collision[@name='base_mesh']/geometry/mesh").attrib["filename"], "base.stl")
        self.assertEqual(root.find("./link[@name='arm']/collision[@name='arm_box']/geometry/box").attrib["size"], "0.4 0.5 0.6")
        self.assertEqual(root.find("./link[@name='base']/collision[@name='base_sphere']/geometry/sphere").attrib["radius"], "0.2")
        self.assertIsNotNone(root.find("./joint[@name='fixed']"))

    def test_export_rejects_stale_invalid_and_duplicate_drafts(self):
        document = load_collision_document(self.source)
        valid = {
            "id": "collision-0-1",
            "link": "base",
            "name": "base_box",
            "origin": {"xyz": [0, 0, 0], "rpy": [0, 0, 0]},
            "geometry": {"type": "box", "size": [1, 1, 1]},
        }
        with self.assertRaises(StaleCollisionDocumentError):
            export_collision_copy(self.source, "stale", [valid])
        invalid = {**valid, "geometry": {"type": "box", "size": [0, 1, 1]}}
        with self.assertRaises(CollisionDocumentError):
            export_collision_copy(self.source, document.revision, [invalid])
        with self.assertRaises(CollisionDocumentError):
            export_collision_copy(self.source, document.revision, [valid, valid])

    def test_timestamp_collision_uses_numbered_suffix(self):
        document = load_collision_document(self.source)
        now = dt.datetime(2026, 8, 13, 1, 2, 3, tzinfo=dt.UTC)
        first = export_collision_copy(self.source, document.revision, [], now)
        second = export_collision_copy(self.source, document.revision, [], now)

        self.assertEqual(first.name, "robot_collision_edited_20260813T010203Z.urdf")
        self.assertEqual(second.name, "robot_collision_edited_20260813T010203Z_2.urdf")

    def test_export_can_delete_mesh_collisions_without_mutating_source(self):
        document = load_collision_document(self.source)

        output = export_collision_copy(self.source, document.revision, [], retained_mesh_ids=[])

        self.assertIn("base_mesh", self.source.read_text(encoding="utf-8"))
        root = ET.fromstring(output.read_bytes())
        self.assertIsNone(root.find("./link[@name='base']/collision[@name='base_mesh']"))

    def test_temporary_draft_materializes_mesh_deletions_and_discards_cleanly(self):
        store = CollisionDraftStore()
        try:
            session = store.create(self.source)
            self.assertTrue(session.temporary.is_file())
            self.assertEqual(session.temporary.read_bytes(), self.source.read_bytes())
            self.assertEqual(len(session.retained_mesh_ids), 1)

            store.update(session.identifier, self.source, session.document.revision, session.primitives, [])
            temporary = ET.fromstring(session.temporary.read_bytes())
            self.assertIsNone(temporary.find("./link[@name='base']/collision[@name='base_mesh']"))

            output = store.export(session.identifier, self.source, session.document.revision)
            self.assertTrue(session.temporary.exists())
            self.assertIsNone(ET.fromstring(output.read_bytes()).find("./link[@name='base']/collision[@name='base_mesh']"))

            store.discard(session.identifier, self.source)
            self.assertFalse(session.temporary.exists())
            with self.assertRaises(CollisionDraftNotFoundError):
                store.discard(session.identifier, self.source)
        finally:
            store.close()

    def test_temporary_draft_reset_uses_current_source_and_stale_save_is_rejected(self):
        store = CollisionDraftStore()
        try:
            session = store.create(self.source)
            revision = session.document.revision
            self.source.write_text(SOURCE.replace("base_mesh", "replacement_mesh"), encoding="utf-8")
            with self.assertRaises(StaleCollisionDocumentError):
                store.update(session.identifier, self.source, revision, session.primitives, list(session.retained_mesh_ids))

            reset = store.reset(session.identifier, self.source)
            self.assertNotEqual(reset.document.revision, revision)
            self.assertIn("replacement_mesh", reset.temporary.read_text(encoding="utf-8"))
        finally:
            store.close()

    def test_temporary_draft_expiration_removes_its_file(self):
        store = CollisionDraftStore(ttl_seconds=1)
        try:
            session = store.create(self.source)
            store.cleanup_expired(session.updated_at + 2)

            self.assertFalse(session.temporary.exists())
            with self.assertRaises(CollisionDraftNotFoundError):
                store.discard(session.identifier, self.source)
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
