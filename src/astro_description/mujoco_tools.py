from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .assets import AssetError, Variant, get_asset_paths, get_variant


def _import_mujoco() -> Any:
    try:
        import mujoco  # type: ignore
    except ImportError as exc:
        raise AssetError("mujoco is not installed; run `uv sync` first") from exc
    return mujoco


def load_model(variant: Variant):
    mujoco = _import_mujoco()
    if variant.mjcf is None:
        raise AssetError(f"variant {variant.name!r} does not define an MJCF asset")
    try:
        return mujoco.MjModel.from_xml_path(str(variant.mjcf))
    except ValueError as exc:
        paths = get_asset_paths(variant.mjcf.parents[1])
        root = ET.fromstring(variant.mjcf.read_text(encoding="utf-8"))
        compiler = root.find("compiler")
        if compiler is None:
            raise AssetError(f"could not load MJCF and no compiler element exists: {variant.mjcf}") from exc
        compiler.set("meshdir", str(paths.meshes_dir.resolve()))
        return mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))


def check_mujoco(variant_name: str | None = None, root: Path | None = None) -> dict[str, int | str]:
    variant = get_variant(variant_name, root)
    model = load_model(variant)
    return {
        "variant": variant.name,
        "nq": int(model.nq),
        "nv": int(model.nv),
        "nbody": int(model.nbody),
        "ngeom": int(model.ngeom),
    }


def launch_mujoco(variant_name: str | None = None, root: Path | None = None, seconds: float | None = None) -> None:
    mujoco = _import_mujoco()
    try:
        import mujoco.viewer  # type: ignore
    except ImportError as exc:
        raise AssetError("mujoco.viewer is not available in this environment") from exc

    variant = get_variant(variant_name, root)
    model = load_model(variant)
    data = mujoco.MjData(model)
    if seconds is None:
        mujoco.viewer.launch(model, data)
        return

    with mujoco.viewer.launch_passive(model, data) as viewer:
        deadline = time.time() + seconds
        while viewer.is_running() and time.time() < deadline:
            mujoco.mj_step(model, data)
            viewer.sync()
            time.sleep(model.opt.timestep)
