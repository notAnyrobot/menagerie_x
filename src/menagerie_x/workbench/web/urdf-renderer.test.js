import assert from "node:assert/strict";
import test from "node:test";
import {
  configureUrdfLoader,
  describeUrdfJoint,
  resolveUrdfMeshAsset,
  urdfSceneTransform,
} from "./urdf-utils.js";
import { createUrdfLoadGate } from "./urdf-load-lifecycle.js";

test("resolves relative and package URDF STL paths into the edition mesh subtree", () => {
  assert.equal(resolveUrdfMeshAsset("mesh:///../meshes/left_foot.STL"), "left_foot.STL");
  assert.equal(resolveUrdfMeshAsset("package://robot/meshes/arm.stl"), "arm.stl");
});

test("rejects traversal and non-STL URDF mesh requests", () => {
  assert.throws(() => resolveUrdfMeshAsset("mesh:///../../secret.obj"), /Unsupported URDF mesh path/);
  assert.throws(() => resolveUrdfMeshAsset("mesh:///meshes/../secret.stl"), /Unsupported URDF mesh path/);
});

test("describes URDF limits and poses for slider-compatible joints", () => {
  const revolute = { urdfName: "knee", jointType: "revolute", limit: { lower: -0.2, upper: 1.4 } };
  const continuous = { urdfName: "wheel", jointType: "continuous", limit: { lower: 0, upper: 0 } };
  assert.deepEqual(describeUrdfJoint(revolute, 4), {
    id: 4, name: "knee", type: "revolute", limited: true, lower: -0.2, upper: 1.4, qposAddress: 4, joint: revolute,
  });
  assert.deepEqual(describeUrdfJoint(continuous, 5), {
    id: 5, name: "wheel", type: "continuous", limited: false, lower: -Math.PI, upper: Math.PI, qposAddress: 5, joint: continuous,
  });
});

test("invalidates stale asynchronous URDF load generations", () => {
  const gate = createUrdfLoadGate();
  const first = gate.begin();
  assert.equal(first.current(), true);
  const second = gate.begin();
  assert.equal(first.current(), false);
  assert.equal(second.current(), true);
  gate.invalidate();
  assert.equal(second.current(), false);
});

test("enables visual and collision parsing on the URDF loader", () => {
  const loader = { parseVisual: false, parseCollision: false };
  assert.equal(configureUrdfLoader(loader), loader);
  assert.equal(loader.parseVisual, true);
  assert.equal(loader.parseCollision, true);
});

test("uses the catalog scene spawn for a URDF root", () => {
  assert.deepEqual(urdfSceneTransform({
    robot_spawn: { xyz: [0.1, -0.2, 0.75], rpy: [0.01, 0.02, 0.03] },
  }), {
    xyz: [0.1, -0.2, 0.75],
    rpy: [0.01, 0.02, 0.03],
  });
  assert.deepEqual(urdfSceneTransform(null), { xyz: [0, 0, 0], rpy: [0, 0, 0] });
});
