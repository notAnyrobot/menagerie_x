from __future__ import annotations

import time
from pathlib import Path

from .assets import AssetError, get_asset_paths


def _import_viz_deps():
    try:
        import trimesh  # type: ignore
        import viser  # type: ignore
    except ImportError as exc:
        raise AssetError("Viser visualization dependencies are missing; run `uv sync --extra viz`") from exc
    return trimesh, viser


def launch_viser(root: Path | None = None, host: str = "127.0.0.1", port: int = 8080) -> None:
    trimesh, viser = _import_viz_deps()
    paths = get_asset_paths(root)
    server = viser.ViserServer(host=host, port=port)
    server.scene.add_grid("/ground", width=2.0, height=2.0, position=(0.0, 0.0, -0.75))
    for mesh_path in sorted(paths.meshes_dir.glob("*.stl")):
        mesh = trimesh.load_mesh(mesh_path, force="mesh")
        if not isinstance(mesh, trimesh.Trimesh):
            continue
        server.scene.add_mesh_trimesh(
            f"/astro/{mesh_path.stem}",
            mesh=mesh,
            wxyz=(1.0, 0.0, 0.0, 0.0),
            position=(0.0, 0.0, 0.0),
        )
    print(f"Viser Astro mesh viewer: http://{host}:{port}")
    try:
        while True:
            time.sleep(10.0)
    except KeyboardInterrupt:
        print("Viser Astro mesh viewer stopped")
