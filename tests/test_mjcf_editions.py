from catalog_fixture import copy_catalog
import pathlib
import runpy
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
ASSETS = ROOT
GENERATED_FILES = runpy.run_path(str(ROOT / "scripts/sync-menagerie.py"))["generated_files"]


class MjcfEditionWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.assets = pathlib.Path(self.directory.name) / "assets"
        copy_catalog(ASSETS, self.assets)

    def tearDown(self):
        self.directory.cleanup()

    def test_primary_editions_are_distinct_from_legacy_mjcf_file_management(self):
        variant = get_variant("astro_p2", self.assets)
        editions = list_mjcf_editions(variant, self.assets)

        self.assertEqual(
            [edition.id for edition in variant.editions],
            ["30dof_primitive_collision", "30dof_mesh_collision", "30dof_primitive_collision_halfway"],
        )
        self.assertEqual(editions[0]["id"], "astro_p2_30dof_primitive_collision")
        self.assertTrue(editions[0]["default"])
        self.assertEqual(len(editions), 1)
        self.assertEqual(list_mjcf_editions(get_variant("astro_with_racket", self.assets), self.assets), [])

    def test_import_duplicate_rename_default_and_delete_use_managed_paths(self):
        source = ASSETS / "astro_p2" / "mjcf" / "astro_p2_30dof_primitive_collision.xml"
        imported = import_mjcf_edition("astro_p2", source, "external-review", self.assets)
        duplicate = duplicate_mjcf_edition("astro_p2", imported["edition_id"], "external-copy", self.assets)
        renamed = rename_mjcf_edition("astro_p2", duplicate["edition_id"], "final-review", self.assets)
        default = set_default_mjcf_edition("astro_p2", renamed["edition_id"], self.assets)

        self.assertEqual(default["edition_id"], "final-review")
        self.assertTrue(pathlib.Path(default["output_path"]).is_file())
        delete_mjcf_edition("astro_p2", "external-review", self.assets)
        self.assertNotIn("external-review", {edition["id"] for edition in list_mjcf_editions(get_variant("astro_p2", self.assets), self.assets)})
        with self.assertRaises(MjcfEditionError):
            delete_mjcf_edition("astro_p2", "final-review", self.assets)

    def test_imported_mjcf_variant_is_self_contained_and_rejects_escaping_meshes(self):
        source = ASSETS / "astro_p2" / "mjcf" / "astro_p2_30dof_primitive_collision.xml"
        result = import_mjcf_variant("external_astro", source, self.assets)

        imported = get_variant("external_astro", self.assets)
        self.assertIsNone(imported.urdf)
        self.assertEqual(result["edition_id"], "default")
        self.assertEqual([edition["id"] for edition in list_mjcf_editions(imported, self.assets)], ["external_astro_default"])
        self.assertEqual(validate_assets(self.assets), [])

        malicious = pathlib.Path(self.directory.name) / "bad.xml"
        malicious.write_text('<mujoco><compiler meshdir="../../outside"/><asset><mesh file="x.stl"/></asset></mujoco>', encoding="utf-8")
        with self.assertRaises(MjcfEditionError):
            import_mjcf_variant("unsafe", malicious, self.assets)

    def test_imported_urdf_variant_converts_a_first_default_edition(self):
        result = import_urdf_variant("imported_v1", ASSETS / "astro_p1" / "urdf" / "astro_p1_30dof.urdf", self.assets)

        variant = get_variant("imported_v1", self.assets)
        self.assertEqual(result["edition_id"], "default")
        self.assertTrue(variant.mjcf and variant.mjcf.is_file())
        self.assertEqual([edition["id"] for edition in list_mjcf_editions(variant, self.assets)], ["imported_v1_default"])

    def test_scene_prefixed_robot_names_remain_selectable_and_keep_a_valid_default(self):
        renamed = rename_mjcf_edition("astro_p2", "astro_p2_30dof_primitive_collision", "scenery", self.assets)
        duplicate = duplicate_mjcf_edition("astro_p2", renamed["edition_id"], "scene_review", self.assets)
        selected = set_default_mjcf_edition("astro_p2", duplicate["edition_id"], self.assets)
        variant = get_variant("astro_p2", self.assets)

        self.assertEqual(variant.mjcf, pathlib.Path(selected["output_path"]))
        self.assertTrue(variant.mjcf.is_file())
        self.assertIn("scene_review", {record["id"] for record in list_mjcf_editions(variant, self.assets)})
        delete_mjcf_edition("astro_p2", "scenery", self.assets)
        self.assertEqual(validate_assets(self.assets), [])

    def test_imports_generate_native_scenes_with_resolvable_meshes(self):
        import mujoco

        sources = (
            ("native_mjcf", import_mjcf_variant, ASSETS / "astro_p2/mjcf/astro_p2_30dof_primitive_collision.xml"),
            ("native_urdf", import_urdf_variant, ASSETS / "astro_p1/urdf/astro_p1_30dof.urdf"),
        )
        for name, importer, source in sources:
            with self.subTest(format=source.suffix):
                importer(name, source, self.assets)
                robot = self.assets / name
                self.assertEqual((robot / "meshes").resolve(), robot / "assets")
                for path, content in GENERATED_FILES(self.assets):
                    if path.parent == robot:
                        path.write_text(content, encoding="utf-8")
                native = mujoco.MjModel.from_xml_path(str(robot / "scene.xml"))
                original = mujoco.MjModel.from_xml_path(str(get_variant(name, self.assets).mjcf))
                self.assertEqual((native.nq, native.nv, native.nmesh), (original.nq, original.nv, original.nmesh))
                self.assertGreater(native.nmesh, 0)

    def test_scene_named_source_generates_a_separate_robot_and_scene(self):
        import mujoco

        renamed = rename_mjcf_edition("astro_p2", "astro_p2_30dof_primitive_collision", "scene", self.assets)
        source = pathlib.Path(renamed["output_path"])
        authored = source.read_bytes()
        for path, content in GENERATED_FILES(self.assets):
            path.write_text(content, encoding="utf-8")

        robot = self.assets / "astro_p2"
        self.assertTrue((robot / "model_scene.xml").is_file())
        self.assertEqual(source.read_bytes(), authored)
        self.assertGreater(mujoco.MjModel.from_xml_path(str(robot / "scene.xml")).nq, 0)

    def test_sync_rejects_source_collisions_before_writing_any_files(self):
        import json

        robot = self.assets / "astro_p2_43dof_dex3_1"
        source = robot / "scene.xml"
        source.write_bytes(get_variant("astro_p2_43dof_dex3_1", self.assets).mjcf.read_bytes())
        authored = source.read_bytes()
        manifest_path = self.assets / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["variants"][robot.name]["editions"]["43dof_primitive_collision"]["mjcf"] = source.name
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "overwrite an authoritative source"):
            for path, content in GENERATED_FILES(self.assets):
                path.write_text(content, encoding="utf-8")
        self.assertEqual(source.read_bytes(), authored)

    def test_sync_rejects_duplicate_model_outputs_before_writing_any_files(self):
        import json
        import xml.etree.ElementTree as ET

        robot = self.assets / "astro_p2"
        default = get_variant("astro_p2", self.assets).mjcf
        alternate = robot / "mjcf/review" / default.name
        alternate.parent.mkdir()
        alternate_model = ET.fromstring(default.read_bytes())
        alternate_model.set("model", "review")
        alternate.write_bytes(ET.tostring(alternate_model))
        manifest_path = self.assets / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["variants"][robot.name]["editions"]["30dof_mesh_collision"]["mjcf"] = str(alternate.relative_to(robot))
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "paths collide"):
            for path, content in GENERATED_FILES(self.assets):
                path.write_text(content, encoding="utf-8")
        self.assertEqual(default.read_bytes(), (ASSETS / "astro_p2/mjcf" / default.name).read_bytes())
