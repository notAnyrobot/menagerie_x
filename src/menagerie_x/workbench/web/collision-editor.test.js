import assert from "node:assert/strict";
import test from "node:test";
import * as THREE from "three";

import {
  defaultCollision,
  degreesToRadians,
  isPickableSceneObject,
  primitiveDimensions,
  primitiveGeometry,
  radiansToDegrees,
} from "./collision-editor.js";

test("dimension mapping and degree conversion are exact", () => {
  assert.deepEqual(primitiveDimensions({ type: "box", size: [1, 2, 3] }), [1, 2, 3]);
  assert.deepEqual(primitiveDimensions({ type: "sphere", radius: 0.2 }), [0.4, 0.4, 0.4]);
  assert.deepEqual(primitiveDimensions({ type: "cylinder", radius: 0.2, length: 0.8 }), [0.4, 0.4, 0.8]);
  assert.equal(radiansToDegrees(degreesToRadians(90)), 90);
});

test("hidden collision overlays cannot capture robot push picking", () => {
  const group = new THREE.Group();
  const hiddenOverlay = new THREE.Mesh(new THREE.PlaneGeometry(10, 10), new THREE.MeshBasicMaterial());
  hiddenOverlay.visible = false;
  hiddenOverlay.userData = { link: "right_foot", layer: "collision-overlay" };
  group.add(hiddenOverlay);
  group.updateMatrixWorld(true);
  const raycaster = new THREE.Raycaster(new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, -1));
  const hits = raycaster.intersectObject(group, true);
  assert.ok(hits.length > 0, "Three.js raycasts invisible objects");
  const visibleMesh = { visible: true, userData: { link: "torso", layer: "visual-mesh" } };
  const visibleEditorShape = { visible: true, userData: { link: "torso", layer: "collision-editor" } };

  assert.equal(isPickableSceneObject(hiddenOverlay, false), false);
  assert.equal(hits.find(hit => isPickableSceneObject(hit.object, false)), undefined);
  assert.equal(isPickableSceneObject(visibleEditorShape, false), false);
  assert.equal(isPickableSceneObject(visibleMesh, false), true);
  assert.equal(isPickableSceneObject(visibleEditorShape, true), true);
  hiddenOverlay.geometry.dispose();
  hiddenOverlay.material.dispose();
});

test("new primitives fit local bounds and cylinders use URDF Z", () => {
  const box = defaultCollision("box", "link", "new-id", "box", { min: [-1, -2, -3], max: [1, 2, 3] });
  assert.deepEqual(box.origin.xyz, [0, 0, 0]);
  assert.deepEqual(box.geometry.size, [2, 4, 6]);
  const geometry = primitiveGeometry(THREE, { type: "cylinder", radius: 0.2, length: 0.8 });
  geometry.computeBoundingBox();
  const size = geometry.boundingBox.getSize(new THREE.Vector3());
  assert.ok(Math.abs(size.z - 0.8) < 1e-6);
  geometry.dispose();
});
