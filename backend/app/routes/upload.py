from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from app.security import get_current_user, require_role
from app.schemas import FileUploadResponse
from app.database import get_db
from app.services.database_service import DatabaseService
from sqlalchemy.orm import Session
import os
import uuid
from datetime import datetime

router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_FOLDER = "uploads"

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@router.post("/upload/", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(require_role("doctor", "lab_tech", "admin"))
):
    """Upload a pathology report file
    
    Saves to:
    1. Local storage (temporary)
    2. MS SQL Server (permanent - company vault)
    3. PostgreSQL (PRIMARY) metadata via DATABASE_URL (e.g., Neon)
    
    Allowed roles: doctor, lab_tech, admin
    """
    
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        saved_filename = f"{file_id}{file_extension}"
        
        # Save file locally first
        file_path = os.path.join(UPLOAD_FOLDER, saved_filename)
        
        contents = await file.read()
        file_size = len(contents)
        
        # Check file size (10MB limit)
        if file_size > 10 * 1024 * 1024:
            return FileUploadResponse(
                file_id="",
                filename="",
                file_size=0,
                status="failed",
                message="File size exceeds 10MB limit"
            )
        
        # Save to local disk
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Save metadata to PostgreSQL (PRIMARY storage for Phase 6)
        try:
            file_type = (file.content_type or "").strip() or file_extension.lstrip(".") or "unknown"
            DatabaseService.save_document(
                db=db,
                file_id=file_id,
                filename=file.filename,
                file_size=file_size,
                file_type=file_type,
            )
        except Exception as db_err:
            return FileUploadResponse(
                file_id=file_id,
                filename=file.filename,
                file_size=file_size,
                status="error",
                message=f"PostgreSQL persistence failed: {db_err}",
            )

        # Save to MS SQL Server (company vault) - best effort only
        try:
            from app.services.mssql_service import MSSQLService

            mssql_service = MSSQLService()
            mssql_result = mssql_service.save_document(
                file_id=file_id,
                filename=file.filename,
                file_size=file_size,
                file_path=file_path,
                file_data=contents,
            )

            if mssql_result.get("status") != "success":
                print(f"⚠️ MS SQL save failed: {mssql_result.get('message')}")
        except Exception as mssql_err:
            print(f"⚠️ MS SQL vault unavailable (skipping): {mssql_err}")
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_size=file_size,
            status="success",
            message=f"File {file.filename} uploaded successfully"
        )
    
    except Exception as e:
        return FileUploadResponse(
            file_id="",
            filename="",
            file_size=0,
            status="error",
            message=str(e)
        )

@router.get("/upload/list", response_model=dict)
async def list_files(
    current_user = Depends(require_role("doctor", "lab_tech", "admin"))
):
    """List all uploaded files
    
    Allowed roles: doctor, lab_tech, admin
    """
    
    try:
        files_list = []
        if os.path.exists(UPLOAD_FOLDER):
            for filename in os.listdir(UPLOAD_FOLDER):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    files_list.append({
                        "filename": filename,
                        "size": file_size,
                        "uploaded_at": datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                    })
        
        return {
            "files": files_list,
            "total": len(files_list),
            "status": "success"
        }
    
    except Exception as e:
        return {
            "files": [],
            "total": 0,
            "status": "error",
            "message": str(e)
        }

@router.put("/report/{report_id}")
async def update_report(
    report_id: int,
    current_user = Depends(require_role("lab_tech", "admin"))
):
    """
    Modify a report result
    
    Allowed: Lab Tech, Admin
    Denied: Doctors (cannot edit results)
    """
    return {
        "report_id": report_id,
        "modified_by": current_user.username,
        "role": current_user.role,
        "message": "Report updated (implementation in Phase 2)"
    }

@router.delete("/report/{report_id}")
async def delete_report(
    report_id: int,
    current_user = Depends(require_role("admin"))
):
    """
    Delete a report
    
    Allowed: Admin only
    Denied: Doctors and Lab Techs
    """
    return {
        "report_id": report_id,
        "deleted_by": current_user.username,
        "role": current_user.role,
        "message": "Report deleted (implementation in Phase 2)"
    }

@router.get("/reports/")
async def list_reports(
    current_user = Depends(require_role("doctor", "lab_tech", "admin"))
):
    """
    List all reports accessible to user
    
    Allowed: Doctor, Lab Tech, Admin
    Doctors see only their uploaded reports
    Lab Techs and Admins see all
    """
    if current_user.role == "doctor":
        # Show only doctor's reports
        return {
            "reports": [],
            "filtered_by": "user",
            "role": current_user.role
        }
    else:
        # Show all reports
        return {
            "reports": [],
            "filtered_by": "none",
            "role": current_user.role
        }
