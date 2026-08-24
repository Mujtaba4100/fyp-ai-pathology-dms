import asyncio
from fastapi import APIRouter, HTTPException, Depends
from app.services.llm_extractor import LLMExtractor
from pydantic import BaseModel
from typing import Optional, List
import os

from app.database import get_db
from app.services.database_service import DatabaseService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/extract", tags=["llm-extraction"])
UPLOAD_FOLDER = "uploads"


class ExtractRequest(BaseModel):
    cleaned_text: Optional[str] = None
    raw_text: Optional[str] = None
    file_id: Optional[str] = None


class HybridExtractRequest(BaseModel):
    ocr_text: str
    file_id: str
    force_vision: Optional[bool] = False


@router.post("/medical-data")
async def extract_medical_data(request: ExtractRequest, db: Session = Depends(get_db)):
    """Extract structured medical data from cleaned text using LLM"""
    try:
        extractor = LLMExtractor()
        text_to_process = request.cleaned_text or request.raw_text or ""
        # --- Blocking: Groq HTTP call ---
        result = await asyncio.to_thread(extractor.extract_from_text, text_to_process)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-hybrid")
async def process_hybrid(request: HybridExtractRequest):
    """
    Hybrid OCR/Vision parser.
    If OCR text is short (< 200 characters) or force_vision is True, it automatically
    falls back to Groq Llama Vision. Otherwise, runs the standard text-based LLM extractor.
    """
    extractor = LLMExtractor()

    try:
        # 1. Fallback to Vision LLM ONLY if manually requested by the user
        if request.force_vision:
            file_found = None
            if os.path.exists(UPLOAD_FOLDER):
                for filename in os.listdir(UPLOAD_FOLDER):
                    if filename.startswith(request.file_id):
                        file_found = filename
                        break

            if file_found:
                file_path = os.path.join(UPLOAD_FOLDER, file_found)
                # --- Blocking: Groq Vision HTTP call ---
                result = await asyncio.to_thread(extractor.extract_from_image_vision, file_path)
                return {
                    "status": result.get("status"),
                    "method": "vision_llm",
                    "message": result.get("message"),
                    "data": result.get("data"),
                }

        # 2. Default: Text LLM
        # --- Blocking: Groq HTTP call ---
        result = await asyncio.to_thread(extractor.extract_from_text, request.ocr_text)
        return {
            "status": result.get("status"),
            "method": "text_llm",
            "message": result.get("message"),
            "data": result.get("data"),
        }
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
        # --- Blocking: Groq HTTP call ---
        result = await asyncio.to_thread(extractor.extract_from_text, sample_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FindingItem(BaseModel):
    test_name: str
    value: str
    unit: str
    reference_range: str
    is_abnormal: bool


class ApproveSaveRequest(BaseModel):
    file_id: str
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    test_type: str
    test_date: Optional[str] = None
    findings: List[FindingItem]
    diagnosis: Optional[str] = None
    recommendations: Optional[str] = None
    summary: str


@router.post("/approve-save")
async def approve_save(request: ApproveSaveRequest, db: Session = Depends(get_db)):
    """
    Commit verified report data to PostgreSQL and generate search index embeddings.
    This implements the Human-in-the-Loop gate.
    """
    try:
        extraction_data = request.dict()

        # --- Blocking: PostgreSQL write ---
        report = await asyncio.to_thread(
            DatabaseService.save_pathology_report,
            db, request.file_id, extraction_data
        )

        # --- Blocking: PostgreSQL read ---
        doc = await asyncio.to_thread(DatabaseService.get_document, db, request.file_id)

        if doc:
            text_to_embed = doc.cleaned_text or doc.raw_text or request.summary
            if text_to_embed:
                try:
                    from app.services.embedding_service import EmbeddingService

                    embed_service = EmbeddingService()
                    # --- Blocking: SentenceTransformer encode (CPU-bound) ---
                    embed_res = await asyncio.to_thread(
                        embed_service.generate_embedding, text_to_embed
                    )
                    if embed_res.get("status") == "success":
                        # --- Blocking: PostgreSQL write ---
                        await asyncio.to_thread(
                            DatabaseService.save_embedding,
                            db,
                            request.file_id,
                            embed_res["embedding"],
                            text_to_embed[:500],
                        )
                except Exception as emb_err:
                    print(
                        f"[WARN] Embedding generation failed during approval: {emb_err}"
                    )

        return {
            "status": "success",
            "message": "Pathology report approved and saved successfully",
            "report_id": report.id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save approved report: {str(e)}"
        )
