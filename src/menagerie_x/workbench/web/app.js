import * as THREE from "/vendor/three.module.js";
import { OrbitControls } from "/vendor/OrbitControls.js";
import loadMujoco from "/vendor/mujoco.js";
import { createMjcfRenderer } from "/mjcf-renderer.js";
import {
  POSITION_SLIDER_LIMIT,
  PRIMITIVE_TYPES,
  defaultCollision,
  degreesToRadians,
  isPickableSceneObject,
  positionSliderValue,
  primitiveGeometry,
  radiansToDegrees,
} from "/collision-editor.js";
import { createVisualDiagnostics } from "/diagnostics.js";
import { createContactVisualizer } from "/contact-visualizer.js";

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
const randomPoseButton = document.querySelector("#random-pose");
const visualMeshToggle = document.querySelector("#visual-mesh-toggle");
const collisionShapeToggle = document.querySelector("#collision-shape-toggle");
const meshOpacity = document.querySelector("#mesh-opacity");
const meshOpacityValue = document.querySelector("#mesh-opacity-value");
const centerOfMassToggle = document.querySelector("#center-of-mass-toggle");
const linkFrameToggle = document.querySelector("#link-frame-toggle");
const worldFrameToggle = document.querySelector("#world-frame-toggle");
const jointAxisToggle = document.querySelector("#joint-axis-toggle");
const simulationState = document.querySelector("#simulation-state");
const collisionLink = document.querySelector("#collision-link");
const collisionList = document.querySelector("#collision-list");
const collisionDetail = document.querySelector("#collision-detail");
const collisionStatus = document.querySelector("#collision-status");
const collisionExport = document.querySelector("#collision-export");
const collisionDrawer = document.querySelector("#collision-drawer");
const collisionDrawerContent = document.querySelector("#collision-drawer-content");
const collisionDrawerToggle = document.querySelector("#collision-drawer-toggle");
const collisionDrawerClose = document.querySelector("#collision-drawer-close");
const collisionContactCount = document.querySelector("#collision-contact-count");
const mjcfTitle = document.querySelector("#mjcf-title");
const mjcfSource = document.querySelector("#mjcf-source");
const mjcfCandidateId = document.querySelector("#mjcf-candidate-id");
const mjcfGenerate = document.querySelector("#mjcf-generate");
const mjcfStatus = document.querySelector("#mjcf-status");
const mjcfCandidateList = document.querySelector("#mjcf-candidate-list");

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x07100a);
renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 100);
camera.up.set(0, 0, 1);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0.75);
controls.enableDamping = true;
const robotGroup = new THREE.Group();
scene.add(robotGroup);
const sceneGroup = new THREE.Group();
scene.add(sceneGroup);
scene.add(new THREE.HemisphereLight(0xe8f0db, 0x0d2417, 2.1));
const keyLight = new THREE.DirectionalLight(0xf2f7e8, 2.35);
keyLight.position.set(3, -3, 5);
scene.add(keyLight);
const grid = new THREE.GridHelper(4, 16, 0x4d865f, 0x244a31);
grid.rotateX(Math.PI / 2);
scene.add(grid);
const forceIndicator = new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), new THREE.Vector3(), 0.001, 0xe8bd66, 0.08, 0.045);
forceIndicator.visible = false;
forceIndicator.renderOrder = 2;
scene.add(forceIndicator);
const diagnostics = createVisualDiagnostics(scene);
const contactVisualizer = createContactVisualizer(scene, updateContactState);

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const mjcfRenderer = createMjcfRenderer(robotGroup);
let catalog = [];
let activeRobot = null;
let activeCandidateId = null;
let mjcfCandidates = [];
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
let forceHighlightedLink = null;
let simulationRootJoint = null;
let jointStates = [];
let activeJointId = null;
let lastJointStatusUpdate = 0;
let randomPoseMotion = null;
let collisionDocument = null;
let collisionDraft = [];
let collisionDraftId = null;
let retainedMeshIds = new Set();
let collisionDraftSave = Promise.resolve();
let collisionDraftSaveTimer = null;
let selectedCollisionId = null;
let collisionMode = false;
let collisionDrawerExpanded = false;
let collisionDraftDirty = false;
let contactGeomIds = new Set();
let contactGeomNames = new Set();
let diagnosticObjects = [];
let diagnosticModel = null;
let diagnosticData = null;
let diagnosticGeneration = 0;
let diagnosticController = null;
const meshAssetCache = new Map();
const visualLinkGroups = new Map();
const mujocoBodyIds = new Map();
const collisionObjects = new Map();
const simulationClock = new THREE.Clock();

function api(path) {
  return fetch(path).then(async response => {
    const data = await response.json().catch(() => ({ ok: false, error: response.statusText }));
    if (!response.ok || !data.ok) throw new Error(data.error || "Request failed");
    return data;
  });
}

function apiRequest(path, method, payload = null) {
  return fetch(path, {
    method,
    headers: payload === null ? undefined : { "Content-Type": "application/json" },
    body: payload === null ? undefined : JSON.stringify(payload),
  }).then(async response => {
    const data = await response.json().catch(() => ({ ok: false, error: response.statusText }));
    if (!response.ok || !data.ok) throw new Error(data.error || "Request failed");
    return data;
  });
}

function activateTab(name) {
  document.querySelectorAll(".tab, .tab-panel").forEach(node => node.classList.remove("active"));
  document.querySelector(`.tab[data-tab="${name}"]`)?.classList.add("active");
  document.querySelector(`#${name}-panel`)?.classList.add("active");
}

function setMjcfStatus(message, error = false) {
  mjcfStatus.textContent = message;
  mjcfStatus.classList.toggle("error", error);
}

function nextMjcfCandidateId(robot) {
  const used = new Set(mjcfCandidates.map(record => record.id));
  const authorizedCandidateId = robot.mjcf_provenance?.candidate_id;
  if (authorizedCandidateId) used.add(authorizedCandidateId);
  const base = `${robot.id}-candidate`;
  let candidateId = base;
  let suffix = 2;
  while (used.has(candidateId)) {
    candidateId = `${base}-${suffix}`;
    suffix += 1;
  }
  return candidateId;
}

function ensureMjcfCandidateId() {
  if (!activeRobot || mjcfCandidateId.dataset.robotId === activeRobot.id) return;
  mjcfCandidateId.value = nextMjcfCandidateId(activeRobot);
  mjcfCandidateId.dataset.robotId = activeRobot.id;
}

async function refreshMjcfCandidates() {
  if (!activeRobot) return;
  const data = await api(`/api/robots/${encodeURIComponent(activeRobot.id)}/mjcf-candidates`);
  mjcfCandidates = data.candidates;
  ensureMjcfCandidateId();
  renderMjcfPanel();
}

function renderMjcfPanel() {
  mjcfCandidateList.replaceChildren();
  if (!activeRobot) {
    mjcfTitle.textContent = "Select a variant";
    mjcfSource.textContent = "URDF remains the authored source. Workbench loads reviewed MJCF.";
    mjcfGenerate.disabled = true;
    return;
  }
  const authorized = activeRobot.workbench_loadable;
  mjcfTitle.textContent = authorized ? "Authorized MJCF" : "URDF-to-MJCF review";
  mjcfSource.textContent = authorized
    ? `Authorized candidate: ${activeRobot.mjcf_provenance?.candidate_id || "legacy MJCF"}. Generate another review candidate without replacing this MJCF.`
    : `URDF revision ${activeRobot.source_revision.slice(0, 12)}. Generate a review candidate for ${activeRobot.name}.`;
  mjcfGenerate.disabled = false;
  for (const record of mjcfCandidates) {
    const row = document.createElement("div");
    row.className = `mjcf-candidate ${record.id === activeCandidateId ? "active" : ""}`;
    const name = document.createElement("strong");
    name.className = "mjcf-candidate-name";
    name.textContent = record.id;
    const meta = document.createElement("span");
    meta.className = "mjcf-candidate-meta";
    meta.textContent = record.valid
      ? `${record.model.nbody} bodies · ${record.model.ngeom} geoms${record.source_drift_warning ? " · source drift" : ""}`
      : `Invalid: ${record.error}`;
    row.append(name, meta);
    if (record.valid) {
      const actions = document.createElement("div");
      actions.className = "mjcf-candidate-actions";
      const preview = document.createElement("button");
      preview.textContent = "Preview";
      preview.addEventListener("click", () => previewMjcfCandidate(record.id));
      const authorize = document.createElement("button");
      authorize.className = "authorize";
      authorize.textContent = "Authorize";
      authorize.disabled = authorized;
      authorize.addEventListener("click", () => authorizeMjcfCandidate(record));
      const discard = document.createElement("button");
      discard.className = "discard";
      discard.textContent = "Discard";
      discard.addEventListener("click", () => discardMjcfCandidate(record));
      actions.append(preview, authorize, discard);
      row.append(actions);
    }
    mjcfCandidateList.append(row);
  }
}

async function generateMjcfCandidate() {
  if (!activeRobot) return;
  const candidateId = mjcfCandidateId.value.trim();
  mjcfGenerate.disabled = true;
  setMjcfStatus("Converting URDF and validating MJCF candidate…");
  try {
    const result = await apiRequest(`/api/robots/${encodeURIComponent(activeRobot.id)}/mjcf-candidates`, "POST", { candidate_id: candidateId });
    setMjcfStatus(`Generated ${result.candidate.candidate_id} at ${result.output}`);
    activeCandidateId = result.candidate.candidate_id;
    await refreshMjcfCandidates();
    mjcfCandidateId.value = nextMjcfCandidateId(activeRobot);
  } catch (error) {
    setMjcfStatus(error.message, true);
  } finally {
    renderMjcfPanel();
  }
}

async function previewMjcfCandidate(candidateId) {
  if (!activeRobot) return;
  activeCandidateId = candidateId;
  selectedSource.textContent = "MJCF candidate preview";
  viewerEmpty.hidden = false;
  viewerEmpty.textContent = "Loading MJCF candidate preview…";
  const controller = new AbortController();
  loadAbortController?.abort();
  loadAbortController = controller;
  const token = ++loadVersion;
  try {
    await loadMujocoModel(activeRobot, token, controller);
    if (isCurrentLoad(token, controller)) {
      selectedTitle.textContent = `${displayName(activeRobot)} · Candidate preview`;
      setMjcfStatus(`Previewing ${candidateId}. It is not authorized.`);
      renderMjcfPanel();
    }
  } catch (error) {
    setMjcfStatus(error.message, true);
  }
}

async function authorizeMjcfCandidate(record) {
  if (!activeRobot || activeRobot.workbench_loadable) return;
  const warning = record.source_drift_warning ? `\n\nWarning: ${record.source_drift_warning}` : "";
  if (!window.confirm(`Authorize ${record.id} for ${activeRobot.name}? This registers the candidate in the manifest.${warning}`)) return;
  try {
    await apiRequest(`/api/robots/${encodeURIComponent(activeRobot.id)}/mjcf-candidates/${encodeURIComponent(record.id)}/authorize`, "POST", { expected_source_revision: record.candidate.source_revision });
    setMjcfStatus(`Authorized ${record.id}. Reloading Workbench model…`);
    const catalogData = await api("/api/robots");
    catalog = catalogData.robots;
    activeCandidateId = null;
    await selectRobot(activeRobot.id);
  } catch (error) {
    setMjcfStatus(error.message, true);
  }
}

async function discardMjcfCandidate(record) {
  if (!activeRobot || !window.confirm(`Discard review candidate ${record.id}?`)) return;
  try {
    await apiRequest(`/api/robots/${encodeURIComponent(activeRobot.id)}/mjcf-candidates/${encodeURIComponent(record.id)}`, "DELETE");
    if (activeCandidateId === record.id) activeCandidateId = null;
    await refreshMjcfCandidates();
    setMjcfStatus(`Discarded ${record.id}.`);
  } catch (error) {
    setMjcfStatus(error.message, true);
  }
}

function deleteWasmObjects(objects) {
  for (const object of objects.splice(0).reverse()) object.delete?.();
}

function disposeWasm() {
  clearDragForce();
  cancelRandomPoseMotion();
  disposeDiagnosticModel();
  contactVisualizer.unbind();
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

function disposeDiagnosticModel() {
  diagnosticGeneration += 1;
  diagnosticController?.abort();
  diagnosticController = null;
  deleteWasmObjects(diagnosticObjects);
  diagnosticModel = null;
  diagnosticData = null;
}

function updateContactState({ count, geomIds, geomNames }) {
  contactGeomIds = geomIds;
  contactGeomNames = geomNames;
  collisionContactCount.textContent = `${count} contact${count === 1 ? "" : "s"}`;
  refreshCollisionObjectStyles();
  paintCompiledCollisionContacts();
}

function isCurrentLoad(token, controller) {
  return token === loadVersion && controller === loadAbortController && !controller.signal.aborted;
}

function assertCurrentLoad(token, controller) {
  if (!isCurrentLoad(token, controller)) throw new DOMException("Robot load was superseded.", "AbortError");
}

function handleSimulationError(error) {
  physicsEnabled = false;
  clearDragForce();
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
  physicsToggle.disabled = !simulationModel || collisionMode;
  physicsReset.disabled = !simulationModel || collisionMode;
  randomPoseButton.disabled = !simulationModel || collisionMode || !limitedJointStates().length;
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
  setLayerVisibility("collision-editor", collisionShapesVisible);
  contactVisualizer.setVisible(collisionShapesVisible);
  if (collisionShapesVisible) syncContactVisualization();
  else clearContactVisualization();
  updateDisplayControls();
}

function clearContactVisualization() {
  contactVisualizer.clear();
}

function syncContactVisualization() {
  if (!collisionShapesVisible) return;
  const model = collisionMode && diagnosticModel ? diagnosticModel : simulationModel;
  const data = collisionMode && diagnosticData ? diagnosticData : simulationData;
  if (!model || !data || !mujoco) return;
  contactVisualizer.bind(mujoco, model, data);
  contactVisualizer.setVisible(true);
  contactVisualizer.sync();
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
    cancelRandomPoseMotion();
    clearDragForce();
    mujoco.mj_resetData(simulationModel, simulationData);
    if (simulationRootJoint !== null) {
      const root = simulationModel.jnt(simulationRootJoint);
      const spawn = activeRobot?.scene_description?.robot_spawn || { xyz: [0, 0, 0.75], rpy: [0, 0, 0] };
      const orientation = new THREE.Quaternion().setFromEuler(new THREE.Euler(...spawn.rpy, "XYZ"));
      const address = Number(root.qposadr);
      simulationData.qpos.set([...spawn.xyz, orientation.w, orientation.x, orientation.y, orientation.z], address);
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
  if (!simulationModel || collisionMode) return;
  cancelRandomPoseMotion();
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

function limitedJointStates() {
  return jointStates.filter(joint => joint.limited && Number.isFinite(joint.lower) && Number.isFinite(joint.upper) && joint.lower < joint.upper);
}

function cancelRandomPoseMotion() {
  randomPoseMotion = null;
}

function applyJointPose(pose) {
  if (!simulationData || !simulationModel || !mujoco) return;
  for (const { joint, value } of pose) simulationData.qpos[joint.qposAddress] = value;
  mujoco.mj_forward?.(simulationModel, simulationData);
  syncVisualsFromMujoco();
  updateJointValues();
}

function driveRandomPose() {
  if (!simulationModel || !simulationData || !mujoco || collisionMode) return;
  const joints = limitedJointStates();
  if (!joints.length) {
    updateSimulationControls("No limited hinge or slide joints are available for a random pose.");
    return;
  }
  physicsEnabled = false;
  clearDragForce();
  simulationData.qvel.fill(0);
  randomPoseMotion = {
    startedAt: performance.now(),
    durationMs: 600,
    pose: joints.map(joint => ({
      joint,
      start: jointValue(joint),
      target: joint.lower + Math.random() * (joint.upper - joint.lower),
    })),
  };
  updateSimulationControls(`Driving a random pose across ${joints.length} limited joints.`);
}

function advanceRandomPose() {
  if (!randomPoseMotion || !simulationData) return;
  const elapsed = performance.now() - randomPoseMotion.startedAt;
  const progress = Math.min(Math.max(elapsed / randomPoseMotion.durationMs, 0), 1);
  const eased = progress * progress * (3 - 2 * progress);
  applyJointPose(randomPoseMotion.pose.map(({ joint, start, target }) => ({ joint, value: start + (target - start) * eased })));
  if (progress < 1) return;
  simulationData.qvel.fill(0);
  randomPoseMotion = null;
  updateSimulationControls("Random pose reached. Physics remains paused.");
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
  mjcfRenderer.sync(simulationData);
  diagnostics.syncMujoco(simulationData);
  if (!collisionMode) syncContactVisualization();
}

function restoreInitialVisualTransforms() {
  syncVisualsFromMujoco();
}

function setForceLinkHighlight(link) {
  if (forceHighlightedLink === link) return;
  forceHighlightedLink = link;
  robotGroup.traverse(node => {
    if (!node.isMesh || node.userData.layer !== "visual-mesh" || !node.material?.emissive) return;
    const material = node.material;
    node.userData.originalEmissive ??= material.emissive.clone();
    node.userData.originalEmissiveIntensity ??= material.emissiveIntensity;
    if (node.userData.link === link) {
      material.emissive.set(0xe3b34e);
      material.emissiveIntensity = 0.8;
    } else {
      material.emissive.copy(node.userData.originalEmissive);
      material.emissiveIntensity = node.userData.originalEmissiveIntensity;
    }
  });
}

function dragForceValues() {
  if (!dragForce || !simulationData) return null;
  const { bodyId, localAnchor, target } = dragForce;
  const position = bodyId * 3;
  const rotation = bodyId * 9;
  const { xpos, xmat, xipos } = simulationData;
  const anchor = new THREE.Vector3(
    xpos[position] + xmat[rotation] * localAnchor.x + xmat[rotation + 1] * localAnchor.y + xmat[rotation + 2] * localAnchor.z,
    xpos[position + 1] + xmat[rotation + 3] * localAnchor.x + xmat[rotation + 4] * localAnchor.y + xmat[rotation + 5] * localAnchor.z,
    xpos[position + 2] + xmat[rotation + 6] * localAnchor.x + xmat[rotation + 7] * localAnchor.y + xmat[rotation + 8] * localAnchor.z,
  );
  const force = target.clone().sub(anchor).multiplyScalar(50);
  const centerOfMass = new THREE.Vector3(xipos[position], xipos[position + 1], xipos[position + 2]);
  return { anchor, force, torque: anchor.clone().sub(centerOfMass).cross(force) };
}

function updateDragForceIndicator() {
  const values = dragForceValues();
  if (!values) {
    forceIndicator.visible = false;
    return;
  }
  const magnitude = values.force.length();
  if (magnitude < 1e-5) {
    forceIndicator.visible = false;
    return;
  }
  // One metre represents 100 N; cap the visual so an extreme drag stays in frame.
  const length = Math.min(Math.max(magnitude / 100, 0.025), 0.8);
  forceIndicator.position.copy(values.anchor);
  forceIndicator.setDirection(values.force.clone().normalize());
  forceIndicator.setLength(length, Math.min(length * 0.28, 0.12), Math.min(length * 0.16, 0.07));
  forceIndicator.userData.forceMagnitude = magnitude;
  forceIndicator.visible = true;
}

function clearDragForce() {
  if (dragForce && simulationData?.xfrc_applied) {
    simulationData.xfrc_applied.fill(0, dragForce.bodyId * 6, dragForce.bodyId * 6 + 6);
  }
  dragForce = null;
  forceIndicator.visible = false;
  setForceLinkHighlight(null);
}

function applyDragForce() {
  if (!dragForce || !simulationData) return;
  const { bodyId } = dragForce;
  const forceOffset = bodyId * 6;
  const values = dragForceValues();
  if (!values) return;
  const { force, torque } = values;
  simulationData.xfrc_applied[forceOffset] = force.x;
  simulationData.xfrc_applied[forceOffset + 1] = force.y;
  simulationData.xfrc_applied[forceOffset + 2] = force.z;
  simulationData.xfrc_applied[forceOffset + 3] = torque.x;
  simulationData.xfrc_applied[forceOffset + 4] = torque.y;
  simulationData.xfrc_applied[forceOffset + 5] = torque.z;
  updateDragForceIndicator();
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
    if (!robot.workbench_loadable) {
      button.classList.add("requires-mjcf");
      button.title = "MJCF required — open the MJCF panel to create a review candidate.";
      button.querySelector(".robot-meta").textContent = `${robot.dof} DOF · MJCF required`;
    }
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
    slider.disabled = collisionMode;
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
  if (collisionMode) return;
  const joint = jointStates.find(item => item.id === id);
  if (!joint || !simulationData || !simulationModel || !mujoco) return;
  cancelRandomPoseMotion();
  const position = joint.limited ? Math.min(joint.upper, Math.max(joint.lower, value)) : value;
  applyJointPose([{ joint, value: position }]);
}

function renderElements() {
  const filter = elementSearch.value.trim().toLowerCase();
  elementList.replaceChildren();
  if (!activeRobot) return;
  const items = [
    ...[...visualLinkGroups.keys()].map(name => ({ name, kind: "link" })),
    ...jointStates.map(item => ({ name: item.name, kind: "joint" })),
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
  mjcfRenderer.clear();
  collisionObjects.clear();
  clearSceneObjects();
  diagnostics.dispose();
  visualLinkGroups.clear();
  while (robotGroup.children.length) {
    const child = robotGroup.children.pop();
    child.traverse(node => {
      node.geometry?.dispose?.();
      node.material?.dispose?.();
    });
  }
}

function clearSceneObjects() {
  while (sceneGroup.children.length) {
    const child = sceneGroup.children.pop();
    child.removeFromParent();
    disposeObject(child);
  }
  grid.visible = true;
  grid.position.set(0, 0, 0);
  grid.scale.set(1, 1, 1);
}

function renderSceneDescription(description) {
  clearSceneObjects();
  const terrains = description?.terrain_instances || [];
  for (const terrain of terrains) {
    if (terrain.geometry?.type !== "plane") continue;
    const [width, height] = terrain.geometry.size;
    const [red, green, blue, alpha] = terrain.appearance.rgba;
    const material = new THREE.MeshBasicMaterial({
      color: terrain.id === "flat_floor"
        ? new THREE.Color(0x143222)
        : new THREE.Color().setRGB(red, green, blue, THREE.SRGBColorSpace),
      transparent: alpha < 1,
      opacity: alpha,
    });
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(width, height), material);
    floor.receiveShadow = true;
    floor.userData = { layer: "scene-terrain", sceneObject: true, collision: terrain.collision };
    setTransform(floor, terrain.pose);
    sceneGroup.add(floor);
    grid.visible = true;
    grid.position.z = terrain.pose.xyz[2] + 0.002;
    grid.scale.set(width / 4, 1, height / 4);
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
  if (PRIMITIVE_TYPES.includes(collision.type)) return primitiveGeometry(THREE, collision);
  return null;
}

async function addCollisionOverlay(collision, group, robot, token, controller, sourceCollisionId = null) {
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
    new THREE.LineBasicMaterial({ color: 0x8fca5e, transparent: true, opacity: 0.86 }),
  );
  overlay.userData = { link: group.name, layer: "collision-overlay", collisionName: collision.name || "", sourceCollisionId, editable: collision.type !== "mesh" };
  overlay.visible = collisionShapesVisible || (collisionMode && collision.type === "mesh");
  setTransform(overlay, collision.origin);
  if (collision.scale) overlay.scale.fromArray(collision.scale);
  overlay.updateMatrix();
  group.add(overlay);
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function collisionSource(id) {
  return collisionDocument?.collisions.find(collision => collision.id === id) || null;
}

function setCollisionStatus(message, error = false) {
  collisionStatus.textContent = message;
  collisionStatus.classList.toggle("error", error);
}

function draftCollision(id) {
  return collisionDraft.find(collision => collision.id === id) || null;
}

function isRetainedMesh(collision) {
  return collision?.geometry?.type === "mesh" && retainedMeshIds.has(collision.id);
}

async function collisionDraftRequest(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({ ok: false, error: response.statusText }));
  if (!response.ok || !data.ok) throw new Error(data.error || "Collision draft request failed");
  return data;
}

function collisionDraftPath(suffix = "") {
  if (!activeRobot || !collisionDraftId) return null;
  const base = activeCandidateId
    ? `/api/robots/${encodeURIComponent(activeRobot.id)}/mjcf-candidates/${encodeURIComponent(activeCandidateId)}/collision-drafts`
    : `/api/robots/${encodeURIComponent(activeRobot.id)}/collision-drafts`;
  return `${base}/${encodeURIComponent(collisionDraftId)}${suffix}`;
}

function collisionDraftBase() {
  if (!activeRobot) return null;
  return activeCandidateId
    ? `/api/robots/${encodeURIComponent(activeRobot.id)}/mjcf-candidates/${encodeURIComponent(activeCandidateId)}/collision-drafts`
    : `/api/robots/${encodeURIComponent(activeRobot.id)}/collision-drafts`;
}

function cancelCollisionDraftSave() {
  if (collisionDraftSaveTimer !== null) clearTimeout(collisionDraftSaveTimer);
  collisionDraftSaveTimer = null;
}

function collisionDraftPayload() {
  return {
    revision: collisionDocument?.revision,
    primitives: collisionDraft,
    retained_mesh_ids: [...retainedMeshIds],
  };
}

function persistCollisionDraft() {
  cancelCollisionDraftSave();
  const path = collisionDraftPath();
  if (!path || !collisionDocument) return Promise.resolve();
  const body = JSON.stringify(collisionDraftPayload());
  collisionDraftSave = collisionDraftSave.catch(() => undefined).then(() => collisionDraftRequest(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body,
  }));
  return collisionDraftSave;
}

function scheduleCollisionDraftSave() {
  cancelCollisionDraftSave();
  collisionDraftDirty = true;
  collisionDraftSaveTimer = setTimeout(() => {
    persistCollisionDraft().catch(error => setCollisionStatus(error.message, true));
  }, 250);
}

async function flushCollisionDraft() {
  if (collisionDraftSaveTimer !== null) return persistCollisionDraft();
  return collisionDraftSave;
}

function applyCollisionDraftSession(session) {
  collisionDocument = session;
  collisionDraftId = session.draft_id;
  collisionDraft = clone(session.primitives);
  retainedMeshIds = new Set(session.retained_mesh_ids);
}

async function discardCollisionDraft() {
  cancelCollisionDraftSave();
  const path = collisionDraftPath();
  collisionDraftId = null;
  retainedMeshIds = new Set();
  if (!path) return;
  try {
    await collisionDraftSave.catch(() => undefined);
    await collisionDraftRequest(path, { method: "DELETE" });
  } catch (error) {
    console.warn(`Could not discard collision draft: ${error.message}`);
  }
}

function disposeObject(object) {
  object.traverse(node => {
    node.geometry?.dispose?.();
    if (Array.isArray(node.material)) node.material.forEach(material => material.dispose?.());
    else node.material?.dispose?.();
  });
}

function clearDraftCollisionObjects() {
  for (const object of collisionObjects.values()) {
    object.parent?.remove(object);
    disposeObject(object);
  }
  collisionObjects.clear();
  robotGroup.traverse(node => {
    if (node.userData.layer === "collision-overlay") node.visible = collisionShapesVisible;
  });
}

function paintCollisionObject(id) {
  const object = collisionObjects.get(id);
  if (!object) return;
  const selected = id === selectedCollisionId;
  const collision = draftCollision(id);
  const colliding = Boolean(collision && contactGeomNames.has(collision.name));
  object.traverse(node => {
    if (!node.material?.color) return;
    // Selected wins for the edge outline; contact wins for the translucent fill.
    node.material.color.set(node.isMesh && colliding ? 0xff754f : selected ? 0xc5f067 : 0x79ac4f);
    if (node.isMesh) node.material.opacity = selected ? 0.38 : colliding ? 0.34 : 0.22;
    if (node.isLineSegments) node.material.color.set(selected ? 0xc5f067 : colliding ? 0xffa15b : 0x8fca5e);
  });
}

function refreshCollisionObjectStyles() {
  for (const id of collisionObjects.keys()) paintCollisionObject(id);
}

function paintCompiledCollisionContacts() {
  robotGroup.traverse(node => {
    if (node.userData.layer !== "collision-overlay" || !node.material?.color) return;
    const colliding = contactGeomIds.has(node.userData.geomId) || contactGeomNames.has(node.userData.collisionName);
    node.material.color.copy(node.userData.originalColor || new THREE.Color(0x79ac4f));
    if (colliding) node.material.color.set(0xff754f);
  });
}

function updateCollisionObject(collision) {
  const object = collisionObjects.get(collision.id);
  if (!object) return;
  setTransform(object, collision.origin);
  object.updateMatrixWorld(true);
  paintCollisionObject(collision.id);
}

function addDraftCollisionObject(collision) {
  const link = visualLinkGroups.get(collision.link);
  if (!link) return;
  const object = new THREE.Group();
  object.userData = { layer: "collision-editor", collisionId: collision.id, link: collision.link };
  const geometry = primitiveGeometry(THREE, collision.geometry);
  const fill = new THREE.Mesh(
    geometry,
    new THREE.MeshBasicMaterial({ color: 0x79ac4f, transparent: true, opacity: 0.22, depthWrite: false }),
  );
  fill.userData = { layer: "collision-editor", collisionId: collision.id, link: collision.link };
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(geometry),
    new THREE.LineBasicMaterial({ color: 0x8fca5e, transparent: true, opacity: 0.98 }),
  );
  edges.userData = { layer: "collision-editor", collisionId: collision.id, link: collision.link };
  object.add(fill, edges);
  setTransform(object, collision.origin);
  object.visible = collisionShapesVisible;
  link.add(object);
  collisionObjects.set(collision.id, object);
}

function replaceDraftCollisionObject(collision) {
  const old = collisionObjects.get(collision.id);
  if (old) {
    old.parent?.remove(old);
    disposeObject(old);
    collisionObjects.delete(collision.id);
  }
  addDraftCollisionObject(collision);
  refreshCollisionObjectStyles();
}

function renderDraftCollisionObjects() {
  clearDraftCollisionObjects();
  if (!collisionMode) return;
  for (const collision of collisionDraft) addDraftCollisionObject(collision);
  robotGroup.traverse(node => {
    if (node.userData.layer !== "collision-overlay") return;
    const source = (collisionDocument?.collisions || []).find(item => item.link === node.userData.link && item.name === node.userData.collisionName);
    if (!source) return;
    node.userData.sourceCollisionId = source.id;
    node.userData.editable = source.editable;
    node.visible = source.editable ? false : retainedMeshIds.has(source.id);
  });
  refreshCollisionObjectStyles();
}

function visualBoundsForLink(linkName) {
  const link = visualLinkGroups.get(linkName);
  if (!link) return null;
  const bounds = new THREE.Box3();
  let found = false;
  robotGroup.traverse(node => {
    if (!node.isMesh || node.userData.layer !== "visual-mesh") return;
    if (node.userData.link !== linkName) return;
    node.geometry.computeBoundingBox();
    const local = node.geometry.boundingBox?.clone();
    if (!local) return;
    node.updateWorldMatrix(true, false);
    link.updateWorldMatrix(true, false);
    local.applyMatrix4(node.matrixWorld).applyMatrix4(link.matrixWorld.clone().invert());
    bounds.union(local);
    found = true;
  });
  return found ? { min: bounds.min.toArray(), max: bounds.max.toArray() } : null;
}

function uniqueCollisionName(linkName, type) {
  const names = new Set((collisionDocument?.collisions || [])
    .filter(item => item.link === linkName && (item.editable || retainedMeshIds.has(item.id)))
    .map(item => item.name)
    .filter(Boolean));
  for (const collision of collisionDraft) if (collision.link === linkName) names.add(collision.name);
  let index = 1;
  let candidate = `${linkName}_${type}_collision_${index}`;
  while (names.has(candidate)) candidate = `${linkName}_${type}_collision_${++index}`;
  return candidate;
}

function addPrimitiveCollision(type) {
  if (!collisionMode || !collisionDocument || !collisionLink.value) return;
  const random = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const collision = defaultCollision(
    type,
    collisionLink.value,
    `${collisionDocument.new_id_prefix}${random}`,
    uniqueCollisionName(collisionLink.value, type),
    visualBoundsForLink(collisionLink.value),
  );
  collisionDraft.push(collision);
  selectedCollisionId = collision.id;
  renderDraftCollisionObjects();
  renderCollisionPanel();
  scheduleCollisionDraftSave();
  setCollisionStatus(`Added ${type} collision to the temporary draft.`);
}

function selectCollision(id) {
  const collision = draftCollision(id) || collisionSource(id);
  if (!collision || (collision.geometry.type === "mesh" && !isRetainedMesh(collision))) return;
  selectedCollisionId = id;
  collisionLink.value = collision.link;
  renderCollisionPanel();
  refreshCollisionObjectStyles();
}

function numberControl(label, value, onChange, options = {}) {
  const row = document.createElement("label");
  row.className = "collision-control";
  const title = document.createElement("span");
  title.textContent = label;
  row.append(title);
  let slider = null;
  if (options.slider) {
    slider = document.createElement("input");
    slider.type = "range";
    slider.min = String(options.min ?? -Math.max(Math.abs(value) * 3, 1));
    slider.max = String(options.max ?? Math.max(Math.abs(value) * 3, 1));
    slider.step = String(options.step ?? 0.001);
    slider.value = String(value);
    row.append(slider);
  } else {
    row.append(document.createElement("span"));
  }
  const input = document.createElement("input");
  input.type = "number";
  input.step = String(options.step ?? 0.001);
  const inputMin = Object.hasOwn(options, "inputMin") ? options.inputMin : options.min;
  if (inputMin !== undefined) input.min = String(inputMin);
  input.value = String(value);
  const apply = raw => {
    const next = Number(raw);
    if (!Number.isFinite(next) || (inputMin !== undefined && next < inputMin)) return;
    input.value = String(next);
    if (slider) slider.value = String(options.sliderValue ? options.sliderValue(next) : Math.max(Number(slider.min), Math.min(Number(slider.max), next)));
    onChange(next);
  };
  input.addEventListener("change", () => apply(input.value));
  slider?.addEventListener("input", () => apply(slider.value));
  row.append(input);
  return row;
}

function renderCollisionDetail() {
  collisionDetail.replaceChildren();
  const collision = draftCollision(selectedCollisionId);
  if (!collision) {
    const mesh = collisionSource(selectedCollisionId);
    if (isRetainedMesh(mesh)) {
      const heading = document.createElement("div");
      heading.className = "collision-section-title";
      heading.textContent = "Mesh collision";
      const metadata = document.createElement("p");
      metadata.className = "collision-readonly";
      metadata.textContent = `${mesh.geometry.filename} · position ${mesh.origin.xyz.join(", ")} m · rotation ${mesh.origin.rpy.map(radiansToDegrees).map(value => value.toFixed(1)).join(", ")}°`;
      const remove = document.createElement("button");
      remove.className = "collision-delete";
      remove.textContent = "Delete mesh from draft";
      remove.addEventListener("click", () => deleteSelectedMeshCollision());
      collisionDetail.append(heading, metadata, remove);
      return;
    }
    collisionDetail.innerHTML = '<p class="collision-readonly">Select a collision or add a primitive to this temporary draft.</p>';
    return;
  }
  const heading = document.createElement("div");
  heading.className = "collision-section-title";
  heading.textContent = `${collision.geometry.type} collision`;
  const name = document.createElement("input");
  name.className = "collision-name";
  name.value = collision.name;
  name.setAttribute("aria-label", "Collision name");
  name.addEventListener("change", () => {
    collision.name = name.value.trim();
    renderCollisionPanel();
    scheduleCollisionDraftSave();
  });
  collisionDetail.append(heading, name);
  const dimensionHeading = document.createElement("div");
  dimensionHeading.className = "collision-section-title";
  dimensionHeading.textContent = "Dimensions (m)";
  collisionDetail.append(dimensionHeading);
  const updateGeometry = () => {
    replaceDraftCollisionObject(collision);
    scheduleCollisionDraftSave();
  };
  if (collision.geometry.type === "box") {
    ["X", "Y", "Z"].forEach((axis, index) => collisionDetail.append(numberControl(axis, collision.geometry.size[index], value => { collision.geometry.size[index] = value; updateGeometry(); }, { slider: true, min: 0.001 })));
  } else if (collision.geometry.type === "sphere") {
    collisionDetail.append(numberControl("Radius", collision.geometry.radius, value => { collision.geometry.radius = value; updateGeometry(); }, { slider: true, min: 0.001 }));
  } else {
    collisionDetail.append(numberControl("Radius", collision.geometry.radius, value => { collision.geometry.radius = value; updateGeometry(); }, { slider: true, min: 0.001 }));
    collisionDetail.append(numberControl("Length", collision.geometry.length, value => { collision.geometry.length = value; updateGeometry(); }, { slider: true, min: 0.001 }));
  }
  const positionHeading = document.createElement("div");
  positionHeading.className = "collision-section-title";
  positionHeading.textContent = "Position (m, slider ±0.1)";
  collisionDetail.append(positionHeading);
  ["X", "Y", "Z"].forEach((axis, index) => collisionDetail.append(numberControl(axis, collision.origin.xyz[index], value => {
    collision.origin.xyz[index] = value;
    updateCollisionObject(collision);
    scheduleCollisionDraftSave();
  }, { slider: true, min: -POSITION_SLIDER_LIMIT, max: POSITION_SLIDER_LIMIT, inputMin: undefined, sliderValue: positionSliderValue, step: 0.001 })));
  const rotationHeading = document.createElement("div");
  rotationHeading.className = "collision-section-title";
  rotationHeading.textContent = "Rotation (degrees)";
  collisionDetail.append(rotationHeading);
  ["Roll", "Pitch", "Yaw"].forEach((axis, index) => collisionDetail.append(numberControl(axis, radiansToDegrees(collision.origin.rpy[index]), value => {
    collision.origin.rpy[index] = degreesToRadians(value);
    updateCollisionObject(collision);
    scheduleCollisionDraftSave();
  }, { slider: true, min: -180, max: 180, step: 0.1 })));
  const actions = document.createElement("div");
  actions.className = "collision-actions";
  const reassign = document.createElement("button");
  reassign.textContent = "Move center to link origin";
  reassign.addEventListener("click", () => reassignCollision(collision, collisionLink.value));
  const remove = document.createElement("button");
  remove.className = "collision-delete";
  remove.textContent = "Delete";
  remove.addEventListener("click", () => deleteSelectedCollision());
  actions.append(reassign, remove);
  collisionDetail.append(actions);
}

function renderCollisionPanel() {
  const previous = collisionLink.value;
  collisionLink.replaceChildren();
  for (const link of collisionDocument?.links || []) {
    const option = document.createElement("option");
    option.value = link;
    option.textContent = link;
    collisionLink.append(option);
  }
  if (collisionDocument?.links.includes(previous)) collisionLink.value = previous;
  else if (draftCollision(selectedCollisionId)) collisionLink.value = draftCollision(selectedCollisionId).link;
  collisionList.replaceChildren();
  if (collisionDocument && collisionLink.value) {
    const editable = new Map(collisionDraft.filter(item => item.link === collisionLink.value).map(item => [item.id, item]));
    for (const source of collisionDocument.collisions.filter(item => item.link === collisionLink.value)) {
      if (source.editable && !editable.has(source.id)) continue;
      if (!source.editable && !retainedMeshIds.has(source.id)) continue;
      const item = source.editable ? editable.get(source.id) : source;
      const row = document.createElement("button");
      row.className = `collision-row ${item.id === selectedCollisionId ? "active" : ""} ${source.editable ? "" : "readonly"}`;
      const label = document.createElement("span");
      label.className = "collision-row-name";
      label.textContent = item.name || `${item.geometry.type} collision`;
      const kind = document.createElement("span");
      kind.className = "collision-row-kind";
      kind.textContent = source.editable ? item.geometry.type : `mesh · ${item.geometry.filename.split("/").pop()}`;
      row.append(label, kind);
      row.addEventListener("click", () => selectCollision(item.id));
      collisionList.append(row);
      editable.delete(source.id);
    }
    for (const item of editable.values()) {
      const row = document.createElement("button");
      row.className = `collision-row ${item.id === selectedCollisionId ? "active" : ""}`;
      row.innerHTML = `<span class="collision-row-name"></span><span class="collision-row-kind"></span>`;
      row.querySelector(".collision-row-name").textContent = item.name;
      row.querySelector(".collision-row-kind").textContent = item.geometry.type;
      row.addEventListener("click", () => selectCollision(item.id));
      collisionList.append(row);
    }
  }
  renderCollisionDetail();
  collisionExport.disabled = !collisionMode || !collisionDocument || !collisionDraftId;
}

function reassignCollision(collision, linkName) {
  const target = visualLinkGroups.get(linkName);
  if (!target) return;
  collision.link = linkName;
  collision.origin.xyz = [0, 0, 0];
  collisionLink.value = linkName;
  renderDraftCollisionObjects();
  renderCollisionPanel();
  scheduleCollisionDraftSave();
  setCollisionStatus(`Centered ${collision.name} on ${linkName}'s origin; rotation was preserved.`);
}

function deleteSelectedCollision() {
  const collision = draftCollision(selectedCollisionId);
  if (!collision || !window.confirm(`Delete collision ${collision.name}?`)) return;
  collisionDraft = collisionDraft.filter(item => item.id !== collision.id);
  selectedCollisionId = null;
  renderDraftCollisionObjects();
  renderCollisionPanel();
  scheduleCollisionDraftSave();
  setCollisionStatus("Collision removed from the temporary draft.");
}

function deleteSelectedMeshCollision() {
  const collision = collisionSource(selectedCollisionId);
  if (!isRetainedMesh(collision) || !window.confirm(`Delete mesh collision ${collision.name || collision.geometry.filename}?`)) return;
  retainedMeshIds.delete(collision.id);
  selectedCollisionId = null;
  renderDraftCollisionObjects();
  renderCollisionPanel();
  scheduleCollisionDraftSave();
  setCollisionStatus("Mesh collision removed from the temporary draft.");
}

function collisionLocalBounds(collision) {
  if (collision.geometry.type === "mesh") {
    const link = visualLinkGroups.get(collision.link);
    let result = null;
    robotGroup.traverse(node => {
      if (node.userData.sourceCollisionId !== collision.id || !node.geometry || !link) return;
      const world = new THREE.Box3().setFromObject(node);
      const local = new THREE.Box3();
      for (const x of [world.min.x, world.max.x]) for (const y of [world.min.y, world.max.y]) for (const z of [world.min.z, world.max.z]) local.expandByPoint(link.worldToLocal(new THREE.Vector3(x, y, z)));
      result = local;
    });
    return result;
  }
  const dimensions = primitiveDimensions(collision.geometry);
  const half = dimensions.map(value => value / 2);
  return new THREE.Box3(new THREE.Vector3(...collision.origin.xyz).sub(new THREE.Vector3(...half)), new THREE.Vector3(...collision.origin.xyz).add(new THREE.Vector3(...half)));
}

function snapCollision(collision) {
  const dimensions = primitiveDimensions(collision.geometry);
  const threshold = Math.min(0.05, Math.max(0.005, Math.max(...dimensions) * 0.1));
  const originDistance = Math.hypot(...collision.origin.xyz);
  const ownBounds = collisionLocalBounds(collision);
  let faceCandidate = null;
  if (ownBounds) {
    for (const neighbor of [...collisionDraft, ...(collisionDocument?.collisions || [])]) {
      if (neighbor.id === collision.id || neighbor.link !== collision.link || (neighbor.geometry.type === "mesh" && !retainedMeshIds.has(neighbor.id))) continue;
      const bounds = collisionLocalBounds(neighbor);
      if (!bounds) continue;
      for (let axis = 0; axis < 3; axis += 1) {
        const otherAxes = [0, 1, 2].filter(index => index !== axis);
        if (!otherAxes.every(index => ownBounds.min.getComponent(index) <= bounds.max.getComponent(index) && ownBounds.max.getComponent(index) >= bounds.min.getComponent(index))) continue;
        const half = (ownBounds.max.getComponent(axis) - ownBounds.min.getComponent(axis)) / 2;
        const current = collision.origin.xyz[axis];
        const target = current >= (bounds.min.getComponent(axis) + bounds.max.getComponent(axis)) / 2 ? bounds.max.getComponent(axis) + half : bounds.min.getComponent(axis) - half;
        const distance = Math.abs(target - current);
        if (distance <= threshold && (!faceCandidate || distance < faceCandidate.distance)) faceCandidate = { axis, target, distance, neighbor };
      }
    }
  }
  if (originDistance <= threshold && (!faceCandidate || originDistance <= faceCandidate.distance)) {
    collision.origin.xyz = [0, 0, 0];
    return { type: "origin" };
  }
  if (faceCandidate) {
    collision.origin.xyz[faceCandidate.axis] = faceCandidate.target;
    return { type: "face", target: faceCandidate.neighbor };
  }
  return null;
}

async function enterCollisionMode() {
  if (!activeRobot || !activeRobot.workbench_loadable) {
    setCollisionDrawerExpanded(true);
    setCollisionStatus("Authorize or preview an MJCF model before editing collisions.", true);
    return;
  }
  if (collisionMode && collisionDraftId) {
    setCollisionDrawerExpanded(true);
    return;
  }
  collisionMode = true;
  updateDisplayControls();
  updateSimulationControls("Loading collision editor…");
  try {
    const session = await collisionDraftRequest(collisionDraftBase(), { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    if (!collisionMode) {
      collisionDraftId = session.draft_id;
      void discardCollisionDraft();
      return;
    }
    applyCollisionDraftSession(session);
    selectedCollisionId = null;
    physicsEnabled = false;
    followEnabled = false;
    collisionShapesVisible = true;
    resetSimulation();
    renderJointInspector();
    renderDraftCollisionObjects();
    renderCollisionPanel();
    setCollisionDrawerExpanded(true);
    updateDisplayControls();
    updateSimulationControls("Collision editor active: the model is reset and physics/joint editing are locked.");
    setCollisionStatus("Temporary MJCF draft loaded. Add a primitive or select a mesh collision to delete it.");
    void compileDraftContacts(collisionDraftId);
  } catch (error) {
    collisionMode = false;
    updateDisplayControls();
    updateSimulationControls("Collision editor could not be loaded.");
    setCollisionStatus(error.message, true);
  }
}

function leaveCollisionMode() {
  if (!collisionMode) return;
  collisionMode = false;
  setCollisionDrawerExpanded(false);
  disposeDiagnosticModel();
  clearContactVisualization();
  void discardCollisionDraft();
  clearDraftCollisionObjects();
  renderJointInspector();
  updateDisplayControls();
  updateSimulationControls("Collision editing closed. Physics and joint controls are available again.");
}

function setCollisionDrawerExpanded(expanded) {
  collisionDrawerExpanded = Boolean(expanded);
  collisionDrawer.dataset.expanded = String(collisionDrawerExpanded);
  collisionDrawerToggle.setAttribute("aria-expanded", String(collisionDrawerExpanded));
  collisionDrawerContent.hidden = !collisionDrawerExpanded;
}

function toggleCollisionDrawer() {
  if (!collisionMode) {
    void enterCollisionMode();
    return;
  }
  setCollisionDrawerExpanded(!collisionDrawerExpanded);
}

function closeCollisionEditor() {
  if (!collisionMode) return;
  if (collisionDraftDirty && !window.confirm("Discard the unsaved temporary collision draft and close the editor?")) return;
  leaveCollisionMode();
}

async function resetCollisionDraft() {
  const path = collisionDraftPath("/reset");
  if (!collisionMode || !path) return;
  try {
    cancelCollisionDraftSave();
    const session = await collisionDraftRequest(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    applyCollisionDraftSession(session);
    selectedCollisionId = null;
    renderDraftCollisionObjects();
    renderCollisionPanel();
    void compileDraftContacts(collisionDraftId);
    setCollisionStatus("Temporary draft reset from the authorized MJCF source.");
  } catch (error) {
    setCollisionStatus(error.message, true);
  }
}

async function exportCollisionDraft() {
  const path = collisionDraftPath("/export");
  if (!collisionDocument || !path) return;
  try {
    collisionExport.disabled = true;
    await flushCollisionDraft();
    const data = await collisionDraftRequest(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ revision: collisionDocument.revision }),
    });
    setCollisionStatus(`Exported ${data.candidate_id || "MJCF candidate"}: ${data.output_path}`);
    if (activeCandidateId && data.candidate_id) await refreshMjcfCandidates();
  } catch (error) {
    setCollisionStatus(error.message, true);
  } finally {
    collisionExport.disabled = false;
  }
}

function collisionDraftSourcePath(draftId = collisionDraftId) {
  if (!activeRobot || !draftId) return null;
  return activeCandidateId
    ? `/api/robots/${encodeURIComponent(activeRobot.id)}/mjcf-candidates/${encodeURIComponent(activeCandidateId)}/collision-drafts/${encodeURIComponent(draftId)}/source`
    : `/api/robots/${encodeURIComponent(activeRobot.id)}/collision-drafts/${encodeURIComponent(draftId)}/source`;
}

function collisionAssetBase() {
  if (!activeRobot) return null;
  return activeCandidateId
    ? `/api/robots/${encodeURIComponent(activeRobot.id)}/mjcf-candidates/${encodeURIComponent(activeCandidateId)}`
    : `/api/robots/${encodeURIComponent(activeRobot.id)}`;
}

async function cachedMeshBytes(sourceBase, name, controller) {
  const key = `${sourceBase}/files/${name}`;
  if (!meshAssetCache.has(key)) {
    meshAssetCache.set(key, fetch(`${sourceBase}/files/${encodeURIComponent(name)}`, { signal: controller.signal })
      .then(response => response.ok ? response.arrayBuffer() : Promise.reject(new Error(`Could not read ${name}`)))
      .then(bytes => new Uint8Array(bytes)));
  }
  return meshAssetCache.get(key);
}

function setSpawnPose(model, data) {
  mujoco.mj_resetData(model, data);
  for (let id = 0; id < Number(model.njnt || 0); id += 1) {
    const joint = model.jnt(id);
    if (Number(joint.type) !== 0) {
      joint.delete?.();
      continue;
    }
    const spawn = activeRobot?.scene_description?.robot_spawn || { xyz: [0, 0, 0.75], rpy: [0, 0, 0] };
    const orientation = new THREE.Quaternion().setFromEuler(new THREE.Euler(...spawn.rpy, "XYZ"));
    data.qpos.set([...spawn.xyz, orientation.w, orientation.x, orientation.y, orientation.z], Number(joint.qposadr));
    joint.delete?.();
    break;
  }
  data.qvel?.fill?.(0);
  mujoco.mj_forward(model, data);
}

async function compileDraftContacts(draftId) {
  const sourcePath = collisionDraftSourcePath(draftId);
  const sourceBase = collisionAssetBase();
  if (!sourcePath || !sourceBase || !mujoco || !collisionMode || !collisionShapesVisible) return;
  disposeDiagnosticModel();
  const generation = ++diagnosticGeneration;
  const controller = new AbortController();
  diagnosticController = controller;
  const objects = [];
  try {
    const raw = await fetch(sourcePath, { signal: controller.signal })
      .then(response => response.ok ? response.text() : Promise.reject(new Error("Could not load temporary MJCF draft")));
    const prepared = prepareSimulationSource(raw, "mjcf", activeRobot);
    const vfs = new mujoco.MjVFS();
    objects.push(vfs);
    const document = new DOMParser().parseFromString(prepared.source, "application/xml");
    const names = [...new Set([...document.querySelectorAll("mesh[filename], mesh[file]")]
      .map(node => (node.getAttribute("filename") || node.getAttribute("file")).split("/").pop()))];
    for (const name of names) vfs.addBuffer(name, await cachedMeshBytes(sourceBase, name, controller));
    if (controller.signal.aborted || generation !== diagnosticGeneration || !collisionMode || draftId !== collisionDraftId) throw new DOMException("Draft contact compilation superseded", "AbortError");
    const model = mujoco.MjModel.from_xml_string(prepared.source, vfs);
    const data = new mujoco.MjData(model);
    objects.push(model, data);
    setSpawnPose(model, data);
    if (controller.signal.aborted || generation !== diagnosticGeneration || !collisionMode || draftId !== collisionDraftId) throw new DOMException("Draft contact compilation superseded", "AbortError");
    diagnosticObjects = objects;
    diagnosticModel = model;
    diagnosticData = data;
    diagnosticController = null;
    syncContactVisualization();
    collisionContactCount.textContent = `${contactVisualizer.count} contact${contactVisualizer.count === 1 ? "" : "s"}`;
  } catch (error) {
    deleteWasmObjects(objects);
    if (error?.name === "AbortError") return;
    if (generation === diagnosticGeneration) {
      collisionContactCount.textContent = "contacts unavailable";
      setCollisionStatus(`Draft saved, but MuJoCo contact check failed: ${error.message}`, true);
    }
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
  const terrain = robot.scene_description?.terrain_instances?.find(item => item.geometry?.type === "plane" && item.collision) || null;
  const appendMujocoTerrain = worldbody => {
    if (!terrain || !worldbody) return;
    const floor = xml.createElement("geom");
    const [width, height] = terrain.geometry.size;
    const [red, green, blue, alpha] = terrain.appearance.rgba;
    // MuJoCo geom colours are consumed by the Three adapter as linear light.
    // Keep the simulation floor aligned with the sRGB presentation surface.
    const simulationRgba = terrain.id === "flat_floor" ? [0.010, 0.042, 0.021, alpha] : [red, green, blue, alpha];
    const friction = terrain.overrides?.mujoco?.friction || [terrain.physics.friction, 0.01, 0.001];
    floor.setAttribute("name", `workbench_scene_${terrain.instance_id}`);
    floor.setAttribute("type", "plane");
    floor.setAttribute("size", `${width / 2} ${height / 2} ${terrain.geometry.thickness}`);
    floor.setAttribute("pos", terrain.pose.xyz.join(" "));
    floor.setAttribute("rgba", simulationRgba.join(" "));
    floor.setAttribute("friction", friction.join(" "));
    worldbody.append(floor);
  };
  if (format === "mjcf") {
    const worldbody = xml.querySelector("worldbody");
    appendMujocoTerrain(worldbody);
  } else {
    throw new Error("Workbench only loads authorized MJCF models.");
  }
  return { source: new XMLSerializer().serializeToString(xml) };
}

async function loadMujocoModel(robot, token, controller) {
  setEngineState("Loading MuJoCo WASM model…");
  const objects = [];
  try {
    mujoco ||= await loadMujoco({ locateFile: file => `/vendor/${file}` });
    assertCurrentLoad(token, controller);
    const sourceBase = activeCandidateId
      ? `/api/robots/${encodeURIComponent(robot.id)}/mjcf-candidates/${encodeURIComponent(activeCandidateId)}`
      : `/api/robots/${encodeURIComponent(robot.id)}`;
    const raw = await fetch(activeCandidateId ? `${sourceBase}/source` : `${sourceBase}/source?format=mjcf`, { signal: controller.signal })
      .then(response => response.ok ? response.text() : Promise.reject(new Error("Could not load model source")));
    assertCurrentLoad(token, controller);
    const prepared = prepareSimulationSource(raw, "mjcf", robot);
    const vfs = new mujoco.MjVFS();
    objects.push(vfs);
    const sourceDocument = new DOMParser().parseFromString(prepared.source, "application/xml");
    const names = [...new Set([...sourceDocument.querySelectorAll("mesh[filename], mesh[file]")].map(node => (node.getAttribute("filename") || node.getAttribute("file")).split("/").pop()))];
    for (const name of names) {
      const bytes = await fetch(`${sourceBase}/files/${encodeURIComponent(name)}`, { signal: controller.signal })
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
    simulationRootJoint = null;
    for (let id = 0; id < model.njnt; id += 1) {
      const joint = model.jnt(id);
      if (Number(joint.type) === 0) simulationRootJoint = id;
      joint.delete?.();
      if (simulationRootJoint !== null) break;
    }
    clearRobot();
    clearSceneObjects();
    const bodyGroups = mjcfRenderer.build(model, data);
    visualLinkGroups.clear();
    for (const [name, group] of bodyGroups) visualLinkGroups.set(name, group);
    jointStates = collectJointStates();
    physicsEnabled = false;
    resetSimulation();
    renderJointInspector();
    updateSimulationControls("Model ready. Press P to toggle physics.");
    applyVisualMeshOpacity();
    setLayerVisibility("visual-mesh", visualMeshesVisible);
    setLayerVisibility("collision-overlay", collisionShapesVisible);
    const bounds = visualBounds();
    diagnostics.bindMujoco(model, data, bodyGroups, bounds?.getSize(new THREE.Vector3()).length() || 0.5);
    viewerEmpty.hidden = false;
    viewerEmpty.hidden = true;
    frameRobot();
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
  leaveCollisionMode();
  collisionDocument = null;
  collisionDraft = [];
  collisionDraftId = null;
  retainedMeshIds = new Set();
  cancelCollisionDraftSave();
  selectedCollisionId = null;
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
    activeCandidateId = null;
    delete mjcfCandidateId.dataset.robotId;
    mjcfCandidateId.value = "";
    selectedName = null;
    selectedKind = null;
    selectedTitle.textContent = displayName(activeRobot);
    selectedElement.textContent = "None";
    if (!activeRobot.workbench_loadable) {
      disposeWasm();
      clearRobot();
      clearSceneObjects();
      renderRobotList();
      renderElements();
      await refreshMjcfCandidates();
      activateTab("mjcf");
      viewerEmpty.textContent = "MJCF authorization required. Generate a candidate in the MJCF panel.";
      setEngineState("MJCF candidate required", "loading");
      return;
    }
    selectedSource.textContent = "MJCF (authorized)";
    physicsEnabled = false;
    followEnabled = false;
    updateSimulationControls("Loading MuJoCo model…");
    renderRobotList();
    renderElements();
    await refreshMjcfCandidates();
    clearRobot();
    await loadMujocoModel(activeRobot, token, controller);
    if (isCurrentLoad(token, controller) && simulationModel) {
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
  if (kind === "joint" && simulationModel) {
    try {
      const joint = simulationModel.jnt(name);
      const body = simulationModel.body(Number(joint.bodyid));
      resolvedName = body.name || name;
      body.delete?.();
      joint.delete?.();
    } catch { resolvedName = name; }
  }
  selectedName = name;
  selectedKind = kind || "link";
  selectedElement.textContent = name;
  selectedSource.textContent = kind === "joint" ? "MJCF joint" : "MJCF body";
  if (kind === "joint") {
    const joint = jointStates.find(item => item.name === name);
    if (joint) activeJointId = joint.id;
  }
  robotGroup.traverse(node => {
    if (node.userData.layer !== "visual-mesh") return;
    const material = node.material;
    material.color.copy(node.userData.originalColor);
    if (node.userData.link === resolvedName) material.color.set(0xc5f067);
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
  advanceRandomPose();
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
  return raycaster.intersectObject(robotGroup, true).find(result => !result.object.userData.visualDiagnostic && isPickableSceneObject(result.object, collisionMode));
}

canvas.addEventListener("pointerdown", event => {
  if (event.button !== 0 || (event.buttons & 1) === 0) return;
  const hit = pickRobotPart(event);
  if (collisionMode) {
    const collisionId = hit?.object.userData.collisionId || hit?.object.userData.sourceCollisionId;
    if (collisionId) {
      selectCollision(collisionId);
    }
    return;
  }
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
    setForceLinkHighlight(pointerGesture.link);
  }
  if (pointerGesture.dragging && dragForce) {
    const rect = canvas.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    raycaster.ray.intersectPlane(dragForce.plane, dragForce.target);
    updateDragForceIndicator();
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
  if (event.key === "Delete" && collisionMode && selectedCollisionId) {
    event.preventDefault();
    deleteSelectedCollision();
    return;
  }
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
randomPoseButton.addEventListener("click", driveRandomPose);
visualMeshToggle.addEventListener("click", toggleVisualMeshes);
collisionShapeToggle.addEventListener("click", toggleCollisionShapes);
collisionDrawerToggle.addEventListener("click", toggleCollisionDrawer);
collisionDrawerClose.addEventListener("click", closeCollisionEditor);
document.querySelector("#collision-reset").addEventListener("click", () => resetCollisionDraft().catch(error => setCollisionStatus(error.message, true)));
collisionExport.addEventListener("click", exportCollisionDraft);
mjcfGenerate.addEventListener("click", generateMjcfCandidate);
collisionLink.addEventListener("change", () => { renderCollisionPanel(); refreshCollisionObjectStyles(); });
for (const button of document.querySelectorAll("[data-collision-add]")) button.addEventListener("click", () => addPrimitiveCollision(button.dataset.collisionAdd));
window.addEventListener("pagehide", () => {
  if (!activeRobot || !collisionDraftId) return;
  const path = collisionDraftPath();
  if (path) fetch(path, { method: "DELETE", keepalive: true });
});
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
for (const tab of document.querySelectorAll(".tab")) tab.addEventListener("click", () => activateTab(tab.dataset.tab));
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
