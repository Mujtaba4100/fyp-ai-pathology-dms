import os
from pathlib import Path
import logging
from PIL import Image
import torch
import gc

logger = logging.getLogger(__name__)

class GotOCRService:
    """Service for OCR processing of images using GOT-OCR-2.0
    
    WARNING: Lazy loading is implemented to prevent OOM (Out Of Memory) crashes.
    The model is loaded only during inference and forcefully unloaded afterwards.
    """

    MODEL_ID = "stepfun-ai/GOT-OCR-2.0-hf"

    @staticmethod
    def process_image(file_path: str) -> dict:
        """Extract text from image using GOT-OCR-2.0"""
        try:
            from transformers import GotOcr2ForConditionalGeneration, GotOcr2Processor
            
            logger.info(f"Loading {GotOCRService.MODEL_ID} into VRAM...")
            
            processor = GotOcr2Processor.from_pretrained(GotOCRService.MODEL_ID, trust_remote_code=True)
            model = GotOcr2ForConditionalGeneration.from_pretrained(
                GotOCRService.MODEL_ID,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )

            image = Image.open(file_path).convert("RGB")
            
            # GOT-OCR natively extracts text when just given the image (no prompt needed)
            inputs = processor(images=image, return_tensors="pt").to("cuda")
            
            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    do_sample=False,
                    tokenizer=processor.tokenizer,
                    stop_strings="<|im_end|>",
                    max_new_tokens=4096
                )
                
            text = processor.decode(out[0], skip_special_tokens=True)

            character_count = len(text)
            
            # Clean up memory aggressively
            del model, processor, inputs, out
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("GOT-OCR-2.0 unloaded from VRAM.")

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
                "message": "OCR completed successfully via GOT-OCR-2.0",
                "character_count": character_count,
                "average_confidence": 95.0,
            }

        except Exception as e:
            logger.error(f"GOT Image OCR error: {str(e)}")
            
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            return {
                "status": "error",
                "text": "",
                "message": str(e),
                "error": "Image processing failed",
                "character_count": 0,
                "average_confidence": 0.0,
            }

    @staticmethod
    def process_file(file_path: str) -> dict:
        if not os.path.exists(file_path):
            return {"status": "error", "text": "", "message": "File not found"}
        file_extension = Path(file_path).suffix.lower()
        if file_extension in [".jpg", ".jpeg", ".png", ".gif", ".tiff", ".bmp"]:
            return GotOCRService.process_image(file_path)
        else:
            return {"status": "unsupported", "text": "", "message": f"File type {file_extension} must be converted to image first for VLM"}
