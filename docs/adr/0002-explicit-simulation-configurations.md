---
status: accepted
---

# Identify simulations by model, scene, and optional initial pose

Each supported simulation choice will explicitly identify its robot model,
scene, and initial pose when one is defined. The CLI and Workbench will retain
the selected scene's contact configuration and initialization semantics,
because scenes can carry behavior beyond a floor and lighting. A robot model
remains independently reusable, while the pairing states the supported
simulation configuration.

Accepted by the user on 2026-10-30. Implementation is pending; metadata schema,
scene-editing ownership, and pose-selection policy remain open design choices.

## Scope clarification on 2026-10-30

Model/scene pairing is expressed by ordinary MJCF includes and documented keyframes. A custom configuration schema and cross-consumer initialization layer are not required in this phase. See [ADR 0011](0011-upstream-asset-structure-first.md), which takes precedence over the original application requirements above.
