from pydantic import BaseModel
from typing import Optional

class MessageResponse(BaseModel):
    message: str

class HealthResponse(BaseModel):
    status: str
    message: str

# Authentication Schemas
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    role: str = "doctor"  # doctor, lab_tech, or admin

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# Upload Schemas
class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_size: int
    status: str
    message: str

class FileListResponse(BaseModel):
    files: list
    total: int

# OCR Schemas
class OCRResponse(BaseModel):
    file_id: str
    status: str
    extracted_text: str
    character_count: int
    error_message: Optional[str] = None

class OCRListResponse(BaseModel):
    file_id: str
    filename: str
    status: str
    extracted_text_preview: str

# Text Cleaning Schemas
class TextCleanResponse(BaseModel):
    status: str
    original_preview: str
    cleaned_preview: str
    original_length: int
    cleaned_length: int
    cleaned_text: str
    message: str

