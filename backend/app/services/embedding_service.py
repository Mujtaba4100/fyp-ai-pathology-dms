import os

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

from sentence_transformers import SentenceTransformer
from app.config import settings
import numpy as np


class EmbeddingService:
    """Service for generating and comparing embeddings locally."""

    _model_instance = None

    def __init__(self):
        self.model_name = "all-MiniLM-L6-v2"
        self.dimension = 384

        # Cache model to avoid reloading on every request
        if EmbeddingService._model_instance is None:
            try:
                EmbeddingService._model_instance = SentenceTransformer(self.model_name)
            except Exception as e:
                print(f"[WARN] Failed to load local SentenceTransformer: {e}")

        self.model = EmbeddingService._model_instance

    @staticmethod
    def _trim_text(text: str, max_chars: int = 32000) -> tuple[str, bool]:
        cleaned_text = (text or "").strip()
        truncated = len(cleaned_text) > max_chars
        if truncated:
            cleaned_text = cleaned_text[:max_chars]
        return cleaned_text, truncated

    def generate_embedding(self, text: str) -> dict:
        """Generate a 384-dim embedding for input text locally."""
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
            # Generate embedding using local model
            emb = self.model.encode(cleaned_text)
            embedding = emb.tolist()

            return {
                "status": "success",
                "embedding": embedding,
                "dimension": len(embedding),
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
