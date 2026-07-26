function serializeUser(user) {
  return {
    user_name: user.name,
    email: user.email,
    active: Boolean(user.active),
  };
}

module.exports = { serializeUser };
