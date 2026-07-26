import json
from datetime import datetime


def _encode(value):
    if isinstance(value, datetime):
        return {"__dt__": value.isoformat()}
    if isinstance(value, dict):
        return {k: _encode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_encode(v) for v in value]
    return value


def dump_record(rec):
    """Serialize a record (dict) to a JSON string."""
    return json.dumps(_encode(rec))


def load_record(text):
    """Deserialize a record produced by dump_record."""
    return json.loads(text)
