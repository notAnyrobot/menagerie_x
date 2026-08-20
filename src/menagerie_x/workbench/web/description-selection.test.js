import assert from "node:assert/strict";
import test from "node:test";
import {
  availableDescriptionFormats,
  editionForFormat,
  editionsForFormat,
  initialDescriptionSelection,
} from "./description-selection.js";

const editions = [
  { id: "primitive", default: true, formats: { urdf: true, mjcf: true } },
  { id: "mesh", default: false, formats: { urdf: true, mjcf: true } },
  { id: "halfway", default: false, formats: { urdf: false, mjcf: true } },
];

test("lists formats before filtering their independently available editions", () => {
  assert.deepEqual(availableDescriptionFormats(editions), ["mjcf", "urdf"]);
  assert.deepEqual(editionsForFormat(editions, "urdf").map(item => item.id), ["primitive", "mesh"]);
  assert.deepEqual(editionsForFormat(editions, "mjcf").map(item => item.id), ["primitive", "mesh", "halfway"]);
});

test("loads the default edition and preserves a matching edition across format changes", () => {
  assert.deepEqual(initialDescriptionSelection(editions), { format: "mjcf", edition: editions[0] });
  assert.equal(editionForFormat(editions, "urdf", "mesh"), editions[1]);
  assert.equal(editionForFormat(editions, "urdf", "halfway"), editions[0]);
});
