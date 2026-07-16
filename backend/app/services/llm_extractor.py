from app.config import settings
import json
import base64

try:
    from groq import Groq
except ImportError:
    Groq = None


class LLMExtractor:
    """Service for extracting medical information using Groq (Llama-3)"""

    def __init__(self):
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY) if (Groq and settings.GROQ_API_KEY and settings.GROQ_API_KEY != "gsk_change_me_to_your_groq_key") else None
        self.groq_model = settings.GROQ_MODEL

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
        """Generate extraction prompt for medical text"""
        return f"""You are a medical data extraction expert. Extract medical information from the following pathology report text.
        
Return the extracted data as JSON with the following structure:
{{
    "patient_id": "extracted or null",
    "patient_name": "extracted or null",
    "test_type": "type of pathology test",
    "test_date": "date of test",
    "findings": [
        {{
            "test_name": "name of test",
            "value": "measured value",
            "unit": "unit of measurement",
            "reference_range": "normal range",
            "is_abnormal": true/false
        }}
    ],
    "diagnosis": "primary diagnosis if mentioned on the report. If not explicitly written, provide a brief AI clinical diagnosis or assessment based on the extracted findings (e.g., identify if findings indicate anemia, mild thrombocytopenia, or normal results).",
    "recommendations": "recommendations or notes if mentioned. If not explicitly written, provide brief recommendations based on any abnormal values (e.g., 'Consult physician for abnormal hemoglobin levels' or 'None needed').",
    "summary": "a brief clinical summary of findings. Highlight any values that are out of range and explain their potential clinical meaning."
}}

Strict Rules:
1. Return ONLY valid JSON, no other text.
2. If a field is not found, use null.
3. is_abnormal must be true if the extracted value lies outside the extracted reference range.
4. Extract values, reference ranges, and units EXACTLY as they appear in the text.
5. DO NOT use standard biological or physiological reference ranges from your general knowledge base to "correct", override, or substitute the actual values, units, or ranges written in the report. Always extract exactly what is in the provided text, even if it looks misplaced, unusual, or clinically incorrect.
6. Pay close attention to column layout and spacing to avoid merging separate numbers from adjacent columns (e.g., do not combine a value column and a reference range column into a single number).
7. Do not hallucinate or guess any data.

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

    def _extract_with_groq(self, clean_text: str) -> dict:
        if not self.groq_client:
            return {
                "status": "error",
                "message": "Groq client not configured or API key missing",
                "data": None,
            }

        prompt = self.get_extraction_prompt(clean_text)

        response = self.groq_client.chat.completions.create(
            model=self.groq_model,
            messages=[
                {"role": "system", "content": "You are a medical data extraction expert. Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=2000,
        )

        response_text = response.choices[0].message.content or ""
        extracted_data = json.loads(self._strip_code_fences(response_text))

        return {
            "status": "success",
            "message": "Extraction successful using Groq",
            "data": extracted_data,
            "cost_estimate": "$0.000000 (Evaluations/Free Tier/Low Cost)",
        }

    def extract_from_text(self, clean_text: str) -> dict:
        """Extract medical information from cleaned text using Groq"""
        try:
            return self._extract_with_groq(clean_text)

        except json.JSONDecodeError as e:
            return {
                "status": "json_error",
                "message": "Could not parse LLM response as JSON",
                "error": str(e),
                "data": None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "data": None
            }

    def extract_from_image_vision(self, file_path: str) -> dict:
        """Extract medical information directly from image using Groq Llama 4 Scout Vision"""
        import os
        if not self.groq_client:
            return {
                "status": "error",
                "message": "Groq client not configured or API key missing",
                "data": None,
            }
            
        try:
            # 1. Encode image to base64
            with open(file_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
            # Determine mime type from file extension
            ext = os.path.splitext(file_path)[1].lower().lstrip(".")
            mime_type = f"image/{ext}" if ext in ["png", "jpg", "jpeg", "webp"] else "image/jpeg"
            
            # 2. Build extraction prompt
            prompt = self.get_vision_extraction_prompt()
            
            # 3. Call Groq Llama 4 Vision API
            response = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical data extraction expert. Return ONLY valid JSON."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0,
                max_tokens=2000,
            )
            
            response_text = response.choices[0].message.content or ""
            extracted_data = json.loads(self._strip_code_fences(response_text))
            
            return {
                "status": "success",
                "message": "Extraction successful using Groq Llama-4 Scout Vision",
                "data": extracted_data,
                "cost_estimate": "$0.000000 (Evaluations/Free Tier/Low Cost)"
            }
            
        except json.JSONDecodeError as e:
            return {
                "status": "json_error",
                "message": "Could not parse Vision LLM response as JSON",
                "error": str(e),
                "data": None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "data": None
            }
