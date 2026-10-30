---
status: accepted
---

# Prioritize the upstream asset structure and defer application compatibility

The user clarified on 2026-10-30 that close alignment with MuJoCo Menagerie is
the primary goal and that Workbench and URDF incompatibilities are acceptable
during this refactor. Adopt ordinary canonical model/scene XML, family-local
assets, and upstream-style documentation and native validation; do not make
application-specific metadata, revision management, or compatibility repair
prerequisites for that work. MJX remains deferred.

The proposed `family.json` is a Menagerie X extension, not an upstream
convention, and is removed from the required target. Q12–Q14's reproducible
revision system, scene-editor scope, and URDF preview compatibility are
withdrawn from this phase. Existing assets, source evidence, URDF files, and
application code are preserved; accepting incompatibility is not permission
to discard them.

This supersedes the required family-metadata and compatibility gates in ADRs
0005 and 0010, defers the authoring systems in ADRs 0006 and 0009, and scopes
ADRs 0001, 0002, 0007, and 0008 to native asset organization for this phase.
