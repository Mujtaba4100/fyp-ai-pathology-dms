from fastapi import APIRouter, HTTPException, Depends
from app.services.llm_extractor import LLMExtractor
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.services.database_service import DatabaseService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/extract", tags=["llm-extraction"])

class ExtractRequest(BaseModel):
    cleaned_text: str
    file_id: Optional[str] = None

@router.post("/medical-data")
async def extract_medical_data(request: ExtractRequest, db: Session = Depends(get_db)):
    """Extract structured medical data from cleaned text using LLM"""
    
    try:
        extractor = LLMExtractor()
        result = extractor.extract_from_text(request.cleaned_text)

        # Persist to PostgreSQL (Phase 6) when caller provides file_id
        if request.file_id and result.get("status") == "success" and result.get("data") is not None:
            try:
                DatabaseService.save_pathology_report(
                    db=db,
                    file_id=request.file_id,
                    extraction_data=result["data"],
                )
            except Exception as db_err:
                raise HTTPException(status_code=500, detail=f"PostgreSQL persistence failed: {db_err}")
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def test_extraction():
    """Test LLM extraction with sample data"""
    
    sample_text = """
    Patient: John Doe
    Test Date: 2026-03-28
    Test Type: Complete Blood Count (CBC)
    
    Findings:
    - Hemoglobin: 14.5 g/dL (Normal: 13.5-17.5)
    - White Blood Cells: 7.2 x10^3/µL (Normal: 4.5-11.0)
    - Platelets: 250 x10^3/µL (Normal: 150-400)
    
    Diagnosis: No abnormalities detected
    """
    
    try:
        extractor = LLMExtractor()
        result = extractor.extract_from_text(sample_text)
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
