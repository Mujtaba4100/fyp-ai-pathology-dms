import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class OCRService:
    """Service for OCR processing of images and PDFs"""
    
    UPLOAD_FOLDER = "uploads"
    # Windows path for Tesseract - will use system PATH if not found
    TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    ALTERNATIVE_PATH = r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    
    @staticmethod
    def _find_tesseract():
        """Find Tesseract installation"""
        if os.path.exists(OCRService.TESSERACT_PATH):
            return OCRService.TESSERACT_PATH
        elif os.path.exists(OCRService.ALTERNATIVE_PATH):
            return OCRService.ALTERNATIVE_PATH
        else:
            # Try system PATH
            try:
                pytesseract.pytesseract.get_tesseract_version()
                return None  # Already in PATH
            except Exception:
                return None
    
    @staticmethod
    def process_image(file_path: str) -> dict:
        """Extract text from image using Tesseract"""
        try:
            # Set tesseract path (Windows)
            tesseract_path = OCRService._find_tesseract()
            if tesseract_path:
                pytesseract.pytesseract.pytesseract_cmd = tesseract_path
            
            # Open image
            image = Image.open(file_path)
            
            # Extract text using Tesseract OCR
            text = pytesseract.image_to_string(image)
            
            if not text or text.strip() == "":
                return {
                    "status": "no_text",
                    "text": "",
                    "message": "No text found in image",
                    "character_count": 0
                }
            
            return {
                "status": "success",
                "text": text.strip(),
                "message": "OCR completed successfully",
                "character_count": len(text)
            }
        
        except Exception as e:
            logger.error(f"Image OCR error: {str(e)}")
            return {
                "status": "error",
                "text": "",
                "message": str(e),
                "error": "Image processing failed",
                "character_count": 0
            }
    
    @staticmethod
    def process_pdf(file_path: str) -> dict:
        """Extract text from PDF using Tesseract on each page"""
        try:
            # Set tesseract path (Windows)
            tesseract_path = OCRService._find_tesseract()
            if tesseract_path:
                pytesseract.pytesseract.pytesseract_cmd = tesseract_path
            
            # Convert PDF to images (high DPI for better OCR)
            images = convert_from_path(file_path, dpi=200)
            
            all_text = ""
            page_texts = []
            
            # Process each page
            for page_num, image in enumerate(images, 1):
                # Extract text from page
                page_text = pytesseract.image_to_string(image)
                if page_text.strip():
                    page_texts.append(f"--- Page {page_num} ---\n{page_text}")
                    all_text += f"\n--- Page {page_num} ---\n{page_text}"
            
            if not all_text or all_text.strip() == "":
                return {
                    "status": "no_text",
                    "text": "",
                    "message": f"No text found in PDF ({len(images)} pages processed)",
                    "character_count": 0,
                    "page_count": len(images)
                }
            
            return {
                "status": "success",
                "text": all_text.strip(),
                "message": f"PDF OCR completed successfully ({len(images)} pages)",
                "character_count": len(all_text),
                "page_count": len(images)
            }
        
        except Exception as e:
            logger.error(f"PDF OCR error: {str(e)}")
            return {
                "status": "error",
                "text": "",
                "message": str(e),
                "error": "PDF processing failed",
                "character_count": 0
            }
    
    @staticmethod
    def process_file(file_path: str) -> dict:
        """Auto-detect file type and process accordingly"""
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "text": "",
                "message": "File not found",
                "error": "File does not exist",
                "character_count": 0
            }
        
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == ".pdf":
            return OCRService.process_pdf(file_path)
        elif file_extension in [".jpg", ".jpeg", ".png", ".gif", ".tiff", ".bmp"]:
            return OCRService.process_image(file_path)
        else:
            return {
                "status": "unsupported",
                "text": "",
                "message": f"File type {file_extension} not supported",
                "error": "Unsupported file format",
                "character_count": 0
            }
