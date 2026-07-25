import os

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

from sentence_transformers import SentenceTransformer
from app.config import settings
import numpy as np


class EmbeddingService:
    """Service for generating and comparing embeddings locally.

    Model: FremyCompany/BioLORD-2023-M
    A domain-specific biomedical / clinical language model fine-tuned for
    medical terminology, pathology, and clinical NLP tasks.
    Dimension: 768 (vs. 384 for generic all-MiniLM-L6-v2).
    """

    # Class-level cache — shared across all instances within the same process.
    # Reset when the model name changes so old weights are never reused.
    _model_instance = None
    _loaded_model_name: str = None

    # BioLORD-2023-M: biomedical/clinical domain-specific embedding model (768-dim)
    MODEL_NAME = "FremyCompany/BioLORD-2023-M"
    DIMENSION = 768

    def __init__(self):
        self.model_name = self.MODEL_NAME
        self.dimension = self.DIMENSION

        # Load once per process; reload only if the model name changed.
        if (
            EmbeddingService._model_instance is None
            or EmbeddingService._loaded_model_name != self.model_name
        ):
            try:
                EmbeddingService._model_instance = SentenceTransformer(self.model_name)
                EmbeddingService._loaded_model_name = self.model_name
            except Exception as e:
                print(f"[WARN] Failed to load local SentenceTransformer ({self.model_name}): {e}")
                EmbeddingService._model_instance = None

        self.model = EmbeddingService._model_instance

    @staticmethod
    def _trim_text(text: str, max_chars: int = 32000) -> tuple[str, bool]:
        cleaned_text = (text or "").strip()
        truncated = len(cleaned_text) > max_chars
        if truncated:
            cleaned_text = cleaned_text[:max_chars]
        return cleaned_text, truncated

    def generate_embedding(self, text: str) -> dict:
        """Generate a 768-dim BioLORD embedding for input text locally."""
        if not text or not text.strip():
            return {
                "status": "error",
                "message": "Text is required",
                "embedding": None,
                "dimension": 0,
                "cost_estimate": None,
            }

        if not self.model:
            try:
                EmbeddingService._model_instance = SentenceTransformer(self.model_name)
                EmbeddingService._loaded_model_name = self.model_name
                self.model = EmbeddingService._model_instance
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Local embedding model not loaded: {str(e)}",
                    "embedding": None,
                    "dimension": 0,
                    "cost_estimate": None,
                }

        cleaned_text, truncated = self._trim_text(text)

        try:
            emb = self.model.encode(cleaned_text)
            embedding = emb.tolist()

            return {
                "status": "success",
                "embedding": embedding,
                "dimension": len(embedding),
                "model": self.model_name,
                "cost_estimate": "$0.000000 (Local - Free)",
                "tokens_used": len(cleaned_text) // 4,
                "truncated": truncated,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "embedding": None,
                "dimension": 0,
                "cost_estimate": None,
            }

    @staticmethod
    def cosine_similarity(vec1: list, vec2: list) -> float:
        """Return cosine similarity clamped to 0-1."""
        if not vec1 or not vec2:
            return 0.0

        array1 = np.array(vec1, dtype=float)
        array2 = np.array(vec2, dtype=float)
        denominator = float(np.linalg.norm(array1) * np.linalg.norm(array2))
        if denominator == 0.0:
            return 0.0

        similarity = float(np.dot(array1, array2) / denominator)
        return max(0.0, min(1.0, similarity))

    @staticmethod
    def normalize_vector(vec: list) -> list:
        """Return L2-normalized vector."""
        if not vec:
            return []

        array = np.array(vec, dtype=float)
        norm = float(np.linalg.norm(array))
        if norm == 0.0:
            return array.tolist()
        return (array / norm).tolist()
