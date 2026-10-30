---
status: accepted
---

# Keep each robot's runtime bundle independently portable

Copying one robot variant folder elsewhere must be sufficient to load its
runtime models and scenes with MuJoCo, without installing Menagerie X or
accessing another robot folder. Runtime dependencies therefore belong within
the family and use portable relative references. The surrounding catalog and
authoring tools remain optional consumers of that bundle.

Accepted by the user on 2026-10-30. Implementation is pending; the exact
placement of URDFs, source snapshots, and authoring revisions remains open.
