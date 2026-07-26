class Worker {
  constructor(queue, handler) {
    this.queue = queue;
    this.handler = handler;
  }

  poll() {
    this.queue.on("job", this.handler);
    this.queue.drain();
  }
}

module.exports = { Worker };
