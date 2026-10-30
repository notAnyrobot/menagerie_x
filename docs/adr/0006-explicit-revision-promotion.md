---
status: deferred by ADR-0011
---

# Separate saved authoring revisions from supported catalog choices

Saved Workbench revisions remain available for preview and editing. Publishing
a revision as a supported robot model or simulation configuration requires
an explicit promotion operation, with the supported choice recorded in family
metadata. This gives revisions and supported choices distinct identities and
prevents saving a draft from silently changing the supported catalog.

Accepted by the user on 2026-10-30. Revision storage, promotion validation, and
the exact canonical save operations remain to be designed.

## Scope clarification on 2026-10-30

A new Workbench revision/promotion system is deferred and does not gate the native asset refactor. See [ADR 0011](0011-upstream-asset-structure-first.md), which takes precedence over the original application requirements above.
