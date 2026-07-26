BINARY_BASE = 1024

_SUFFIXES = {
    "B": 1,
    "KB": BINARY_BASE,
    "MB": BINARY_BASE ** 2,
    "GB": BINARY_BASE ** 3,
}


def parse_size(text):
    """Parse a human-readable size such as '10KB' into a number of bytes."""
    text = text.strip().upper()
    for suffix, mult in sorted(_SUFFIXES.items(), key=lambda kv: -len(kv[0])):
        if text.endswith(suffix):
            return int(float(text[: -len(suffix)]) * mult)
    return int(text)
