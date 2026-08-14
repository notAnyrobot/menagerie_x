import * as THREE from "/vendor/three.module.js";
import { OrbitControls } from "/vendor/OrbitControls.js";
import { STLLoader } from "/vendor/STLLoader.js";
import loadMujoco from "/vendor/mujoco.js";
import { createVisualDiagnostics } from "/diagnostics.js";

const canvas = document.querySelector("#robot-canvas");
const viewerEmpty = document.querySelector("#viewer-empty");
const selectedTitle = document.querySelector("#selected-title");
const selectedElement = document.querySelector("#selected-element");
const selectedSource = document.querySelector("#selected-source");
const engineState = document.querySelector("#engine-state");
const robotStatus = document.querySelector("#robot-status");
const robotList = document.querySelector("#robot-list");
const jointCount = document.querySelector("#joint-count");
const jointList = document.querySelector("#joint-list");
const elementList = document.querySelector("#element-list");
const elementSearch = document.querySelector("#element-search");
const physicsToggle = document.querySelector("#physics-toggle");
const physicsReset = document.querySelector("#physics-reset");
const followToggle = document.querySelector("#follow-toggle");
const visualMeshToggle = document.querySelector("#visual-mesh-toggle");
const collisionShapeToggle = document.querySelector("#collision-shape-toggle");
const meshOpacity = document.querySelector("#mesh-opacity");
const meshOpacityValue = document.querySelector("#mesh-opacity-value");
const centerOfMassToggle = document.querySelector("#center-of-mass-toggle");
const linkFrameToggle = document.querySelector("#link-frame-toggle");
const worldFrameToggle = document.querySelector("#world-frame-toggle");
const jointAxisToggle = document.querySelector("#joint-axis-toggle");
const simulationState = document.querySelector("#simulation-state");

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x101215);
renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 100);
camera.up.set(0, 0, 1);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0.75);
controls.enableDamping = true;
const robotGroup = new THREE.Group();
scene.add(robotGroup);
scene.add(new THREE.HemisphereLight(0xeaf1ff, 0x1a2024, 2.2));
const keyLight = new THREE.DirectionalLight(0xffffff, 2.5);
keyLight.position.set(3, -3, 5);
scene.add(keyLight);
const grid = new THREE.GridHelper(4, 16, 0x3b4652, 0x222a31);
grid.rotateX(Math.PI / 2);
scene.add(grid);
const diagnostics = createVisualDiagnostics(scene);

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const stlLoader = new STLLoader();
let catalog = [];
let activeRobot = null;
let selectedName = null;
let selectedKind = null;
let mujoco = null;
let wasmObjects = [];
let loadVersion = 0;
let loadAbortController = null;
let simulationModel = null;
let simulationData = null;
let physicsEnabled = false;
let followEnabled = false;
let visualMeshesVisible = true;
let collisionShapesVisible = false;
let meshOpacityPercent = 100;
let centersOfMassVisible = false;
let linkFramesVisible = false;
let worldFrameVisible = false;
let jointAxesVisible = false;
let physicsAccumulator = 0;
let pointerGesture = null;
let dragForce = null;
let simulationRootJoint = null;
let jointStates = [];
let activeJointId = null;
let lastJointStatusUpdate = 0;
const visualLinkGroups = new Map();
const initialLinkTransforms = new Map();
const visualJoints = new Map();
const visualRootLinks = new Set();
const mujocoBodyIds = new Map();
const simulationClock = new THREE.Clock();

function api(path) {
  return fetch(path).then(async response => {
    const data = await response.json().catch(() => ({ ok: false, error: response.statusText }));
    if (!response.ok || !data.ok) throw new Error(data.error || "Request failed");
    return data;
  });
}

function deleteWasmObjects(objects) {
  for (const object of objects.splice(0).reverse()) object.delete?.();
}

function disposeWasm() {
  clearDragForce();
  deleteWasmObjects(wasmObjects);
  simulationModel = null;
  simulationData = null;
  simulationRootJoint = null;
  jointStates = [];
  activeJointId = null;
  jointList.replaceChildren();
  jointCount.textContent = "";
  mujocoBodyIds.clear();
  physicsAccumulator = 0;
}

function isCurrentLoad(token, controller) {
  return token === loadVersion && controller === loadAbortController && !controller.signal.aborted;
}

function assertCurrentLoad(token, controller) {
  if (!isCurrentLoad(token, controller)) throw new DOMException("Robot load was superseded.", "AbortError");
}

function handleSimulationError(error) {
  physicsEnabled = false;
  dragForce = null;
  pointerGesture = null;
  controls.enabled = true;
  canvas.classList.remove("pushing");
  updateSimulationControls("Physics paused after a MuJoCo error. Select a robot to reload it.");
  setEngineState(`MuJoCo WASM paused: ${error.message}`, "error");
}

function setEngineState(message, state = "loading") {
  engineState.textContent = message;
  robotStatus.className = `status-dot ${state === "ready" ? "ready" : state === "error" ? "error" : ""}`;
}

function updateSimulationControls(message = null) {
  physicsToggle.setAttribute("aria-checked", String(physicsEnabled));
  physicsToggle.disabled = !simulationModel;
  physicsReset.disabled = !simulationModel;
  followToggle.setAttribute("aria-checked", String(followEnabled));
  if (message) simulationState.textContent = message;
}

function updateDisplayControls() {
  visualMeshToggle.setAttribute("aria-checked", String(visualMeshesVisible));
  collisionShapeToggle.setAttribute("aria-checked", String(collisionShapesVisible));
  centerOfMassToggle.setAttribute("aria-checked", String(centersOfMassVisible));
  linkFrameToggle.setAttribute("aria-checked", String(linkFramesVisible));
  worldFrameToggle.setAttribute("aria-checked", String(worldFrameVisible));
  jointAxisToggle.setAttribute("aria-checked", String(jointAxesVisible));
  meshOpacity.value = String(meshOpacityPercent);
  meshOpacityValue.textContent = `${meshOpacityPercent}%`;
  diagnostics.applyDisplayState({
    centersOfMass: centersOfMassVisible,
    linkFrames: linkFramesVisible,
    worldFrame: worldFrameVisible,
    jointAxes: jointAxesVisible,
  });
}

function setLayerVisibility(layer, visible) {
  robotGroup.traverse(node => {
    if (node.userData.layer === layer) node.visible = visible;
  });
}

function toggleVisualMeshes() {
  visualMeshesVisible = !visualMeshesVisible;
  setLayerVisibility("visual-mesh", visualMeshesVisible);
  updateDisplayControls();
}

function applyVisualMeshOpacity() {
  const multiplier = meshOpacityPercent / 100;
  robotGroup.traverse(node => {
    if (node.userData.layer !== "visual-mesh") return;
    const material = node.material;
    const original = node.userData.originalMaterial;
    if (!material || !original) return;
    const opacity = original.opacity * multiplier;
    material.opacity = opacity;
    material.transparent = original.transparent || opacity < 1;
    material.depthWrite = original.depthWrite && opacity >= 1;
    material.needsUpdate = true;
  });
}

function setMeshOpacity(value) {
  meshOpacityPercent = Math.round(Math.min(100, Math.max(0, Number(value) || 0)));
  applyVisualMeshOpacity();
  updateDisplayControls();
}

function toggleCollisionShapes() {
  collisionShapesVisible = !collisionShapesVisible;
  setLayerVisibility("collision-overlay", collisionShapesVisible);
  updateDisplayControls();
}

function toggleDiagnostics(key) {
  if (key === "centersOfMass") centersOfMassVisible = !centersOfMassVisible;
  if (key === "linkFrames") linkFramesVisible = !linkFramesVisible;
  if (key === "worldFrame") worldFrameVisible = !worldFrameVisible;
  if (key === "jointAxes") jointAxesVisible = !jointAxesVisible;
  updateDisplayControls();
}

function resetSimulation() {
  if (!simulationModel || !simulationData || !mujoco) return;
  try {
    clearDragForce();
    mujoco.mj_resetData(simulationModel, simulationData);
    if (simulationRootJoint) {
      const root = simulationData.jnt(simulationRootJoint);
      root.qpos.set([0, 0, 0.75, 1, 0, 0, 0]);
      root.delete?.();
      simulationData.qvel.fill(0);
    }
    mujoco.mj_forward?.(simulationModel, simulationData);
    physicsAccumulator = 0;
    restoreInitialVisualTransforms();
    updateJointValues();
    updateSimulationControls("Simulation reset to the packaged model state.");
    if (followEnabled) frameRobot();
  } catch (error) {
    handleSimulationError(error);
  }
}

function togglePhysics() {
  if (!simulationModel) return;
  physicsEnabled = !physicsEnabled;
  updateSimulationControls(physicsEnabled ? "Physics is running in MuJoCo WASM." : "Physics paused. Drag the robot to apply a push.");
}

function toggleFollow() {
  followEnabled = !followEnabled;
  updateSimulationControls(followEnabled ? "Camera will follow the robot." : "Camera follow is off.");
  if (followEnabled) frameRobot();
}

function advancePhysics(deltaSeconds) {
  if (!simulationModel || !simulationData || !physicsEnabled || !mujoco) return;
  try {
    const timestep = Number(simulationModel.opt?.timestep) || 0.002;
    physicsAccumulator = Math.min(physicsAccumulator + deltaSeconds, timestep * 8);
    let stepped = false;
    while (physicsAccumulator >= timestep) {
      applyDragForce();
      mujoco.mj_step(simulationModel, simulationData);
      physicsAccumulator -= timestep;
      stepped = true;
    }
    if (stepped) syncVisualsFromMujoco();
  } catch (error) {
    handleSimulationError(error);
  }
}

function getMujocoBodyId(linkName) {
  if (!simulationModel || !linkName) return null;
  if (mujocoBodyIds.has(linkName)) return mujocoBodyIds.get(linkName);
  try {
    const body = simulationModel.body(linkName);
    const id = body.id;
    body.delete?.();
    mujocoBodyIds.set(linkName, id);
    return id;
  } catch {
    return null;
  }
}

function syncVisualsFromMujoco() {
  if (!simulationData) return;
  for (const linkName of visualRootLinks) {
    const group = visualLinkGroups.get(linkName);
    const bodyId = getMujocoBodyId(linkName);
    if (!group || bodyId === null) continue;
    const bodyTransform = new THREE.Matrix4().set(
      simulationData.xmat[bodyId * 9], simulationData.xmat[bodyId * 9 + 1], simulationData.xmat[bodyId * 9 + 2], simulationData.xpos[bodyId * 3],
      simulationData.xmat[bodyId * 9 + 3], simulationData.xmat[bodyId * 9 + 4], simulationData.xmat[bodyId * 9 + 5], simulationData.xpos[bodyId * 3 + 1],
      simulationData.xmat[bodyId * 9 + 6], simulationData.xmat[bodyId * 9 + 7], simulationData.xmat[bodyId * 9 + 8], simulationData.xpos[bodyId * 3 + 2],
      0, 0, 0, 1,
    );
    group.parent?.updateWorldMatrix(true, false);
    const parentInverse = group.parent ? group.parent.matrixWorld.clone().invert() : new THREE.Matrix4();
    setObjectFromMatrix(group, parentInverse.multiply(bodyTransform));
  }
  syncVisualJointTransforms();
}

function syncVisualJointTransforms() {
  if (!simulationData) return;
  for (const joint of visualJoints.values()) {
    const group = visualLinkGroups.get(joint.child);
    if (!group) continue;
    const initial = initialLinkTransforms.get(joint.child) || new THREE.Matrix4();
    const motion = new THREE.Matrix4();
    if (joint.type !== "fixed" && joint.qposAddress !== null) {
      const qposAddress = joint.qposAddress;
      const value = qposAddress === null ? 0 : simulationData.qpos[qposAddress];
      if (joint.type === "prismatic") motion.makeTranslation(joint.axis[0] * value, joint.axis[1] * value, joint.axis[2] * value);
      else motion.makeRotationAxis(new THREE.Vector3(...joint.axis).normalize(), value);
    }
    setObjectFromMatrix(group, initial.clone().multiply(motion));
  }
}

function setObjectFromMatrix(object, matrix) {
  object.position.setFromMatrixPosition(matrix);
  object.quaternion.setFromRotationMatrix(matrix);
}

function restoreInitialVisualTransforms() {
  for (const [linkName, group] of visualLinkGroups) {
    setObjectFromMatrix(group, initialLinkTransforms.get(linkName) || new THREE.Matrix4());
  }
}

function clearDragForce() {
  if (dragForce && simulationData?.xfrc_applied) {
    simulationData.xfrc_applied.fill(0, dragForce.bodyId * 6, dragForce.bodyId * 6 + 6);
  }
  dragForce = null;
}

function applyDragForce() {
  if (!dragForce || !simulationData) return;
  const { bodyId, localAnchor, target } = dragForce;
  const position = bodyId * 3;
  const rotation = bodyId * 9;
  const forceOffset = bodyId * 6;
  const { xpos, xmat, xipos, xfrc_applied } = simulationData;
  const anchor = new THREE.Vector3(
    xpos[position] + xmat[rotation] * localAnchor.x + xmat[rotation + 1] * localAnchor.y + xmat[rotation + 2] * localAnchor.z,
    xpos[position + 1] + xmat[rotation + 3] * localAnchor.x + xmat[rotation + 4] * localAnchor.y + xmat[rotation + 5] * localAnchor.z,
    xpos[position + 2] + xmat[rotation + 6] * localAnchor.x + xmat[rotation + 7] * localAnchor.y + xmat[rotation + 8] * localAnchor.z,
  );
  const force = target.clone().sub(anchor).multiplyScalar(50);
  const centerOfMass = new THREE.Vector3(xipos[position], xipos[position + 1], xipos[position + 2]);
  const torque = anchor.sub(centerOfMass).cross(force);
  xfrc_applied[forceOffset] = force.x;
  xfrc_applied[forceOffset + 1] = force.y;
  xfrc_applied[forceOffset + 2] = force.z;
  xfrc_applied[forceOffset + 3] = torque.x;
  xfrc_applied[forceOffset + 4] = torque.y;
  xfrc_applied[forceOffset + 5] = torque.z;
}

function displayName(robot) {
  return `${robot.name.replaceAll("_", " ")} · ${robot.dof} DOF`;
}

function renderRobotList() {
  robotList.replaceChildren();
  for (const robot of catalog) {
    const button = document.createElement("button");
    button.className = `robot-row ${robot.id === activeRobot?.id ? "active" : ""}`;
    button.innerHTML = `<span class="robot-name"><span></span><span class="badge"></span></span><span class="robot-meta"></span>`;
    button.querySelector(".robot-name span").textContent = robot.name;
    button.querySelector(".badge").textContent = robot.status;
    const errors = robot.summary.errors;
    const warnings = robot.summary.warnings;
    const meta = errors ? `${errors} error${errors === 1 ? "" : "s"}` : warnings ? `${warnings} warning${warnings === 1 ? "" : "s"}` : "validated";
    button.querySelector(".robot-meta").textContent = `${robot.dof} DOF · ${meta}`;
    if (errors) button.querySelector(".badge").classList.add("error");
    if (!errors && warnings) button.querySelector(".badge").classList.add("warning");
    button.addEventListener("click", () => selectRobot(robot.id));
    robotList.append(button);
  }
}

function jointUnit(joint) {
  return joint.type === 2 ? "m" : "rad";
}

function formatJointValue(value) {
  return Number.isFinite(value) ? value.toFixed(4) : "—";
}

function collectJointStates() {
  if (!simulationModel) return [];
  const joints = [];
  for (let id = 0; id < simulationModel.njnt; id += 1) {
    const joint = simulationModel.jnt(id);
    const type = Number(joint.type);
    const qposAddress = Number(joint.qposadr);
    const limited = Boolean(joint.limited);
    const lower = Number(joint.range?.[0] ?? simulationModel.jnt_range[id * 2]);
    const upper = Number(joint.range?.[1] ?? simulationModel.jnt_range[id * 2 + 1]);
    const configurable = type === 2 || type === 3;
    if (configurable) joints.push({ id, name: joint.name, type, qposAddress, limited, lower, upper });
    joint.delete?.();
  }
  return joints;
}

function cacheVisualJointAddresses() {
  for (const joint of visualJoints.values()) {
    try {
      const modelJoint = simulationModel.jnt(joint.name);
      joint.qposAddress = Number(modelJoint.qposadr);
      modelJoint.delete?.();
    } catch {
      joint.qposAddress = null;
    }
  }
}

function jointValue(joint) {
  return simulationData ? Number(simulationData.qpos[joint.qposAddress]) : NaN;
}

function sliderRange(joint) {
  if (joint.limited && Number.isFinite(joint.lower) && Number.isFinite(joint.upper) && joint.lower < joint.upper) {
    return [joint.lower, joint.upper];
  }
  return joint.type === 2 ? [-1, 1] : [-Math.PI, Math.PI];
}

function renderJointInspector() {
  jointList.replaceChildren();
  jointCount.textContent = jointStates.length ? `${jointStates.length}` : "";
  if (!jointStates.length) {
    const empty = document.createElement("p");
    empty.className = "joint-empty";
    empty.textContent = simulationModel ? "This model has no hinge or slide joints." : "Loading MuJoCo joint state…";
    jointList.append(empty);
    return;
  }
  for (const joint of jointStates) {
    const row = document.createElement("div");
    row.className = "joint-row";
    row.dataset.jointId = String(joint.id);
    const heading = document.createElement("div");
    heading.className = "joint-row-heading";
    const name = document.createElement("span");
    name.className = "joint-row-name";
    name.textContent = joint.name;
    const value = document.createElement("span");
    value.className = "joint-row-value";
    value.dataset.jointValue = String(joint.id);
    value.textContent = `${formatJointValue(jointValue(joint))} ${jointUnit(joint)}`;
    heading.append(name, value);
    const [lower, upper] = sliderRange(joint);
    const slider = document.createElement("input");
    slider.type = "range";
    slider.className = "joint-slider";
    slider.dataset.jointSlider = String(joint.id);
    slider.min = String(lower);
    slider.max = String(upper);
    slider.step = String(Math.max((upper - lower) / 1000, 0.0001));
    slider.value = String(Math.min(upper, Math.max(lower, jointValue(joint))));
    slider.setAttribute("aria-label", `Set ${joint.name} position`);
    slider.addEventListener("pointerdown", () => selectElement(joint.name, "joint"));
    slider.addEventListener("input", () => setJointPosition(joint.id, Number(slider.value)));
    const limits = document.createElement("div");
    limits.className = "joint-row-limits";
    limits.innerHTML = `<span>${formatJointValue(lower)}</span><span>${formatJointValue(upper)} ${jointUnit(joint)}</span>`;
    row.append(heading, slider, limits);
    jointList.append(row);
  }
}

function updateJointValues() {
  if (!simulationData || !jointStates.length) return;
  for (const joint of jointStates) {
    const value = `${formatJointValue(jointValue(joint))} ${jointUnit(joint)}`;
    const rowValue = jointList.querySelector(`[data-joint-value="${joint.id}"]`);
    if (rowValue) rowValue.textContent = value;
    const slider = jointList.querySelector(`[data-joint-slider="${joint.id}"]`);
    if (slider && document.activeElement !== slider) slider.value = String(Math.min(Number(slider.max), Math.max(Number(slider.min), jointValue(joint))));
  }
}

function selectJoint(id) {
  const joint = jointStates.find(item => item.id === id);
  if (!joint) return;
  activeJointId = id;
  selectElement(joint.name, "joint");
}

function setJointPosition(id, value) {
  const joint = jointStates.find(item => item.id === id);
  if (!joint || !simulationData || !simulationModel || !mujoco) return;
  const position = joint.limited ? Math.min(joint.upper, Math.max(joint.lower, value)) : value;
  simulationData.qpos[joint.qposAddress] = position;
  mujoco.mj_forward?.(simulationModel, simulationData);
  syncVisualsFromMujoco();
  updateJointValues();
}

function renderElements() {
  const filter = elementSearch.value.trim().toLowerCase();
  elementList.replaceChildren();
  if (!activeRobot) return;
  const items = [
    ...activeRobot.scene.links.map(item => ({ name: item.name, kind: "link" })),
    ...activeRobot.scene.joints.map(item => ({ name: item.name, kind: "joint" })),
  ].filter(item => item.name.toLowerCase().includes(filter));
  for (const item of items) {
    const button = document.createElement("button");
    button.className = `element ${item.name === selectedName && item.kind === selectedKind ? "active" : ""}`;
    const name = document.createElement("span");
    name.textContent = item.name;
    const kind = document.createElement("span");
    kind.className = "element-kind";
    kind.textContent = item.kind;
    button.append(name, kind);
    button.addEventListener("click", () => selectElement(item.name, item.kind));
    elementList.append(button);
  }
}

function clearRobot() {
  diagnostics.dispose();
  visualLinkGroups.clear();
  initialLinkTransforms.clear();
  visualJoints.clear();
  visualRootLinks.clear();
  while (robotGroup.children.length) {
    const child = robotGroup.children.pop();
    child.traverse(node => {
      node.geometry?.dispose?.();
      node.material?.dispose?.();
    });
  }
}

function visualBounds() {
  const bounds = new THREE.Box3();
  let hasVisualMesh = false;
  robotGroup.updateWorldMatrix(true, true);
  robotGroup.traverse(node => {
    if (node.userData.layer !== "visual-mesh" || !node.geometry) return;
    if (!node.geometry.boundingBox) node.geometry.computeBoundingBox();
    if (!node.geometry.boundingBox) return;
    bounds.union(node.geometry.boundingBox.clone().applyMatrix4(node.matrixWorld));
    hasVisualMesh = true;
  });
  return hasVisualMesh ? bounds : null;
}

function setTransform(object, origin) {
  object.position.fromArray(origin.xyz);
  object.rotation.set(...origin.rpy, "XYZ");
}

function collisionGeometry(collision) {
  if (collision.type === "box") return new THREE.BoxGeometry(...collision.size);
  if (collision.type === "sphere") return new THREE.SphereGeometry(collision.radius, 16, 10);
  if (collision.type === "cylinder") return new THREE.CylinderGeometry(collision.radius, collision.radius, collision.length, 16);
  return null;
}

async function addCollisionOverlay(collision, group, robot, token, controller) {
  let geometry = collisionGeometry(collision);
  if (collision.type === "mesh") {
    const filename = collision.filename.split("/").pop();
    const response = await fetch(`/api/robots/${encodeURIComponent(robot.id)}/files/${encodeURIComponent(filename)}`, { signal: controller.signal });
    if (!response.ok) throw new Error(`Could not load collision mesh ${filename}`);
    geometry = stlLoader.parse(await response.arrayBuffer());
    assertCurrentLoad(token, controller);
  }
  if (!geometry) return;
  const overlay = new THREE.LineSegments(
    new THREE.EdgesGeometry(geometry),
    new THREE.LineBasicMaterial({ color: 0xffb84d, transparent: true, opacity: 0.86 }),
  );
  overlay.userData = { link: group.name, layer: "collision-overlay" };
  overlay.visible = collisionShapesVisible;
  setTransform(overlay, collision.origin);
  if (collision.scale) overlay.scale.fromArray(collision.scale);
  group.add(overlay);
}

async function renderRobotMeshes(robot, token, controller) {
  clearRobot();
  const links = new Map();
  for (const link of robot.scene.links) {
    const group = new THREE.Group();
    group.name = link.name;
    links.set(link.name, group);
    visualLinkGroups.set(link.name, group);
    initialLinkTransforms.set(link.name, new THREE.Matrix4());
  }
  const childNames = new Set();
  for (const joint of robot.scene.joints) {
    const parent = links.get(joint.parent);
    const child = links.get(joint.child);
    if (!parent || !child) continue;
    setTransform(child, joint.origin);
    child.updateMatrix();
    initialLinkTransforms.set(joint.child, child.matrix.clone());
    visualJoints.set(joint.child, {
      name: joint.name,
      child: joint.child,
      type: joint.type === "prismatic" ? "prismatic" : joint.type === "fixed" ? "fixed" : "revolute",
      axis: joint.axis,
      qposAddress: null,
    });
    parent.add(child);
    childNames.add(joint.child);
  }
  for (const [name, link] of links) {
    if (childNames.has(name)) continue;
    robotGroup.add(link);
    visualRootLinks.add(name);
  }
  let renderedFirstMesh = false;
  for (const link of robot.scene.links) {
    const group = links.get(link.name);
    for (const visual of link.visuals) {
      const filename = visual.filename.split("/").pop();
      const response = await fetch(`/api/robots/${encodeURIComponent(robot.id)}/files/${encodeURIComponent(filename)}`, { signal: controller.signal });
      if (!response.ok) throw new Error(`Could not load ${filename}`);
      const buffer = await response.arrayBuffer();
      assertCurrentLoad(token, controller);
      if (!renderedFirstMesh) {
        renderedFirstMesh = true;
        viewerEmpty.hidden = true;
      }
      const geometry = stlLoader.parse(buffer);
      geometry.computeVertexNormals();
      const material = new THREE.MeshStandardMaterial({ color: 0xbfc9d3, metalness: .18, roughness: .58 });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.castShadow = true;
      mesh.userData = {
        link: link.name,
        layer: "visual-mesh",
        originalColor: material.color.clone(),
        originalMaterial: { opacity: material.opacity, transparent: material.transparent, depthWrite: material.depthWrite },
        filename,
      };
      mesh.visible = visualMeshesVisible;
      setTransform(mesh, visual.origin);
      mesh.scale.fromArray(visual.scale);
      group.add(mesh);
      if (robotGroup.children.length && renderedFirstMesh) {
        frameRobot();
      }
      await new Promise(resolve => requestAnimationFrame(resolve));
    }
    for (const collision of link.collisions || []) {
      try {
        await addCollisionOverlay(collision, group, robot, token, controller);
      } catch (error) {
        if (error?.name === "AbortError") throw error;
        console.warn(`Skipping collision overlay for ${link.name}: ${error.message}`);
      }
    }
  }
  if (isCurrentLoad(token, controller)) {
    const bounds = visualBounds();
    const visualBoundsDiagonal = bounds?.getSize(new THREE.Vector3()).length() || 0.5;
    diagnostics.bindRobot(robot, links, visualBoundsDiagonal);
    applyVisualMeshOpacity();
    viewerEmpty.hidden = true;
    frameRobot();
  }
}

function prepareSimulationSource(source, format, robot) {
  const parser = new DOMParser();
  const xml = parser.parseFromString(source, "application/xml");
  if (xml.querySelector("parsererror")) throw new Error("Model XML could not be parsed before MuJoCo loading.");
  for (const compiler of xml.querySelectorAll("compiler")) compiler.removeAttribute("meshdir");
  for (const mesh of xml.querySelectorAll("mesh[filename], mesh[file]")) {
    const attribute = mesh.hasAttribute("filename") ? "filename" : "file";
    const filename = mesh.getAttribute(attribute);
    mesh.setAttribute(attribute, filename.split("/").pop());
  }
  const makeFloor = () => {
    const floor = xml.createElement("geom");
    floor.setAttribute("name", "workbench_floor");
    floor.setAttribute("type", "plane");
    floor.setAttribute("size", "8 8 0.1");
    floor.setAttribute("rgba", "0.10 0.14 0.16 1");
    floor.setAttribute("friction", "1 0.01 0.001");
    return floor;
  };
  const rootLink = robot.scene.root_links[0];
  let injectedRootJoint = null;
  if (format === "mjcf") {
    for (const geom of xml.querySelectorAll("geom")) {
      if (geom.getAttribute("type") === "mesh" || geom.hasAttribute("mesh")) geom.remove();
    }
    for (const mesh of xml.querySelectorAll("asset > mesh")) mesh.remove();
    const worldbody = xml.querySelector("worldbody");
    if (worldbody) worldbody.append(makeFloor());
    const rootBody = rootLink ? xml.querySelector(`body[name="${CSS.escape(rootLink)}"]`) : null;
    if (rootBody) {
      const collider = xml.createElement("geom");
      collider.setAttribute("name", "workbench_root_collision");
      collider.setAttribute("type", "box");
      collider.setAttribute("size", "0.18 0.16 0.25");
      collider.setAttribute("pos", "0 0 0");
      collider.setAttribute("friction", "1 0.01 0.001");
      rootBody.append(collider);
    }
  } else {
    let mujocoExtension = xml.querySelector("robot > mujoco");
    if (!mujocoExtension) {
      mujocoExtension = xml.createElement("mujoco");
      xml.documentElement.append(mujocoExtension);
    }
    const hasFloatingBase = [...xml.querySelectorAll("joint[type='floating']")].some(joint => !joint.closest("mujoco"));
    let floorParent = "workbench_world";
    if (!hasFloatingBase) {
      if (!rootLink) throw new Error("The URDF has no root link for local free-base physics.");
      const worldLink = xml.createElement("link");
      worldLink.setAttribute("name", "workbench_world");
      const rootJoint = xml.createElement("joint");
      rootJoint.setAttribute("name", "workbench_floating_base");
      rootJoint.setAttribute("type", "floating");
      const parent = xml.createElement("parent");
      parent.setAttribute("link", "workbench_world");
      const child = xml.createElement("child");
      child.setAttribute("link", rootLink);
      rootJoint.append(parent, child);
      xml.documentElement.append(worldLink, rootJoint);
      injectedRootJoint = rootJoint.getAttribute("name");
    } else {
      floorParent = "world";
    }
    for (const geometry of xml.querySelectorAll("robot > link > visual, robot > link > collision")) geometry.remove();
    const rootLinkNode = rootLink ? [...xml.querySelectorAll("robot > link")].find(link => link.getAttribute("name") === rootLink) : null;
    if (rootLinkNode) {
      const collision = xml.createElement("collision");
      collision.setAttribute("name", "workbench_root_collision");
      const geometry = xml.createElement("geometry");
      const box = xml.createElement("box");
      box.setAttribute("size", "0.36 0.32 0.50");
      geometry.append(box);
      collision.append(geometry);
      rootLinkNode.append(collision);
    }
    if (!hasFloatingBase && rootLink) {
      const floorLink = xml.createElement("link");
      floorLink.setAttribute("name", "workbench_floor_link");
      const collision = xml.createElement("collision");
      collision.setAttribute("name", "workbench_floor");
      const origin = xml.createElement("origin");
      origin.setAttribute("xyz", "0 0 -0.05");
      const geometry = xml.createElement("geometry");
      const box = xml.createElement("box");
      box.setAttribute("size", "16 16 0.1");
      geometry.append(box);
      collision.append(origin, geometry);
      floorLink.append(collision);
      const floorJoint = xml.createElement("joint");
      floorJoint.setAttribute("name", "workbench_floor_joint");
      floorJoint.setAttribute("type", "fixed");
      const parent = xml.createElement("parent");
      parent.setAttribute("link", floorParent);
      const child = xml.createElement("child");
      child.setAttribute("link", "workbench_floor_link");
      floorJoint.append(parent, child);
      xml.documentElement.append(floorLink, floorJoint);
    }
  }
  return { source: new XMLSerializer().serializeToString(xml), injectedRootJoint };
}

async function loadMujocoModel(robot, token, controller) {
  setEngineState("Loading MuJoCo WASM model…");
  const objects = [];
  try {
    mujoco ||= await loadMujoco({ locateFile: file => `/vendor/${file}` });
    assertCurrentLoad(token, controller);
    const format = robot.formats.mjcf ? "mjcf" : "urdf";
    const raw = await fetch(`/api/robots/${encodeURIComponent(robot.id)}/source?format=${format}`, { signal: controller.signal })
      .then(response => response.ok ? response.text() : Promise.reject(new Error("Could not load model source")));
    assertCurrentLoad(token, controller);
    const prepared = prepareSimulationSource(raw, format, robot);
    const vfs = new mujoco.MjVFS();
    objects.push(vfs);
    const sourceDocument = new DOMParser().parseFromString(prepared.source, "application/xml");
    const names = [...new Set([...sourceDocument.querySelectorAll("mesh[filename], mesh[file]")].map(node => (node.getAttribute("filename") || node.getAttribute("file")).split("/").pop()))];
    for (const name of names) {
      const bytes = await fetch(`/api/robots/${encodeURIComponent(robot.id)}/files/${encodeURIComponent(name)}`, { signal: controller.signal })
        .then(response => response.ok ? response.arrayBuffer() : Promise.reject(new Error(`Could not read ${name}`)));
      assertCurrentLoad(token, controller);
      vfs.addBuffer(name, new Uint8Array(bytes));
    }
    assertCurrentLoad(token, controller);
    const model = mujoco.MjModel.from_xml_string(prepared.source, vfs);
    const data = new mujoco.MjData(model);
    objects.push(model, data);
    assertCurrentLoad(token, controller);
    disposeWasm();
    wasmObjects = objects;
    simulationModel = model;
    simulationData = data;
    simulationRootJoint = prepared.injectedRootJoint;
    cacheVisualJointAddresses();
    jointStates = collectJointStates();
    physicsEnabled = false;
    resetSimulation();
    renderJointInspector();
    updateSimulationControls("Model ready. Press P to toggle physics.");
    setEngineState(`MuJoCo WASM loaded · ${model.nbody} bodies · ${model.ngeom} geoms`, "ready");
  } catch (error) {
    deleteWasmObjects(objects);
    if (error?.name === "AbortError") return;
    if (isCurrentLoad(token, controller)) {
      physicsEnabled = false;
      updateSimulationControls("Model load failed. Select a robot to try again.");
      setEngineState(`MuJoCo WASM model check failed: ${error?.message || error}`, "error");
    }
  }
}

async function selectRobot(id) {
  loadAbortController?.abort();
  const controller = new AbortController();
  loadAbortController = controller;
  const token = ++loadVersion;
  viewerEmpty.hidden = false;
  viewerEmpty.textContent = "Loading robot assets…";
  try {
    const data = await api(`/api/robots/${encodeURIComponent(id)}`);
    assertCurrentLoad(token, controller);
    activeRobot = data.robot;
    selectedName = null;
    selectedKind = null;
    selectedTitle.textContent = displayName(activeRobot);
    selectedElement.textContent = "None";
    selectedSource.textContent = activeRobot.formats.mjcf ? "MJCF + URDF" : "URDF";
    physicsEnabled = false;
    followEnabled = false;
    updateSimulationControls("Loading MuJoCo model…");
    renderRobotList();
    renderElements();
    await Promise.all([renderRobotMeshes(activeRobot, token, controller), loadMujocoModel(activeRobot, token, controller)]);
    if (isCurrentLoad(token, controller) && simulationModel) {
      cacheVisualJointAddresses();
      restoreInitialVisualTransforms();
    }
  } catch (error) {
    if (error?.name === "AbortError") return;
    viewerEmpty.hidden = false;
    viewerEmpty.textContent = error.message;
    setEngineState(error.message, "error");
  }
}

function selectElement(name, kind) {
  if (!activeRobot || !name) return;
  let resolvedName = name;
  if (kind === "joint") resolvedName = activeRobot.scene.joints.find(joint => joint.name === name)?.child || name;
  selectedName = name;
  selectedKind = kind || "link";
  selectedElement.textContent = name;
  const source = activeRobot.scene.links.find(link => link.name === resolvedName)?.visuals[0]?.filename;
  selectedSource.textContent = source || kind || "robot";
  if (kind === "joint") {
    const joint = jointStates.find(item => item.name === name);
    if (joint) activeJointId = joint.id;
  }
  robotGroup.traverse(node => {
    if (node.userData.layer !== "visual-mesh") return;
    const material = node.material;
    material.color.copy(node.userData.originalColor);
    if (node.userData.link === resolvedName) material.color.set(0xd5ff4c);
  });
  renderElements();
}

function frameRobot() {
  const bounds = visualBounds();
  if (!bounds || bounds.isEmpty()) return;
  const center = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3()).length();
  controls.target.copy(center);
  camera.position.copy(center).add(new THREE.Vector3(size * 1.15, -size * 1.15, size * .65));
  camera.near = Math.max(size / 1000, .001);
  camera.far = Math.max(size * 20, 10);
  camera.updateProjectionMatrix();
  controls.update();
}

function resize() {
  const { width, height } = canvas.getBoundingClientRect();
  if (!width || !height) return;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function animate() {
  const deltaSeconds = Math.min(simulationClock.getDelta(), 0.05);
  advancePhysics(deltaSeconds);
  if (performance.now() - lastJointStatusUpdate > 100) {
    updateJointValues();
    lastJointStatusUpdate = performance.now();
  }
  if (followEnabled && robotGroup.children.length) {
    const bounds = visualBounds();
    if (bounds) controls.target.lerp(bounds.getCenter(new THREE.Vector3()), Math.min(deltaSeconds * 7, 1));
  }
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

function pickRobotPart(event) {
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  return raycaster.intersectObject(robotGroup, true).find(result => result.object.userData.link && !result.object.userData.visualDiagnostic);
}

canvas.addEventListener("pointerdown", event => {
  const hit = pickRobotPart(event);
  if (!hit) return;
  const link = hit.object.userData.link;
  const bodyId = getMujocoBodyId(link);
  pointerGesture = { link, startX: event.clientX, startY: event.clientY, dragging: false };
  if (bodyId !== null && simulationData) {
    const position = bodyId * 3;
    const rotation = bodyId * 9;
    const { xpos, xmat } = simulationData;
    const offset = hit.point.clone().sub(new THREE.Vector3(xpos[position], xpos[position + 1], xpos[position + 2]));
    const localAnchor = new THREE.Vector3(
      xmat[rotation] * offset.x + xmat[rotation + 3] * offset.y + xmat[rotation + 6] * offset.z,
      xmat[rotation + 1] * offset.x + xmat[rotation + 4] * offset.y + xmat[rotation + 7] * offset.z,
      xmat[rotation + 2] * offset.x + xmat[rotation + 5] * offset.y + xmat[rotation + 8] * offset.z,
    );
    const normal = camera.getWorldDirection(new THREE.Vector3()).normalize();
    dragForce = { bodyId, localAnchor, target: hit.point.clone(), plane: new THREE.Plane().setFromNormalAndCoplanarPoint(normal, hit.point) };
  }
  canvas.setPointerCapture(event.pointerId);
});

canvas.addEventListener("pointermove", event => {
  if (!pointerGesture) return;
  const moved = Math.hypot(event.clientX - pointerGesture.startX, event.clientY - pointerGesture.startY);
  if (!pointerGesture.dragging && moved > 5) {
    pointerGesture.dragging = true;
    controls.enabled = false;
    canvas.classList.add("pushing");
  }
  if (pointerGesture.dragging && dragForce) {
    const rect = canvas.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    raycaster.ray.intersectPlane(dragForce.plane, dragForce.target);
    if (!physicsEnabled) updateSimulationControls("Push queued on the selected link. Turn Physics on to integrate it.");
  }
});

function finishPointerGesture(event) {
  if (!pointerGesture) return;
  if (!pointerGesture.dragging) selectElement(pointerGesture.link, "link");
  controls.enabled = true;
  canvas.classList.remove("pushing");
  if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
  clearDragForce();
  pointerGesture = null;
}

canvas.addEventListener("pointerup", finishPointerGesture);
canvas.addEventListener("pointercancel", finishPointerGesture);

window.addEventListener("keydown", event => {
  if (event.repeat || event.target.matches("input, textarea, select, button")) return;
  if (event.key.toLowerCase() === "p") {
    event.preventDefault();
    togglePhysics();
  } else if (event.key.toLowerCase() === "r") {
    event.preventDefault();
    resetSimulation();
  } else if (event.key.toLowerCase() === "f") {
    event.preventDefault();
    toggleFollow();
  }
});

document.querySelector("#reset-camera").addEventListener("click", frameRobot);
physicsToggle.addEventListener("click", togglePhysics);
physicsReset.addEventListener("click", resetSimulation);
followToggle.addEventListener("click", toggleFollow);
visualMeshToggle.addEventListener("click", toggleVisualMeshes);
collisionShapeToggle.addEventListener("click", toggleCollisionShapes);
meshOpacity.addEventListener("input", () => setMeshOpacity(meshOpacity.value));
centerOfMassToggle.addEventListener("click", () => toggleDiagnostics("centersOfMass"));
linkFrameToggle.addEventListener("click", () => toggleDiagnostics("linkFrames"));
worldFrameToggle.addEventListener("click", () => toggleDiagnostics("worldFrame"));
jointAxisToggle.addEventListener("click", () => toggleDiagnostics("jointAxes"));
elementSearch.addEventListener("input", renderElements);
document.querySelector("#collapse-menagerie").addEventListener("click", () => {
  document.querySelector(".workbench").classList.add("collapsed");
  document.querySelector("#expand-menagerie").classList.remove("hidden");
  setTimeout(resize, 200);
});
document.querySelector("#expand-menagerie").addEventListener("click", () => {
  document.querySelector(".workbench").classList.remove("collapsed");
  document.querySelector("#expand-menagerie").classList.add("hidden");
  setTimeout(resize, 200);
});
for (const tab of document.querySelectorAll(".tab")) tab.addEventListener("click", () => {
  document.querySelectorAll(".tab, .tab-panel").forEach(node => node.classList.remove("active"));
  tab.classList.add("active");
  document.querySelector(`#${tab.dataset.tab}-panel`).classList.add("active");
});
new ResizeObserver(resize).observe(canvas);
resize();
updateDisplayControls();
animate();

try {
  const data = await api("/api/robots");
  catalog = data.robots;
  await selectRobot(catalog[0]?.id);
} catch (error) {
  viewerEmpty.textContent = error.message;
  setEngineState(error.message, "error");
}
