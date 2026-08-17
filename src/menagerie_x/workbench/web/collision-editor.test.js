import assert from "node:assert/strict";
import test from "node:test";
import * as THREE from "three";

import {
  createCollisionMaterial,
  defaultCollision,
  degreesToRadians,
  isPickableSceneObject,
  POSITION_SLIDER_LIMIT,
  positionSliderValue,
  primitiveDimensions,
  primitiveGeometry,
  radiansToDegrees,
  syncPrimitiveToMjModel,
  setCollisionMaterialSelected,
} from "./collision-editor.js";

test("collision shapes use the shaded translucent MuJoCo-style material", () => {
  const material = createCollisionMaterial(THREE);
  assert.equal(material.isMeshStandardMaterial, true);
  assert.equal(material.transparent, true);
  assert.equal(material.depthWrite, false);
  assert.equal(material.side, THREE.DoubleSide);
  assert.ok(material.opacity > 0 && material.opacity < 1);
  const idleColor = material.color.getHex();

  setCollisionMaterialSelected(material, true);
  assert.notEqual(material.color.getHex(), idleColor);
  assert.ok(material.opacity > 0 && material.opacity < 1);
  material.dispose();
});

test("dimension mapping and degree conversion are exact", () => {
  assert.deepEqual(primitiveDimensions({ type: "box", size: [1, 2, 3] }), [1, 2, 3]);
  assert.deepEqual(primitiveDimensions({ type: "sphere", radius: 0.2 }), [0.4, 0.4, 0.4]);
  assert.deepEqual(primitiveDimensions({ type: "cylinder", radius: 0.2, length: 0.8 }), [0.4, 0.4, 0.8]);
  assert.deepEqual(primitiveDimensions({ type: "capsule", radius: 0.2, length: 0.8 }), [0.4, 0.4, 0.8]);
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
  const visibleCollisionOverlay = { visible: true, userData: { link: "torso", layer: "collision-overlay" } };

  assert.equal(isPickableSceneObject(hiddenOverlay, false), false);
  assert.equal(hits.find(hit => isPickableSceneObject(hit.object, false)), undefined);
  assert.equal(isPickableSceneObject(visibleEditorShape, false), false);
  assert.equal(isPickableSceneObject(visibleMesh, false), true);
  assert.equal(isPickableSceneObject(visibleMesh, true), false);
  assert.equal(isPickableSceneObject(visibleEditorShape, true), true);
  assert.equal(isPickableSceneObject(visibleCollisionOverlay, true), true);
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
  const capsule = primitiveGeometry(THREE, { type: "capsule", radius: 0.2, length: 0.8 });
  capsule.computeBoundingBox();
  assert.ok(capsule.boundingBox.getSize(new THREE.Vector3()).z > 0.8);
  capsule.dispose();
});

test("position slider pins values to its local fine-adjustment range", () => {
  assert.equal(POSITION_SLIDER_LIMIT, 0.1);
  assert.equal(positionSliderValue(-0.4), -0.1);
  assert.equal(positionSliderValue(0.037), 0.037);
  assert.equal(positionSliderValue(0.4), 0.1);
});

test("consecutive primitive edits update the compiled MuJoCo geom in place", () => {
  const geom = {
    name: "pelvis_cylinder_collision_1",
    pos: new Float64Array(3),
    quat: new Float64Array(4),
    size: new Float64Array(3),
    delete() {},
  };
  const model = {
    geom(name) {
      assert.equal(name, geom.name);
      return geom;
    },
  };
  const collision = {
    name: geom.name,
    origin: { xyz: [0.01, -0.02, 0.03], rpy: [0, 0, 0] },
    geometry: { type: "cylinder", radius: 0.08, length: 0.12 },
  };

  assert.equal(syncPrimitiveToMjModel(model, collision), true);
  assert.deepEqual(Array.from(geom.pos), [0.01, -0.02, 0.03]);
  assert.deepEqual(Array.from(geom.size), [0.08, 0.06, 0]);

  collision.geometry.radius = 0.09;
  collision.geometry.length = 0.14;
  collision.origin.xyz = [-0.04, 0.05, 0.06];
  assert.equal(syncPrimitiveToMjModel(model, collision), true);
  assert.deepEqual(Array.from(geom.pos), [-0.04, 0.05, 0.06]);
  assert.deepEqual(Array.from(geom.size), [0.09, 0.07, 0]);
});
