from typing import Protocol

from pydantic import BaseModel

from app.agent.models import AgentExecutionContext, ToolResult


class AgentTool(Protocol):
    name: str
    description: str
    input_model: type[BaseModel]

    def execute(self, arguments: BaseModel, context: AgentExecutionContext) -> ToolResult: ...
