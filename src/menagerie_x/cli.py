from __future__ import annotations

import argparse
import json
from pathlib import Path

from .assets import AssetError, get_asset_paths, load_manifest, validate_assets, variants
from .commands.mujoco import check_mujoco, launch_mujoco
from .commands.mjcf import MjcfCandidateError, authorize_candidate, convert_variant_to_candidate
from .commands.urdf_capsules import CapsuleError, convert_mjcf_capsules_to_urdf
from .commands.viser import launch_viser
from .tools import calc_heights, pd_params_tool
from .workbench import main as workbench_main


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="menagerie_x", description="Robot-description asset and workbench tools")
    parser.add_argument("--root", type=Path, default=None, help="Menagerie checkout or asset root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("manifest", help="Print the robot-description manifest")
    subparsers.add_parser("variants", help="List known URDF/MJCF variants")
    subparsers.add_parser("validate", help="Validate manifest, asset paths, and mesh files")

    mujoco_parser = subparsers.add_parser("mujoco", help="Launch or check a manifest MJCF or exact MJCF XML file")
    mujoco_target = mujoco_parser.add_mutually_exclusive_group()
    mujoco_target.add_argument("--variant", default=None, help="Manifest variant (defaults to the manifest default variant)")
    mujoco_target.add_argument("--mjcf", type=Path, default=None, help="Exact existing .xml file to load")
    mujoco_parser.add_argument("--check", action="store_true", help="Load the model and print dimensions without opening a viewer")
    mujoco_parser.add_argument("--seconds", type=float, default=None, help="Close passive viewer after this many seconds")

    mjcf_parser = subparsers.add_parser("mjcf", help="Generate and explicitly authorize MJCF candidates")
    mjcf_subparsers = mjcf_parser.add_subparsers(dest="mjcf_command", required=True)
    mjcf_convert = mjcf_subparsers.add_parser("convert", help="Convert one URDF variant into an unregistered MJCF candidate")
    mjcf_convert.add_argument("--source", required=True, help="Manifest variant to convert")
    mjcf_convert.add_argument("--candidate-id", required=True, help="Human-reviewable candidate identifier")
    mjcf_convert.add_argument("--output", required=True, type=Path, help="New .xml file for the review candidate")
    mjcf_authorize = mjcf_subparsers.add_parser("authorize", help="Install a reviewed candidate for one declared manifest variant")
    mjcf_authorize.add_argument("--candidate", required=True, type=Path)
    mjcf_authorize.add_argument("--target", required=True, help="Existing manifest variant without MJCF")

    viser_parser = subparsers.add_parser("viser", help="Launch a Viser mesh browser")
    viser_parser.add_argument("--host", default="127.0.0.1")
    viser_parser.add_argument("--port", type=int, default=8080)

    workbench_parser = subparsers.add_parser("workbench", help="Launch the browser robot asset workbench")
    workbench_parser.add_argument("--host", default="127.0.0.1")
    workbench_parser.add_argument("--port", type=int, default=8000, help="Stable local port for browser-refresh-friendly restarts")
    workbench_browser_mode = workbench_parser.add_mutually_exclusive_group()
    workbench_browser_mode.add_argument(
        "--open-browser",
        action="store_true",
        help="Open the workbench URL in a browser after starting (off by default).",
    )
    workbench_browser_mode.add_argument("--no-browser", action="store_true", help=argparse.SUPPRESS)

    capsules_parser = subparsers.add_parser("urdf-capsules", help="Generate URDF extension capsule collisions from MJCF capsules")
    capsules_parser.add_argument("--urdf", type=Path, default=None)
    capsules_parser.add_argument("--mjcf", type=Path, default=None)
    capsules_parser.add_argument("--output", type=Path, required=True)

    heights_parser = subparsers.add_parser("heights", help="Compute keyframe body heights from the packaged MJCF")
    heights_parser.add_argument("--config", default="knees_bent", choices=("home", "zero", "knees_bent", "t_pose"))

    pd_parser = subparsers.add_parser("pd-tool", help="Launch the browser PD-parameter editor")
    pd_parser.add_argument("--doc", type=Path, default=Path("docs/robots/astro.md"))
    pd_parser.add_argument("--host", default="127.0.0.1")
    pd_parser.add_argument("--port", type=int, default=0)
    pd_parser.add_argument("--no-browser", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "manifest":
            _print_json(load_manifest(args.root))
        elif args.command == "variants":
            _print_json(
                {
                    name: {
                        "dof": variant.dof,
                        "urdf": str(variant.urdf) if variant.urdf else None,
                        "mjcf": str(variant.mjcf) if variant.mjcf else None,
                        "status": variant.status,
                    }
                    for name, variant in variants(args.root).items()
                }
            )
        elif args.command == "validate":
            errors = validate_assets(args.root)
            if errors:
                for error in errors:
                    print(error)
                raise SystemExit(1)
            print("Menagerie assets are valid")
        elif args.command == "mujoco":
            if args.check:
                _print_json(check_mujoco(args.variant, args.root, args.mjcf))
            else:
                launch_mujoco(args.variant, args.root, args.seconds, args.mjcf)
        elif args.command == "mjcf":
            if args.mjcf_command == "convert":
                _print_json(convert_variant_to_candidate(args.source, args.candidate_id, args.output, args.root))
            else:
                _print_json(authorize_candidate(args.candidate, args.target, args.root))
        elif args.command == "viser":
            launch_viser(args.root, args.host, args.port)
        elif args.command == "workbench":
            workbench_args = ["--host", args.host, "--port", str(args.port)]
            if args.root is not None:
                workbench_args.extend(["--root", str(args.root)])
            if args.open_browser:
                workbench_args.append("--open-browser")
            raise SystemExit(workbench_main(workbench_args))
        elif args.command == "urdf-capsules":
            paths = get_asset_paths(args.root)
            urdf_path = args.urdf or paths.urdf_dir / "astro_p1_30dof.urdf"
            mjcf_path = args.mjcf or paths.mjcf_dir / "astro_p1_30dof.xml"
            args.output.write_text(convert_mjcf_capsules_to_urdf(urdf_path, mjcf_path), encoding="utf-8")
            print(f"wrote {args.output}")
        elif args.command == "heights":
            config = calc_heights.create_astro_embodiment_config(args.root)
            result = calc_heights.compute_keyframe_heights(config, args.config, render=False)
            _print_json(calc_heights.result_to_json(result))
        elif args.command == "pd-tool":
            pd_args = ["--doc", str(args.doc), "--host", args.host, "--port", str(args.port)]
            if args.no_browser:
                pd_args.append("--no-browser")
            raise SystemExit(pd_params_tool.main(pd_args))
    except (AssetError, CapsuleError, MjcfCandidateError) as exc:
        parser.exit(2, f"menagerie_x: error: {exc}\n")


if __name__ == "__main__":
    main()
