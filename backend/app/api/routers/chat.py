from fastapi import APIRouter, HTTPException
from typing import Any
import traceback

from app.schemas.chat import ChatRequest
from app.services.chat_service import get_user_sessions, get_session_messages, process_chat_message

router = APIRouter()

@router.get("/sessions/{user_id}")
async def get_sessions_endpoint(user_id: str) -> Any:
    try:
        sessions = get_user_sessions(user_id)
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/messages")
async def get_session_messages_endpoint(session_id: str) -> Any:
    try:
        messages = get_session_messages(session_id)
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat_endpoint(request: ChatRequest) -> Any:
    try:
        result = process_chat_message(request)
        return result
    except Exception as e:
        traceback.print_exc()
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=200, content={"answer": f"An error occurred: {str(e)}", "sources": []})
