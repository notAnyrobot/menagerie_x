# Upstream scaffold

Menagerie X follows the native asset organization of
[google-deepmind/mujoco_menagerie](https://github.com/google-deepmind/mujoco_menagerie/tree/f3b6013629c7b94f8ee93fd977b161fa8350f9bc),
pinned at `f3b6013629c7b94f8ee93fd977b161fa8350f9bc` (2026-10-23).
The current-repository refactor keeps Menagerie X's Git history and existing
assets rather than replacing the repository with an upstream fork.

| Local file | Upstream source and treatment |
| --- | --- |
| `format_xml.py` | Copied unchanged; Apache-2.0 copyright retained. |
| `catalog.py` | Adapted root `MODEL_MAP` and preview overrides, pruned to local native models; independent of the legacy application manifest. |
| `test/model_test.py`, `test/model_dir_test.py` | Adapt upstream native control/no-warning and layout checks to unittest and the retained local inventory. Apache-2.0 headers retained. |
| Family `scene*.xml` | Presentation structure adapted from `unitree_g1/scene.xml`, using local model references, names, and ground heights. Upstream G1 license retained in `LICENSES/MuJoCo-Menagerie-G1.txt`. |
| `unitree_g1/g1_mjx.xml`, `unitree_g1/scene_mjx.xml` | Copied from the pinned upstream G1 family, retaining its 27 primitive colliders, 49 scene contact pairs, controls, sensors and keyframes. Actual notice in `unitree_g1/LICENSE.Menagerie`; hashes in the family provenance record. Native execution is verified; MJX runtime support is deferred. |
| `Makefile`, `.pre-commit-config.yaml`, `.github/workflows/build.yml` | Adapt upstream development and native validation patterns; browser compatibility is deferred. |
| Family README/changelog and root docs | Follow upstream organization using local inventory, notices, and provenance. |

Apache-2.0 terms for copied/adapted Python tools remain in
[LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt). Asset-specific notices remain
with each family; see [LICENSING.md](LICENSING.md).

## Native ownership and preservation

- The active collection has eight models across four families. Astro P1's two
  models are retained in `LEGACY_MODEL_MAP` and receive native checks until
  later retirement; they are excluded from the active gallery.
- Astro P2 is one family with three native model/scene pairs, like upstream G1:
  the default fixed-head 29-joint Astro P2, and the same refined body with
  14 additional Dex3-1 finger joints, plus an arm-optimized default-hand collision
  configuration. The old three 30-DoF P2 choices are retired.
- Its additional arm-optimized model retains every default non-arm collider,
  including pelvis, legs, feet, torso and head, and all visual meshes. Only arm
  and hand collision shapes are reduced. Its hybrid policy preserves automatic
  non-arm contacts and explicitly selects optimized-arm interactions. It does
  not copy G1's servos or solver tuning, and does not claim MJX runtime
  compatibility. Existing Astro models/scenes/assets remain byte-identical.
- The rubber model restores the original Astro hand meshes, fixed-joint frames,
  hand masses/inertias, and capsule collision envelopes. The G1 hand trial was
  rejected for fit; its source evidence is retained separately. The refined
  Astro body and Dex3-1 variant remain unchanged. See the
  [restoration record](docs/astro-native-hand-restoration.md).
- Family-root XML is canonical and directly maintained, with actual local
  assets. No generator overwrites native edits. Astro conversion/refinement
  originals and records are preserved byte-for-byte under `astro_p2/provenance/`;
  its migration receipt identifies old paths and hashes. The native Dex model
  retains its dynamics, finger definitions, and `fist` keyframe.
  Its public label is Astro P2 with hands; the 16 hand visual geoms now use
  silver coloring, without changing mesh bytes or physics.
- All non-hand Astro body properties are shared between the two variants. Source
  frames are retained; both scenes use one floor at `z=-0.75`. Atom, SOMA, G1,
  and retained P1 physical assets are unchanged by Astro consolidation.
- The local G1 source snapshot contains a demonstration floor; its canonical
  root model omits it and its scene supplies one. Its local descriptions remain
  distinct from upstream Menagerie's G1 tuning/keyframes.
- The additional G1 primitive model preserves the upstream MJX configuration as
  a separate native pair. Its robot masks disable automatic contacts;
  `scene_mjx.xml` supplies the explicit floor/self-contact pairs and saved poses.
  Existing G1 source descriptions and runtime models are retained unchanged.
- No `family.json`, revision/promotion framework, or application adapter is
  introduced. Native MuJoCo loads a copied family without global metadata.
- Astro P2 body/default-model material is released under Apache-2.0, as directed
  by the maintainer. Unitree and ProtoMotions material retains its own notices.
  Legacy P1 and Atom keep their existing licensing records.

## Deferred compatibility and omitted upstream machinery

Workbench, URDF compatibility, and MJX are deferred. Application metadata now
lists the five retained families and two native Astro editions; retained Astro
URDFs describe earlier geometry and are not advertised as current equivalents.
Legacy authoring scripts and tests may refer to retired layouts. Historical
experiments were archived under local `.local/archives/` storage and are excluded
from source archives. Browser includes, initialization, and collision editing have
known gaps in the
[compatibility investigation](docs/research/mujoco-workbench-compatibility.md).

The stale `robots/` compatibility directory has been retired; use family paths
at the repository root. The family-local `meshes/` aliases, URDFs, conversion
scripts, and application code remain available. `hatch_build.py` retains the
relative mesh aliases in source archives; wheels retain the code-only
packaging policy. The upstream download package, generated remote registry,
unrelated gallery assets, and release workflows are omitted. Native `make all` is the acceptance gate.

See the [accepted scope](docs/adr/0011-upstream-asset-structure-first.md),
[Astro consolidation scope](docs/design/astro-p2-variants.md), and
[research report](docs/research/mujoco-upstream-contract.md).
