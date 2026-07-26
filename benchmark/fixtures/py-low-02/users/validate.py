import re

USERNAME_RE = re.compile(r"^[a-z0-9_]+$")


def is_valid_username(name):
    """A valid username is 3-20 characters of [a-z0-9_], inclusive bounds."""
    if not isinstance(name, str):
        return False
    if len(name) <= 3 or len(name) > 20:
        return False
    return bool(USERNAME_RE.match(name))
