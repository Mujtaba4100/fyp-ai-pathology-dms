import asyncio
from fastapi import APIRouter, Depends
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
        return {
            "status": "error",
            "answer": "Please ask a question about pathology reports or patient records.",
            "source_documents": [],
        }

    rag_service = RAGService()

    formatted_history = []
    if request.conversation_history:
        for msg in request.conversation_history:
            formatted_history.append({"role": msg.role, "content": msg.content})

    result = await asyncio.to_thread(
        rag_service.answer_question, db, request.question, formatted_history
    )

    return result
