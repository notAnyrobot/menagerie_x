import * as THREE from "/vendor/three.module.js";
import {
  contactVisualizationValues,
  mujocoEnumValue,
} from "./mujoco-visualization.js";

// MuJoCo is the only contact authority here.  We ask its visualizer for the
// contact decorations that the native viewer draws, then adapt those MjvGeom
// records for the Three.js scene.  No MjData.contact inspection or custom
// collision-pair highlighting is needed.
function decorationGeometry(values, geom) {
  const type = mujocoEnumValue(geom.type);
  const size = Array.from(geom.size || [], Number);
  if (type === values.sphereType) return new THREE.SphereGeometry(Math.max(size[0], 0.003), 12, 8);
  if (type === values.capsuleType) {
    const geometry = new THREE.CapsuleGeometry(Math.max(size[0], 0.003), Math.max(size[1] * 2, 0.001), 6, 10);
    geometry.rotateX(Math.PI / 2);
    return geometry;
  }
  if (type === values.cylinderType) {
    const geometry = new THREE.CylinderGeometry(Math.max(size[0], 0.003), Math.max(size[0], 0.003), Math.max(size[1] * 2, 0.001), 16);
    geometry.rotateX(Math.PI / 2);
    return geometry;
  }
  if (type === values.boxType) return new THREE.BoxGeometry(Math.max(size[0] * 2, 0.006), Math.max(size[1] * 2, 0.006), Math.max(size[2] * 2, 0.006));
  return new THREE.SphereGeometry(Math.max(size[0] || 0.006, 0.003), 12, 8);
}

function applyPose(object, geom) {
  const matrix = new THREE.Matrix4().set(
    ...Array.from(geom.mat || [], Number).slice(0, 3), 0,
    ...Array.from(geom.mat || [], Number).slice(3, 6), 0,
    ...Array.from(geom.mat || [], Number).slice(6, 9), 0,
    0, 0, 0, 1,
  );
  object.position.fromArray(Array.from(geom.pos || [], Number));
  object.quaternion.setFromRotationMatrix(matrix);
}

function decorationMaterial(geom) {
  const rgba = Array.from(geom.rgba || [], Number);
  const color = new THREE.Color(rgba[0] ?? 1, rgba[1] ?? 0.75, rgba[2] ?? 0.2);
  return new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: rgba[3] ?? 1,
    depthTest: false,
    depthWrite: false,
  });
}

export function createContactVisualizer(parent) {
  const group = new THREE.Group();
  group.name = "mujoco-contact-decorations";
  group.userData = { visualDiagnostic: true, layer: "contact-decoration" };
  parent.add(group);
  let binding = null;
  let visible = false;

  function clearDecorations() {
    while (group.children.length) {
      const child = group.children[0];
      group.remove(child);
      child.traverse((object) => {
        object.geometry?.dispose?.();
        object.material?.dispose?.();
      });
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
    const visualization = contactVisualizationValues(mujoco);
    option.flags[visualization.contactPointFlag] = 1;
    binding = { mujoco, model, data, option, perturb, camera, scene: visualScene, visualization };
  }

  function setVisible(next) {
    visible = Boolean(next);
    group.visible = visible;
    if (!visible) clearDecorations();
  }

  function sync() {
    if (!binding || !visible) return;
    const { mujoco, model, data, option, perturb, camera, scene: visualScene, visualization } = binding;
    mujoco.mjv_updateScene(model, data, option, perturb, camera, visualization.decorCategory, visualScene);
    clearDecorations();
    for (let index = 0; index < Number(visualScene.ngeom || 0); index += 1) {
      const geom = visualScene.geoms.get(index);
      if (!geom || (mujocoEnumValue(geom.category) & visualization.decorCategory) === 0) {
        geom?.delete?.();
        continue;
      }
      const decoration = new THREE.Mesh(
        decorationGeometry(visualization, geom),
        decorationMaterial(geom),
      );
      applyPose(decoration, geom);
      decoration.renderOrder = 4;
      decoration.userData = { visualDiagnostic: true, layer: "contact-decoration", pickable: false };
      group.add(decoration);
      geom.delete?.();
    }
  }

  function clear() { clearDecorations(); }
  function unbind() { clear(); disposeBinding(); }
  function dispose() { unbind(); group.removeFromParent(); }

  return { bind, setVisible, sync, clear, unbind, dispose };
}
