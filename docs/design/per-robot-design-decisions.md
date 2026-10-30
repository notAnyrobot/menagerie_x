# Per-robot design decisions

The user clarified the priority on 2026-10-30: **align closely with MuJoCo
Menagerie's native asset structure; accept Workbench and URDF incompatibilities
for now; keep MJX deferred.** [ADR 0011](../adr/0011-upstream-asset-structure-first.md)
takes precedence over earlier application-heavy decisions.

The simplified migration is implemented on `codex/native-menagerie-refactor`,
from baseline `27d9e7c`. Root models/scenes are directly maintained; the generator
is retired and native CI is independent of Workbench. Astro 29's existing
conversion is explicitly included in the native catalog with a new scene; the
legacy application manifest is unchanged. Original XML and asset bytes are
preserved, including the two HHTools models' relative mesh alias and formatting.
See [verification](../native-refactor-verification.md) for acceptance evidence.

## Current target

- Evolve the current repository on a dedicated implementation branch, using
  pinned upstream Menagerie source as the reference.
- Retain the seven existing robot families and their model choices.
- Maintain canonical robot XML and separate scene XML directly in each family
  folder, with portable family-local dependencies, normally in `assets/`.
- Use native XML includes and keyframes to express the robot/scene setup.
- Follow upstream README/changelog/style/native load-and-step conventions.
- Preserve existing physical descriptions, source evidence, licenses, URDF
  files, application code, and user-local work.
- Document known Workbench/URDF incompatibilities; repairing them is a follow-up.
- Keep MJX compatibility deferred.

## Requirements removed or deferred

| Earlier item | Current disposition |
| --- | --- |
| Mandatory `family.json` / family metadata schema (ADR 0005, Q11 proposal) | Removed from the required target; it is not an upstream per-robot convention |
| Revision promotion/workspace architecture (ADR 0006) | Deferred |
| New source-ownership editor and Apply/Promote system (ADR 0009) | Deferred |
| Workbench/URDF feature parity and compatibility aliases as merge gates (ADR 0010) | Superseded; incompatibilities are acceptable and must be documented |
| Reproducible dependency snapshots per saved revision (Q12) | Withdrawn from this phase |
| New scene-editor capability policy (Q13) | Withdrawn from this phase |
| URDF preview compatibility framework (Q14) | Withdrawn from this phase |
| Shared native/browser pose and initialization framework | Deferred; retain native model/scene/keyframe semantics |

Upstream does have metadata: root `catalog.py` supplies curated model labels,
types and preview overrides, and package tooling derives a registry. The G1
and T1 examples do not use `family.json`. The proposed per-family schema was
an application design for Menagerie X, not an upstream requirement.

## Prior decisions and evidence

ADRs 0001–0010 retain the earlier interview history and now identify where
ADR 0011 narrows or defers their requirements. The research remains useful
background, rather than a list of mandatory application features:

- [Upstream contract](../research/mujoco-upstream-contract.md).
- [G1/T1 structure](../research/mujoco-per-robot-structure.md).
- [Workbench compatibility findings](../research/mujoco-workbench-compatibility.md).
- [Current-checkout versus fork/copy comparison](../research/mujoco-refactor-options.md).

The [simplified proposal](menagerie-paired-refactor-proposal.md) is the current
implementation outline. The former Q11–Q14 checklist is no longer the design
frontier; further choices should be limited to actual native-asset ambiguities.
