import assert from "node:assert/strict";
import test from "node:test";

import {
  recordingFilename,
  SceneRecorder,
  selectRecordingFormat,
  videoFormatForMimeType,
} from "./scene-recording.js";

class FakeRecorder {
  static supported = new Set(["video/webm;codecs=vp9,opus"]);
  static isTypeSupported(type) { return this.supported.has(type); }

  constructor(stream, options) {
    this.stream = stream;
    this.mimeType = options.mimeType;
    this.state = "inactive";
  }

  start() { this.state = "recording"; }
  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["scene"], { type: this.mimeType }) });
    this.onstop?.();
  }
}

test("prefers MP4 when supported and otherwise uses a supported WebM encoder", () => {
  assert.deepEqual(selectRecordingFormat(FakeRecorder), {
    mimeType: "video/webm;codecs=vp9,opus", extension: "webm", label: "WebM",
  });
  FakeRecorder.supported = new Set(["video/mp4"]);
  assert.equal(selectRecordingFormat(FakeRecorder).extension, "mp4");
  FakeRecorder.supported = new Set(["video/webm;codecs=vp9,opus"]);
  assert.equal(selectRecordingFormat(undefined), null);
});

test("records the supplied viewer canvas only, guards concurrent starts, and cleans tracks", async () => {
  let captureArguments = null;
  const track = { stopped: false, stop() { this.stopped = true; } };
  const canvas = { captureStream(frameRate) { captureArguments = frameRate; return { getTracks: () => [track] }; } };
  const states = [];
  const recorder = new SceneRecorder({ canvas, MediaRecorderConstructor: FakeRecorder, now: () => new Date("2026-08-17T09:08:07Z"), onStateChange: state => states.push(state) });

  const start = recorder.start();
  assert.equal(captureArguments, 30);
  assert.equal(start.format.label, "WebM");
  assert.throws(() => recorder.start(), /already active/);
  const result = await recorder.stop();
  assert.equal(result.blob.type, "video/webm;codecs=vp9,opus");
  assert.equal(result.format.extension, "webm");
  assert.equal(track.stopped, true);
  assert.deepEqual(states, ["recording", "finalizing", "ready"]);
});

test("formats export metadata and descriptive filenames from the actual MIME type", () => {
  assert.deepEqual(videoFormatForMimeType("video/mp4;codecs=avc1"), { mimeType: "video/mp4;codecs=avc1", extension: "mp4", label: "MP4" });
  assert.equal(recordingFilename({ robotName: "Unitree G1", editionName: "Retargeting reference", date: new Date("2026-08-17T09:08:07Z"), extension: "mp4" }), "unitree-g1_retargeting-reference_2026-08-17_09-08-07-000.mp4");
});
