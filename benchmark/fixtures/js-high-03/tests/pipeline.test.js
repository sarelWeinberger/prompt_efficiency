const test = require("node:test");
const assert = require("node:assert");
const { makePipeline } = require("../src/index");

test("each job handled exactly once across ticks", () => {
  const handled = [];
  const { queue, worker } = makePipeline((job) => handled.push(job));
  queue.push("j1");
  worker.poll();
  queue.push("j2");
  worker.poll();
  assert.deepStrictEqual(handled, ["j1", "j2"]);
});
