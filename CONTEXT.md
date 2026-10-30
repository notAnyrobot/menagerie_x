# Menagerie X context

The domain glossary is maintained in [GLOSSARY.md](GLOSSARY.md).
Accepted design decisions and their implementation status are recorded in
[the per-robot decision log](docs/design/per-robot-design-decisions.md).

Canonical native robot/scene XML lives at each family root; root `catalog.py`
curates seven active models plus two legacy P1 models, independently of the
application `manifest.json`. Astro P2 is one family with a shared 29-joint body
and two maintained models: the approved default and articulated Dex3-1 variant.
The default has 52 collision primitives with automatic elbow contacts and no
explicit pairs. The simplified alternative is retired to frozen provenance;
only the two maintained Astro entries receive native runtime checks.
Astro P2 body/default-model material is Apache-2.0; Unitree Dex3-1 hand material
remains BSD-3-Clause. The articulated model is labeled Astro P2 with hands and
uses silver hand visuals. G1 includes Menagerie's 27-primitive configuration and
its complete 49-pair scene as native XML; MJX execution remains deferred.
There is no regeneration step. `make all` is the native acceptance gate.
Workbench, URDF compatibility, and MJX remain deferred. See
[UPSTREAM.md](UPSTREAM.md) for preservation and ownership details.
