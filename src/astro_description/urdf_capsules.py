from __future__ import annotations

import argparse
import dataclasses
import xml.etree.ElementTree as ET
from pathlib import Path


class CapsuleError(ValueError):
    """Raised when capsule collision data cannot be generated."""


@dataclasses.dataclass(frozen=True)
class CapsuleCollision:
    link_name: str
    name: str
    radius: str
    fromto: str


def _mjcf_capsules_by_body(body: ET.Element, current_link: str | None = None) -> list[CapsuleCollision]:
    link_name = body.attrib.get("name", current_link)
    capsules: list[CapsuleCollision] = []
    for geom in body.findall("geom"):
        if geom.attrib.get("type") != "capsule" or "fromto" not in geom.attrib:
            continue
        if link_name is None:
            continue
        capsules.append(
            CapsuleCollision(
                link_name=link_name,
                name=geom.attrib.get("name", f"{link_name}_capsule_collision"),
                radius=geom.attrib.get("size", "0").split()[0],
                fromto=geom.attrib["fromto"],
            )
        )
    for child in body.findall("body"):
        capsules.extend(_mjcf_capsules_by_body(child, link_name))
    return capsules


def extract_capsules_from_mjcf(mjcf_path: Path) -> list[CapsuleCollision]:
    root = ET.parse(mjcf_path).getroot()
    worldbody = root.find("worldbody")
    if worldbody is None:
        raise CapsuleError(f"MJCF has no worldbody: {mjcf_path}")
    capsules: list[CapsuleCollision] = []
    for body in worldbody.findall("body"):
        capsules.extend(_mjcf_capsules_by_body(body))
    return capsules


def add_capsule_extension_collisions(urdf_text: str, capsules: list[CapsuleCollision]) -> str:
    root = ET.fromstring(urdf_text)
    links = {link.attrib.get("name"): link for link in root.findall("link")}
    missing = sorted({capsule.link_name for capsule in capsules if capsule.link_name not in links})
    if missing:
        raise CapsuleError(f"URDF is missing links for MJCF capsules: {', '.join(missing)}")

    for capsule in capsules:
        link = links[capsule.link_name]
        assert link is not None
        collision = ET.SubElement(link, "collision", {"name": capsule.name})
        geometry = ET.SubElement(collision, "geometry")
        ET.SubElement(
            geometry,
            "capsule",
            {
                "radius": capsule.radius,
                "fromto": " ".join(capsule.fromto.split()),
                "format": "astro-extension-v1",
            },
        )
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode") + "\n"


def convert_mjcf_capsules_to_urdf(urdf_path: Path, mjcf_path: Path) -> str:
    capsules = extract_capsules_from_mjcf(mjcf_path)
    if not capsules:
        raise CapsuleError(f"MJCF contains no capsule geoms with fromto: {mjcf_path}")
    return add_capsule_extension_collisions(urdf_path.read_text(encoding="utf-8"), capsules)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate an Astro URDF with extension capsule collision tags.")
    parser.add_argument("--urdf", type=Path, required=True)
    parser.add_argument("--mjcf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.write_text(convert_mjcf_capsules_to_urdf(args.urdf, args.mjcf), encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
