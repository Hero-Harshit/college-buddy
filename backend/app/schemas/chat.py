from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    user_id: str
    user_name: str = "Student"
    session_id: str | None = None
    rag_mode: bool = True
