from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.database_models import Document, PathologyReport, DocumentEmbedding, User
from app.security import require_role
from typing import Dict, Any, List

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_role("doctor", "lab_tech", "admin")),
):
    """
    Returns real-time dashboard telemetry from PostgreSQL:
    Total documents, extracted reports, vector embeddings, abnormal count, and recent items.
    """
    total_documents = db.query(Document).count()
    total_reports = db.query(PathologyReport).count()
    total_embeddings = db.query(DocumentEmbedding).count()
    
    # Calculate abnormal flags across reports
    reports = db.query(PathologyReport).order_by(PathologyReport.created_at.desc()).limit(10).all()
    
    abnormal_count = 0
    recent_list = []
    
    for r in reports:
        has_abnormal = False
        findings = r.findings if isinstance(r.findings, list) else []
        for f in findings:
            if isinstance(f, dict):
                if f.get("is_abnormal") is True or f.get("flag") in ["High", "Low"]:
                    has_abnormal = True
                    abnormal_count += 1
        
        recent_list.append({
            "id": str(r.id),
            "patient_name": r.patient_name or "Unknown Patient",
            "patient": r.patient_name or "Unknown Patient",
            "patient_id": r.patient_id or "N/A",
            "test_type": r.test_type or "Pathology Report",
            "test": r.test_type or "Pathology Report",
            "test_date": str(r.test_date) if r.test_date else "Recent",
            "date": str(r.test_date) if r.test_date else "Recent",
            "diagnosis": r.diagnosis or "",
            "is_abnormal": has_abnormal,
            "status": "Completed"
        })
    
    # If no structured reports yet, populate recent items from raw uploaded documents
    if not recent_list:
        docs = db.query(Document).order_by(Document.upload_date.desc()).limit(5).all()
        for d in docs:
            recent_list.append({
                "id": str(d.file_id),
                "patient_name": d.filename or "Uploaded Document",
                "patient": d.filename or "Uploaded Document",
                "patient_id": str(d.file_id)[:8],
                "test_type": "Raw Scanned Document",
                "test": "Raw Scanned Document",
                "test_date": str(d.upload_date.strftime("%b %d, %Y")) if d.upload_date else "Recent",
                "date": str(d.upload_date.strftime("%b %d, %Y")) if d.upload_date else "Recent",
                "diagnosis": "",
                "is_abnormal": False,
                "status": d.ocr_status or "Completed"
            })

    return {
        "status": "success",
        "stats": {
            "total_documents": total_documents,
            "total_reports": total_reports,
            "total_embeddings": total_embeddings,
            "active_patients": db.query(PathologyReport.patient_id).distinct().count(),
            "abnormal_flags": abnormal_count,
        },
        "recent_reports": recent_list,
    }


@router.get("/reports")
async def get_all_reports(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_role("doctor", "lab_tech", "admin")),
):
    """Returns all extracted clinical pathology reports in the EMR vault."""
    import json
    reports = db.query(PathologyReport).order_by(PathologyReport.created_at.desc()).all()
    out = []
    for r in reports:
        # Safely parse findings JSON
        parsed_findings = []
        if isinstance(r.findings, list):
            parsed_findings = r.findings
        elif isinstance(r.findings, str) and r.findings.strip():
            try:
                parsed_findings = json.loads(r.findings)
            except Exception:
                parsed_findings = []

        out.append({
            "id": str(r.id),
            "document_id": str(r.document_id) if r.document_id else "",
            "file_id": str(r.document_id) if r.document_id else "",
            "patient_name": r.patient_name or "Unknown Patient",
            "patient_id": r.patient_id or "N/A",
            "test_type": r.test_type or "General Pathology",
            "test_date": str(r.test_date) if r.test_date else "Recent",
            "diagnosis": r.diagnosis or "Normal",
            "findings": parsed_findings,
            "findings_count": len(parsed_findings),
            "summary": r.summary or "",
            "clinical_summary": r.summary or "",
            "created_at": str(r.created_at) if r.created_at else "",
        })
    return {"status": "success", "reports": out, "total": len(out)}


@router.get("/documents")
async def get_all_documents(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_role("doctor", "lab_tech", "admin")),
):
    """Returns all raw uploaded documents in the PostgreSQL binary vault."""
    docs = db.query(Document).order_by(Document.upload_date.desc()).all()
    out = []
    for d in docs:
        out.append({
            "file_id": str(d.file_id),
            "filename": d.filename or "Document",
            "file_size_kb": round((d.file_size or 0) / 1024, 1),
            "upload_date": str(d.upload_date.strftime("%b %d, %Y %H:%M")) if d.upload_date else "",
            "ocr_status": d.ocr_status or "completed",
            "raw_text_preview": (d.raw_text[:400] + "...") if d.raw_text and len(d.raw_text) > 400 else (d.raw_text or "No text preview"),
        })
    return {"status": "success", "documents": out, "total": len(out)}


@router.get("/patients")
async def get_patient_directory(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_role("doctor", "lab_tech", "admin")),
):
    """Returns aggregated patient directory grouped by patient identifier."""
    reports = db.query(PathologyReport).order_by(PathologyReport.created_at.desc()).all()
    patient_map = {}

    for r in reports:
        pid = r.patient_id or "UNKNOWN"
        if pid not in patient_map:
            patient_map[pid] = {
                "id": str(r.id),
                "name": r.patient_name or "Unknown Patient",
                "mrn": pid,
                "total_reports": 0,
                "latest_test": r.test_type or "Pathology Panel",
                "last_visit": str(r.test_date) if r.test_date else "Recent",
                "status": "Active",
                "recent_diagnosis": r.diagnosis or "Normal",
                "has_abnormal": False,
            }
        patient_map[pid]["total_reports"] += 1
        findings = r.findings if isinstance(r.findings, list) else []
        for f in findings:
            if isinstance(f, dict) and (f.get("is_abnormal") is True or f.get("flag") in ["High", "Low"]):
                patient_map[pid]["has_abnormal"] = True

    return {"status": "success", "patients": list(patient_map.values()), "total": len(patient_map)}
