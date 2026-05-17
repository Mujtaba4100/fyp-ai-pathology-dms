import re
from typing import Dict

class TextCleaner:
    """Service for cleaning and normalizing OCR text"""
    
    # Common OCR mistakes
    OCR_FIXES = {
        '0': 'O',  # Zero to O (context dependent)
        '|': 'I',  # Pipe to I
        'l': '1',  # lowercase L to 1
    }
    
    @staticmethod
    def remove_extra_whitespace(text: str) -> str:
        """Remove extra spaces and normalize whitespace"""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\n+', '\n\n', text)
        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in text.split('\n')]
        return '\n'.join(lines)
    
    @staticmethod
    def remove_special_characters(text: str) -> str:
        """Remove unwanted special characters"""
        # Keep only: letters, numbers, spaces, punctuation, newlines
        text = re.sub(r'[^\w\s\.\,\:\;\?\!\-\n]', '', text)
        return text
    
    @staticmethod
    def normalize_medical_terms(text: str) -> str:
        """Normalize common medical abbreviations"""
        replacements = {
            r'\bHGB\b': 'Hemoglobin',
            r'\bWBC\b': 'White Blood Cells',
            r'\bRBC\b': 'Red Blood Cells',
            r'\bPLT\b': 'Platelets',
            r'\bHCT\b': 'Hematocrit',
            r'\bMCV\b': 'Mean Corpuscular Volume',
            r'\bHTN\b': 'Hypertension',
            r'\bDM\b': 'Diabetes Mellitus',
            r'\bCAD\b': 'Coronary Artery Disease',
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def fix_common_ocr_errors(text: str) -> str:
        """Fix common OCR mistakes"""
        # Fix common "O" vs "0" in numbers
        text = re.sub(r'(?<!\d)O(\d)', r'0\1', text)  # O followed by digit -> 0
        
        # Fix gas analysis common errors
        text = text.replace('pO2', 'pO2')
        text = text.replace('pCO2', 'pCO2')
        
        return text
    
    @staticmethod
    def clean_text(text: str) -> Dict[str, str]:
        """Full text cleaning pipeline"""
        try:
            # Apply cleaning steps in order
            cleaned = text
            cleaned = TextCleaner.remove_extra_whitespace(cleaned)
            cleaned = TextCleaner.remove_special_characters(cleaned)
            cleaned = TextCleaner.fix_common_ocr_errors(cleaned)
            cleaned = TextCleaner.normalize_medical_terms(cleaned)
            cleaned = TextCleaner.remove_extra_whitespace(cleaned)  # Again after normalization
            
            return {
                "status": "success",
                "cleaned_text": cleaned,
                "original_length": len(text),
                "cleaned_length": len(cleaned),
                "message": "Text cleaned successfully"
            }
        
        except Exception as e:
            return {
                "status": "error",
                "cleaned_text": text,
                "message": str(e),
                "error": "Text cleaning failed"
            }
