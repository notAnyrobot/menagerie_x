# Menagerie X context

The domain glossary is maintained in [GLOSSARY.md](GLOSSARY.md).
Accepted design decisions and their implementation status are recorded in
[the per-robot decision log](docs/design/per-robot-design-decisions.md).

Canonical native robot/scene XML lives at each family root; root `catalog.py`
curates 11 native models and scenes independently of legacy `manifest.json`.
There is no regeneration step. `make all` is the native acceptance gate.
Workbench, URDF compatibility, and MJX remain deferred. See
[UPSTREAM.md](UPSTREAM.md) for preservation and ownership details.
