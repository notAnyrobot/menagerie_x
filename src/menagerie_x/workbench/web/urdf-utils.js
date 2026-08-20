export function resolveUrdfMeshAsset(value) {
  const decoded = decodeURIComponent(String(value).replace(/^mesh:\/\/+/, "").replace(/^package:\/\//, ""));
  const marker = decoded.lastIndexOf("/meshes/");
  const relative = marker >= 0 ? decoded.slice(marker + 8) : decoded.split("/").at(-1);
  if (!relative || (decoded.split("/").includes("..") && marker < 0) || relative.includes("..") || !/\.stl$/i.test(relative)) {
    throw new Error(`Unsupported URDF mesh path: ${value}. Only packaged STL meshes are supported.`);
  }
  return relative;
}

export function configureUrdfLoader(loader) {
  loader.parseVisual = true;
  loader.parseCollision = true;
  return loader;
}

export function urdfSceneTransform(sceneDescription) {
  const spawn = sceneDescription?.robot_spawn;
  return {
    xyz: Array.isArray(spawn?.xyz) && spawn.xyz.length === 3 ? [...spawn.xyz] : [0, 0, 0],
    rpy: Array.isArray(spawn?.rpy) && spawn.rpy.length === 3 ? [...spawn.rpy] : [0, 0, 0],
  };
}

export function describeUrdfJoint(joint, index) {
  const type = joint.jointType;
  const lower = Number(joint.limit?.lower);
  const upper = Number(joint.limit?.upper);
  const limited = type !== "continuous" && Number.isFinite(lower) && Number.isFinite(upper) && lower < upper;
  return {
    id: index,
    name: joint.urdfName || `joint_${index}`,
    type,
    limited,
    lower: limited ? lower : type === "continuous" ? -Math.PI : -1,
    upper: limited ? upper : type === "continuous" ? Math.PI : 1,
    qposAddress: index,
    joint,
  };
}
