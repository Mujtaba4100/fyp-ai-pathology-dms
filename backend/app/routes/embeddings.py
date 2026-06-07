from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.embedding_service import EmbeddingService
from app.services.database_service import DatabaseService

router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])


class EmbeddingRequest(BaseModel):
    text: str
    file_id: Optional[str] = None


class SimilarityRequest(BaseModel):
    text1: str
    text2: str


@router.post("/generate")
async def generate_embedding(request: EmbeddingRequest, db: Session = Depends(get_db)):
    """Generate an embedding and optionally persist it to PostgreSQL."""
    service = EmbeddingService()
    result = service.generate_embedding(request.text)

    if result.get("status") != "success":
        message = result.get("message", "Embedding generation failed")
        status_code = 400 if "required" in message.lower() else 500
        raise HTTPException(status_code=status_code, detail=message)

    if request.file_id:
        try:
            DatabaseService.save_embedding(
                db=db,
                file_id=request.file_id,
                embedding=result["embedding"],
                text_chunk=request.text[:500],
            )
        except Exception as db_err:
            raise HTTPException(status_code=500, detail=f"PostgreSQL persistence failed: {db_err}")

    return result


@router.post("/similarity")
async def calculate_similarity(request: SimilarityRequest):
    """Calculate cosine similarity between two texts."""
    service = EmbeddingService()

    emb1 = service.generate_embedding(request.text1)
    if emb1.get("status") != "success":
        raise HTTPException(status_code=500, detail=emb1.get("message", "Failed to embed text1"))

    emb2 = service.generate_embedding(request.text2)
    if emb2.get("status") != "success":
        raise HTTPException(status_code=500, detail=emb2.get("message", "Failed to embed text2"))

    similarity_score = service.cosine_similarity(emb1["embedding"], emb2["embedding"])

    return {
        "status": "success",
        "similarity_score": round(similarity_score, 4),
        "similarity_percentage": f"{round(similarity_score * 100):.0f}%",
    }


@router.post("/test")
async def test_embedding():
    """Generate a sample embedding for verification."""
    service = EmbeddingService()
    sample_text = "Patient hemoglobin elevated at 18 g/dL with suspected anemia follow-up."
    result = service.generate_embedding(sample_text)

    if result.get("status") != "success":
        raise HTTPException(status_code=500, detail=result.get("message", "Test embedding failed"))

    return {
        "status": "success",
        "message": "Test embedding generated",
        "dimension": result["dimension"],
        "embedding_sample": result["embedding"][:5],
        "cost_estimate": result["cost_estimate"],
    }