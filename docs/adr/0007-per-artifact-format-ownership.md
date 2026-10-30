---
status: accepted
---

# Declare URDF and MJCF ownership independently per artifact

Each format has independently declared ownership and derivation, with source
hashes recorded per artifact. Conversion is an explicit, reviewable revision;
updating one format can flag drift in a related artifact but does not
automatically overwrite it. This preserves intentional differences, including
the Dex model's independently refined MJCF collisions and pose.

Accepted by the user on 2026-10-30. Implementation is pending. The metadata
must distinguish original source evidence from maintained runtime artifacts.

## Scope clarification on 2026-10-30

Preserve actual source evidence and independently refined models. A new derivation schema, drift-reporting system, or URDF compatibility layer is not required in this phase. See [ADR 0011](0011-upstream-asset-structure-first.md), which takes precedence over the original application requirements above.
