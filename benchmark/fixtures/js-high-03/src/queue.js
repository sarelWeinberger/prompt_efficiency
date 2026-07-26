class JobQueue {
  constructor() {
    this.jobs = [];
    this.handlers = [];
  }

  on(event, fn) {
    if (event === "job") this.handlers.push(fn);
  }

  push(job) {
    this.jobs.push(job);
  }

  drain() {
    const pending = this.jobs.splice(0);
    for (const job of pending) {
      for (const fn of this.handlers) fn(job);
    }
  }
}

module.exports = { JobQueue };
