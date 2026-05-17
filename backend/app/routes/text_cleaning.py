from fastapi import APIRouter, HTTPException, Depends
from app.services.text_cleaner import TextCleaner
from app.schemas import TextCleanResponse
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.services.database_service import DatabaseService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/clean", tags=["text-cleaning"])

class CleanTextRequest(BaseModel):
    text: str
    file_id: Optional[str] = None

@router.post("/text", response_model=dict)
async def clean_text(request: CleanTextRequest, db: Session = Depends(get_db)):
    """Clean and normalize extracted text"""
    
    try:
        result = TextCleaner.clean_text(request.text)

        # Persist cleaned text if caller provides a document file_id
        if request.file_id:
            try:
                saved = DatabaseService.save_cleaned_text(
                    db=db,
                    file_id=request.file_id,
                    cleaned_text=result["cleaned_text"],
                )
                if saved is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Document {request.file_id} not found in PostgreSQL",
                    )
            except HTTPException:
                raise
            except Exception as db_err:
                raise HTTPException(
                    status_code=500,
                    detail=f"PostgreSQL persistence failed: {db_err}",
                )
        
        return {
            "status": result["status"],
            "original_preview": request.text[:200],
            "cleaned_preview": result["cleaned_text"][:200],
            "original_length": result["original_length"],
            "cleaned_length": result["cleaned_length"],
            "cleaned_text": result["cleaned_text"],
            "message": result["message"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
