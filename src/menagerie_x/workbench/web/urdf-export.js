export class UrdfExportRequestError extends Error {
  constructor(message, report = null) {
    super(message);
    this.name = "UrdfExportRequestError";
    this.report = report;
  }
}

export async function requestUrdfExport(fetchImpl, url) {
  const response = await fetchImpl(url, { cache: "no-store" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: response.statusText, report: null }));
    throw new UrdfExportRequestError(payload.error || "URDF export failed", payload.report || null);
  }
  const disposition = response.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="([^"/\\]+\.urdf)"/i);
  const sourceCollisionCount = Number(response.headers.get("x-menagerie-mjcf-collision-count"));
  const outputCollisionCount = Number(response.headers.get("x-menagerie-urdf-collision-count"));
  if (!match || !Number.isInteger(sourceCollisionCount) || !Number.isInteger(outputCollisionCount)) {
    throw new UrdfExportRequestError("URDF export response metadata is invalid");
  }
  return { filename: match[1], blob: await response.blob(), sourceCollisionCount, outputCollisionCount };
}

export function downloadUrdf(documentRef, urlApi, download) {
  const objectUrl = urlApi.createObjectURL(download.blob);
  try {
    const anchor = documentRef.createElement("a");
    anchor.href = objectUrl;
    anchor.download = download.filename;
    documentRef.body.append(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    urlApi.revokeObjectURL(objectUrl);
  }
}
