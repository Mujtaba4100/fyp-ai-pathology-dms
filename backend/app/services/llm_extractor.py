from app.config import settings
import json

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
    "diagnosis": "primary diagnosis if mentioned",
    "recommendations": "recommendations or notes",
    "summary": "brief summary of findings"
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
