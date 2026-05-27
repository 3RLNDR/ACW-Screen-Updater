import test from "node:test";
import assert from "node:assert/strict";

import { buildAssociationViewModel } from "../public/video-admin-model.mjs";

test("buildAssociationViewModel marks linked events", () => {
  const rows = buildAssociationViewModel(
    [{ id: "event-jazz", title: "Jazz Night" }],
    [{ id: "video-jazz", title: "Jazz Trailer" }],
    { "event-jazz": "video-jazz" }
  );

  assert.equal(rows[0].selectedVideoId, "video-jazz");
  assert.equal(rows[0].hasAssociation, true);
});
