# MuJoCo Menagerie conventions and the Menagerie X refactor

Research date: 2026-10-30. Upstream inspected at
[`f3b6013629c7b94f8ee93fd977b161fa8350f9bc`](https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc),
committed 2026-10-23 16:08:31 -07:00. The repository landing page was also
opened through web browsing; implementation claims below use pinned source
files. A shallow, filtered checkout under `/tmp/menagerie-upstream-research/`
provided the inspected primary sources. GitHub's unauthenticated API was rate
limited, so the Git checkout supplied the commit and file inventory.

The local observations describe the starting checkout at
[`d2070956558ffbf9226dcf74017d40740724d8d8`](https://github.com/notAnyrobot/menagerie_x/tree/d2070956558ffbf9226dcf74017d40740724d8d8),
before this refactor. Recommendations are engineering judgments, distinguished
from observed upstream behavior.

## Main finding

The closest useful match is a model collection with one top-level directory
per existing local family, flat MJCF entry points, family-local `assets/`, and
explicit `scene*.xml` wrappers. Keep Menagerie X's existing edition metadata,
URDFs, Workbench, retargeting bundles, and provenance as extensions. Do not
import other upstream families or replace a local robot with Google's model
merely because its family name matches. This follows the upstream separation
between robot definitions, scene definitions, and model-local resources.
See the upstream [layout and usage description](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/README.md#overview).

## Upstream's actual organization

Each model directory ordinarily carries `assets/`, `<model>.xml`, `scene.xml`,
`README.md`, an exact `LICENSE` filename, an image, and `CHANGELOG.md`. Meshes
can serve visual or collision purposes. The robot XML describes the robot;
the scene includes it and adds its environment. Optional MJX variants use
separate model and scene entry points. The current structural tests enforce
README, LICENSE, CHANGELOG, and at least one `scene*.xml`, with a sensor
exception; they do not require an image or an assets directory for every
model. Sources: [README](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/README.md#overview),
[structural tests](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/test/model_dir_test.py).

The root also contains `catalog.py`, `build_registry.py`, `generate_gallery.py`,
`format_xml.py`, `regenerate_license.py`, `test/`, and a separate `python/`
package. Therefore “mimic upstream” should not be interpreted as removing all
Python code. Its current package downloads model archives lazily, exposes
robot and scene entry points, and can use a local checkout. A local
manifest-driven Workbench is a different distribution model; adopting release
hosting and remote caching is optional additional work, not a prerequisite
for matching model layout. Sources:
[root tree](https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc),
[package documentation](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/python/DOC.md).

`catalog.MODEL_MAP` stores `<directory>/<model-stem>` category metadata;
display names generally come from the family README. `PREVIEW_OVERRIDES`
handles families whose default scene is named differently. The registry
builder discovers compilable top-level XML files, labels scene/robot entry
points, follows file dependencies, and verifies that copied dependency
closures still compile. It derives defaults from catalog metadata and scene
includes. URDFs and unrelated authoring files are not automatically included
unless referenced by that closure or specifically retained. Sources:
[catalog.py](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/catalog.py),
[build_registry.py](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/build_registry.py).

## Representative families and model/scene separation

`unitree_g1` is particularly relevant: it has `g1.xml`,
`g1_with_hands.xml`, `g1_mjx.xml`, `g1_mjlab.xml`, `scene.xml`,
`scene_with_hands.xml`, `scene_mjx.xml`, and shared `assets/`. The default
gallery entry is the 29-DOF `g1`; the hand-equipped model is also shipped.
Thus multiple editions in one directory are compatible with upstream practice.
The README describes source derivation, default classes, a stand keyframe,
position actuators, and distinct MJX collision/tuning changes. Sources:
[G1 family tree](https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1),
[G1 README](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/README.md),
[catalog entry](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/catalog.py).

G1's model uses `meshdir="assets"`, separate visual/collision defaults, and
contains a directional light. Its scene includes the model and supplies
ground, skybox, haze, and viewing parameters. This matters: keeping robot-only
kinematics is the firm boundary, while moving every light out of the robot
is a reasonable local cleanup rather than an invariant all upstream models
already obey. Sources:
[g1.xml](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/g1.xml),
[scene.xml](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/scene.xml),
[scene_with_hands.xml](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/scene_with_hands.xml).

`unitree_go2` demonstrates the same pattern and documents its URDF-to-MJCF
derivation and separate MJX adaptation. Its historical MJX limitations should
not be treated as a current universal MuJoCo feature matrix. Copying a family
layout does not justify making those physical simplifications locally.
Source: [Go2 README](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_go2/README.md).

## Style, checks, and contributor workflow

Upstream's XML style uses two-space indentation, double quotes, `<foo/>`
empty elements, 120-character wrapping, preserved sibling blank lines, and
default classes to reduce repeated physics properties. Its Python formatter
uses two spaces, single quotes, 80 columns, conservative Ruff E/F/W/I rules,
and single-line imports. Sources:
[CONTRIBUTING](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/CONTRIBUTING.md#xml-style),
[pyproject.toml](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/pyproject.toml).

`make install` installs pre-commit and its hook. `make check` runs formatting,
lint, license aggregation, and XML checks; `make test` runs model tests;
`make all` also runs Python-package tests after deriving its registry.
The hook keeps simulation tests on its manual stage. GitHub Actions runs
model pytest and registry/package checks separately from pre-commit. Sources:
[Makefile](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/Makefile),
[hooks](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/.pre-commit-config.yaml),
[build workflow](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/.github/workflows/build.yml),
[pre-commit workflow](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/.github/workflows/pre-commit.yml).

The model test compiles every first-level family's `scene*.xml`, simulates
0.1 seconds with deterministic Halton control noise scaled to actuator
ranges, and rejects MuJoCo warnings. This is a useful structural and numerical
smoke test, not proof of long-term stability or hardware fidelity. Sources:
[model_test.py](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/test/model_test.py),
[test dependencies](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/test/requirements.txt).

Upstream asks contributors to coordinate major changes in an issue, record
model changes in family changelogs, record shared changes in the root
changelog, and sign Google's CLA for contributions to Google's project.
These are upstream contribution rules; a private/local layout refactor does
not require opening an upstream issue or adopting Google's CLA process.
Source: [CONTRIBUTING](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/CONTRIBUTING.md).

## Licensing and provenance

Upstream retains a license in each model family and generates its root
LICENSE by combining `*/LICENSE` texts with its base project license. The
registry's license detection is heuristic, so mixed-source models need more
precise provenance than a single detected label. Sources:
[license generator](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/regenerate_license.py),
[license detection](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/catalog.py),
[G1 license](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/unitree_g1/LICENSE).

Local G1 combines Unitree models/assets with ProtoMotions retargeting
references; SOMA-23 comes from ProtoMotions; Astro with Dex3-1 combines local
Astro body material and Unitree hand material. Preserve all vendor license
texts, notices, revision IDs, and source hashes. Some Astro/Atom families have
no tracked license text in the inspected checkout; do not invent a license
or describe the whole family as BSD/Apache because one dependency is.
An exact `LICENSE` index can explain scope and point to unchanged vendor
files, while clearly recording undocumented local material. If packaged file
paths change, preserve the upstream source hash and separately update the
packaged hash. Sources: starting local
[manifest](https://github.com/notAnyrobot/menagerie_x/blob/d2070956558ffbf9226dcf74017d40740724d8d8/robots/manifest.json),
[Dex3 provenance](https://github.com/notAnyrobot/menagerie_x/blob/d2070956558ffbf9226dcf74017d40740724d8d8/robots/astro_p2_43dof_dex3_1/SOURCE.json),
[G1 notice](https://github.com/notAnyrobot/menagerie_x/blob/d2070956558ffbf9226dcf74017d40740724d8d8/robots/unitree_g1/NOTICE.ProtoMotions).

## Local scope and recommended migration

The starting manifest defines exactly these seven family/workspace IDs and
12 logical editions. Retain this allowlist, defaults, IDs, and format
availability. The upstream catalog contains many other families, which are
outside this task. Source: starting local
[manifest](https://github.com/notAnyrobot/menagerie_x/blob/d2070956558ffbf9226dcf74017d40740724d8d8/robots/manifest.json).

| Existing family | Editions to preserve | Important exception |
| --- | --- | --- |
| `astro_p1` | 30dof, 27dof, with_racket | Racket edition is URDF-only; legacy configuration sources remain references. |
| `astro_p2` | 30dof primitive, mesh, primitive halfway | Preserve collision choices and reviewed MJCF provenance. |
| `astro_p2_29dof` | 29dof primitive | Canonical catalog entry is URDF-only; HHTools uses root URDF/robot.yaml. |
| `astro_p2_43dof_dex3_1` | 43dof primitive | Sample mounting remains unverified; preserve hand provenance. |
| `atom_p3` | 27dof | MJCF-only, imported model has no actuators. |
| `soma23` | free_base | MJCF-only, 66 internal DOF; retain ProtoMotions provenance. |
| `unitree_g1` | 29dof_with_hand_rev_1_0, 29dof_box_feet | Default has 43 internal joints; box-feet reference has 29. |

Recommended implementation order:

1. Move the seven directories to the repository root; use family-local
   `assets/` and flat canonical XMLs. Update mesh paths rather than changing
   mesh bytes. Preserve auxiliary URDF/retargeting files where their consumers
   require them; their existence is an intentional extension.
2. Add scene wrappers per existing MJCF edition and a default `scene.xml`
   only where a cataloged MJCF exists. Keep a URDF-only family explicit rather
   than registering an experimental XML as its newly authorized canonical
   model. Starting local G1's hand-equipped XML embeds a floor; separate that
   environment from its robot entry point and verify no duplicate floor is
   introduced when composing scenes.
3. Update root discovery, manifest paths, mesh resolution, Workbench serving,
   import/export and edition-management paths, scripts, packaging, and tests
   together. The starting loader hardcodes `robots/manifest.json` and
   `<family>/meshes`; physical moves alone are insufficient. Sources:
   [asset loader](https://github.com/notAnyrobot/menagerie_x/blob/d2070956558ffbf9226dcf74017d40740724d8d8/src/menagerie_x/assets/__init__.py),
   [native loader](https://github.com/notAnyrobot/menagerie_x/blob/d2070956558ffbf9226dcf74017d40740724d8d8/src/menagerie_x/commands/mujoco.py),
   [existing layout assertions](https://github.com/notAnyrobot/menagerie_x/blob/d2070956558ffbf9226dcf74017d40740724d8d8/tests/test_description_package.py).
4. Add family READMEs, changelogs, precise license indexes, root catalog
   documentation, and developer checks following upstream's model collection
   workflow. Keep Menagerie X identity and provenance. Adding a root catalog
   module is useful if it derives from one authoritative metadata source;
   duplicating edition/default metadata in two hand-maintained catalogs is a
   drift risk.
5. Validate the unchanged seven-family/12-edition inventory, all supported
   URDF asset references, model/scene compilation, scene simulation warnings,
   and Workbench behavior. Compare robot joint order, limits, masses, inertias,
   actuators, and collision geometry before/after so layout changes cannot
   silently replace a physical model. Existing local tests already cover
   provenance, cross-format/export behavior, import, and Workbench contracts:
   [tests](https://github.com/notAnyrobot/menagerie_x/tree/d2070956558ffbf9226dcf74017d40740724d8d8/tests).

Do not mass-refactor robot physics into new default classes or add actuators
solely to look like an upstream example: those edits require separate model
validation. Remote release archives, caching, automatic publishing, new MJX
models, and Google CLA infrastructure are additional product decisions.

## Alternative: copy upstream and prune

The user's proposed shortcut is reasonable as a source of scaffold files.
A literal replacement checkout is more work than selective import because
the existing `src/menagerie_x` CLI and Workbench must remain, local family
content differs from upstream G1, and several local families have no upstream
equivalent. Preserve the current Git repository/history; import selected
upstream files from the pinned checkout and adapt them around the local
catalog. Copying the repository does not require importing every model or
replicating Google's release service. This is a recommendation based on the
dependencies and discovery rules in the inspected
[Makefile](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/Makefile),
[catalog](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/catalog.py),
and [registry builder](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/build_registry.py).

| Upstream scaffold | Recommended treatment |
| --- | --- |
| `format_xml.py` | Copy with original copyright/license header; its inline dependency is `lxml`. Apply selectively to authored XMLs, preserving imported-file provenance and tracking intentional byte changes. |
| `test/model_test.py` | Adapt the 0.1-second no-warning scene smoke test to explicit local catalog entries; integrate into existing `tests/`. |
| `test/model_dir_test.py` | Adapt required-document/scene checks to the seven-family allowlist, with a documented URDF-only exception. Do not discover experimental XMLs accidentally. |
| `Makefile`, `.pre-commit-config.yaml` | Adapt targets and checks to the existing uv project, Python tests, and Workbench JavaScript tests. Avoid a repository-wide reformat of unrelated code merely to enable a hook. |
| `catalog.py` | Retain the small API shape if useful, replacing Google's model map with locally derived metadata; avoid two independent default/edition registries. |
| `generate_gallery.py` | Optional renderer, after adapting camera/keyframe maps and inventory to local models. Its global render dependencies and root `assets/` images are extra work. |
| `regenerate_license.py` | Reuse only after defining accurate family license scope and retaining Apache attribution for copied tools. The existing script assumes a base license already exists. |
| Root `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md` | Use as document structure, writing Menagerie X-specific content and preserving its CLI/Workbench instructions. |
| Root `pyproject.toml`, `.gitignore` | Merge selected tool settings only. Preserve the local project's dependency/build metadata and lockfile; upstream ignores `uv.lock`. |
| `build_registry.py`, `python/`, release workflow | Defer unless downloadable model distributions are requested. The builder imports upstream package internals, relies on Git tree IDs, and only retains dependency closures plus selected docs/patches. It does not replace local URDF/edition/provenance management. |
| Upstream model directories and gallery images | Do not copy unrelated families. Reorganize the existing seven local families instead. |

Sources for additional scaffold details:
[formatter](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/format_xml.py),
[gallery generator](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/generate_gallery.py),
[gitignore](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/.gitignore),
[license generator](https://github.com/google-deepmind/mujoco_menagerie/blob/f3b6013629c7b94f8ee93fd977b161fa8350f9bc/regenerate_license.py).

The sparse checkout available for inspection is
`/tmp/menagerie-upstream-research/checkout`; it contains the root scaffold,
`.github/`, `test/`, `python/`, and representative G1/Go2 families. This report
does not authorize or initiate publication, upstream contributions, or a new
release service.

## Limits and uncertainty

This investigation inspected source and representative files; it did not
execute the entire upstream collection's simulation suite or establish local
hardware fidelity. The API failure did not prevent source inspection. The
upstream SHA is fixed; later upstream changes are outside these conclusions.
The local checkout also contains untracked experimental floating-MJCF files,
retargeting output, and local runtime material; these are not additional
catalog families or permission to discard user work. Keep them separate from
canonical entry-point discovery and preserve them when moving directories.
Undocumented local licensing remains undocumented after a layout refactor;
convention matching cannot resolve missing provenance.
