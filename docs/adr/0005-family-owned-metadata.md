---
status: superseded by ADR-0011
---

# Give each family ownership of its semantic metadata

Each robot family will own its descriptions, model/scene/pose configurations,
defaults, and provenance. A small root index will own family discovery and
global defaults, with one authoritative owner for each field. This keeps a
copied family meaningful to the application and concentrates family-specific
edits alongside the assets they describe.

Accepted by the user on 2026-10-30. The metadata filename and schema remain
to be designed. Existing HHTools `robot.yaml` semantics are preserved.

## Scope clarification on 2026-10-30

Mandatory family-owned application metadata and family.json are removed from the target. Upstream-style XML and root catalog conventions take priority. See [ADR 0011](0011-upstream-asset-structure-first.md), which takes precedence over the original application requirements above.
