---
status: accepted
---

# Initialize and reset the explicitly selected complete state

Each simulation configuration selects a named initial pose or normal MuJoCo
reference initialization. Native and browser reset restore the complete
selected state, including actuator targets when present; pose names such as
`home`, `stand`, or `fist` do not imply automatic selection. Preserve existing
coordinate frames during migration and make placement overrides explicit.

Accepted by the user on 2026-10-30. Implementation is pending; the exact pose
reference representation belongs to the configuration schema.

## Scope clarification on 2026-10-30

Retain explicit native XML/keyframe semantics and current physical descriptions. A shared CLI/browser initialization framework is deferred. See [ADR 0011](0011-upstream-asset-structure-first.md), which takes precedence over the original application requirements above.
