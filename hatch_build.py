"""Preserve relative directory links in the source distribution.

Hatch traverses directory links and suppresses repeated inodes. Restoring the
links keeps family-local mesh paths runnable without duplicating asset data.
"""
import gzip
import json
import os
from pathlib import Path
import tarfile

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class PreserveCatalogLinks(BuildHookInterface):
    def finalize(self, version, build_data, artifact_path):
        root = Path(self.root)
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        families = manifest["variants"]
        candidates = [root / family / "meshes" for family in families]
        links = {str(path.relative_to(root)): os.readlink(path) for path in candidates if path.is_symlink()}
        artifact = Path(artifact_path)
        temporary = artifact.with_suffix(artifact.suffix + ".tmp")
        try:
            with tarfile.open(artifact, "r:gz") as source:
                members = source.getmembers()
                prefix = members[0].name.split("/")[0]
                aliases = {f"{prefix}/{name}": target for name, target in links.items()}
                with temporary.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                    with tarfile.open(fileobj=compressed, mode="w") as target:
                        for member in members:
                            if any(member.name == alias or member.name.startswith(alias + "/") for alias in aliases):
                                continue
                            stream = source.extractfile(member) if member.isfile() else None
                            try:
                                target.addfile(member, stream)
                            finally:
                                if stream is not None:
                                    stream.close()
                        for alias, destination in sorted(aliases.items()):
                            member = tarfile.TarInfo(alias)
                            member.type = tarfile.SYMTYPE
                            member.linkname = destination
                            member.mode = 0o777
                            member.mtime = members[0].mtime
                            target.addfile(member)
            os.replace(temporary, artifact)
        finally:
            temporary.unlink(missing_ok=True)
