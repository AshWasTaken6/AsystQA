from dataclasses import dataclass
from typing import Any

# Import agent classes for registry
try:
    from agents.sentinel import SentinelAgent, run_sentinel
    from agents.critic import CriticAgent, run_critic
    from agents.security import AuditorAgent, run_security
    from agents.planner import ArchitectAgent, run_planner
    from agents.tester import ChaosEngineerAgent, run_tester
    from agents.reporter import ReporterAgent
    AGENT_CLASSES_AVAILABLE = True
except ImportError:
    AGENT_CLASSES_AVAILABLE = False
    run_sentinel = None
    run_critic = None
    run_security = None
    run_planner = None
    run_tester = None

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
    agent_class: type = None  # Reference to agent class for factory


# Agent registry with version tracking
AGENT_REGISTRY: dict[str, AgentDefinition] = {
    "architect": AgentDefinition(
        "architect",
        "3.0.0",
        "planning",
        run_planner,  # compatibility wrapper
        required=True,
        agent_class=ArchitectAgent if AGENT_CLASSES_AVAILABLE else None,
    ),
    "sentinel": AgentDefinition(
        "sentinel",
        "3.0.0",
        "diagnostics",
        run_sentinel,
        required=True,
        agent_class=SentinelAgent if AGENT_CLASSES_AVAILABLE else None,
    ),
    "auditor": AgentDefinition(
        "auditor",
        "3.0.0",
        "security",
        run_security,
        required=True,
        agent_class=AuditorAgent if AGENT_CLASSES_AVAILABLE else None,
    ),
    "critic": AgentDefinition(
        "critic",
        "3.0.0",
        "formal-review",
        run_critic,
        required=True,
        agent_class=CriticAgent if AGENT_CLASSES_AVAILABLE else None,
    ),
    "chaos_engineer": AgentDefinition(
        "chaos_engineer",
        "3.0.0",
        "testing",
        run_tester,
        required=True,
        agent_class=ChaosEngineerAgent if AGENT_CLASSES_AVAILABLE else None,
    ),
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
