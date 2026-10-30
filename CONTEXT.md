# Menagerie X context

The domain glossary is maintained in [GLOSSARY.md](GLOSSARY.md).
Accepted design decisions and their implementation status are recorded in
[the per-robot decision log](docs/design/per-robot-design-decisions.md).

Canonical native robot/scene XML lives at each family root; root `catalog.py`
curates eight active models plus two legacy P1 models, independently of the
application `manifest.json`. Astro P2 is one family with a shared 29-joint body
and default Astro P2 / articulated Dex3-1 variants, plus an optional arm-optimized
collision model with the original fixed hands. Astro P2 body/default-model
material is Apache-2.0; Unitree Dex3-1 hand material remains BSD-3-Clause.
The articulated variant is labeled Astro P2 with hands and uses silver hand
visuals. G1 also includes Menagerie's 27-primitive configuration and its complete
49-pair scene as native XML; MJX device execution is not yet verified.
The revised Astro alternative preserves every original non-arm collider and
its contact policy. Only arms/hands are optimized and use explicit scene pairs;
Astro's unactuated dynamics, source frames and existing variants are retained.
The current wrist refinement removes redundant wrist-roll proxies and uses
compact G1-style palm-only capsules, with extended digits intentionally outside;
40 body plus 10 arm colliders remain.
There is no regeneration step. `make all` is the native acceptance gate.
Workbench, URDF compatibility, and MJX remain deferred. See
[UPSTREAM.md](UPSTREAM.md) for preservation and ownership details.
