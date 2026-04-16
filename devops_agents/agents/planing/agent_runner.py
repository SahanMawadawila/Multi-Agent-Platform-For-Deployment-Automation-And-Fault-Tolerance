"""Shared runner for planning sub-agents."""

from typing import Any, Dict, List, Type

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config.settings import settings


async def run_agent(
    *,
    system_prompt: str,
    user_prompt: str,
    output_tool: Type[BaseModel],
    tools: List[Any],
    agent_state: Dict[str, Any],
    logger,
    max_iterations: int = 30,
) -> BaseModel:
    """Runs an agentic loop with tool calls and returns the structured output."""
    llm = ChatOpenAI(
        model="o4-mini",
        api_key=settings.openai_key,
    )

    tool_map = {}
    for tool in tools:
        tool_name = getattr(tool, "__name__", None) or getattr(tool, "name", None)
        if not tool_name:
            raise ValueError("Tool is missing a name attribute.")
        tool_map[tool_name] = tool
    llm_with_tools = llm.bind_tools([*tools, output_tool])

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    output_tool_name = output_tool.__name__

    for iteration in range(max_iterations):
        logger.info("Planning sub-agent step %s (%s)", iteration + 1, output_tool_name)

        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            if response.content:
                messages.append(HumanMessage(
                    content=f"Please continue and call {output_tool_name} when ready."
                ))
            continue

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if tool_name == output_tool_name:
                return output_tool(**tool_args)

            if tool_name in tool_map:
                result = await tool_map[tool_name].ainvoke({**tool_args, "state": agent_state})
                messages.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                ))
                continue

            messages.append(ToolMessage(
                content=f"Unknown tool: {tool_name}",
                tool_call_id=tool_call["id"],
            ))

    raise RuntimeError(f"{output_tool_name} did not converge within the iteration limit.")
