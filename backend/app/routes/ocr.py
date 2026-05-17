from fastapi import APIRouter, HTTPException, Depends
from app.services.ocr_service import OCRService
from app.schemas import OCRResponse
from app.security import get_current_user
from app.database import get_db
from app.services.database_service import DatabaseService
from sqlalchemy.orm import Session
import os
from pathlib import Path

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

UPLOAD_FOLDER = "uploads"

@router.post("/process/{file_id}", response_model=OCRResponse)
async def process_file_ocr(
    file_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
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
        # Check upload folder exists
        if not os.path.exists(UPLOAD_FOLDER):
            raise HTTPException(
                status_code=404, 
                detail="Upload folder not found"
            )
        
        # Find file with matching file_id
        file_found = None
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith(file_id):
                file_found = filename
                break
        
        if not file_found:
            raise HTTPException(
                status_code=404, 
                detail=f"File with ID {file_id} not found in uploads"
            )
        
        file_path = os.path.join(UPLOAD_FOLDER, file_found)
        
        # Process file with OCR
        result = OCRService.process_file(file_path)

        # Persist OCR results to PostgreSQL (Phase 6 primary storage)
        try:
            ocr_db_status = "completed" if result.get("status") == "success" else "failed"
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
        except Exception as db_err:
            raise HTTPException(status_code=500, detail=f"PostgreSQL persistence failed: {db_err}")
        
        # Return response
        return OCRResponse(
            file_id=file_id,
            status=result["status"],
            extracted_text=result["text"],
            character_count=result.get("character_count", 0),
            error_message=result.get("message")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing error: {str(e)}")


@router.get("/status/{file_id}")
async def get_ocr_status(file_id: str, current_user = Depends(get_current_user)):
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
            return {
                "status": "not_found", 
                "message": "Upload folder not found"
            }
        
        # Find file with matching file_id
        file_found = None
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith(file_id):
                file_found = filename
                break
        
        if not file_found:
            return {
                "status": "not_found", 
                "file_id": file_id,
                "message": f"File {file_id} not found"
            }
        
        # Get file info
        file_path = os.path.join(UPLOAD_FOLDER, file_found)
        file_size = os.path.getsize(file_path)
        
        return {
            "status": "ready",
            "file_id": file_id,
            "filename": file_found,
            "file_size": file_size,
            "message": "File ready for OCR processing"
        }
    
    except Exception as e:
        return {
            "status": "error", 
            "file_id": file_id,
            "message": str(e)
        }


@router.get("/list")
async def list_processed_files(current_user = Depends(get_current_user)):
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
                "message": "Upload folder not found"
            }
        
        files = []
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                files.append({
                    "filename": filename,
                    "size": os.path.getsize(file_path),
                    "path": file_path
                })
        
        return {
            "files": files,
            "total": len(files),
            "status": "success"
        }
    
    except Exception as e:
        return {
            "files": [],
            "total": 0,
            "status": "error",
            "message": str(e)
        }
