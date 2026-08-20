import assert from "node:assert/strict";
import test from "node:test";

import { downloadUrdf, requestUrdfExport, UrdfExportRequestError } from "./urdf-export.js";

function responseStub({ status, body, headers }) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Unprocessable Entity",
    headers: new Headers(headers),
    blob: async () => new Blob([body], { type: "application/xml" }),
    json: async () => JSON.parse(body),
  };
}

test("returns a URDF download with server counts", async () => {
  const result = await requestUrdfExport(async () => responseStub({
    status: 200,
    body: '<robot name="astro_v2"/>',
    headers: {
      "content-disposition": 'attachment; filename="astro_v2-reviewed-collisions.urdf"',
      "x-menagerie-mjcf-collision-count": "47",
      "x-menagerie-urdf-collision-count": "125",
    },
  }), "/export");
  assert.equal(result.filename, "astro_v2-reviewed-collisions.urdf");
  assert.equal(result.sourceCollisionCount, 47);
  assert.equal(result.outputCollisionCount, 125);
});

test("retains every structured export issue", async () => {
  await assert.rejects(
    requestUrdfExport(async () => responseStub({
      status: 422,
      body: JSON.stringify({ error: "blocked", report: { issues: [{ message: "mesh" }, { message: "frame" }] } }),
      headers: {},
    }), "/export"),
    error => error instanceof UrdfExportRequestError && error.report.issues.length === 2,
  );
});

test("downloads through a transient object URL", () => {
  const anchor = { click: () => { anchor.clicked = true; }, remove: () => { anchor.removed = true; } };
  const documentRef = { createElement: () => anchor, body: { append: value => { assert.equal(value, anchor); } } };
  const urlApi = { createObjectURL: () => "blob:urdf", revokeObjectURL: value => { assert.equal(value, "blob:urdf"); } };
  downloadUrdf(documentRef, urlApi, { blob: new Blob(["x"]), filename: "robot.urdf" });
  assert.equal(anchor.href, "blob:urdf");
  assert.equal(anchor.download, "robot.urdf");
  assert.ok(anchor.clicked && anchor.removed);
});
