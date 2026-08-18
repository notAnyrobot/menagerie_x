const PREFERRED_VIDEO_FORMATS = [
  { mimeType: "video/mp4;codecs=avc1.42E01E,mp4a.40.2", extension: "mp4", label: "MP4" },
  { mimeType: "video/mp4", extension: "mp4", label: "MP4" },
  { mimeType: "video/webm;codecs=vp9,opus", extension: "webm", label: "WebM" },
  { mimeType: "video/webm;codecs=vp8,opus", extension: "webm", label: "WebM" },
  { mimeType: "video/webm", extension: "webm", label: "WebM" },
];

export function videoFormatForMimeType(mimeType) {
  const normalized = (mimeType || "").toLowerCase();
  if (normalized.includes("mp4")) return { mimeType, extension: "mp4", label: "MP4" };
  if (normalized.includes("webm")) return { mimeType, extension: "webm", label: "WebM" };
  return { mimeType, extension: "webm", label: "video" };
}

export function selectRecordingFormat(MediaRecorderConstructor) {
  if (typeof MediaRecorderConstructor !== "function") return null;
  const supports = typeof MediaRecorderConstructor.isTypeSupported === "function"
    ? MediaRecorderConstructor.isTypeSupported.bind(MediaRecorderConstructor)
    : () => false;
  return PREFERRED_VIDEO_FORMATS.find(format => supports(format.mimeType)) || null;
}

export function recordingFilename({ robotName, editionName, date = new Date(), extension = "webm" }) {
  const safePart = value => String(value || "scene")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "scene";
  const stamp = date.toISOString().replace(/[:.]/g, "-").replace("T", "_").replace("Z", "");
  return `${safePart(robotName)}_${safePart(editionName)}_${stamp}.${extension}`;
}

/**
 * Captures exactly one canvas stream. Scene overlays are part of the WebGL
 * canvas, while surrounding workbench controls are intentionally excluded.
 */
export class SceneRecorder {
  constructor({ canvas, frameRate = 30, MediaRecorderConstructor = globalThis.MediaRecorder, now = () => new Date(), onStateChange = () => {} }) {
    this.canvas = canvas;
    this.frameRate = frameRate;
    this.MediaRecorderConstructor = MediaRecorderConstructor;
    this.now = now;
    this.onStateChange = onStateChange;
    this.state = "ready";
    this.stream = null;
    this.recorder = null;
    this.chunks = [];
    this.startedAt = null;
    this.format = null;
  }

  start() {
    if (this.state !== "ready") throw new Error("A scene recording is already active.");
    if (!this.canvas?.captureStream) throw new Error("This browser cannot capture the 3D viewer canvas.");
    const format = selectRecordingFormat(this.MediaRecorderConstructor);
    if (!format) throw new Error("This browser cannot encode MP4 or WebM video from the 3D viewer.");

    try {
      this.stream = this.canvas.captureStream(this.frameRate);
      this.recorder = new this.MediaRecorderConstructor(this.stream, { mimeType: format.mimeType });
    } catch (error) {
      this.cleanup();
      throw new Error(`Could not start scene recording: ${error.message || error}`);
    }
    this.chunks = [];
    this.format = videoFormatForMimeType(this.recorder.mimeType || format.mimeType);
    this.startedAt = this.now();
    this.recorder.ondataavailable = event => {
      if (event.data?.size) this.chunks.push(event.data);
    };
    this.recorder.start(1000);
    this.setState("recording");
    return { format: this.format, startedAt: this.startedAt };
  }

  stop() {
    if (this.state !== "recording" || !this.recorder) return Promise.reject(new Error("No scene recording is active."));
    this.setState("finalizing");
    return new Promise((resolve, reject) => {
      const recorder = this.recorder;
      recorder.onerror = event => {
        const error = event.error || new Error("The browser could not encode the scene recording.");
        this.cleanup();
        this.setState("ready");
        reject(error);
      };
      recorder.onstop = () => {
        const mimeType = recorder.mimeType || this.format?.mimeType || this.chunks[0]?.type || "video/webm";
        const format = videoFormatForMimeType(mimeType);
        const result = { blob: new Blob(this.chunks, { type: mimeType }), format, startedAt: this.startedAt, completedAt: this.now() };
        this.cleanup();
        this.setState("ready");
        resolve(result);
      };
      try {
        recorder.stop();
      } catch (error) {
        this.cleanup();
        this.setState("ready");
        reject(error);
      }
    });
  }

  cleanup() {
    this.stream?.getTracks?.().forEach(track => track.stop());
    this.stream = null;
    this.recorder = null;
    this.chunks = [];
    this.startedAt = null;
  }

  setState(state) {
    this.state = state;
    this.onStateChange(state, this.format);
  }
}
