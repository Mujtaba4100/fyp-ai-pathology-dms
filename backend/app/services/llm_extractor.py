from app.config import settings
import json
import base64
import gc

class LLMExtractor:
    """Service for extracting medical information using local Transformers LLM"""

    def __init__(self):
        self.local_model = settings.LOCAL_LLM_MODEL
        self.hf_token = settings.HF_TOKEN

    @staticmethod
    def get_vision_extraction_prompt() -> str:
        """Generate extraction prompt for medical image vision analysis"""
        return """You are a medical data extraction expert. Extract medical information directly from the provided pathology report image.
        
Return the extracted data as JSON with the following structure:
{
    "patient_id": "extracted Report ID or patient ID or null",
    "patient_name": "extracted patient name or null",
    "test_type": "type of pathology test (e.g. LIVER PROFILE)",
    "test_date": "date of test (usually under Report Date or Collection Date)",
    "findings": [
        {
            "test_name": "name of test/parameter (e.g., S. Bilirubin (Total), Total Protein, Albumin, Globulin, SGOT, SGPT, Alkaline Phosphatase, etc.)",
            "value": "measured value (numeric or text, e.g., 9.1 or 1.50)",
            "unit": "unit of measurement (e.g., g/dl or mg/dl or IU/L)",
            "reference_range": "normal range (e.g., 6 - 7.8 or 1 - 2.3)",
            "is_abnormal": true/false
        }
    ],
    "diagnosis": "primary clinical diagnosis/interpretation details if mentioned on the report. If not explicitly written on the report, provide a brief AI clinical diagnosis or assessment based on the extracted findings (e.g., identify if findings indicate anemia, mild thrombocytopenia, or normal results).",
    "recommendations": "recommendations or urgent checkup advice if mentioned on the report. If not explicitly written, provide brief recommendations based on any abnormal values (e.g., 'Consult physician for abnormal hemoglobin levels' or 'None needed').",
    "summary": "a brief clinical summary of findings. Highlight any values that are out of range and explain their potential clinical meaning."
}

Strict Rules:
1. Return ONLY valid JSON, no other text.
2. If a patient detail or test value is not found, use null.
3. is_abnormal must be true if the extracted value lies outside the extracted reference range.
4. Extract values, reference ranges, and units EXACTLY as they appear visually in the image.
5. DO NOT use standard reference ranges from your general knowledge base to "correct", override, or substitute the actual values, units, or ranges written in the report. Always extract exactly what is visible in the provided image.
6. Make sure to capture ALL parameters in the findings table. Do not miss any rows!
7. Do not hallucinate or guess any data for the patient info, test names, values, or reference ranges.
"""

    @staticmethod
    def get_extraction_prompt(clean_text: str) -> str:
        """Generate extraction prompt with medical pathology domain validation"""
        return f"""You are an expert clinical medical intelligence validator and data extractor.
Your task is to:
1. FIRST, determine if the provided text represents a valid medical pathology or clinical diagnostic laboratory report (such as Complete Blood Count, Liver Function Test, Lipid Profile, Renal Function, Urine Routine, Histopathology, etc.).
2. If the text is NOT a medical pathology report (for example: a photo of nature/landscape, food, selfie, retail invoice, vehicle paper, random text, or gibberish), you MUST set "is_valid_medical_report": false.
3. If it IS a medical pathology report, set "is_valid_medical_report": true and extract the structured clinical fields.

Return ONLY valid JSON with the following structure:
{{
    "is_valid_medical_report": true/false,
    "rejection_reason": "Provide reason if false, or null if true",
    "patient_id": "extracted or null",
    "patient_name": "extracted or null",
    "test_type": "type of pathology test (e.g. Complete Blood Count, Lipid Profile)",
    "test_date": "date of test",
    "findings": [
        {{
            "test_name": "name of test (e.g. Hemoglobin, WBC, Platelets, Total Cholesterol)",
            "value": "measured value",
            "unit": "unit of measurement",
            "reference_range": "normal biological reference range",
            "is_abnormal": true/false
        }}
    ],
    "diagnosis": "primary diagnosis or brief AI clinical evaluation based strictly on findings",
    "recommendations": "medical advice or recommendations",
    "summary": "brief summary of findings highlighting abnormal biomarkers"
}}

Strict Rules:
1. Return ONLY valid JSON, no markdown outside JSON fences.
2. If the text has no medical/laboratory content, set "is_valid_medical_report": false.
3. Extract values, reference ranges, and units EXACTLY as they appear in the text. Do not hallucinate or guess.

Medical Report Text:
{clean_text}

Extract and return as JSON:"""

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        if not text:
            return ""
        response_text = text
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```", 1)[1].split("```", 1)[0]
        return response_text.strip()

    def _extract_with_local_llm(self, clean_text: str) -> dict:
        if not self.local_model:
            return {
                "status": "error",
                "message": "Local LLM model not configured in .env",
                "data": None,
            }

        if not clean_text or len(clean_text.strip()) < 15:
            return {
                "status": "error",
                "error_type": "INVALID_DOCUMENT_TYPE",
                "message": "Invalid Document: No readable pathology or laboratory text detected in this image. Please upload a clear diagnostic lab report.",
                "data": None,
            }

        prompt = self.get_extraction_prompt(clean_text)

        # Lazy load the transformers pipeline to avoid memory hogs when not extracting
        try:
            import torch
            from transformers import pipeline

            # Load pipeline (downloads model if not cached). Using device_map="auto" to use GPU if available.
            pipe = pipeline(
                "text-generation", 
                model=self.local_model, 
                token=self.hf_token if self.hf_token else None,
                device_map="auto",
                torch_dtype=torch.float16
            )

            messages = [
                {
                    "role": "system",
                    "content": "You are a medical data extraction expert. Return ONLY valid JSON.",
                },
                {"role": "user", "content": prompt},
            ]

            # Generate output locally
            response = pipe(messages, max_new_tokens=4096, temperature=0.1, do_sample=True)
            
            # Extract generated content
            # Pipeline with 'messages' returns a list of dicts. We extract the generated assistant content.
            response_text = response[0]["generated_text"][-1]["content"] or ""

            # Unload model and free VRAM
            del pipe
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

            extracted_data = json.loads(self._strip_code_fences(response_text))

            # Check medical validation guardrail
            if extracted_data.get("is_valid_medical_report") is False:
                reason = extracted_data.get("rejection_reason") or "The uploaded document is not a recognized medical pathology report."
                return {
                    "status": "error",
                    "error_type": "INVALID_DOCUMENT_TYPE",
                    "message": f"Invalid Document: {reason}",
                    "data": None,
                }

            return {
                "status": "success",
                "message": f"Extraction successful using Local Model {self.local_model}",
                "data": extracted_data,
                "cost_estimate": "$0.000000 (Local Open-Source)",
            }
        except Exception as err:
            raise Exception(f"Local Extraction failed: {str(err)}")

    def extract_from_text(self, clean_text: str) -> dict:
        """Extract medical information from cleaned text using local model"""
        try:
            return self._extract_with_local_llm(clean_text)

        except json.JSONDecodeError as e:
            return {
                "status": "json_error",
                "message": "Could not parse LLM response as JSON",
                "error": str(e),
                "data": None,
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}
