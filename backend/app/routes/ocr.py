import asyncio
from fastapi import APIRouter, HTTPException, Depends
#from app.services.ocr_tesseract_service import TesseractOCRService
from app.services.ocr_deepseek_service import DeepSeekOCRService
# from app.services.ocr_qwen_service import QwenOCRService
# from app.services.ocr_gotocr_service import GotOCRService
# from app.services.ocr_paddle_service import PaddleOCRService
from app.schemas import OCRResponse
from app.security import get_current_user
from app.database import get_db
from app.services.database_service import DatabaseService
from sqlalchemy.orm import Session
import os
from pathlib import Path

import tempfile

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(tempfile.gettempdir(), "aidatrix_uploads"))


@router.post("/process/{file_id}", response_model=OCRResponse)
async def process_file_ocr(
    file_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Process uploaded file with OCR (extract text from image/PDF)

    **Roles:** doctor, lab_tech, admin
    **Parameters:**
    - file_id: ID of file to process (returned from /api/upload/)

    **Returns:**
    - file_id: File identifier
    - status: success/error/no_text/unsupported
    - extracted_text: Full text extracted from file
    - character_count: Number of characters in extracted text
    - error_message: Error details if status != success
    """

    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # 1. Try finding file on local disk staging cache
        file_found = None
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith(file_id):
                file_found = filename
                break

        # 2. If not on disk, pull original file bytes directly from PostgreSQL DB
        if not file_found:
            from app.models.database_models import Document
            doc = db.query(Document).filter(Document.file_id == file_id).first()
            if doc and doc.file_data:
                file_found = f"{file_id}_{doc.filename or 'document.jpg'}"
                file_path = os.path.join(UPLOAD_FOLDER, file_found)
                with open(file_path, "wb") as f:
                    f.write(doc.file_data)
            else:
                raise HTTPException(
                    status_code=404, detail=f"File with ID {file_id} not found in PostgreSQL or local cache"
                )
        else:
            file_path = os.path.join(UPLOAD_FOLDER, file_found)

        # --- Blocking: Tesseract OCR (CPU-bound) ---
        result = await asyncio.to_thread(DeepSeekOCRService.process_file, file_path)

        # --- Blocking: PostgreSQL writes via SQLAlchemy ---
        def _persist_ocr():
            ocr_db_status = (
                "completed" if result.get("status") == "success" else "failed"
            )
            saved = DatabaseService.save_raw_text(
                db=db,
                file_id=file_id,
                raw_text=result.get("text", ""),
                status=ocr_db_status,
            )

            # If the document row doesn't exist (e.g., older uploads), create it from disk info.
            if saved is None:
                file_size = os.path.getsize(file_path)
                file_type = Path(file_found).suffix.lstrip(".") or "unknown"
                DatabaseService.save_document(
                    db=db,
                    file_id=file_id,
                    filename=file_found,
                    file_size=file_size,
                    file_type=file_type,
                )
                DatabaseService.save_raw_text(
                    db=db,
                    file_id=file_id,
                    raw_text=result.get("text", ""),
                    status=ocr_db_status,
                )

        try:
            await asyncio.to_thread(_persist_ocr)
        except Exception as db_err:
            raise HTTPException(
                status_code=500, detail=f"PostgreSQL persistence failed: {db_err}"
            )

        return OCRResponse(
            file_id=file_id,
            status=result["status"],
            extracted_text=result["text"],
            character_count=result.get("character_count", 0),
            average_confidence=result.get("average_confidence"),
            error_message=result.get("message"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")


@router.get("/status/{file_id}")
async def get_ocr_status(file_id: str, current_user=Depends(get_current_user)):
    """
    Check if file is ready for OCR processing

    **Roles:** doctor, lab_tech, admin
    **Parameters:**
    - file_id: ID of file to check

    **Returns:**
    - status: ready/not_found/error
    - file_id: File identifier
    - filename: Actual filename in storage
    - message: Status details
    """

    try:
        if not os.path.exists(UPLOAD_FOLDER):
            return {"status": "not_found", "message": "Upload folder not found"}

        file_found = None
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith(file_id):
                file_found = filename
                break

        if not file_found:
            return {
                "status": "not_found",
                "file_id": file_id,
                "message": f"File {file_id} not found",
            }

        file_path = os.path.join(UPLOAD_FOLDER, file_found)
        file_size = await asyncio.to_thread(os.path.getsize, file_path)

        return {
            "status": "ready",
            "file_id": file_id,
            "filename": file_found,
            "file_size": file_size,
            "message": "File ready for OCR processing",
        }

    except Exception as e:
        return {"status": "error", "file_id": file_id, "message": str(e)}


@router.get("/list")
async def list_processed_files(current_user=Depends(get_current_user)):
    """
    List all uploaded files available for OCR

    **Roles:** doctor, lab_tech, admin

    **Returns:**
    - files: Array of file information
    - total: Total number of files
    - status: success/error
    """

    try:
        if not os.path.exists(UPLOAD_FOLDER):
            return {
                "files": [],
                "total": 0,
                "status": "error",
                "message": "Upload folder not found",
            }

        def _list_files():
            result = []
            for filename in os.listdir(UPLOAD_FOLDER):
                fp = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.isfile(fp):
                    result.append(
                        {
                            "filename": filename,
                            "size": os.path.getsize(fp),
                            "path": fp,
                        }
                    )
            return result

        files = await asyncio.to_thread(_list_files)
        return {"files": files, "total": len(files), "status": "success"}

    except Exception as e:
        return {"files": [], "total": 0, "status": "error", "message": str(e)}
