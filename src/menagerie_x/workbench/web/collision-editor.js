export const PRIMITIVE_TYPES = ["box", "sphere", "cylinder", "capsule"];
export const POSITION_SLIDER_LIMIT = 0.1;

const COLLISION_COLOR = 0x347c43;
const SELECTED_COLLISION_COLOR = 0x9dcc58;
const COLLISION_OPACITY = 0.4;
const SELECTED_COLLISION_OPACITY = 0.58;

/**
 * Match MuJoCo's collision-view presentation: a lit, translucent solid instead
 * of a wireframe. The shape remains readable against both visual meshes and
 * the floor while preserving the depth cues from the viewer lighting.
 */
export function createCollisionMaterial(THREE) {
  return new THREE.MeshStandardMaterial({
    color: COLLISION_COLOR,
    metalness: 0,
    roughness: 0.58,
    transparent: true,
    opacity: COLLISION_OPACITY,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
}

export function setCollisionMaterialSelected(material, selected) {
  if (!material?.color) return;
  material.color.set(selected ? SELECTED_COLLISION_COLOR : COLLISION_COLOR);
  material.opacity = selected ? SELECTED_COLLISION_OPACITY : COLLISION_OPACITY;
  material.transparent = true;
  material.depthWrite = false;
  material.needsUpdate = true;
}

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
    : layer === "visual-mesh" || layer === "collision-overlay";
}

/**
 * Select the geometry that represents the physical contact surface first.
 * A visual mesh remains a convenient fallback only when collision geometry is
 * hidden or unavailable for that part of the model.
 */
export function pickInteractionHit(intersections, collisionMode) {
  const hits = intersections.filter(result => !result.object.userData.visualDiagnostic && isPickableSceneObject(result.object, collisionMode));
  if (collisionMode) return hits[0];
  return hits.find(result => result.object.userData.layer === "collision-overlay")
    || hits.find(result => result.object.userData.layer === "visual-mesh");
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

export function mjcfPrimitiveSize(geometry) {
  if (geometry.type === "box") return geometry.size.map(value => Number(value) / 2);
  if (geometry.type === "sphere") return [Number(geometry.radius), 0, 0];
  return [Number(geometry.radius), Number(geometry.length) / 2, 0];
}

export function rpyToMjcfQuaternion(rpy) {
  const [roll, pitch, yaw] = rpy.map(value => Number(value) / 2);
  const [sx, sy, sz] = [Math.sin(roll), Math.sin(pitch), Math.sin(yaw)];
  const [cx, cy, cz] = [Math.cos(roll), Math.cos(pitch), Math.cos(yaw)];
  return [
    cx * cy * cz - sx * sy * sz,
    sx * cy * cz + cx * sy * sz,
    cx * sy * cz - sx * cy * sz,
    cx * cy * sz + sx * sy * cz,
  ];
}

/**
 * Apply an ordinary primitive edit to an already compiled MuJoCo model.
 * Compiling MJCF is synchronous in WASM and can stall the browser for seconds,
 * while these arrays are intentionally exposed as mutable model views.
 */
export function syncPrimitiveToMjModel(model, collision) {
  if (!model || !collision?.name) return false;
  let geom = null;
  try {
    geom = model.geom(collision.name);
    if (!geom || geom.name !== collision.name) return false;
    geom.pos.set(collision.origin.xyz.map(Number));
    geom.quat.set(rpyToMjcfQuaternion(collision.origin.rpy));
    geom.size.fill(0);
    geom.size.set(mjcfPrimitiveSize(collision.geometry));
    return true;
  } catch {
    return false;
  } finally {
    geom?.delete?.();
  }
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
