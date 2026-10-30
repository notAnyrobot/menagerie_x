---
status: deferred by ADR-0011
---

# Save revisions by default and apply canonical edits explicitly

Ordinary editor saving creates an authoring revision. Canonical changes
require an explicit, validated Apply/Promote operation targeting the owning
XML file; shared-file or scene edits require explicit scope and identify
affected configurations. Preserve untouched attributes, reject stale writes,
and keep source snapshots immutable so a preview or routine save cannot
silently alter supported runtime behavior.

Accepted by the user on 2026-10-30. Implementation is pending. Detailed
authoring capabilities and revision storage remain to be specified.

## Scope clarification on 2026-10-30

A new authoring overlay, source-ownership editor, and Apply/Promote system are deferred; their implementation is not a prerequisite for close upstream asset alignment. See [ADR 0011](0011-upstream-asset-structure-first.md), which takes precedence over the original application requirements above.
