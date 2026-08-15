import * as THREE from "/vendor/three.module.js";

// This adapter deliberately asks MuJoCo to construct contact decorations.  It
// does not perform an overlap test in Three.js: `MjData.contact` remains the
// authority for both the count and the geom pairs we highlight.
function decorationGeometry(mujoco, geom) {
  const type = Number(geom.type);
  const size = Array.from(geom.size || [], Number);
  if (type === Number(mujoco.mjtGeom.mjGEOM_SPHERE)) return new THREE.SphereGeometry(Math.max(size[0], 0.003), 12, 8);
  if (type === Number(mujoco.mjtGeom.mjGEOM_CAPSULE)) {
    const geometry = new THREE.CapsuleGeometry(Math.max(size[0], 0.003), Math.max(size[1] * 2, 0.001), 6, 10);
    geometry.rotateX(Math.PI / 2);
    return geometry;
  }
  if (type === Number(mujoco.mjtGeom.mjGEOM_CYLINDER)) {
    const geometry = new THREE.CylinderGeometry(Math.max(size[0], 0.003), Math.max(size[0], 0.003), Math.max(size[1] * 2, 0.001), 10);
    geometry.rotateX(Math.PI / 2);
    return geometry;
  }
  if (type === Number(mujoco.mjtGeom.mjGEOM_BOX)) return new THREE.BoxGeometry(Math.max(size[0] * 2, 0.006), Math.max(size[1] * 2, 0.006), Math.max(size[2] * 2, 0.006));
  return new THREE.SphereGeometry(Math.max(size[0] || 0.006, 0.003), 12, 8);
}

function pose(object, geom) {
  const values = Array.from(geom.mat || [], Number);
  const matrix = new THREE.Matrix4().set(
    values[0], values[1], values[2], 0,
    values[3], values[4], values[5], 0,
    values[6], values[7], values[8], 0,
    0, 0, 0, 1,
  );
  object.position.fromArray(Array.from(geom.pos || [], Number));
  object.quaternion.setFromRotationMatrix(matrix);
}

function readContactPairs(data) {
  const pairs = new Set();
  const names = new Set();
  const count = Number(data?.ncon || 0);
  for (let index = 0; index < count; index += 1) {
    const contact = data.contact?.get(index);
    if (!contact) continue;
    pairs.add(Number(contact.geom1));
    pairs.add(Number(contact.geom2));
    contact.delete?.();
  }
  return { count, geomIds: pairs, names };
}

/**
 * A small seam between MuJoCo's abstract visual scene and Three.js.  MuJoCo
 * owns the decoration generation (including contact-point placement); Three
 * only adapts the resulting MjvGeom records for this workbench renderer.
 */
export function createContactVisualizer(parent, onContacts = () => {}) {
  const group = new THREE.Group();
  group.name = "mujoco-contact-decorations";
  group.userData = { visualDiagnostic: true, layer: "contact-decoration" };
  parent.add(group);
  let binding = null;
  let visible = false;
  let lastCount = 0;

  function clearDecorations() {
    while (group.children.length) {
      const child = group.children.pop();
      child.geometry?.dispose?.();
      child.material?.dispose?.();
    }
  }

  function disposeBinding() {
    if (!binding) return;
    binding.scene?.delete?.();
    binding.camera?.delete?.();
    binding.perturb?.delete?.();
    binding.option?.delete?.();
    binding = null;
  }

  function bind(mujoco, model, data) {
    if (binding?.mujoco === mujoco && binding?.model === model && binding?.data === data) return;
    disposeBinding();
    clearDecorations();
    if (!mujoco || !model || !data) return;
    const option = new mujoco.MjvOption();
    const perturb = new mujoco.MjvPerturb();
    const camera = new mujoco.MjvCamera();
    const visualScene = new mujoco.MjvScene(model, Math.max(Number(model.ngeom || 0) + 128, 256));
    mujoco.mjv_defaultOption(option);
    mujoco.mjv_defaultPerturb(perturb);
    mujoco.mjv_defaultCamera(camera);
    option.flags[Number(mujoco.mjtVisFlag.mjVIS_CONTACTPOINT)] = 1;
    binding = { mujoco, model, data, option, perturb, camera, scene: visualScene };
  }

  function setVisible(next) {
    visible = Boolean(next);
    group.visible = visible;
    if (!visible) {
      clearDecorations();
      lastCount = 0;
      onContacts({ count: 0, geomIds: new Set(), geomNames: new Set() });
    }
  }

  function sync() {
    if (!binding || !visible) return;
    const { mujoco, model, data, option, perturb, camera, scene: visualScene } = binding;
    const contacts = readContactPairs(data);
    for (const geomId of contacts.geomIds) {
      const geom = model.geom(geomId);
      if (geom?.name) contacts.names.add(geom.name);
      geom?.delete?.();
    }
    mujoco.mjv_updateScene(model, data, option, perturb, camera, Number(mujoco.mjtCatBit.mjCAT_DECOR), visualScene);
    clearDecorations();
    for (let index = 0; index < Number(visualScene.ngeom || 0); index += 1) {
      const geom = visualScene.geoms.get(index);
      if (!geom || (Number(geom.category) & Number(mujoco.mjtCatBit.mjCAT_DECOR)) === 0) {
        geom?.delete?.();
        continue;
      }
      const mesh = new THREE.Mesh(
        decorationGeometry(mujoco, geom),
        new THREE.MeshBasicMaterial({ color: 0xffbd54, transparent: true, opacity: 0.95, depthTest: false, depthWrite: false }),
      );
      pose(mesh, geom);
      mesh.renderOrder = 4;
      mesh.userData = { visualDiagnostic: true, layer: "contact-decoration", pickable: false };
      group.add(mesh);
      geom.delete?.();
    }
    lastCount = contacts.count;
    onContacts({ count: contacts.count, geomIds: contacts.geomIds, geomNames: contacts.names });
  }

  function clear() {
    clearDecorations();
    lastCount = 0;
    onContacts({ count: 0, geomIds: new Set(), geomNames: new Set() });
  }

  function dispose() {
    clear();
    disposeBinding();
    group.removeFromParent();
  }

  function unbind() {
    clear();
    disposeBinding();
  }

  return { bind, setVisible, sync, clear, unbind, dispose, get count() { return lastCount; } };
}
