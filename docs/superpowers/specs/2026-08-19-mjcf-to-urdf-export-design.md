# MJCF collision to URDF export design

## Goal

Add a non-destructive Workbench action that transfers collision geometry from
the selected MJCF edition into the selected variant's existing canonical URDF
and downloads the result as a standards-compliant URDF file.

The first reference conversion is Astro V2. Its canonical URDF supplies the
kinematic tree, inertials, visuals, materials, and joints. Its authorized
`astro_v2_primitive_collision.xml` supplies the reviewed collision geometry.

## Version-one scope

Version one is a collision-transfer feature, not a general MJCF-to-URDF robot
converter. It requires both:

- a registered variant with an existing canonical URDF; and
- a selected MJCF edition for that same variant.

The export preserves every non-collision URDF element semantically and replaces
all URDF `<collision>` elements with standard primitives derived from the MJCF
collision geoms. It does not modify the canonical URDF, the selected MJCF,
manifest data, edition metadata, or collision-editor drafts.

The following are out of scope:

- URDF-to-MJCF conversion;
- creating a URDF for an MJCF-only variant;
- editing or mirroring collisions;
- authorizing or registering the downloaded URDF;
- mesh collision transfer; and
- custom URDF capsule extensions.

## User flow

1. The user selects a robot variant and one saved MJCF edition in the left asset
   panel.
2. Workbench enables **Export URDF** only when the variant also has a canonical
   URDF.
3. The user selects **Export URDF**.
4. The server reads the currently saved MJCF edition and canonical URDF, performs
   a fail-closed conversion, and returns the generated URDF plus a conversion
   report.
5. The browser downloads
   `<variant>__<edition>__collision-export.urdf` and reports the source and
   output collision counts.

The action never reads an unsaved collision-editor draft. If the editor has
unsaved changes, the UI states that export uses the saved edition and requires
confirmation before continuing.

## Module and interface

The conversion seam belongs in `menagerie_x.assets`, below Workbench. A new
deep module owns MJCF collision selection, frame conversion, primitive
conversion, URDF rewriting, deterministic naming, and reporting. Workbench is a
thin adapter that resolves the selected variant and edition, calls the module,
and serializes the result.

The external interface is intentionally small: the immutable
`UrdfCollisionExport` record contains `filename: str`, `content: bytes`, and
`report: CollisionExportReport`; callers use
`export_urdf_with_mjcf_collisions(variant, mjcf_path, *, edition_id,
asset_root) -> UrdfCollisionExport`.

`CollisionExportReport` contains source and output revisions, source and output
collision counts, output counts by primitive type, the number of expanded
capsules, and warnings. A successful version-one export has no skipped geoms.

## Collision selection

The converter compiles the saved edition with the pinned MuJoCo 3.11.0 runtime
so MJCF defaults, `fromto`, quaternion normalization, effective dimensions, and
contact masks are resolved consistently. A geom is a collision when its
compiled `contype` or `conaffinity` is non-zero. Contact-disabled visual geoms
are never transferred. Every selected collision geom must:

- be a `box`, `sphere`, `cylinder`, or `capsule`;
- have finite, positive dimensions;
- belong to a named MJCF body;
- map to a same-named URDF link; and
- use a supported pose encoding.

Any mesh, plane, ellipsoid, height field, unnamed owner, missing target link,
unsupported pose encoding, duplicate output name, or malformed dimension blocks
the entire export. The converter never silently drops a collision.

## Frames and geometry

The converter evaluates zero-pose transforms relative to the canonical robot
root rather than assuming that equal body and link names imply equal local
frames. Root placement in the world and free-joint mobility are excluded. For
each geom it computes:

```text
T_urdf_link_geom = inverse(T_root_urdf_link)
                   * T_root_mjcf_body
                   * T_mjcf_body_geom
```

The resulting translation becomes URDF `origin xyz`; the resulting rotation is
serialized as fixed-axis roll, pitch, yaw. MJCF quaternions use `w x y z`.

Primitive dimensions map as follows:

- sphere: preserve the radius and translated center;
- cylinder: preserve the radius and convert MJCF half-length `h` to URDF
  `length="2h"`;
- box: convert all three MJCF half-extents to full URDF dimensions; and
- capsule: emit one cylinder with radius `r` and length `2h`, plus two spheres
  of radius `r` at the rotated local endpoints `p ± R(0, 0, h)`.

The three-element capsule decomposition is an exact solid-set representation of
a MuJoCo capsule using standard URDF primitives. Consumers may nevertheless
report contacts against the three component elements separately.

## Names and ordering

Generated names follow `docs/robots/description-conventions.md`. Direct
primitives retain a unique, convention-compliant source name. Missing or
non-conforming names are deterministically normalized from the semantic source
name, shape, and ordinal.

A source capsule produces names that preserve its source identity while making
the standard components explicit:

```text
<source-stem>_cylinder_collision_1
<source-stem>_sphere_collision_1
<source-stem>_sphere_collision_2
```

Output order is deterministic: URDF link order, then MJCF source geom order,
then cylinder followed by the two endpoint spheres for a capsule.

## URDF preservation

The converter parses with XML comments enabled, replaces only direct
`<collision>` children of `<link>` elements, and serializes valid UTF-8 XML.
Formatting may be normalized, but tests compare a collision-stripped semantic
projection to prove that links, joints, origins, axes, limits, inertials,
visuals, materials, transmissions, gazebo extensions, and other non-collision
content are unchanged. The existing top-level Astro `<mujoco>` extension is
preserved as non-collision content; version one's standards guarantee applies
to the emitted URDF collision geometry.

## Workbench interface

The left asset-panel action is placed beside **Import MJCF edition**. It is
disabled unless both a variant and edition are selected and the variant has a
canonical URDF.

Workbench calls:

```text
GET /api/robots/<variant>/editions/<edition>/export-urdf
```

The server resolves both source paths through existing variant and edition
lookups; the request accepts no filesystem path. A successful response is an
XML attachment with the source and output collision counts in response headers.
The browser creates a `Blob`, starts the download, revokes the object URL, and
renders a concise success status. A blocked conversion returns HTTP 422 with a
structured JSON report containing every blocker. No server-side export file or
token persists.

## Failure behavior

- A variant without a canonical URDF cannot export.
- A missing or stale edition returns not found.
- Invalid XML, unsupported geometry, unsafe mapping, and name collisions return
  a bad-request response with a precise error.
- No partial URDF is returned on failure.
- No repository file changes on success or failure.

## Reference evidence

Astro V2's authorized MJCF contains 47 collision geoms: 39 capsules, seven
cylinders, and one sphere. The expected export contains 125 standard URDF
collisions: 46 cylinders and 79 spheres. All Astro V2 collision-owner body names
exist as URDF links.

The official Unitree G1 URDF and MJCF contain physically equivalent sets of 52
collisions despite format-specific ownership of fixed frames. This establishes
physical-set equivalence as the cross-format criterion; G1's anonymous collision
elements are not a naming precedent.

## Acceptance criteria

- Astro V2 export produces exactly 125 standard primitive collisions and no
  mesh or custom capsule collision.
- Capsule components reproduce the authorized MJCF geometry within numeric
  tolerance.
- Collision-stripped output is semantically identical to the canonical URDF.
- The downloaded file loads in a standard URDF consumer and MuJoCo's URDF
  loader.
- Unsupported geometry causes a complete, explicit failure.
- The collision editor, selected MJCF edition, canonical URDF, and manifest stay
  byte-identical after export.
- The Workbench action is covered by backend and browser tests and remains
  unavailable for variants without a canonical URDF.
