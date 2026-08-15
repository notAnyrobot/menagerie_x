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
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true, depthTest: false, depthWrite: false }));
  sprite.scale.setScalar(scale);
  return sprite;
}

function overlayMaterial(color) {
  // Diagnostics must share the transparent render pass with translucent visual
  // meshes. Their renderOrder then keeps them composited over the robot.
  return new THREE.MeshBasicMaterial({ color, transparent: true, depthTest: false, depthWrite: false });
}

function makeThickArrow(direction, length, color) {
  const arrow = new THREE.Group();
  const unit = direction.clone().normalize();
  const shaftRadius = clamp(length * 0.045, 0.0015, 0.014);
  const headLength = Math.max(length * 0.20, shaftRadius * 3);
  const shaftLength = Math.max(length - headLength, shaftRadius * 2);
  const orientation = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), unit);
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(shaftRadius, shaftRadius, shaftLength, 12), overlayMaterial(color));
  shaft.position.copy(unit).multiplyScalar(shaftLength / 2);
  shaft.quaternion.copy(orientation);
  const head = new THREE.Mesh(new THREE.ConeGeometry(shaftRadius * 2.7, headLength, 12), overlayMaterial(color));
  head.position.copy(unit).multiplyScalar(shaftLength + headLength / 2);
  head.quaternion.copy(orientation);
  shaft.renderOrder = 2;
  head.renderOrder = 2;
  arrow.add(shaft, head);
  return arrow;
}

function makeRotationDirectionArrow(direction, size) {
  const directionArrow = new THREE.Group();
  const radius = size * 0.38;
  const startAngle = Math.PI * 0.12;
  const endAngle = startAngle + Math.PI * 1.58;
  const points = Array.from({ length: 25 }, (_, index) => {
    const angle = startAngle + (endAngle - startAngle) * index / 24;
    return new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0);
  });
  const tubeRadius = clamp(size * 0.028, 0.0012, 0.008);
  const arc = new THREE.Mesh(
    new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), 32, tubeRadius, 8, false),
    overlayMaterial(0xf59e0b),
  );
  const tangent = new THREE.Vector3(-Math.sin(endAngle), Math.cos(endAngle), 0);
  const tip = points.at(-1);
  const headLength = size * 0.22;
  const head = new THREE.Mesh(new THREE.ConeGeometry(tubeRadius * 3, headLength, 12), overlayMaterial(0xf59e0b));
  head.position.copy(tip).addScaledVector(tangent, -headLength / 2);
  head.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent);
  arc.renderOrder = 2;
  head.renderOrder = 2;
  directionArrow.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), direction.clone().normalize());
  directionArrow.add(arc, head);
  return directionArrow;
}

function makeFrame(size, labels = false) {
  const frame = new THREE.Group();
  for (const axis of AXES) {
    const arrow = makeThickArrow(axis.direction, size, axis.color);
    frame.add(arrow);
    if (labels) {
      const label = makeTextLabel(axis.name, axis.color, size * 0.22);
      label.position.copy(axis.direction).multiplyScalar(size * 1.14);
      frame.add(label);
    }
  }
  return frame;
}

function makeJointAxis(direction, size) {
  const axis = new THREE.Group();
  axis.add(makeThickArrow(direction, size, 0xc084fc));
  const rotationDirection = makeRotationDirectionArrow(direction, size);
  rotationDirection.name = "rotation-direction-arrow";
  axis.add(rotationDirection);
  return axis;
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
            overlayMaterial(0xfbbf24),
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
      const axis = tagDiagnostic(makeJointAxis(direction.normalize(), localSize), "joint-axis");
      axis.name = `${joint.name}-axis`;
      axis.position.fromArray(joint.origin.xyz);
      axis.rotation.set(...joint.origin.rpy, "XYZ");
      parent.add(axis);
      jointAxes.push(axis);
    }
    applyDisplayState(displayState);
  }

  /** Bind markers to compiled MuJoCo bodies and joints, not a URDF hierarchy. */
  function bindMujoco(model, data, bodies, visualBoundsDiagonal) {
    dispose();
    const worldSize = clamp(visualBoundsDiagonal * 0.20, 0.10, 0.50);
    const localSize = clamp(visualBoundsDiagonal * 0.05, 0.025, 0.12);
    const markerRadius = clamp(visualBoundsDiagonal * 0.01, 0.005, 0.025);
    worldFrame = tagDiagnostic(makeFrame(worldSize, true), "world-frame");
    worldFrame.name = "workbench-world-frame";
    visualizationLayer.add(worldFrame);
    for (const [name, group] of bodies) {
      const body = model.body(name);
      const id = Number(body.id);
      body.delete?.();
      const frame = tagDiagnostic(makeFrame(localSize), "link-frame");
      frame.name = `${name}-frame`;
      group.add(frame);
      linkFrames.push(frame);
      const marker = tagDiagnostic(new THREE.Mesh(new THREE.SphereGeometry(markerRadius, 12, 8), overlayMaterial(0xfbbf24)), "center-of-mass");
      marker.name = `${name}-center-of-mass`;
      marker.position.fromArray(model.body_ipos.slice(id * 3, id * 3 + 3));
      marker.renderOrder = 2;
      group.add(marker);
      linkCentersOfMass.push(marker);
    }
    for (let id = 0; id < model.njnt; id += 1) {
      const joint = model.jnt(id);
      const type = Number(joint.type);
      const name = joint.name || `joint_${id}`;
      joint.delete?.();
      if (!new Set([2, 3]).has(type)) continue;
      // Build in a canonical local orientation.  syncMujoco maps +Z to the
      // current world-space MuJoCo axis whenever the robot pose changes.
      const axis = tagDiagnostic(makeJointAxis(new THREE.Vector3(0, 0, 1), localSize), "joint-axis");
      axis.name = `${name}-axis`;
      axis.userData.mujocoJointId = id;
      visualizationLayer.add(axis);
      jointAxes.push(axis);
    }
    syncMujoco(data);
    applyDisplayState(displayState);
  }

  /** Synchronize world-space joint diagnostics from current MuJoCo kinematics. */
  function syncMujoco(data) {
    if (!data) return;
    const canonicalAxis = new THREE.Vector3(0, 0, 1);
    for (const axis of jointAxes) {
      const id = axis.userData?.mujocoJointId;
      if (!Number.isInteger(id)) continue;
      const direction = new THREE.Vector3(data.xaxis[id * 3], data.xaxis[id * 3 + 1], data.xaxis[id * 3 + 2]);
      if (direction.lengthSq() === 0) {
        axis.visible = false;
        continue;
      }
      axis.position.set(data.xanchor[id * 3], data.xanchor[id * 3 + 1], data.xanchor[id * 3 + 2]);
      axis.quaternion.setFromUnitVectors(canonicalAxis, direction.normalize());
      axis.visible = Boolean(displayState.jointAxes);
    }
  }

  function dispose() {
    for (const marker of linkCentersOfMass.splice(0)) disposeObject(marker);
    for (const frame of linkFrames.splice(0)) disposeObject(frame);
    for (const axis of jointAxes.splice(0)) disposeObject(axis);
    if (worldFrame) disposeObject(worldFrame);
    worldFrame = null;
  }

  return { bindRobot, bindMujoco, syncMujoco, applyDisplayState, dispose };
}
