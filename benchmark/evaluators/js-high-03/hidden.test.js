const test = require("node:test");
const assert = require("node:assert");
const { makePipeline } = require("../src/index");

test("three ticks, three jobs, three handlings", () => {
  const handled = [];
  const { queue, worker } = makePipeline((job) => handled.push(job));
  for (const j of ["a", "b", "c"]) {
    queue.push(j);
    worker.poll();
  }
  assert.deepStrictEqual(handled, ["a", "b", "c"]);
});
