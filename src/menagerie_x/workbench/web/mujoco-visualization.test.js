import assert from "node:assert/strict";
import test from "node:test";

import {
  contactVisualizationValues,
  mujocoEnumValue,
} from "./mujoco-visualization.js";

test("reads numeric values from MuJoCo Embind enum wrappers", () => {
  assert.equal(mujocoEnumValue({ value: 14 }), 14);
  assert.equal(mujocoEnumValue(4), 4);
});

test("resolves the native contact-point visualization values", () => {
  const mujoco = {
    mjtVisFlag: { mjVIS_CONTACTPOINT: { value: 14 } },
    mjtCatBit: { mjCAT_DECOR: { value: 4 } },
    mjtGeom: {
      mjGEOM_SPHERE: { value: 2 },
      mjGEOM_CAPSULE: { value: 3 },
      mjGEOM_CYLINDER: { value: 5 },
      mjGEOM_BOX: { value: 6 },
    },
  };

  assert.deepEqual(contactVisualizationValues(mujoco), {
    contactPointFlag: 14,
    decorCategory: 4,
    sphereType: 2,
    capsuleType: 3,
    cylinderType: 5,
    boxType: 6,
  });
});
