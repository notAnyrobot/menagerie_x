# Copyright 2026 DeepMind Technologies Limited
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

"""Layout and style checks adapted from upstream model_dir_test.py."""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from catalog import MODEL_MAP, LEGACY_MODEL_MAP, PREVIEW_OVERRIDES, model_entries
from format_xml import format_xml

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = {"astro_p1", "astro_p2", "atom_p3", "soma23", "unitree_g1"}


class ModelDirectoryTests(unittest.TestCase):
    def test_catalog_and_family_layout(self):
        entries = list(model_entries())
        self.assertEqual({entry["family"] for entry in entries}, FAMILIES)
        self.assertEqual(len(entries), 8)
        self.assertEqual(len(MODEL_MAP), 6)
        self.assertEqual(len(LEGACY_MODEL_MAP), 2)
        self.assertFalse(set(MODEL_MAP) & set(LEGACY_MODEL_MAP))
        self.assertTrue(all(key.startswith("astro_p1/") for key in LEGACY_MODEL_MAP))
        self.assertEqual({entry["family"] for entry in model_entries(include_legacy=False)}, FAMILIES - {"astro_p1"})
        self.assertTrue(set(PREVIEW_OVERRIDES).issubset(set(MODEL_MAP) | set(LEGACY_MODEL_MAP)))
        self.assertEqual(len({entry["scene"] for entry in entries}), len(entries))
        for family in FAMILIES:
            for name in ("README.md", "CHANGELOG.md", "LICENSING.md", "scene.xml"):
                self.assertTrue((ROOT / family / name).is_file(), f"{family}/{name}")
            self.assertTrue((ROOT / family / "assets").is_dir())
        for entry in entries:
            for kind in ("model", "scene"):
                self.assertEqual(entry[kind].parent, ROOT / entry["family"])
                self.assertTrue(entry[kind].is_file(), str(entry[kind]))
                for node in ET.parse(entry[kind]).iter():
                    for attribute in ("file", "meshdir", "texturedir", "assetdir"):
                        value = node.get(attribute)
                        if value is not None:
                            self.assertFalse(Path(value).is_absolute(), value)
                            self.assertNotIn("..", Path(value).parts, value)
            scene = ET.parse(entry["scene"]).getroot()
            self.assertEqual([node.get("file") for node in scene.findall("include")], [entry["model"].name])

    def test_maintained_xml_style(self):
        for entry in model_entries():
            for kind in ("model", "scene"):
                path = entry[kind]
                with self.subTest(path=str(path.relative_to(ROOT))):
                    text = path.read_text(encoding="utf-8")
                    self.assertEqual(text, format_xml(text))
