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
| `Makefile`, `.pre-commit-config.yaml`, `.github/workflows/build.yml` | Adapt upstream development and native validation patterns; browser compatibility is deferred. |
| Family README/changelog and root docs | Follow upstream organization using local inventory, notices, and provenance. |

Apache-2.0 terms for copied/adapted Python tools remain in
[LICENSES/Apache-2.0.txt](LICENSES/Apache-2.0.txt). Asset-specific notices remain
with each family; see [LICENSING.md](LICENSING.md).

## Native ownership and preservation

- The same seven robot families remain. Eleven already existing robot MJCFs are
  now explicit native entries, including the separately maintained Astro 29
  conversion. No upstream robot or physical model replaces a local one.
- Family-root XML is canonical and directly maintained. The former
  `scripts/sync-menagerie.py` generator is retired, so native edits cannot be
  overwritten by synchronizing old snapshots. Nested `mjcf/` files are retained
  byte-for-byte as source evidence and for legacy consumers. Every existing
  tracked model, mesh, source record, and license notice is unchanged by this
  simplified migration.
- `assets/` stores actual meshes. The original Astro 29 and Dex3-1 HHTools XMLs
  retain their original formatting and `meshes/` paths, with a local relative
  `meshes -> assets` alias. Their recorded hashes remain valid. Other native
  models already reference `assets/` directly.
- Source robot frames, options, contacts, keyframes, sensors, and actuators stay
  unchanged. Scenes add one floor and lighting. Existing floors retain their
  established offsets; Astro 29's new scene uses `z=-0.75`, matching its retained
  standing-height convention and preserving the zero-height robot datum.
- The local G1 source snapshot contains a demonstration floor; its canonical
  root model already omits that plane and the scene supplies one. Upstream G1
  and Booster T1 were organizational references, not sources for local physics.
- No `family.json`, revision/promotion framework, or application adapter is
  introduced. Native MuJoCo loads each family without application metadata.
- Actual license notices and explicit `LICENSING.md` records are kept where
  redistribution terms remain unresolved; no license grant is invented.

## Deferred compatibility and omitted upstream machinery

Workbench, URDF compatibility, and MJX are deferred. The preserved manifest
still describes 12 legacy application editions, including Astro 29 as URDF-only.
CLI/Workbench paths may select source snapshots; their saved edits are not
synchronized into canonical native XML. Includes, initialization, and browser
collision editing have documented gaps in the
[compatibility investigation](docs/research/mujoco-workbench-compatibility.md).

The stale `robots/` compatibility directory has been retired; use family paths
at the repository root. The family-local `meshes/` aliases, URDFs, conversion
scripts, and application code remain available. `hatch_build.py` retains the
relative mesh aliases in source archives; wheels retain the code-only
packaging policy. The upstream download package, generated remote registry,
unrelated gallery assets, and release workflows are omitted. Native `make all` is the acceptance gate.

See the [accepted scope](docs/adr/0011-upstream-asset-structure-first.md),
[implementation outline](docs/design/menagerie-paired-refactor-proposal.md), and
[research report](docs/research/mujoco-upstream-contract.md).
