from bson import ObjectId


def object_id_to_str(value: ObjectId) -> str:
    """Convert a MongoDB ObjectId into a normal string for JSON responses."""
    return str(value)


def is_valid_object_id(value: str) -> bool:
    """Check whether a string can be used as a MongoDB ObjectId."""
    return ObjectId.is_valid(value)
