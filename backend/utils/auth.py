# JWT token blocklist (in-memory for single worker; use Redis for multi-worker)
# Held here to avoid circular imports between app.py and routes/users.py.
_jwt_blocklist: set = set()


def add_token_to_blocklist(jti: str) -> None:
    _jwt_blocklist.add(jti)


def is_token_revoked(jti: str) -> bool:
    return jti in _jwt_blocklist
