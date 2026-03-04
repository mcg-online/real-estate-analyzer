from bson import ObjectId
from bson.errors import InvalidId


def is_valid_objectid(value):
    """Check if value is a valid 24-character hex ObjectId string."""
    try:
        ObjectId(value)
        return True
    except (InvalidId, TypeError):
        return False
