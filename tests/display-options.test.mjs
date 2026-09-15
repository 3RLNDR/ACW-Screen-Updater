import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(new URL("../public/display-options.js", import.meta.url), "utf8");
const context = { URL, window: {} };
context.globalThis = context;
vm.runInNewContext(source, context);

const { buildFullscreenUrl, shouldIncludeClasses } = context.window.AcwDisplayOptions;

test("fullscreen includes classes when the URL does not opt out", () => {
  assert.equal(shouldIncludeClasses(new URLSearchParams("")), true);
});

test("fullscreen excludes classes only when includeClasses is explicitly false", () => {
  assert.equal(shouldIncludeClasses(new URLSearchParams("includeClasses=false")), false);
  assert.equal(shouldIncludeClasses(new URLSearchParams("includeClasses=true")), true);
});

test("dashboard fullscreen URL follows the selected include-classes state", () => {
  const url = buildFullscreenUrl("https://example.test/acw/index.html", {
    includeClasses: true,
    theme: "heritage"
  });

  assert.equal(url.toString(), "https://example.test/acw/fullscreen.html?includeClasses=true&theme=heritage");
});

test("default fullscreen filtering keeps every event payload item", () => {
  const eventsSource = fs.readFileSync(new URL("../public/events.json", import.meta.url), "utf8").replace(/^\uFEFF/, "");
  const payload = JSON.parse(eventsSource);
  const includeClasses = shouldIncludeClasses(new URLSearchParams(""));
  const visibleItems = payload.items.filter((item) => includeClasses || !item.isClass);

  assert.equal(visibleItems.length, payload.items.length);
});

test("frontend runtime no longer supports the deprecated local server API", () => {
  const frontendSources = [
    fs.readFileSync(new URL("../public/app.js", import.meta.url), "utf8"),
    fs.readFileSync(new URL("../public/fullscreen.js", import.meta.url), "utf8")
  ].join("\n");

  assert.doesNotMatch(frontendSources, /\/api\/events/);
  assert.doesNotMatch(frontendSources, /localhost:8080|isLocalServer|dataMode === "server"/);
});
