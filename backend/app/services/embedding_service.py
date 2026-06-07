from openai import OpenAI
from app.config import settings
import numpy as np


class EmbeddingService:
    """Service for generating and comparing embeddings."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = "text-embedding-3-small"
        self.dimension = 1536

    @staticmethod
    def _trim_text(text: str, max_chars: int = 32000) -> tuple[str, bool]:
        cleaned_text = (text or "").strip()
        truncated = len(cleaned_text) > max_chars
        if truncated:
            cleaned_text = cleaned_text[:max_chars]
        return cleaned_text, truncated

    def generate_embedding(self, text: str) -> dict:
        """Generate a 1536-dim embedding for input text."""
        if not text or not text.strip():
            return {
                "status": "error",
                "message": "Text is required",
                "embedding": None,
                "dimension": 0,
                "cost_estimate": None,
            }

        if not self.client:
            return {
                "status": "error",
                "message": "OpenAI API key not configured",
                "embedding": None,
                "dimension": 0,
                "cost_estimate": None,
            }

        cleaned_text, truncated = self._trim_text(text)

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=cleaned_text,
            )
            embedding = response.data[0].embedding
            tokens_used = getattr(getattr(response, "usage", None), "total_tokens", None)
            if tokens_used is None:
                tokens_used = max(1, len(cleaned_text) // 4)

            cost_estimate = f"~${(tokens_used * 0.02 / 1_000_000):.6f}"

            return {
                "status": "success",
                "embedding": embedding,
                "dimension": len(embedding),
                "cost_estimate": cost_estimate,
                "tokens_used": tokens_used,
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