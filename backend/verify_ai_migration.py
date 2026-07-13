import sys
import os

# Add backend to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.embedding_service import EmbeddingService
from app.services.llm_extractor import LLMExtractor
from app.config import settings

print("=" * 60)
print("             AI STACK MIGRATION VALIDATION")
print("=" * 60)

# 1. Test local embeddings
print("\n[1] Testing local Sentence-Transformers model ('all-MiniLM-L6-v2')...")
try:
    embedding_service = EmbeddingService()
    sample_text = "Hemoglobin elevated at 17.5 g/dL with normal platelet counts."
    res = embedding_service.generate_embedding(sample_text)
    
    if res["status"] == "success":
        dimension = res["dimension"]
        print("Success: Embedding generated successfully locally!")
        print(f"Success: Dimension is {dimension} (Expected: 384)")
        assert dimension == 384, f"Dimension mismatch: expected 384, got {dimension}"
        print(f"Success: Cost: {res['cost_estimate']}")
    else:
        print(f"Error: Embedding generation failed: {res['message']}")
except Exception as e:
    print(f"Error: Error testing embeddings: {e}")

# 2. Test Groq connection
print("\n[2] Checking Groq API Key and connection...")
groq_key = settings.GROQ_API_KEY
if not groq_key or groq_key == "gsk_change_me_to_your_groq_key":
    print("Warning: GROQ_API_KEY is not configured in .env.")
    print("Please set a valid GROQ_API_KEY to test the Groq/Llama pipeline.")
else:
    print(f"Success: GROQ_API_KEY configured (starts with: {groq_key[:6]}...)")
    print(f"Success: Groq Model: {settings.GROQ_MODEL}")
    
    print("Testing Groq completion (medical data extraction)...")
    try:
        extractor = LLMExtractor()
        sample_report = "Patient: Jane Smith, Test Type: Complete Blood Count, Test Date: 2026-07-13, Findings: Hemoglobin: 12.0 g/dL"
        extract_res = extractor.extract_from_text(sample_report)
        
        if extract_res["status"] == "success":
            print("Success: Groq medical extraction succeeded!")
            print(f"Patient Name: {extract_res['data'].get('patient_name')}")
            print(f"Test Type: {extract_res['data'].get('test_type')}")
        else:
            print(f"Error: Groq extraction failed: {extract_res['message']}")
    except Exception as e:
        print(f"Error: Error testing Groq completion: {e}")

print("\n" + "=" * 60)
