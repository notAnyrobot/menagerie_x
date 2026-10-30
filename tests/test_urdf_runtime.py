import pathlib
import unittest
import xml.etree.ElementTree as ET

from menagerie_x.assets import get_edition, get_variant, resolve_scene
from menagerie_x.workbench.urdf_runtime import prepare_urdf_runtime


ROOT = pathlib.Path(__file__).resolve().parents[1]


class UrdfRuntimeTests(unittest.TestCase):
    def test_root_level_hhtools_description_compiles_without_changing_assets(self):
        edition = get_edition("astro_p2_29dof", root=ROOT)
        authored = edition.urdf.read_bytes()
        scene = resolve_scene(get_variant("astro_p2_29dof", ROOT), ROOT).as_dict()

        runtime = prepare_urdf_runtime(edition, scene)
        try:
            self.assertEqual(edition.urdf.read_bytes(), authored)
            self.assertEqual(runtime.nq, 36)
            self.assertEqual(runtime.nv, 35)
            root = ET.parse(runtime.path).getroot()
            mesh_root = (edition.urdf.parent / "meshes").resolve()
            meshes = root.findall("asset/mesh")
            self.assertTrue(meshes)
            self.assertTrue(all(pathlib.Path(mesh.attrib["file"]).is_relative_to(mesh_root) for mesh in meshes))
        finally:
            runtime.close()

    def test_manifest_exposes_explicit_free_base_mode_for_humanoids(self):
        edition = get_edition("astro_p2", "30dof_primitive_collision", ROOT)

        self.assertEqual(edition.base_mode, "free")

    def test_preparation_keeps_authored_bytes_and_adds_runtime_world(self):
        edition = get_edition("astro_p2", "30dof_primitive_collision", ROOT)
        authored = edition.urdf.read_bytes()

        runtime = prepare_urdf_runtime(edition, {"gravity": [0, 0, -9.81], "robot_spawn": {"xyz": [0, 0, 0.75], "rpy": [0, 0, 0]}, "terrain_instances": [{"instance_id": "flat_floor", "geometry": {"type": "plane", "size": [16, 16], "thickness": 0.1}, "pose": {"xyz": [0, 0, 0], "rpy": [0, 0, 0]}, "collision": True, "appearance": {"rgba": [0, 0, 0, 1]}, "physics": {"friction": 1}}]})
        try:
            self.assertEqual(edition.urdf.read_bytes(), authored)
            self.assertTrue(runtime.path.is_file())
            root = ET.fromstring(runtime.path.read_bytes())
            self.assertEqual(root.tag, "mujoco")
            self.assertIsNotNone(root.find(".//joint[@type='free']"))
            self.assertIsNotNone(root.find(".//geom[@name='workbench_scene_flat_floor']"))
            self.assertGreater(runtime.nq, 30)
            self.assertGreater(runtime.nv, 30)
        finally:
            runtime.close()


if __name__ == "__main__":
    unittest.main()
