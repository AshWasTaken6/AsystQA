from typing import Any

from agents.critic import run_critic
from agents.sentinel import run_sentinel


async def run_reviewer(code: str, language: str, context: dict[str, Any] | None = None) -> list[dict]:
    """
    Compatibility wrapper for the review lane.

    The review lane now contains two autonomous specialists:
    - Sentinel: execution, exception, and recovery diagnostics.
    - Critic: formal review, semantic defects, and design-contract drift.
    """
    sentinel_findings = await run_sentinel(code, language, context)
    critic_context = {**(context or {}), "sentinel": sentinel_findings}
    critic_findings = await run_critic(code, language, critic_context)
    return [*sentinel_findings, *critic_findings]
