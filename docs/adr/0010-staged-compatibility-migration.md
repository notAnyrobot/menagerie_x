---
status: superseded by ADR-0011
---

# Migrate compatibility around the canonical paired contract

Preserve existing CLI commands, edition IDs, Workbench workflows, and
documented HHTools entrypoints while allowing internal APIs and folder
assumptions to change. Inventory old paths and provide migration mappings or
temporary aliases where needed, with one canonical authority. Retire
compatibility paths only after supported consumers migrate and replacement
behavior passes verification.

Accepted by the user on 2026-10-30. Implementation is pending. MJX
compatibility remains deferred.

## Scope clarification on 2026-10-30

Workbench and URDF incompatibilities are acceptable in this phase. Document known breaks and preserve the files/code, but compatibility aliases and application regression parity do not gate native asset alignment. See [ADR 0011](0011-upstream-asset-structure-first.md), which takes precedence over the original application requirements above.
