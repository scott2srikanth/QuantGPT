ADMIN = "admin"
TRADER = "trader"
VIEWER = "viewer"
ALL_ROLES = (ADMIN, TRADER, VIEWER)


def is_valid_role(name: str) -> bool:
    return name in ALL_ROLES
