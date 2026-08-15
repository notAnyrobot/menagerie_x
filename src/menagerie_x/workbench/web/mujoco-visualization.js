// MuJoCo's Embind-generated JavaScript API exposes C enums as wrapper objects
// with their integer in `.value`. Some alternate builds expose plain numbers,
// so keep this boundary tolerant of both representations.
export function mujocoEnumValue(value) {
  const candidate = value && typeof value === "object" && "value" in value
    ? value.value
    : value;
  const numeric = Number(candidate);
  if (!Number.isFinite(numeric)) throw new TypeError("MuJoCo enum does not contain a finite numeric value");
  return numeric;
}

export function contactVisualizationValues(mujoco) {
  return {
    contactPointFlag: mujocoEnumValue(mujoco.mjtVisFlag.mjVIS_CONTACTPOINT),
    decorCategory: mujocoEnumValue(mujoco.mjtCatBit.mjCAT_DECOR),
    sphereType: mujocoEnumValue(mujoco.mjtGeom.mjGEOM_SPHERE),
    capsuleType: mujocoEnumValue(mujoco.mjtGeom.mjGEOM_CAPSULE),
    cylinderType: mujocoEnumValue(mujoco.mjtGeom.mjGEOM_CYLINDER),
    boxType: mujocoEnumValue(mujoco.mjtGeom.mjGEOM_BOX),
  };
}
