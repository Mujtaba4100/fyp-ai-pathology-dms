from app.config import settings
import json

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class LLMExtractor:
    """Service for extracting medical information using LLM"""

    def __init__(self):
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY) if (Groq and settings.GROQ_API_KEY and settings.GROQ_API_KEY != "gsk_change_me_to_your_groq_key") else None
        self.groq_model = settings.GROQ_MODEL
        
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if (OpenAI and settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "sk-change-me-to-your-key") else None
        self.openai_model = "gpt-3.5-turbo"
        self.google_model = "gemini-2.5-flash"

    @staticmethod
    def get_extraction_prompt(clean_text: str) -> str:
        """Generate extraction prompt for medical text"""
        return f"""You are a medical data extraction expert. Extract medical information from the following pathology report.

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

Important rules:
1. Return ONLY valid JSON, no other text
2. If a field is not found, use null
3. is_abnormal should be true if value is outside reference range
4. Be accurate and don't hallucinate data

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

    def _extract_with_openai(self, clean_text: str) -> dict:
        if not self.openai_client:
            return {
                "status": "error",
                "message": "OpenAI API key not configured",
                "data": None,
            }

        prompt = self.get_extraction_prompt(clean_text)

        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
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
            "message": "Extraction successful using OpenAI",
            "data": extracted_data,
            "cost_estimate": (
                f"~${response.usage.prompt_tokens * 0.0005 / 1000:.4f} + "
                f"${response.usage.completion_tokens * 0.0015 / 1000:.4f}"
                if getattr(response, "usage", None)
                else None
            ),
        }

    def _extract_with_google(self, clean_text: str) -> dict:
        if not settings.GOOGLE_API_KEY:
            return {
                "status": "error",
                "message": "Google API key not configured",
                "data": None,
            }

        try:
            import google.generativeai as genai
        except Exception as import_err:
            return {
                "status": "error",
                "message": f"google-generativeai not available: {import_err}",
                "data": None,
            }

        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(self.google_model)

        prompt = (
            "You are a medical data extraction expert.\n"
            "Return ONLY valid JSON (no markdown, no commentary).\n\n"
            + self.get_extraction_prompt(clean_text)
        )

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0,
            },
        )

        response_text = getattr(response, "text", None) or ""
        extracted_data = json.loads(self._strip_code_fences(response_text))

        return {
            "status": "success",
            "message": "Extraction successful using Google Gemini",
            "data": extracted_data,
            "cost_estimate": None,
        }

    def extract_from_text(self, clean_text: str) -> dict:
        """Extract medical information from cleaned text"""
        try:
            # Primary: Groq (Llama-3)
            if self.groq_client:
                try:
                    return self._extract_with_groq(clean_text)
                except Exception as groq_err:
                    print(f"⚠️ Groq extraction failed: {groq_err}. Trying fallback...")
            
            # Fallback 1: OpenAI
            if self.openai_client:
                try:
                    return self._extract_with_openai(clean_text)
                except Exception as openai_err:
                    print(f"⚠️ OpenAI extraction fallback failed: {openai_err}. Trying fallback...")

            # Fallback 2: Google Gemini
            if settings.GOOGLE_API_KEY:
                try:
                    return self._extract_with_google(clean_text)
                except Exception as google_err:
                    return {
                        "status": "error",
                        "message": f"All extraction providers failed. Groq/OpenAI/Google errors occurred.",
                        "data": None
                    }

            return {
                "status": "error",
                "message": "No valid LLM API provider key is configured (set GROQ_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY)",
                "data": None,
            }

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
