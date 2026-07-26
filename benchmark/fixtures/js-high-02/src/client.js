const USERS = { 1: { id: 1, name: "ada" }, 2: { id: 2, name: "lin" } };

function getUser(id, callback) {
  setImmediate(() => {
    const user = USERS[id];
    if (!user) return callback(new Error("not found"));
    callback(null, user);
  });
}

module.exports = { getUser };
