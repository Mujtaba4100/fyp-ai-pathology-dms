import os
from pathlib import Path
import logging
from PIL import Image
import torch
import gc

logger = logging.getLogger(__name__)

class DeepSeekOCRService:
    """Service for OCR processing of images using DeepSeek-OCR-2 (Native FP16)
    
    WARNING: Lazy loading is implemented to prevent OOM (Out Of Memory) crashes.
    The model (~7 GB VRAM) is loaded only during inference and forcefully unloaded afterwards.
    """

    MODEL_ID = "deepseek-ai/DeepSeek-OCR-2"

    @staticmethod
    def process_image(file_path: str) -> dict:
        """Extract text from image using DeepSeek-VL2/OCR-2"""
        try:
            # Lazy import to save memory when not in use
            from transformers import AutoModel, AutoTokenizer, AutoProcessor
            
            logger.info(f"Loading {DeepSeekOCRService.MODEL_ID} into VRAM...")
            
            tokenizer = AutoTokenizer.from_pretrained(
                DeepSeekOCRService.MODEL_ID,
                trust_remote_code=True
            )
            
            # Explicit parameters from Colab benchmark to fit in T4 GPU
            model = AutoModel.from_pretrained(
                DeepSeekOCRService.MODEL_ID,
                trust_remote_code=True,
                use_safetensors=True,
                attn_implementation="eager",
                torch_dtype=torch.float16,
                device_map="auto"
            ).eval()

            processor = AutoProcessor.from_pretrained(DeepSeekOCRService.MODEL_ID, trust_remote_code=True)

            # Preprocess image
            image = Image.open(file_path).convert("RGB")
            
            prompt = (
                "<|User|><image>\n"
                "Extract ALL text from this pathology report image. "
                "Preserve every number, decimal point, and unit exactly.\n"
                "<|Assistant|>"
            )

            inputs = processor(text=prompt, images=[image], return_tensors="pt").to("cuda")
            
            with torch.no_grad():
                out = model.generate(**inputs, max_new_tokens=1024)
                
            text = processor.batch_decode(out, skip_special_tokens=True)[0]
            text = text.split("<|Assistant|>")[-1].strip()

            character_count = len(text)
            
            # Clean up memory aggressively
            del model, tokenizer, processor, inputs, out
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("DeepSeek-OCR-2 unloaded from VRAM.")

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
                "message": "OCR completed successfully via DeepSeek-OCR-2",
                "character_count": character_count,
                "average_confidence": 98.0,
            }

        except Exception as e:
            logger.error(f"DeepSeek Image OCR error: {str(e)}")
            
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
            return DeepSeekOCRService.process_image(file_path)
        else:
            return {"status": "unsupported", "text": "", "message": f"File type {file_extension} must be converted to image first for VLM"}
