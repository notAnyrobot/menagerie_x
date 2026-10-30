"""Copy catalog assets into an isolated writable fixture, excluding tooling."""
import json
from pathlib import Path
import shutil


def copy_catalog(source: Path, destination: Path) -> Path:
    destination.mkdir()
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    shutil.copyfile(source / "manifest.json", destination / "manifest.json")
    for name in (*manifest["variants"], "scenes", "terrains"):
        shutil.copytree(source / name, destination / name, symlinks=True)
    return destination
