# Astro P2 consolidation and hand variants

Requested on 2026-10-30; baseline `fcbb3f222359df8b275fee1bc79d47721efdd2ec`.
Branch: `codex/astro-p2-variants`.

## Accepted scope

1. Mark Astro P1 as legacy and retain its assets and native loading checks until
   a later retirement. Its appearance in the supplied screenshot does not
   override the explicit instruction to retire P1 later.
2. Retire the three 30-DoF Astro P2 choices shown in the screenshot: primitive,
   mesh, and intermediate primitive collisions. Their history remains in Git.
3. Consolidate the previously separate fixed-head and Dex3-1 Astro directories
   into one `astro_p2/` family, using ordinary sibling models/scenes like G1.
4. Maintain only the fixed-head 29-DoF Astro body. Offer fixed rubber hands and
   three-finger Dex3-1 hands. The latter adds 14 hand joints for 43 total internal
   DoFs; it does not introduce a 43-joint body.
5. Reuse the actual left/right G1 rubber-hand meshes and verified standalone
   vendor inertias, retaining Astro wrist dynamics and hand-frame placement.
   Document attachment as a sample assumption, without inventing hardware fit.
6. Keep Workbench, URDF compatibility, and MJX deferred. Preserve local untracked
   work; retain original Astro source evidence and actual license notices.

## Resulting native structure

`astro_p2/astro_p2.xml` + `scene.xml` is the 29-DoF rubber-hand default.
`astro_p2/astro_p2_with_hands.xml` + `scene_with_hands.xml` is the 29-body-plus-14-
finger Dex3-1 alternative. Both share the latest refined Astro body and use
family-local `assets/`. Native XML is maintained directly.

`MODEL_MAP` declares six active models across four families. `LEGACY_MODEL_MAP`
retains two P1 entries. Native verification covers all eight pairs. The source
archive includes five tracked robot families; the old Astro directories may
remain physically present only because they contain preserved local experiments.

Original fixed-head/Dex3-1 XML, URDF, reports, and documentation are preserved
under `astro_p2/provenance/` with migration hashes. Historical source documents
keep their original bytes and may retain old relative paths. They are evidence,
not additional supported variants or runnable conversion instructions.

## Verification

Verify native compilation and short warning-free simulation for all pairs,
standalone copied-family loading, source-archive loading, common Astro body
properties, fixed head and 29/43 joint counts, rubber mesh hashes/full inertia/
collision records, Dex finger/keyframe preservation, source evidence hashes,
and unchanged untracked user files. Record independent review before merging.
