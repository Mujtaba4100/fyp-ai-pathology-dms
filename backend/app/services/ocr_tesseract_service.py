import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TesseractOCRService:
    """Service for OCR processing of images and PDFs using Tesseract"""

    UPLOAD_FOLDER = "uploads"
    # Windows path for Tesseract - will use system PATH if not found
    TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    ALTERNATIVE_PATH = r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"

    @staticmethod
    def _find_tesseract():
        """Find Tesseract installation"""
        if os.path.exists(TesseractOCRService.TESSERACT_PATH):
            return TesseractOCRService.TESSERACT_PATH
        elif os.path.exists(TesseractOCRService.ALTERNATIVE_PATH):
            return TesseractOCRService.ALTERNATIVE_PATH
        else:
            # Try system PATH
            try:
                pytesseract.pytesseract.get_tesseract_version()
                return None  # Already in PATH
            except Exception:
                return None

    @staticmethod
    def _preprocess_image(image: Image) -> Image:
        """Apply advanced high-contrast grayscale scaling and binarization for tabular layout scanning"""
        # 1. Scale image if width is low (target width at least 2000px) for smooth sub-pixel rendering
        if image.width < 2000:
            scale_factor = 2000.0 / image.width
            new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # 2. Convert to Grayscale to remove shadow artifacts and gridlines
        image = image.convert("L")
        
        # 3. Enhance text boundaries and boost contrast
        image = ImageEnhance.Contrast(image).enhance(2.5)
        image = ImageEnhance.Sharpness(image).enhance(2.0)
        
        # 4. Balance black/white levels (binarization) to prevent decimal point omission
        image = image.point(lambda p: 255 if p > 135 else 0)
        return image

    @staticmethod
    def process_image(file_path: str) -> dict:
        """Extract text from image using Tesseract"""
        try:
            # Set tesseract path (Windows)
            tesseract_path = TesseractOCRService._find_tesseract()
            if tesseract_path:
                pytesseract.pytesseract.pytesseract_cmd = tesseract_path

            # Open and preprocess image
            image = Image.open(file_path)
            image = TesseractOCRService._preprocess_image(image)

            # Extract text using Tesseract OCR with PSM 6 (single uniform block of text)
            # This forces horizontal tabular reading rather than column splitting
            custom_config = "--oem 3 --psm 6"
            text = pytesseract.image_to_string(image, config=custom_config)

            avg_conf = 100.0
            try:
                data = pytesseract.image_to_data(
                    image, config=custom_config, output_type=pytesseract.Output.DICT
                )
                confidences = [float(c) for c in data.get("conf", []) if float(c) != -1]
                if confidences:
                    avg_conf = sum(confidences) / len(confidences)
            except Exception as conf_err:
                logger.warning(f"Could not calculate OCR confidence: {conf_err}")

            if not text or text.strip() == "":
                return {
                    "status": "no_text",
                    "text": "",
                    "message": "No text found in image",
                    "character_count": 0,
                    "average_confidence": 0.0,
                }

            return {
                "status": "success",
                "text": text.strip(),
                "message": "OCR completed successfully",
                "character_count": len(text),
                "average_confidence": avg_conf,
            }

        except Exception as e:
            logger.error(f"Image OCR error: {str(e)}")
            return {
                "status": "error",
                "text": "",
                "message": str(e),
                "error": "Image processing failed",
                "character_count": 0,
                "average_confidence": 0.0,
            }

    @staticmethod
    def process_pdf(file_path: str) -> dict:
        """Extract text from PDF using Tesseract on each page"""
        try:
            # Set tesseract path (Windows)
            tesseract_path = TesseractOCRService._find_tesseract()
            if tesseract_path:
                pytesseract.pytesseract.pytesseract_cmd = tesseract_path

            # Convert PDF to images (high DPI for better OCR)
            images = convert_from_path(file_path, dpi=200)

            all_text = ""
            page_texts = []

            # Process each page
            for page_num, image in enumerate(images, 1):
                # Preprocess page image
                image = TesseractOCRService._preprocess_image(image)
                # Extract text from page with PSM 6 configuration
                custom_config = "--oem 3 --psm 6"
                page_text = pytesseract.image_to_string(image, config=custom_config)
                if page_text.strip():
                    page_texts.append(f"--- Page {page_num} ---\n{page_text}")
                    all_text += f"\n--- Page {page_num} ---\n{page_text}"

            if not all_text or all_text.strip() == "":
                return {
                    "status": "no_text",
                    "text": "",
                    "message": f"No text found in PDF ({len(images)} pages processed)",
                    "character_count": 0,
                    "page_count": len(images),
                }

            return {
                "status": "success",
                "text": all_text.strip(),
                "message": f"PDF OCR completed successfully ({len(images)} pages)",
                "character_count": len(all_text),
                "page_count": len(images),
            }

        except Exception as e:
            logger.error(f"PDF OCR error: {str(e)}")
            return {
                "status": "error",
                "text": "",
                "message": str(e),
                "error": "PDF processing failed",
                "character_count": 0,
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
                "character_count": 0,
            }

        file_extension = Path(file_path).suffix.lower()

        if file_extension == ".pdf":
            return TesseractOCRService.process_pdf(file_path)
        elif file_extension in [".jpg", ".jpeg", ".png", ".gif", ".tiff", ".bmp"]:
            return TesseractOCRService.process_image(file_path)
        else:
            return {
                "status": "unsupported",
                "text": "",
                "message": f"File type {file_extension} not supported",
                "error": "Unsupported file format",
                "character_count": 0,
            }
