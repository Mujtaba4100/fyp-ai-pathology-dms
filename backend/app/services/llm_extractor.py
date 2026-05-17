from openai import OpenAI
from app.config import settings
import json

class LLMExtractor:
    """Service for extracting medical information using LLM"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-3.5-turbo"
    
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
    
    def extract_from_text(self, clean_text: str) -> dict:
        """Extract medical information from cleaned text"""
        try:
            if not settings.OPENAI_API_KEY:
                return {
                    "status": "error",
                    "message": "OpenAI API key not configured",
                    "data": None
                }
            
            prompt = self.get_extraction_prompt(clean_text)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical data extraction expert. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,  # Deterministic output
                max_tokens=2000
            )
            
            # Parse LLM response
            response_text = response.choices[0].message.content
            
            # Try to extract JSON if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            extracted_data = json.loads(response_text)
            
            return {
                "status": "success",
                "message": "Extraction successful",
                "data": extracted_data,
                "cost_estimate": f"~${response.usage.prompt_tokens * 0.0005 / 1000:.4f} + ${response.usage.completion_tokens * 0.0015 / 1000:.4f}"
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
