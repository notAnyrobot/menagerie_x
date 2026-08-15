export const PRIMITIVE_TYPES = ["box", "sphere", "cylinder", "capsule"];
export const POSITION_SLIDER_LIMIT = 0.1;

export function positionSliderValue(value) {
  return Math.max(-POSITION_SLIDER_LIMIT, Math.min(POSITION_SLIDER_LIMIT, Number(value)));
}

/**
 * Limit pointer picking to objects that are actually interactive in the active mode.
 * Three.js still raycasts invisible children, so visibility must be checked here.
 */
export function isPickableSceneObject(object, collisionMode) {
  if (!object?.visible || !object.userData?.link) return false;
  const layer = object.userData.layer;
  return collisionMode
    ? layer === "collision-editor" || layer === "collision-overlay"
    : layer === "visual-mesh";
}

export function degreesToRadians(value) {
  return Number(value) * Math.PI / 180;
}

export function radiansToDegrees(value) {
  return Number(value) * 180 / Math.PI;
}

export function primitiveDimensions(geometry) {
  if (geometry.type === "box") return geometry.size.map(Number);
  if (geometry.type === "sphere") return [Number(geometry.radius) * 2, Number(geometry.radius) * 2, Number(geometry.radius) * 2];
  return [Number(geometry.radius) * 2, Number(geometry.radius) * 2, Number(geometry.length)];
}

export function primitiveGeometry(THREE, geometry) {
  if (geometry.type === "box") return new THREE.BoxGeometry(...geometry.size);
  if (geometry.type === "sphere") return new THREE.SphereGeometry(geometry.radius, 20, 14);
  if (geometry.type === "capsule") {
    const capsule = new THREE.CapsuleGeometry(geometry.radius, geometry.length, 8, 16);
    capsule.rotateX(Math.PI / 2);
    capsule.computeBoundingBox();
    return capsule;
  }
  // Three.js cylinders use Y as their length axis. MJCF collision drafts use Z.
  const cylinder = new THREE.CylinderGeometry(geometry.radius, geometry.radius, geometry.length, 20);
  cylinder.rotateX(Math.PI / 2);
  cylinder.computeBoundingBox();
  return cylinder;
}

export function defaultCollision(type, link, id, name, bounds) {
  const size = bounds ? bounds.max.map((value, index) => Math.max(value - bounds.min[index], 0.001)) : [0.1, 0.1, 0.1];
  const center = bounds ? bounds.min.map((value, index) => (value + bounds.max[index]) / 2) : [0, 0, 0];
  const geometry = type === "box"
    ? { type, size }
    : type === "sphere"
      ? { type, radius: Math.max(Math.min(...size) / 2, 0.001) }
      : { type, radius: Math.max(Math.min(size[0], size[1]) / 2, 0.001), length: Math.max(size[2], 0.001) };
  return { id, link, name, origin: { xyz: center, rpy: [0, 0, 0] }, geometry };
}
