import * as THREE from "/vendor/three.module.js";
import { createCollisionMaterial } from "/collision-editor.js";

function matrixFromArray(array, offset, position) {
  return new THREE.Matrix4().set(
    array[offset], array[offset + 1], array[offset + 2], position[0],
    array[offset + 3], array[offset + 4], array[offset + 5], position[1],
    array[offset + 6], array[offset + 7], array[offset + 8], position[2],
    0, 0, 0, 1,
  );
}

function primitiveGeometry(type, size) {
  if (type === 0) return new THREE.PlaneGeometry(size[0] * 2, size[1] * 2);
  if (type === 2) return new THREE.SphereGeometry(size[0], 20, 14);
  if (type === 5) {
    const geometry = new THREE.CylinderGeometry(size[0], size[0], size[1] * 2, 20);
    geometry.rotateX(Math.PI / 2);
    return geometry;
  }
  if (type === 3) {
    const radius = size[0];
    const length = Math.max(size[1] * 2, 0.0001);
    const capsule = new THREE.CapsuleGeometry(radius, length, 8, 16);
    capsule.rotateX(Math.PI / 2);
    return capsule;
  }
  if (type === 6) return new THREE.BoxGeometry(size[0] * 2, size[1] * 2, size[2] * 2);
  return new THREE.SphereGeometry(size[0], 20, 14);
}

function meshGeometry(model, geom) {
  const meshId = Number(geom.dataid);
  const vertexStart = model.mesh_vertadr[meshId] * 3;
  const vertexCount = model.mesh_vertnum[meshId] * 3;
  const faceStart = model.mesh_faceadr[meshId] * 3;
  const faceCount = model.mesh_facenum[meshId] * 3;
  const positions = Float32Array.from(model.mesh_vert.slice(vertexStart, vertexStart + vertexCount));
  const source = model.mesh_face.slice(faceStart, faceStart + faceCount);
  const indices = positions.length / 3 > 65535 ? Uint32Array.from(source) : Uint16Array.from(source);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setIndex(new THREE.BufferAttribute(indices, 1));
  // MuJoCo's compiler folds mesh centering/alignment into the geom pose.  The
  // current world pose therefore comes exclusively from data.geom_xpos/xmat;
  // applying model.mesh_pos/mesh_quat here would transform visual meshes twice.
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  return geometry;
}

function geomColor(geom) {
  const rgba = geom.rgba || [0.75, 0.75, 0.75, 1];
  return { color: new THREE.Color(Number(rgba[0]), Number(rgba[1]), Number(rgba[2])), opacity: Number(rgba[3] ?? 1) };
}

function isContact(model, id, geom) {
  return Number(model.geom_contype?.[id] ?? geom.contype ?? 1) !== 0 || Number(model.geom_conaffinity?.[id] ?? geom.conaffinity ?? 1) !== 0;
}

/** Build Three objects straight from compiled MuJoCo arrays. */
export function createMjcfRenderer(robotGroup) {
  const objects = [];
  const bodyGroups = new Map();

  function clear() {
    for (const object of objects.splice(0)) {
      object.removeFromParent();
      object.traverse(node => {
        node.geometry?.dispose?.();
        const materials = Array.isArray(node.material) ? node.material : [node.material];
        materials.forEach(material => material?.dispose?.());
      });
    }
    bodyGroups.clear();
  }

  function build(model, data) {
    clear();
    for (let bodyId = 1; bodyId < model.nbody; bodyId += 1) {
      const body = model.body(bodyId);
      const name = body.name;
      body.delete?.();
      if (!name) continue;
      const group = new THREE.Group();
      group.name = name;
      group.userData = { link: name, bodyId, layer: "mjcf-body" };
      robotGroup.add(group);
      objects.push(group);
      bodyGroups.set(name, group);
    }
    for (let id = 0; id < model.ngeom; id += 1) {
      const geom = model.geom(id);
      const bodyId = Number(geom.bodyid);
      const body = model.body(bodyId);
      const link = body.name || "world";
      body.delete?.();
      const type = Number(geom.type);
      const size = Array.from(geom.size || model.geom_size.slice(id * 3, id * 3 + 3), Number);
      const contact = isContact(model, id, geom);
      let geometry;
      try {
        geometry = type === 7 ? meshGeometry(model, geom) : primitiveGeometry(type, size);
      } catch (error) {
        console.warn(`Skipping MuJoCo geom ${geom.name || id}: ${error.message}`);
        geom.delete?.();
        continue;
      }
      const { color, opacity } = geomColor(geom);
      const material = contact ? createCollisionMaterial(THREE) : new THREE.MeshStandardMaterial({ color, metalness: 0.12, roughness: 0.7, transparent: opacity < 1, opacity, depthWrite: opacity >= 1 });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.name = geom.name || `geom_${id}`;
      const layer = bodyId === 0 ? "scene-terrain" : contact ? "collision-overlay" : "visual-mesh";
      mesh.userData = {
        link,
        bodyId,
        geomId: id,
        collisionName: geom.name || "",
        layer,
        originalColor: material.color.clone(),
        originalMaterial: { opacity: material.opacity, transparent: material.transparent, depthWrite: material.depthWrite },
      };
      mesh.visible = layer === "scene-terrain" || !contact;
      robotGroup.add(mesh);
      objects.push(mesh);
      geom.delete?.();
    }
    sync(data);
    return bodyGroups;
  }

  function sync(data) {
    if (!data) return;
    for (const object of objects) {
      if (!object.userData?.geomId && object.userData?.geomId !== 0) continue;
      const id = object.userData.geomId;
      const position = [data.geom_xpos[id * 3], data.geom_xpos[id * 3 + 1], data.geom_xpos[id * 3 + 2]];
      object.position.setFromMatrixPosition(matrixFromArray(data.geom_xmat, id * 9, position));
      object.quaternion.setFromRotationMatrix(matrixFromArray(data.geom_xmat, id * 9, position));
    }
    for (const group of bodyGroups.values()) {
      const id = group.userData.bodyId;
      const position = [data.xpos[id * 3], data.xpos[id * 3 + 1], data.xpos[id * 3 + 2]];
      group.position.setFromMatrixPosition(matrixFromArray(data.xmat, id * 9, position));
      group.quaternion.setFromRotationMatrix(matrixFromArray(data.xmat, id * 9, position));
    }
  }

  return { build, clear, sync, bodyGroups };
}
