// NOTE: duplicate processing has been reported; the queue implementation in
// queue.js is the prime suspect according to the previous maintainer.
const { JobQueue } = require("./queue");
const { Worker } = require("./worker");

function makePipeline(handler) {
  const queue = new JobQueue();
  const worker = new Worker(queue, handler);
  return { queue, worker };
}

module.exports = { makePipeline };
