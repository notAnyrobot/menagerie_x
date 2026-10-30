---
status: accepted
---

# Maintain canonical robot and scene files at the family root

Each supported robot MJCF and scene will be maintained directly at its robot
variant's folder root, and the CLI and Workbench will use these same
authoritative files. Original vendor snapshots remain preserved separately.
This replaces the current nested-source/generated-flat-copy arrangement,
giving authoring and simulation a single maintained target and eliminating
edits that are lost when a flat mirror is regenerated.

Accepted by the user on 2026-10-30. Implementation is pending the remaining
design decisions; this ADR describes the target, not the current runtime.

## Scope clarification on 2026-10-30

Canonical root files remain accepted. CLI/Workbench adaptation is a follow-up, not a prerequisite for the native asset refactor. See [ADR 0011](0011-upstream-asset-structure-first.md), which takes precedence over the original application requirements above.
