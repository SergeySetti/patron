import logging
from typing import Callable, Union

from langchain.agents.middleware import AgentMiddleware
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from dependencies import app_container, AssistantLogger

logger: logging.Logger = app_container.get(AssistantLogger)


class ToolLoggingMiddleware(AgentMiddleware):
    def wrap_tool_call(
            self,
            request: ToolCallRequest,
            handler: Callable[[ToolCallRequest], Union[ToolMessage, Command]],
    ) -> Union[ToolMessage, Command]:
        tool_name = request.tool_call["name"]
        tool_args = request.tool_call["args"]
        logger.info(f"Tool call: {tool_name} | args: {tool_args}")
        return handler(request)
