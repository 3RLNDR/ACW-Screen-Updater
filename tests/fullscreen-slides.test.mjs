import test from "node:test";
import assert from "node:assert/strict";

import { getNextRenderableSlide } from "../public/slide-sequence.mjs";

test("getNextRenderableSlide skips broken video slides", () => {
  const slides = [
    { type: "video", id: "video-1", src: "./cache/videos/missing.mp4", eventId: "event-1" },
    { type: "event", id: "event-1", title: "Jazz Night" }
  ];

  const nextSlide = getNextRenderableSlide(slides, 0, new Set(["video-1"]));

  assert.equal(nextSlide.id, "event-1");
});
