"""Hierarchical access control: role + area scoping (blueprint §2.1, §5 RBAC).

Privileged roles (super admin, admin empresa, security/compliance) see every
area of their tenant. Business users and devops see only their own area plus
unassigned/"general" content (area == ""). The super admin additionally crosses
tenant boundaries (handled at the router level).
"""
from __future__ import annotations

from .models import Role, User

# Roles that can see all areas within their tenant.
PRIVILEGED_ROLES = {Role.SUPER_ADMIN, Role.ADMIN, Role.SECURITY}


def sees_all_areas(user: User) -> bool:
    return user.role in PRIVILEGED_ROLES


def visible_areas(user: User) -> list[str] | None:
    """Areas the user may see. None means 'all' (no restriction)."""
    if sees_all_areas(user):
        return None
    return [user.area] if user.area else []


def can_view_area(user: User, area: str) -> bool:
    """General/unassigned content (area == '') is visible to everyone in the tenant."""
    if sees_all_areas(user):
        return True
    if not (area or "").strip():
        return True
    return area == user.area
