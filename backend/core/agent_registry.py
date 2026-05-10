from dataclasses import dataclass

from agents.planner import run_planner
from agents.reviewer import run_reviewer
from agents.security import run_security
from agents.tester import run_tester
from core.auth import TokenData, get_current_user, get_user
from core.authorization import get_all_user_permissions
from fastapi import Depends, HTTPException, status


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    name: str
    version: str
    category: str
    callable: object
    required: bool = False


AGENT_REGISTRY: dict[str, AgentDefinition] = {
    "planner": AgentDefinition("planner", "1.0.0", "planning", run_planner),
    "reviewer": AgentDefinition("reviewer", "1.0.0", "quality", run_reviewer),
    "security": AgentDefinition("security", "1.0.0", "security", run_security),
    "tester": AgentDefinition("tester", "1.0.0", "testing", run_tester),
}


def list_agents() -> list[dict]:
    return [
        {
            "name": agent.name,
            "version": agent.version,
            "category": agent.category,
            "required": agent.required,
            "status": "available",
        }
        for agent in AGENT_REGISTRY.values()
    ]


# ============== Principal (User Identity) ==============

@dataclass(frozen=True, slots=True)
class Principal:
    """
    Represents an authenticated user's identity and permissions.
    Used for dependency injection in route handlers.
    """
    user_id: str
    username: str
    roles: list[str]
    permissions: set[str]
    session_id: str
    mfa_verified: bool = False


def get_current_principal(
    token_data: TokenData = Depends(get_current_user)
) -> Principal:
    """
    FastAPI dependency to extract current user's principal.
    """
    # Get full user from database
    user = get_user(token_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Build permissions set
    perms = get_all_user_permissions(token_data)

    return Principal(
        user_id=user.user_id,
        username=user.username,
        roles=user.roles,
        permissions=perms,
        session_id=token_data.session_id,
        mfa_verified=token_data.mfa_verified
    )


def require_permission(permission: str):
    """
    FastAPI dependency that requires a specific permission.
    Usage: principal: Principal = Depends(require_permission("code:analyze"))
    """
    async def dependency(
        token_data: TokenData = Depends(get_current_user)
    ) -> Principal:
        user = get_user(token_data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        perms = get_all_user_permissions(token_data)
        if permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}"
            )

        return Principal(
            user_id=user.user_id,
            username=user.username,
            roles=user.roles,
            permissions=perms,
            session_id=token_data.session_id,
            mfa_verified=token_data.mfa_verified
        )

    return dependency
