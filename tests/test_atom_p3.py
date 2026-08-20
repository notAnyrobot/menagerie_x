"""Regression checks for the packaged MJCF-only Atom P3 description."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from menagerie_x.assets import get_variant, inspect_variant, load_manifest, resolve_scene, validate_assets
from menagerie_x.assets.editions import import_mjcf_variant
from menagerie_x.cli import main as cli_main
from menagerie_x.commands.mujoco import check_mujoco


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "menagerie_x" / "assets"
ATOM = ASSETS / "atom_p3"
MJCF = ATOM / "mjcf" / "atom_p3_27dof.xml"
SHA256 = "f8d27bb5d9002bb3899136a407b9492f63762ec0f1d71508fd9005abfc2c48cd"


class AtomP3CatalogTests(unittest.TestCase):
    def test_manifest_keeps_the_authorized_internal_mjcf_provenance(self) -> None:
        entry = load_manifest(ASSETS)["variants"]["atom_p3"]

        edition = entry["editions"]["27dof"]
        self.assertEqual(edition["urdf"], None)
        self.assertEqual(edition["source_provenance"]["kind"], "internal")
        self.assertEqual(edition["source_provenance"]["sha256"], SHA256)
        self.assertEqual(edition["mjcf_provenance"]["mujoco_version"], "3.11.0")
        self.assertTrue(edition["mjcf_provenance"]["authorized_at"].endswith("+00:00"))

    def test_mjcf_only_variant_is_inspectable_and_cli_uses_json_null(self) -> None:
        variant = get_variant("atom_p3", ASSETS)
        inspection = inspect_variant(variant)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            cli_main(["--root", str(ROOT), "variants"])

        self.assertIsNone(variant.urdf)
        self.assertIsNone(inspection.description)
        self.assertTrue(any(issue.code == "urdf-unavailable" and issue.severity == "info" for issue in inspection.issues))
        self.assertIsNone(json.loads(output.getvalue())["atom_p3"]["urdf"])

    def test_bundle_is_closed_over_referenced_meshes_and_keeps_all_expanded_assets(self) -> None:
        mesh_files = {path.name for path in (ATOM / "meshes").iterdir() if path.is_file() and path.suffix.lower() == ".stl"}
        root = ET.parse(MJCF).getroot()
        referenced = {mesh.get("file") for mesh in root.findall(".//asset/mesh") if mesh.get("file")}

        self.assertEqual(len(mesh_files), 56)
        self.assertTrue(referenced <= mesh_files)
        self.assertEqual(len(mesh_files - referenced), 26)
        self.assertEqual(hashlib.sha256(MJCF.read_bytes()).hexdigest(), SHA256)
        self.assertFalse((ASSETS / "atom_p3.zip").exists())

    def test_mujoco_model_dimensions_and_scene_spawn(self) -> None:
        variant = get_variant("atom_p3", ASSETS)
        result = check_mujoco("atom_p3", ASSETS)

        self.assertEqual(resolve_scene(variant, ASSETS).robot_spawn["xyz"], [0.0, 0.0, 0.98])
        self.assertEqual(
            {key: result[key] for key in ("nq", "nv", "nu", "nbody", "ngeom", "nsensor")},
            {"nq": 34, "nv": 33, "nu": 0, "nbody": 31, "ngeom": 68, "nsensor": 87},
        )

    def test_generic_mjcf_import_has_no_placeholder_urdf_and_validates_uppercase_stl(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            assets = Path(directory) / "assets"
            shutil.copytree(ASSETS, assets)
            import_mjcf_variant("external_atom", MJCF, assets)
            uppercase_empty = assets / "atom_p3" / "meshes" / "empty.STL"
            uppercase_empty.write_bytes(b"")

            self.assertFalse((assets / "external_atom" / "urdf").exists())
            self.assertIn(f"empty mesh file: {uppercase_empty}", validate_assets(assets))


if __name__ == "__main__":
    unittest.main()
