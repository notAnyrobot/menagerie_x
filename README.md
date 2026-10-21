# Menagerie X — HHTools robot library

The `hhtools` branch is a robot-asset library for HHTools WebUI, CLI and MCP.
It tracks only **Astro P2 29 DOF**, with head yaw fixed at zero. The main branch
contains the multi-robot catalog and Workbench application.

```text
robots/
└── astro_p2_29dof/
    ├── robot.yaml
    ├── astro_p2_29dof.urdf
    ├── meshes/
    └── SOURCE.json
scripts/
└── hhtools-env.sh
```

This is the canonical, self-contained robot edition: edit it directly and
commit reviewed changes. Exactly one URDF, its referenced meshes, and the
HHTools preset live together. No generation, symlink, or export step is needed.
HHTools remains a separate upstream checkout; this branch has no Python app
or dependency environment of its own.

## Use on each device

In Bash, source the script from any working directory:

```bash
source /path/to/menagerie_x/scripts/hhtools-env.sh
cd /path/to/human-humanoid-tools
uv run hhtools robot list
uv run hhtools robot validate astro_p2_29dof
uv run hhtools web
```

The script calculates this checkout's location and sets `HHTOOLS_ROBOT_DIR`
to its `robots` directory. It does not install dependencies or modify shell
startup files. On another device, clone this branch and source its local copy.
Commands run in the HHTools environment, not the old Menagerie X environment.

For one command without changing your shell:

```bash
/path/to/menagerie_x/scripts/hhtools-env.sh \
  /path/to/human-humanoid-tools/.venv/bin/hhtools robot list
```

An existing `HHTOOLS_ROBOT_PATH` still takes precedence on WebUI/CLI name
collisions; avoid another preset named `astro_p2_29dof` there. That variable
does not add an allowlisted robot root to the current MCP Agent.

## MCP setup

MCP runs its own runtime and must receive the same robot-library environment.
Sourcing this script in a terminal does not change an already running MCP
process. Configure Codex to execute the wrapper, using absolute paths for
the local device, for example:

```toml
[mcp_servers.hhtools]
command = "/path/to/menagerie_x/scripts/hhtools-env.sh"
args = [
  "/path/to/human-humanoid-tools/.venv/bin/hhtools-mcp",
  "--source", "/path/to/existing/motion-library",
  "--save-dir", "/path/to/menagerie_x/.local/agent/save",
  "--cache", "/path/to/menagerie_x/.local/agent/cache",
  "--job-settings", "/path/to/menagerie_x/.local/agent/job-settings.json",
  "--web-ui-url", "http://127.0.0.1:8010",
]
cwd = "/path/to/human-humanoid-tools"
enabled = true
startup_timeout_sec = 60
tool_timeout_sec = 120
```

Replace every example path before using this configuration. The source must
exist: the current catalog resolves all configured roots, even for robot-only
queries. Install HHTools' MCP and retargeting dependencies in its checkout.
Reconnect the MCP server after configuration changes. Verify that
`list_robots` includes `astro_p2_29dof`, then that `list_available_assets` under
`robot-library` advertises this directory before registering it.

`--web-ui-url` is a fallback link, not the address MCP connects to. One runtime
owns a given save directory; do not start WebUI and MCP with the same save
directory concurrently.

## Official HHTools robots

Yes: the current installer supports Unitree G1, ROBOTO_ORIGIN, AgiBot X2,
Asimov 1, Fourier GR-2 and Berkeley Humanoid Lite. They use the same bundle
format. With the environment above, install them **into the same library**
from the HHTools checkout:

```bash
uv run python scripts/install_builtin_robots.py \
  --destination "$HHTOOLS_ROBOT_DIR"
```

For just G1, append `--only g1_29dof`. This downloads upstream assets and
requires network access. No official robots are downloaded by the environment
script. Existing robots under the default `~/.config/hhtools/robots` are not
automatically merged when `HHTOOLS_ROBOT_DIR` is overridden.

Downloaded official-robot directories are Git-ignored, so this branch continues
to track only Astro. WebUI/CLI and MCP can discover the additional installed
bundles from this same root. Review their calibration separately.

## Calibration and dataset runs

The 29-joint order is pinned in `robot.yaml`. The fixed `head_joint` is excluded
from exported joint coordinates and the head IK target is omitted. Head mass,
inertia, visuals and collision remain in the URDF.

No reference calibration or motion-quality approval is bundled. Calibrate
Astro for each input reference family, then review short representative clips
before full dataset processing. HHTools may save calibration in the robot
directory or under `robots/.calibration-overlays/astro_p2_29dof/`; both locations
are tracked for Astro. Do not calibrate the same preset on two devices at once.
Commit calibration before switching devices.

The current HHTools loader may normalize the source URDF in place. Review
asset diffs after loading before committing them. Registered bundle content is
hash-bound; after changing it, register and inspect the updated bundle and
perform a new preflight.

Keep large motion datasets, exports and caches outside Git, for example under
`.local/` or external storage. Record the HHTools revision, this repository's
revision, dataset version, reference family and command parameters for each run.
