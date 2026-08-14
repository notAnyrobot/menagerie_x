import * as THREE from "/vendor/three.module.js";

const AXES = [
  { name: "X", direction: new THREE.Vector3(1, 0, 0), color: 0xef4444 },
  { name: "Y", direction: new THREE.Vector3(0, 1, 0), color: 0x22c55e },
  { name: "Z", direction: new THREE.Vector3(0, 0, 1), color: 0x3b82f6 },
];

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function tagDiagnostic(object, kind) {
  object.traverse(node => {
    node.userData.visualDiagnostic = true;
    node.userData.layer = "visual-diagnostic";
    node.userData.diagnosticKind = kind;
  });
  return object;
}

function makeTextLabel(text, color, scale) {
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  const context = canvas.getContext("2d");
  context.font = "bold 38px sans-serif";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillStyle = `#${color.toString(16).padStart(6, "0")}`;
  context.fillText(text, 32, 32);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), depthTest: false }));
  sprite.scale.setScalar(scale);
  return sprite;
}

function makeFrame(size, labels = false) {
  const frame = new THREE.Group();
  for (const axis of AXES) {
    const arrow = new THREE.ArrowHelper(axis.direction, new THREE.Vector3(), size, axis.color, size * 0.18, size * 0.10);
    frame.add(arrow);
    if (labels) {
      const label = makeTextLabel(axis.name, axis.color, size * 0.22);
      label.position.copy(axis.direction).multiplyScalar(size * 1.14);
      frame.add(label);
    }
  }
  return frame;
}

function disposeObject(object) {
  object.traverse(node => {
    node.geometry?.dispose?.();
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    for (const material of materials) {
      material?.map?.dispose?.();
      material?.dispose?.();
    }
  });
  object.removeFromParent();
}

/**
 * Manages non-pickable visual diagnostics for one rendered robot.
 * Link-attached nodes inherit the renderer's authored, joint, and physics poses;
 * the world frame remains a scene child and never follows robot motion.
 */
export function createVisualDiagnostics(scene) {
  const visualizationLayer = new THREE.Group();
  visualizationLayer.name = "workbench-visual-diagnostics";
  tagDiagnostic(visualizationLayer, "visualization-layer");
  scene.add(visualizationLayer);
  let worldFrame = null;
  let displayState = {};
  const linkCentersOfMass = [];
  const linkFrames = [];
  const jointAxes = [];

  function applyDisplayState(nextState) {
    displayState = { ...displayState, ...nextState };
    for (const marker of linkCentersOfMass) marker.visible = Boolean(displayState.centersOfMass);
    for (const frame of linkFrames) frame.visible = Boolean(displayState.linkFrames);
    for (const axis of jointAxes) axis.visible = Boolean(displayState.jointAxes);
    if (worldFrame) worldFrame.visible = Boolean(displayState.worldFrame);
  }

  function bindRobot(robot, links, visualBoundsDiagonal) {
    dispose();
    const worldSize = clamp(visualBoundsDiagonal * 0.20, 0.10, 0.50);
    const localSize = clamp(visualBoundsDiagonal * 0.05, 0.025, 0.12);
    const markerRadius = clamp(visualBoundsDiagonal * 0.01, 0.005, 0.025);

    worldFrame = tagDiagnostic(makeFrame(worldSize, true), "world-frame");
    worldFrame.name = "workbench-world-frame";
    visualizationLayer.add(worldFrame);

    for (const link of robot.scene.links) {
      const group = links.get(link.name);
      if (!group) continue;
      const frame = tagDiagnostic(makeFrame(localSize), "link-frame");
      frame.name = `${link.name}-frame`;
      group.add(frame);
      linkFrames.push(frame);
      if (link.inertial) {
        const marker = tagDiagnostic(
          new THREE.Mesh(
            new THREE.SphereGeometry(markerRadius, 12, 8),
            new THREE.MeshBasicMaterial({ color: 0xfbbf24, depthTest: false }),
          ),
          "center-of-mass",
        );
        marker.name = `${link.name}-center-of-mass`;
        marker.position.fromArray(link.inertial.origin.xyz);
        marker.renderOrder = 2;
        group.add(marker);
        linkCentersOfMass.push(marker);
      }
    }

    for (const joint of robot.scene.joints) {
      if (!new Set(["revolute", "continuous"]).has(joint.type)) continue;
      const parent = links.get(joint.parent);
      if (!parent) continue;
      const direction = new THREE.Vector3(...joint.axis);
      if (direction.lengthSq() === 0) continue;
      const axis = tagDiagnostic(new THREE.ArrowHelper(direction.normalize(), new THREE.Vector3(), localSize, 0xc084fc, localSize * 0.18, localSize * 0.10), "joint-axis");
      axis.name = `${joint.name}-axis`;
      axis.position.fromArray(joint.origin.xyz);
      axis.rotation.set(...joint.origin.rpy, "XYZ");
      parent.add(axis);
      jointAxes.push(axis);
    }
    applyDisplayState(displayState);
  }

  function dispose() {
    for (const marker of linkCentersOfMass.splice(0)) disposeObject(marker);
    for (const frame of linkFrames.splice(0)) disposeObject(frame);
    for (const axis of jointAxes.splice(0)) disposeObject(axis);
    if (worldFrame) disposeObject(worldFrame);
    worldFrame = null;
  }

  return { bindRobot, applyDisplayState, dispose };
}
