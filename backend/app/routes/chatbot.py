from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.rag_service import RAGService
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/chat", tags=["chatbot"])


class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    conversation_history: Optional[List[ChatMessage]] = []


@router.post("/ask")
async def ask_chatbot(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Query the EMR Pathology Assistant.
    Retrieves semantically relevant records first, then answers using Groq (Llama-3).
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    rag_service = RAGService()

    # Format history into the standard openai/groq format
    formatted_history = []
    if request.conversation_history:
        for msg in request.conversation_history:
            formatted_history.append({"role": msg.role, "content": msg.content})

    result = rag_service.answer_question(db, request.question, formatted_history)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result
