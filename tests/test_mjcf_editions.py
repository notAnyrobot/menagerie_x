import pathlib
import shutil
import tempfile
import unittest

from menagerie_x.assets import (
    MjcfEditionError,
    delete_mjcf_edition,
    duplicate_mjcf_edition,
    get_variant,
    import_mjcf_edition,
    import_mjcf_variant,
    import_urdf_variant,
    list_mjcf_editions,
    rename_mjcf_edition,
    set_default_mjcf_edition,
    validate_assets,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "menagerie_x" / "assets"


class MjcfEditionWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.assets = pathlib.Path(self.directory.name) / "assets"
        shutil.copytree(ASSETS, self.assets)

    def tearDown(self):
        self.directory.cleanup()

    def test_discovery_keeps_halfway_fixture_and_empty_variants_are_safe(self):
        editions = list_mjcf_editions(get_variant("astro_v2", self.assets), self.assets)

        self.assertEqual(editions[0]["id"], "astro_v2_primitive_collision")
        self.assertTrue(editions[0]["default"])
        self.assertIn("astro_v2_primitive_collision_halfway", {edition["id"] for edition in editions})
        self.assertEqual(list_mjcf_editions(get_variant("astro_with_racket", self.assets), self.assets), [])

    def test_import_duplicate_rename_default_and_delete_use_managed_paths(self):
        source = ASSETS / "astro_v2" / "mjcf" / "astro_v2_primitive_collision.xml"
        imported = import_mjcf_edition("astro_v2", source, "external-review", self.assets)
        duplicate = duplicate_mjcf_edition("astro_v2", imported["edition_id"], "external-copy", self.assets)
        renamed = rename_mjcf_edition("astro_v2", duplicate["edition_id"], "final-review", self.assets)
        default = set_default_mjcf_edition("astro_v2", renamed["edition_id"], self.assets)

        self.assertEqual(default["edition_id"], "final-review")
        self.assertTrue(pathlib.Path(default["output_path"]).is_file())
        delete_mjcf_edition("astro_v2", "external-review", self.assets)
        self.assertNotIn("external-review", {edition["id"] for edition in list_mjcf_editions(get_variant("astro_v2", self.assets), self.assets)})
        with self.assertRaises(MjcfEditionError):
            delete_mjcf_edition("astro_v2", "final-review", self.assets)

    def test_imported_mjcf_variant_is_self_contained_and_rejects_escaping_meshes(self):
        source = ASSETS / "astro_v2" / "mjcf" / "astro_v2_primitive_collision.xml"
        result = import_mjcf_variant("external_astro", source, self.assets)

        imported = get_variant("external_astro", self.assets)
        self.assertIsNone(imported.urdf)
        self.assertEqual(result["edition_id"], "external_astro")
        self.assertEqual([edition["id"] for edition in list_mjcf_editions(imported, self.assets)], ["external_astro"])
        self.assertEqual(validate_assets(self.assets), [])

        malicious = pathlib.Path(self.directory.name) / "bad.xml"
        malicious.write_text('<mujoco><compiler meshdir="../../outside"/><asset><mesh file="x.stl"/></asset></mujoco>', encoding="utf-8")
        with self.assertRaises(MjcfEditionError):
            import_mjcf_variant("unsafe", malicious, self.assets)

    def test_imported_urdf_variant_converts_a_first_default_edition(self):
        result = import_urdf_variant("imported_v1", ASSETS / "astro_v1" / "urdf" / "astro_v1.urdf", self.assets)

        variant = get_variant("imported_v1", self.assets)
        self.assertEqual(result["edition_id"], "imported_v1")
        self.assertTrue(variant.mjcf and variant.mjcf.is_file())
        self.assertEqual([edition["id"] for edition in list_mjcf_editions(variant, self.assets)], ["imported_v1"])
