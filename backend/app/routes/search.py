from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.search_service import SearchService
from pydantic import BaseModel

router = APIRouter(prefix="/api/search", tags=["search"])


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class KeywordSearchRequest(BaseModel):
    keyword: str
    top_k: int = 5


@router.post("/semantic")
async def semantic_search(
    request: SemanticSearchRequest, db: Session = Depends(get_db)
):
    """
    Search medical documents semantically using vector similarity.
    Calculates L2 distance against local Sentence-Transformers embeddings.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query text cannot be empty")

    result = SearchService.semantic_search(db, request.query, request.top_k)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result


@router.post("/keyword")
async def keyword_search(request: KeywordSearchRequest, db: Session = Depends(get_db)):
    """
    Search pathology reports using standard text matching on diagnosis, findings, and summaries.
    """
    if not request.keyword.strip():
        raise HTTPException(status_code=400, detail="Keyword cannot be empty")

    result = SearchService.keyword_search(db, request.keyword, request.top_k)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result
