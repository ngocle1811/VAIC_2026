"""Explicit Agent composition; no fake tool is registered implicitly in production."""

from collections.abc import Iterable

from app.agent.orchestrator import AgentOrchestrator
from app.agent.tool_protocol import AgentTool
from app.agent.tool_registry import ToolRegistry
from app.config import Settings
from app.llm.base import LLMClient


def create_tool_registry(tools: Iterable[AgentTool]) -> ToolRegistry:
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return registry


def create_agent_orchestrator(
    settings: Settings,
    llm: LLMClient,
    tools: Iterable[AgentTool],
    *,
    allow_scaffold_run: bool = False,
) -> AgentOrchestrator:
    return AgentOrchestrator(
        llm,
        create_tool_registry(tools),
        max_steps=settings.agent_max_steps,
        production_enabled=settings.agent_enable_production_orchestration,
        allow_scaffold_run=allow_scaffold_run,
    )
