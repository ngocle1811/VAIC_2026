"""Dependency-injected tool registry with validation and safe errors."""

import logging
from time import perf_counter

from pydantic import ValidationError

from app.agent.models import (
    AgentExecutionContext,
    ToolDefinition,
    ToolError,
    ToolResult,
)
from app.agent.tool_protocol import AgentTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)

    def definitions(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_model.model_json_schema(),
            )
            for tool in self._tools.values()
        ]

    def execute(self, name: str, arguments: dict, context: AgentExecutionContext) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                success=False,
                error=ToolError(code="unknown_tool", message=f"Unknown tool: {name}"),
            )
        started = perf_counter()
        try:
            validated = tool.input_model.model_validate(arguments)
            result = tool.execute(validated, context)
        except ValidationError:
            result = ToolResult(
                success=False,
                error=ToolError(code="invalid_arguments", message="Tool arguments are invalid"),
            )
        except Exception:
            logger.exception("Agent tool execution failed", extra={"tool_name": name})
            result = ToolResult(
                success=False,
                error=ToolError(code="tool_failure", message="Tool execution failed safely"),
            )
        result.duration_ms = (perf_counter() - started) * 1000
        return result
