import uuid


def new_id(prefix: str, short: int = 8) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:short]}"
