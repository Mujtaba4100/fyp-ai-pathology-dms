import asyncio
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import Response, FileResponse
from app.security import get_current_user, require_role
from app.schemas import FileUploadResponse
from app.database import get_db
from app.services.database_service import DatabaseService
from app.models.database_models import Document
from sqlalchemy.orm import Session
import os
import uuid
import mimetypes
from datetime import datetime

import tempfile

router = APIRouter(prefix="/api", tags=["upload"])

# Portable temp directory for uploads cache (works on Windows, Linux, and HF Spaces Docker)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(tempfile.gettempdir(), "aidatrix_uploads"))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@router.get("/upload/file/{file_id}")
async def view_uploaded_file(file_id: str, db: Session = Depends(get_db)):
    """Stream and view the actual original uploaded document (PDF or image)"""
    # 1. First check if file exists on disk
    if os.path.exists(UPLOAD_FOLDER):
        for fname in os.listdir(UPLOAD_FOLDER):
            if fname.startswith(file_id):
                local_path = os.path.join(UPLOAD_FOLDER, fname)
                mime_type, _ = mimetypes.guess_type(local_path)
                return FileResponse(
                    local_path,
                    media_type=mime_type or "application/octet-stream",
                    headers={"Content-Disposition": f"inline; filename={fname}"}
                )

    # 2. Fallback to PostgreSQL binary vault
    doc = db.query(Document).filter(Document.file_id == file_id).first()
    if doc and doc.file_data:
        mime_type = doc.file_type or mimetypes.guess_type(doc.filename)[0] or "application/octet-stream"
        return Response(
            content=doc.file_data,
            media_type=mime_type,
            headers={"Content-Disposition": f"inline; filename={doc.filename}"}
        )

    raise HTTPException(status_code=404, detail="Original document file not found")


@router.post("/upload/", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_role("doctor", "lab_tech", "admin")),
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
                message="File size exceeds 10MB limit",
            )

        # --- Blocking: disk write ---
        def _write_file():
            with open(file_path, "wb") as f:
                f.write(contents)

        await asyncio.to_thread(_write_file)

        # Save metadata AND raw file bytes to PostgreSQL (single source of truth)
        try:
            file_type = (
                (file.content_type or "").strip()
                or file_extension.lstrip(".")
                or "unknown"
            )
            # --- Blocking: PostgreSQL write ---
            await asyncio.to_thread(
                DatabaseService.save_document,
                db,
                file_id,
                file.filename,
                file_size,
                file_type,
                contents,  # Store original file bytes in PostgreSQL vault
            )
        except Exception as db_err:
            safe_db_err = str(db_err).encode("ascii", "ignore").decode("ascii")
            return FileUploadResponse(
                file_id=file_id,
                filename=file.filename,
                file_size=file_size,
                status="error",
                message=f"PostgreSQL persistence failed: {safe_db_err}",
            )

        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            file_size=file_size,
            status="success",
            message=f"File {file.filename} uploaded successfully",
        )

    except Exception as e:
        return FileUploadResponse(
            file_id="", filename="", file_size=0, status="error", message=str(e)
        )


@router.get("/upload/list", response_model=dict)
async def list_files(current_user=Depends(require_role("doctor", "lab_tech", "admin"))):
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
                    files_list.append(
                        {
                            "filename": filename,
                            "size": file_size,
                            "uploaded_at": datetime.fromtimestamp(
                                os.path.getctime(file_path)
                            ).isoformat(),
                        }
                    )

        return {"files": files_list, "total": len(files_list), "status": "success"}

    except Exception as e:
        return {"files": [], "total": 0, "status": "error", "message": str(e)}


@router.put("/report/{report_id}")
async def update_report(
    report_id: int, current_user=Depends(require_role("lab_tech", "admin"))
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
        "message": "Report updated (implementation in Phase 2)",
    }


@router.delete("/upload/document/{file_id}")
async def delete_document(
    file_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("admin", "lab_tech")),
):
    """
    Delete a document, its extracted reports, and associated vector embeddings (SRS Use Case 11)
    Maintains database referential integrity without orphaned vectors.
    """
    from app.models.database_models import PathologyReport, DocumentEmbedding

    deleted_items = []

    # 1. Delete extracted pathology report
    report = db.query(PathologyReport).filter(PathologyReport.document_id == file_id).first()
    if report:
        db.delete(report)
        deleted_items.append("pathology_report")

    # 2. Delete vector embeddings
    emb = db.query(DocumentEmbedding).filter(DocumentEmbedding.document_id == file_id).first()
    if emb:
        db.delete(emb)
        deleted_items.append("vector_embedding")

    # 3. Delete document record
    doc = db.query(Document).filter(Document.file_id == file_id).first()
    if doc:
        db.delete(doc)
        deleted_items.append("document_record")

    db.commit()

    # 4. Remove local file from disk if present
    if os.path.exists(UPLOAD_FOLDER):
        for fname in os.listdir(UPLOAD_FOLDER):
            if fname.startswith(file_id):
                try:
                    os.remove(os.path.join(UPLOAD_FOLDER, fname))
                    deleted_items.append("disk_file")
                except Exception:
                    pass

    return {
        "status": "success",
        "message": f"Document {file_id} and all related EMR artifacts deleted successfully",
        "deleted_components": deleted_items,
    }


@router.get("/reports/")
async def list_reports(
    current_user=Depends(require_role("doctor", "lab_tech", "admin"))
):
    """
    List all reports accessible to user

    Allowed: Doctor, Lab Tech, Admin
    Doctors see only their uploaded reports
    Lab Techs and Admins see all
    """
    if current_user.role == "doctor":
        # Show only doctor's reports
        return {"reports": [], "filtered_by": "user", "role": current_user.role}
    else:
        # Show all reports
        return {"reports": [], "filtered_by": "none", "role": current_user.role}
