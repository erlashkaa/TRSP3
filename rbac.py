from enum import Enum
from typing import Dict, List, Optional
from fastapi import HTTPException, status, Depends

from auth import get_current_user_jwt, get_current_user_basic, fake_users_db

class Role(str, Enum):
    """User roles (Задание 7.1)"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

# Role permissions mapping
ROLE_PERMISSIONS: Dict[Role, List[str]] = {
    Role.ADMIN: ["create", "read", "update", "delete"],
    Role.USER: ["read", "update"],
    Role.GUEST: ["read"],
}

# Store user roles (in-memory for demo)
user_roles: Dict[str, Role] = {
    "admin": Role.ADMIN,
    "user1": Role.USER,
    "guest": Role.GUEST,
}

def get_user_role(username: str) -> Role:
    """Get role for a user"""
    return user_roles.get(username, Role.GUEST)

def has_permission(username: str, required_permission: str) -> bool:
    """Check if user has a specific permission"""
    role = get_user_role(username)
    permissions = ROLE_PERMISSIONS.get(role, [])
    return required_permission in permissions

def require_permission(required_permission: str):
    """Dependency factory for role-based access control"""
    async def permission_dependency(username: str = Depends(get_current_user_jwt)):
        if not has_permission(username, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Need '{required_permission}' permission."
            )
        return username
    return permission_dependency

def require_role(allowed_roles: List[Role]):
    """Dependency factory for role-based access control"""
    async def role_dependency(username: str = Depends(get_current_user_jwt)):
        user_role = get_user_role(username)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}. Your role: {user_role.value}"
            )
        return username
    return role_dependency

# Helper to register user with role (for testing RBAC)
def register_user_with_role(username: str, password: str, role: Role):
    """Register user with specific role (for testing)"""
    from auth import get_password_hash, fake_users_db
    
    if username in fake_users_db:
        return False
    
    fake_users_db[username] = type('User', (), {
        'username': username,
        'hashed_password': get_password_hash(password)
    })()
    
    user_roles[username] = role
    return True