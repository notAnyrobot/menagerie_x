"""Maintain flat Menagerie model/scene entry points without editing source assets.

Default invocation writes generated files; --check reports drift without writing.
Legacy URDF/MJCF files, their hashes, and retargeting bundles stay authoritative.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from catalog import model_entries
from format_xml import format_xml


def _render_entrypoints(entries):
    for entry in entries:
        source, model = entry["source"], entry["model"]
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        robot = ET.fromstring(source.read_bytes(), parser=parser)
        if source != model:
            compiler = robot.find("compiler")
            if compiler is None:
                compiler = ET.SubElement(robot, "compiler")
            compiler.set("meshdir", "assets")
            # Some vendor snapshots include their demonstration floor. Only
            # root-level planes are environment; robot bodies stay intact.
            for world in robot.findall("worldbody"):
                for geom in list(world.findall("geom")):
                    if geom.get("type") == "plane":
                        world.remove(geom)
            ET.indent(robot, space="  ")
            yield model, format_xml(ET.tostring(robot, encoding="unicode"))
        bodies = [body for world in robot.findall("worldbody") for body in world.findall("body")]
        initial_z = float(bodies[0].get("pos", "0 0 0").split()[2]) if bodies else 0.0
        # Keep the source robot datum unchanged. Put the presentation floor
        # one configured standing height below that datum instead.
        floor_z = initial_z - entry["spawn_z"]
        scene = f'''<mujoco model="{entry['family']} {entry['edition']} scene">
  <include file="{model.name}"/>

  <visual>
    <headlight diffuse="0.6 0.6 0.6" ambient="0.1 0.1 0.1" specular="0.9 0.9 0.9"/>
    <rgba haze="0.15 0.25 0.35 1"/>
    <global azimuth="140" elevation="-20"/>
  </visual>

  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>
    <texture type="2d" name="menagerie_ground" builtin="checker" rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3"
      width="300" height="300"/>
    <material name="menagerie_ground" texture="menagerie_ground" texuniform="true" texrepeat="5 5" reflectance="0.2"/>
  </asset>

  <worldbody>
    <light name="menagerie_light" pos="0 0 3" dir="0 0 -1" directional="true"/>
    <geom name="menagerie_floor" pos="0 0 {floor_z:.9g}" size="0 0 0.05" type="plane" material="menagerie_ground"/>
  </worldbody>
</mujoco>
'''
        yield entry["scene"], format_xml(scene)


def generated_files(root=ROOT):
    """Validate the entire output plan before yielding anything writable."""
    entries = list(model_entries(root))
    sources = {entry["source"].resolve() for entry in entries}
    outputs = {}
    for path, content in _render_entrypoints(entries):
        resolved = path.resolve()
        if resolved in sources:
            raise ValueError(f"generated entrypoint would overwrite an authoritative source: {path}")
        if resolved in outputs and outputs[resolved][1] != content:
            raise ValueError(f"generated model and scene paths collide: {path}")
        outputs[resolved] = (path, content)
    yield from outputs.values()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        outputs = list(generated_files())
    except ValueError as exc:
        print(f"Cannot sync native entrypoints: {exc}", file=sys.stderr)
        return 1
    drift = []
    for path, content in outputs:
        if path.is_file() and path.read_text(encoding="utf-8") == content:
            continue
        if args.check:
            drift.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(content, encoding="utf-8")
    if drift:
        print("Generated entry points need syncing: " + ", ".join(drift), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
