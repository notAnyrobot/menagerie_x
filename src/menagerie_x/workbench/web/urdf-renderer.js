import * as THREE from "/vendor/three.module.js";
import { STLLoader } from "/vendor/STLLoader.js";
import URDFLoader from "/vendor/urdf/URDFLoader.js";
import { createUrdfLoadGate } from "/urdf-load-lifecycle.js";
import { configureUrdfLoader, describeUrdfJoint, resolveUrdfMeshAsset } from "/urdf-utils.js";

function disposeObject(object) {
  object.traverse(node => {
    node.geometry?.dispose?.();
    for (const material of Array.isArray(node.material) ? node.material : [node.material]) {
      material?.map?.dispose?.();
      material?.dispose?.();
    }
  });
  object.removeFromParent();
}

function assignRenderableMetadata(root) {
  root.traverse(node => {
    if (!node.isMesh) return;
    if (node.userData.layer) return;
    let owner = node.parent;
    let link = null;
    let collision = false;
    while (owner) {
      link ||= owner.urdfName || null;
      collision ||= Boolean(owner.isURDFCollider);
      owner = owner.parent;
    }
    const layer = collision ? "collision-overlay" : "visual-mesh";
    const material = Array.isArray(node.material) ? node.material[0] : node.material;
    if (collision) {
      node.material = new THREE.MeshStandardMaterial({ color: 0xe09b49, emissive: 0x3d1d08, transparent: true, opacity: 0.38, depthWrite: false });
    }
    const current = Array.isArray(node.material) ? node.material[0] : node.material;
    node.userData = {
      ...node.userData,
      link: link || "world",
      layer,
      originalColor: current?.color?.clone?.() || new THREE.Color(0xffffff),
      originalMaterial: current ? { opacity: current.opacity, transparent: current.transparent, depthWrite: current.depthWrite } : null,
    };
    if (collision) node.visible = false;
    // The loader-owned placeholder material is not retained for collisions.
    if (collision && material !== current) material?.dispose?.();
  });
}

/** A small description-viewer adapter for actual URDF bytes. */
export function createUrdfRenderer(robotGroup, { editionFilesUrl }) {
  let robot = null;
  let joints = [];
  let links = new Map();
  let activeLoad = null;
  const loadGate = createUrdfLoadGate();

  function clear() {
    loadGate.invalidate();
    if (activeLoad && !activeLoad.settled) {
      activeLoad.settled = true;
      activeLoad.reject(new DOMException("URDF load was superseded.", "AbortError"));
    }
    activeLoad = null;
    if (robot) disposeObject(robot);
    robot = null;
    joints = [];
    links = new Map();
  }

  async function load(xmlText) {
    clear();
    const gate = loadGate.begin();
    let complete;
    const ready = new Promise((resolve, reject) => { complete = { resolve, reject, settled: false, parsed: false, pending: 0 }; });
    activeLoad = complete;
    const fail = error => {
      if (complete.settled) return;
      complete.settled = true;
      if (gate.current()) {
        if (robot) disposeObject(robot);
        robot = null;
        joints = [];
        links = new Map();
      }
      complete.reject(error instanceof Error ? error : new Error(String(error)));
    };
    const finish = () => {
      if (complete.settled || !complete.parsed || complete.pending) return;
      if (!gate.current()) return fail(new DOMException("URDF load was superseded.", "AbortError"));
      assignRenderableMetadata(robot);
      robotGroup.add(robot);
      links = new Map(Object.entries(robot.links || {}));
      joints = Object.values(robot.joints || {}).map(describeUrdfJoint);
      complete.settled = true;
      activeLoad = null;
      complete.resolve({ robot, links, joints });
    };
    const loader = configureUrdfLoader(new URDFLoader(new THREE.LoadingManager()));
    loader.workingPath = "mesh:///";
    loader.packages = () => "mesh:///";
    loader.loadMeshCb = (path, manager, done) => {
      complete.pending += 1;
      let relative;
      try {
        relative = resolveUrdfMeshAsset(path);
      } catch (error) {
        done(null, error);
        complete.pending -= 1;
        fail(error);
        return;
      }
      new STLLoader(manager).load(
        editionFilesUrl(relative),
        geometry => {
          complete.pending -= 1;
          if (!gate.current() || complete.settled) {
            geometry.dispose();
            return;
          }
          geometry.computeVertexNormals();
          const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: 0xc7d5df, metalness: 0.08, roughness: 0.72 }));
          done(mesh);
          finish();
        },
        undefined,
        error => {
          complete.pending -= 1;
          if (!gate.current() || complete.settled) return;
          done(null, error);
          fail(new Error(`Could not load URDF mesh ${relative}: ${error?.message || error}`));
        },
      );
    };
    try {
      robot = loader.parse(xmlText, "mesh:///");
      robot.name = robot.urdfName || "urdf-robot";
      complete.parsed = true;
      finish();
    } catch (error) {
      fail(error);
    }
    return ready;
  }

  function listJoints() { return joints.map(({ joint, ...record }) => record); }
  function getJointValue(record) { return Number(record.joint?.jointValue?.[0] ?? 0); }
  function setJointValue(record, value) { record.joint?.setJointValue(value); }
  function getLinkGroups() { return links; }
  function capabilities() {
    return { visualization: true, physics: false, contacts: false, pushing: false, nativeViewer: false, recording: false, collisionEditor: false };
  }

  return { load, clear, listJoints, getJointValue, setJointValue, getLinkGroups, capabilities };
}
