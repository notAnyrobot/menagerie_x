from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from ..assets import AssetError, Variant, get_variant


def _import_mujoco() -> Any:
    try:
        import mujoco  # type: ignore
    except ImportError as exc:
        raise AssetError("mujoco is not installed; run `uv sync` first") from exc
    return mujoco


def _checked_mjcf_path(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise AssetError(f"MJCF file does not exist: {resolved}")
    if not resolved.is_file():
        raise AssetError(f"MJCF path is not a file: {resolved}")
    if resolved.suffix.lower() != ".xml":
        raise AssetError(f"MJCF file must use the .xml extension: {resolved}")
    return resolved


def _mjcf_path(variant: Variant | None, mjcf_path: Path | None) -> Path:
    if mjcf_path is not None:
        return _checked_mjcf_path(mjcf_path)
    if variant is None:
        raise AssetError("select an MJCF variant or pass --mjcf PATH")
    if variant.mjcf is None:
        raise AssetError(f"variant {variant.name!r} does not define an MJCF asset")
    return _checked_mjcf_path(variant.mjcf)


def load_model(variant: Variant | None = None, mjcf_path: Path | None = None):
    """Load an MJCF from a declared variant or an exact XML file.

    MuJoCo's path loader keeps ``include`` and compiler-relative mesh paths
    relative to the supplied XML, which is particularly important for manual
    editions outside the packaged manifest.
    """
    path = _mjcf_path(variant, mjcf_path)
    mujoco = _import_mujoco()
    try:
        return mujoco.MjModel.from_xml_path(str(path))
    except ValueError as exc:
        try:
            root = ET.fromstring(path.read_text(encoding="utf-8"))
        except ET.ParseError as parse_error:
            raise AssetError(f"could not parse MJCF XML: {path}: {parse_error}") from exc
        compiler = root.find("compiler")
        if compiler is None:
            raise AssetError(f"could not load MJCF and no compiler element exists: {path}") from exc
        # This fallback only repairs legacy manifest descriptions that omitted
        # meshdir.  A manually supplied MJCF must retain its own relative
        # asset rules instead of being silently redirected into a variant.
        if variant is None or compiler.get("meshdir"):
            raise AssetError(f"could not load MJCF: {path}: {exc}") from exc
        compiler.set("meshdir", str(variant.meshes_dir.resolve()))
        return mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))


def check_mujoco(variant_name: str | None = None, root: Path | None = None, mjcf_path: Path | None = None) -> dict[str, int | str | None]:
    variant = None if mjcf_path is not None else get_variant(variant_name, root)
    path = _mjcf_path(variant, mjcf_path)
    model = load_model(variant, path)
    return {
        "variant": variant.name if variant else None,
        "mjcf": str(path),
        "nq": int(model.nq),
        "nv": int(model.nv),
        "nu": int(model.nu),
        "nbody": int(model.nbody),
        "ngeom": int(model.ngeom),
        "nsensor": int(model.nsensor),
    }


def launch_mujoco(variant_name: str | None = None, root: Path | None = None, seconds: float | None = None, mjcf_path: Path | None = None) -> None:
    variant = None if mjcf_path is not None else get_variant(variant_name, root)
    path = _mjcf_path(variant, mjcf_path)
    mujoco = _import_mujoco()
    try:
        import mujoco.viewer  # type: ignore
    except ImportError as exc:
        raise AssetError("mujoco.viewer is not available in this environment") from exc

    model = load_model(variant, path)
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
