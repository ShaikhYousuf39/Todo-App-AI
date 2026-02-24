"""
Todo AI Agent using OpenAI Agents SDK.

This agent handles natural language commands for managing todo tasks
and uses MCP tools to perform task operations.
"""

import json
import os
import re
from typing import List, Optional, Tuple
from sqlmodel import Session

from openai import OpenAI
from ..mcp.tools import TOOL_DEFINITIONS, execute_tool
from ..models import Message
from ..config import get_settings

settings = get_settings()

# Initialize OpenAI client
client = OpenAI(api_key=settings.openai_api_key)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_CONTEXT_MESSAGES = 12
MAX_TOOL_ITERATIONS = 4

# Shorter prompt reduces token count and latency.
SYSTEM_PROMPT = """You manage todo tasks with tools.
Use tools for add/list/complete/delete/update actions.
Be concise and friendly.
If the user is ambiguous, ask a clarifying question.
If a task is not found, say so clearly."""


def _recent_openai_messages(messages: List[Message]) -> list[dict]:
    """Trim history to recent messages to keep latency low."""
    recent = messages[-MAX_CONTEXT_MESSAGES:]
    return [{"role": "system", "content": SYSTEM_PROMPT}] + [
        {
            "role": msg.role,
            "content": msg.content,
        }
        for msg in recent
    ]


def _strip_wrapping_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def _fast_path_command(
    user_id: str,
    messages: List[Message],
    session: Session,
) -> Optional[Tuple[str, List[dict]]]:
    """Handle common explicit commands without an LLM round-trip."""
    latest_user = next((m for m in reversed(messages) if m.role == "user"), None)
    if not latest_user:
        return None

    text = latest_user.content.strip()
    if not text:
        return None
    lower = text.lower().strip()

    def run_tool(tool_name: str, arguments: dict, response_text: str | None = None):
        result = execute_tool(
            session=session,
            user_id=user_id,
            tool_name=tool_name,
            arguments=arguments,
        )
        if response_text is None:
            if tool_name == "add_task":
                response_text = f"Added task: {result.get('title', arguments.get('title', 'Untitled'))}."
            elif tool_name == "list_tasks":
                items = result if isinstance(result, list) else []
                if not items:
                    response_text = "You don't have any matching tasks yet."
                else:
                    lines = [
                        f"{'Done' if item.get('completed') else 'Todo'} #{item.get('id')}: {item.get('title')}"
                        for item in items[:10]
                    ]
                    if len(items) > 10:
                        lines.append(f"...and {len(items) - 10} more.")
                    response_text = "Here are your tasks:\n" + "\n".join(lines)
            elif tool_name == "complete_task":
                response_text = (
                    f"Completed task #{result.get('task_id')}: {result.get('title')}."
                    if result.get("status") == "completed"
                    else result.get("error", "Task not found.")
                )
            elif tool_name == "delete_task":
                response_text = (
                    f"Deleted task #{result.get('task_id')}: {result.get('title')}."
                    if result.get("status") == "deleted"
                    else result.get("error", "Task not found.")
                )
            elif tool_name == "update_task":
                response_text = (
                    f"Updated task #{result.get('task_id')}: {result.get('title')}."
                    if result.get("status") == "updated"
                    else result.get("error", "Task not found.")
                )
            else:
                response_text = "Done."

        return response_text, [{"name": tool_name, "arguments": arguments, "result": result}]

    # add/create task
    add_match = re.match(
        r"^(?:add|create)\s+(?:a\s+)?task(?:\s+to)?\s+(.+)$",
        text,
        flags=re.IGNORECASE,
    ) or re.match(r"^remember\s+to\s+(.+)$", text, flags=re.IGNORECASE)
    if add_match:
        title = _strip_wrapping_quotes(add_match.group(1))
        if title:
            return run_tool("add_task", {"title": title})

    # list/show tasks
    if any(phrase in lower for phrase in ["what's pending", "what is pending", "pending tasks"]):
        return run_tool("list_tasks", {"status": "pending"})
    if any(phrase in lower for phrase in ["completed tasks", "done tasks", "finished tasks"]):
        return run_tool("list_tasks", {"status": "completed"})
    if (
        ("task" in lower or "todo" in lower)
        and any(word in lower for word in ["list", "show", "what", "display"])
    ) or lower in {"tasks", "todos", "show tasks", "list tasks"}:
        status = "all"
        if "pending" in lower:
            status = "pending"
        elif any(word in lower for word in ["completed", "done", "finished"]):
            status = "completed"
        return run_tool("list_tasks", {"status": status})

    # complete task by id
    complete_match = re.search(
        r"(?:complete|finish|mark)\s+task\s+(\d+)(?:\s+as\s+(?:done|complete))?",
        lower,
    )
    if complete_match:
        return run_tool("complete_task", {"task_id": int(complete_match.group(1))})

    # delete/remove task by id
    delete_match = re.search(r"(?:delete|remove)\s+task\s+(\d+)", lower)
    if delete_match:
        return run_tool("delete_task", {"task_id": int(delete_match.group(1))})

    # update task by id
    update_match = re.search(
        r"(?:change|update|rename)\s+task\s+(\d+)\s+(?:to|as)\s+(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if update_match:
        task_id = int(update_match.group(1))
        title = _strip_wrapping_quotes(update_match.group(2))
        if title:
            return run_tool("update_task", {"task_id": task_id, "title": title})

    return None


async def run_agent(
    user_id: str,
    messages: List[Message],
    session: Session,
) -> Tuple[str, List[dict]]:
    """
    Run the AI agent with the given conversation history.

    Args:
        user_id: The user's ID
        messages: List of conversation messages
        session: Database session for tool execution

    Returns:
        Tuple of (agent response, list of tool calls made)
    """
    fast_path = _fast_path_command(user_id=user_id, messages=messages, session=session)
    if fast_path:
        return fast_path

    # Convert messages to OpenAI format (trimmed for latency)
    openai_messages = _recent_openai_messages(messages)

    tool_calls_made = []

    for _ in range(MAX_TOOL_ITERATIONS):
        # Call OpenAI API with tools
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=openai_messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            max_tokens=220,
        )

        assistant_message = response.choices[0].message

        # If no tool calls, return the response
        if not assistant_message.tool_calls:
            return assistant_message.content or "I'm not sure how to help with that.", tool_calls_made

        # Process tool calls
        openai_messages.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant_message.tool_calls
            ],
        })

        # Execute each tool call
        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            # Execute the tool
            result = execute_tool(
                session=session,
                user_id=user_id,
                tool_name=tool_name,
                arguments=arguments,
            )

            # Track tool calls
            tool_calls_made.append({
                "name": tool_name,
                "arguments": arguments,
                "result": result,
            })

            # Add tool result to messages
            openai_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    # If we hit max iterations, return what we have
    return "I've completed the requested operations. Is there anything else you'd like me to do?", tool_calls_made
