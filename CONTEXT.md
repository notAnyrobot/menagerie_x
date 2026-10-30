# Menagerie X context

The domain glossary is maintained in [GLOSSARY.md](GLOSSARY.md).
Accepted design decisions and their implementation status are recorded in
[the per-robot decision log](docs/design/per-robot-design-decisions.md).

Canonical native robot/scene XML lives at each family root; root `catalog.py`
curates six active models plus two legacy P1 models, independently of the
application `manifest.json`. Astro P2 is one family with a shared 29-joint body
and default Astro P2 / articulated Dex3-1 variants. Astro P2 body/default-model
material is Apache-2.0; Unitree Dex3-1 hand material remains BSD-3-Clause.
There is no regeneration step. `make all` is the native acceptance gate.
Workbench, URDF compatibility, and MJX remain deferred. See
[UPSTREAM.md](UPSTREAM.md) for preservation and ownership details.
