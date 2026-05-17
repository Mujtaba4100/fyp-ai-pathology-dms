from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class Document(Base):
    """Model for uploaded documents"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True)
    file_id = Column(String(36), unique=True, index=True)
    filename = Column(String(255))
    file_size = Column(Integer)
    file_type = Column(String(50))
    upload_date = Column(DateTime, default=datetime.utcnow)
    ocr_status = Column(String(50), default="pending")  # pending, completed, failed
    extraction_status = Column(String(50), default="pending")
    raw_text = Column(Text, nullable=True)
    cleaned_text = Column(Text, nullable=True)

class PathologyReport(Base):
    """Model for extracted pathology report data"""
    __tablename__ = "pathology_reports"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(String(36), index=True)
    patient_id = Column(String(100), nullable=True)
    patient_name = Column(String(255), nullable=True)
    test_type = Column(String(255))
    test_date = Column(DateTime, nullable=True)
    findings = Column(Text)  # JSON string
    diagnosis = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DocumentEmbedding(Base):
    """Model for document embeddings (vector storage)"""
    __tablename__ = "document_embeddings"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(String(36), index=True, unique=True)
    embedding = Column(Vector(1536))  # OpenAI embedding is 1536-dimensional
    text_chunk = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    """Model for user management"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    role = Column(String(50), default="doctor")  # doctor, lab_tech, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
