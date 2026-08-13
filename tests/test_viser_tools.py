import pathlib
import unittest
from unittest import mock

from menagerie_x.commands.viser import launch_viser


ROOT = pathlib.Path(__file__).resolve().parents[1]
ROBOT_ROOT = ROOT / "src" / "menagerie_x" / "assets" / "astro_v1"


class ViserLaunchTests(unittest.TestCase):
    def test_launch_viser_uses_current_add_mesh_trimesh_signature(self):
        class FakeScene:
            def __init__(self):
                self.mesh_calls = []

            def add_grid(self, *args, **kwargs):
                return None

            def add_mesh_trimesh(self, *args, **kwargs):
                self.mesh_calls.append((args, kwargs))
                if "color" in kwargs:
                    raise AssertionError("add_mesh_trimesh does not accept color")

        class FakeServer:
            scene = FakeScene()

        class FakeMesh:
            pass

        fake_trimesh = mock.Mock()
        fake_trimesh.Trimesh = FakeMesh
        fake_trimesh.load_mesh.return_value = FakeMesh()
        fake_viser = mock.Mock()
        fake_viser.ViserServer.return_value = FakeServer()

        with (
            mock.patch("menagerie_x.commands.viser._import_viz_deps", return_value=(fake_trimesh, fake_viser)),
            mock.patch("menagerie_x.commands.viser.time.sleep", side_effect=KeyboardInterrupt),
        ):
            launch_viser(ROBOT_ROOT, port=42178)

        self.assertGreater(len(FakeServer.scene.mesh_calls), 1)


if __name__ == "__main__":
    unittest.main()
