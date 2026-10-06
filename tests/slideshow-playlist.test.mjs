import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

import { buildStaticPlaylist, findSlideIndex } from "../public/slideshow-playlist.mjs";

test("buildStaticPlaylist appends configured videos after visible events", () => {
  const playlist = buildStaticPlaylist(
    {
      items: [
        { title: "Main Stage", isClass: false },
        { title: "Workshop", isClass: true }
      ]
    },
    {
      videos: [
        {
          title: "Season Trailer",
          src: "cache/videos/season-trailer.mp4",
          durationSeconds: 30
        }
      ]
    },
    false
  );

  assert.deepEqual(
    playlist.map((slide) => slide.type),
    ["event", "video"]
  );
  assert.equal(playlist[0].title, "Main Stage");
  assert.equal(playlist[1].title, "Season Trailer");
  assert.equal(playlist[1].src, "cache/videos/season-trailer.mp4");
});

test("buildStaticPlaylist ignores video entries without a source", () => {
  const playlist = buildStaticPlaylist(
    { items: [{ title: "Main Stage", isClass: false }] },
    { videos: [{ title: "Broken Trailer" }] },
    true
  );

  assert.deepEqual(
    playlist.map((slide) => slide.type),
    ["event"]
  );
});

test("findSlideIndex keeps the current event after refreshed events are reordered", () => {
  const currentSlide = {
    type: "event",
    title: "Event 31",
    link: "https://example.test/events/31"
  };
  const refreshedPlaylist = [
    { type: "event", title: "New event", link: "https://example.test/events/new" },
    { type: "event", title: "Event 31, updated", link: "https://example.test/events/31" },
    { type: "event", title: "Later event", link: "https://example.test/events/later" }
  ];

  assert.equal(findSlideIndex(refreshedPlaylist, currentSlide), 1);
});

test("fullscreen runtime is wired for the static video playlist", () => {
  const html = fs.readFileSync(new URL("../public/fullscreen.html", import.meta.url), "utf8");
  const source = fs.readFileSync(new URL("../public/fullscreen.js", import.meta.url), "utf8");

  assert.match(html, /id="slideVideo"/);
  assert.match(html, /type="module" src="\.\/fullscreen\.js\?v=20261006"/);
  assert.match(source, /playlist-manifest\.json/);
  assert.doesNotMatch(source, /videos\.json/);
  assert.match(source, /renderVideoSlide/);
});

test("video slides are unmuted and use a dedicated full-screen layout", () => {
  const html = fs.readFileSync(new URL("../public/fullscreen.html", import.meta.url), "utf8");
  const source = fs.readFileSync(new URL("../public/fullscreen.js", import.meta.url), "utf8");
  const styles = fs.readFileSync(new URL("../public/styles.css", import.meta.url), "utf8");
  const slideVideoIdIndex = html.indexOf('id="slideVideo"');
  const slideVideoStart = html.lastIndexOf("<video", slideVideoIdIndex);
  const slideVideoEnd = html.indexOf("</video>", slideVideoIdIndex) + "</video>".length;
  const slideVideoMarkup = html.slice(slideVideoStart, slideVideoEnd);

  assert.notEqual(slideVideoIdIndex, -1);
  assert.doesNotMatch(slideVideoMarkup, /\s muted(?:\s|>)/);
  assert.match(source, /document\.body\.setAttribute\("data-slide-type", "video"\)/);
  assert.match(source, /slideVideo\.muted = false/);
  assert.match(styles, /\.fullscreen-body\[data-slide-type="video"\] \.fullscreen-stage/);
  assert.match(styles, /\.fullscreen-body\[data-slide-type="video"\] \.fullscreen-content/);
  assert.match(styles, /display: none/);
  assert.match(styles, /object-fit: contain/);
});

test("test output page keeps the slide video aligned with fullscreen markup", () => {
  const html = fs.readFileSync(new URL("../public/test-output.html", import.meta.url), "utf8");
  const slideVideoIdIndex = html.indexOf('id="slideVideo"');
  const slideVideoStart = html.lastIndexOf("<video", slideVideoIdIndex);
  const slideVideoEnd = html.indexOf("</video>", slideVideoIdIndex) + "</video>".length;
  const slideVideoMarkup = html.slice(slideVideoStart, slideVideoEnd);

  assert.notEqual(slideVideoIdIndex, -1);
  assert.doesNotMatch(slideVideoMarkup, /\s muted(?:\s|>)/);
  assert.match(html, /type="module" src="\.\/fullscreen\.js\?v=20261006"/);
});

test("trailer preview page shows only the configured trailer video", () => {
  const html = fs.readFileSync(new URL("../public/trailer-preview.html", import.meta.url), "utf8");

  assert.match(html, /src="cache\/videos\/trailer\.mp4"/);
  assert.match(html, /object-fit: contain/);
  assert.doesNotMatch(html, /fullscreen-content|slideTitle|slideDetails/);
});

test("trailer flow preview shows one slide before the trailer", () => {
  const html = fs.readFileSync(new URL("../public/trailer-flow-preview.html", import.meta.url), "utf8");

  assert.match(html, /id="previewSlide"/);
  assert.match(html, /id="previewVideo"/);
  assert.match(html, /src="cache\/videos\/trailer\.mp4"/);
  assert.match(html, /setTimeout\(showVideo, slideDurationMs\)/);
  assert.match(html, /previewVideo\.muted = false/);
  assert.match(html, /previewVideo\.addEventListener\("ended", showSlide\)/);
  assert.match(html, /function showSlide\(\)/);
});
