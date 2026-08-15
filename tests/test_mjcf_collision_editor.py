import pathlib
import shutil
import tempfile
import unittest

from menagerie_x.workbench.mjcf_collisions import MjcfCollisionDraftStore, load_mjcf_collision_document


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "menagerie_x" / "assets" / "astro_v1" / "legacy" / "mjcf" / "astro_v1.xml"


class MjcfCollisionDraftTests(unittest.TestCase):
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
