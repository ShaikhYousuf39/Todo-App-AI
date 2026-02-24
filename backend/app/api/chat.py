from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional, List
from sqlmodel import Session, select
from datetime import datetime

from ..database import get_session
from ..auth import get_current_user_id
from ..models import Conversation, Message

router = APIRouter()


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    conversation_id: Optional[int] = None
    message: str


class ToolCall(BaseModel):
    """Tool call information."""
    name: str
    arguments: dict
    result: Optional[Any] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    conversation_id: int
    response: str
    tool_calls: List[ToolCall] = Field(default_factory=list)


@router.post("/{user_id}/chat", response_model=ChatResponse)
async def chat(
    user_id: str,
    request: ChatRequest,
    session: Session = Depends(get_session),
    auth_user_id: str = Depends(get_current_user_id),
):
    """
    Send a message to the AI chatbot and get a response.

    The chatbot understands natural language commands for managing todos:
    - "Add a task to buy groceries"
    - "Show me all my tasks"
    - "Mark task 3 as complete"
    - "Delete the meeting task"
    """
    # Verify user authorization
    if user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's chat")

    # Get or create conversation
    if request.conversation_id:
        conversation = session.get(Conversation, request.conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation.updated_at = datetime.utcnow()
    else:
        conversation = Conversation(user_id=user_id)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)

    # Store user message
    user_message = Message(
        user_id=user_id,
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    session.add(user_message)
    session.commit()

    # Get conversation history
    messages = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    ).all()

    # Run agent with MCP tools (to be implemented)
    from ..agent.todo_agent import run_agent

    agent_response, tool_calls = await run_agent(
        user_id=user_id,
        messages=messages,
        session=session,
    )

    # Store assistant response
    assistant_message = Message(
        user_id=user_id,
        conversation_id=conversation.id,
        role="assistant",
        content=agent_response,
    )
    session.add(assistant_message)
    session.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        response=agent_response,
        tool_calls=tool_calls,
    )
