from sqlalchemy.orm import Session
from app.models.database_models import Document, PathologyReport, DocumentEmbedding, User
from datetime import datetime
import json

class DatabaseService:
    """Service for database operations"""
    
    @staticmethod
    def save_document(db: Session, file_id: str, filename: str, file_size: int, file_type: str) -> Document:
        """Save document metadata"""
        doc = Document(
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            file_type=file_type
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc
    
    @staticmethod
    def save_raw_text(db: Session, file_id: str, raw_text: str, status: str = "completed"):
        """Save OCR extracted text"""
        doc = db.query(Document).filter(Document.file_id == file_id).first()
        if doc:
            doc.raw_text = raw_text
            doc.ocr_status = status
            db.commit()
            db.refresh(doc)
            return doc
        return None
    
    @staticmethod
    def save_cleaned_text(db: Session, file_id: str, cleaned_text: str):
        """Save cleaned text"""
        doc = db.query(Document).filter(Document.file_id == file_id).first()
        if doc:
            doc.cleaned_text = cleaned_text
            db.commit()
            db.refresh(doc)
            return doc
        return None
    
    @staticmethod
    def save_pathology_report(db: Session, file_id: str, extraction_data: dict) -> PathologyReport:
        """Save extracted pathology report data"""
        test_date_value = extraction_data.get("test_date")
        parsed_test_date = None
        if isinstance(test_date_value, datetime):
            parsed_test_date = test_date_value
        elif isinstance(test_date_value, str) and test_date_value.strip():
            # Accept ISO date or datetime strings (e.g., 2026-03-28 or 2026-03-28T12:34:56)
            try:
                parsed_test_date = datetime.fromisoformat(test_date_value.strip())
            except Exception:
                parsed_test_date = None

        report = PathologyReport(
            document_id=file_id,
            patient_id=extraction_data.get("patient_id"),
            patient_name=extraction_data.get("patient_name"),
            test_type=extraction_data.get("test_type", ""),
            test_date=parsed_test_date,
            findings=json.dumps(extraction_data.get("findings", [])),
            diagnosis=extraction_data.get("diagnosis"),
            recommendations=extraction_data.get("recommendations"),
            summary=extraction_data.get("summary", "")
        )
        db.add(report)

        # Mark extraction status on the parent document (if present)
        doc = db.query(Document).filter(Document.file_id == file_id).first()
        if doc:
            doc.extraction_status = "completed"

        db.commit()
        db.refresh(report)
        return report
    
    @staticmethod
    def save_embedding(db: Session, file_id: str, embedding: list, text_chunk: str):
        """Save document embedding"""
        emb = DocumentEmbedding(
            document_id=file_id,
            embedding=embedding,
            text_chunk=text_chunk
        )
        db.add(emb)
        db.commit()
        db.refresh(emb)
        return emb
    
    @staticmethod
    def get_document(db: Session, file_id: str):
        """Get document by file ID"""
        return db.query(Document).filter(Document.file_id == file_id).first()
    
    @staticmethod
    def list_documents(db: Session, limit: int = 10):
        """List all documents"""
        return db.query(Document).order_by(Document.upload_date.desc()).limit(limit).all()
    
    @staticmethod
    def get_pathology_report(db: Session, file_id: str):
        """Get pathology report by file ID"""
        return db.query(PathologyReport).filter(PathologyReport.document_id == file_id).first()
    
    @staticmethod
    def get_embedding(db: Session, file_id: str):
        """Get embedding by file ID"""
        return db.query(DocumentEmbedding).filter(DocumentEmbedding.document_id == file_id).first()
    
    @staticmethod
    def save_user(db: Session, username: str, email: str, password_hash: str, role: str = "doctor") -> User:
        """Save user to database"""
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_user_by_username(db: Session, username: str):
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str):
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
