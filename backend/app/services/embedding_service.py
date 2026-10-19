import logging
import re
import hashlib
from typing import List
import google.generativeai as genai
from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.mock_mode = settings.MOCK_AI
        self.model_name = "models/text-embedding-004"

        if not self.mock_mode:
            if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.strip() == "your_gemini_api_key_here":
                raise ValueError(
                    "GEMINI_API_KEY is not configured in .env. "
                    "Set a valid key or explicitly set MOCK_AI=true for local unit tests."
                )
            genai.configure(api_key=settings.GEMINI_API_KEY)
        else:
            logger.warning("[EmbeddingService] MOCK_AI=true is enabled. Using deterministic pseudo-semantic vectors.")

    def _get_pseudo_semantic_embedding(self, text: str) -> List[float]:
        """
        Creates a deterministic pseudo-semantic vector of 768 dimensions.
        Words are extracted, filtered, and hashed to specific dimensions with specific signs.
        Allows actual term-matching and cosine similarity during offline mock mode.
        """
        dim = 768
        vec = [0.0] * dim
        
        # Clean text and split into words
        words = re.findall(r'[a-zA-Z0-9_]+', text.lower())
        if not words:
            return vec
            
        stopwords = {
            'the', 'and', 'of', 'to', 'in', 'is', 'for', 'that', 'on', 'with', 'at', 'by', 
            'an', 'be', 'this', 'are', 'from', 'it', 'as', 'your', 'all', 'any', 'or', 'a',
            'has', 'have', 'had', 'been', 'was', 'were', 'which', 'who', 'whom', 'whose'
        }
        
        word_counts = {}
        for w in words:
            if w not in stopwords and len(w) > 1:
                word_counts[w] = word_counts.get(w, 0) + 1
                
        if not word_counts:
            # Fallback if only stopwords or short words
            for w in words:
                word_counts[w] = word_counts.get(w, 0) + 1

        # Accumulate into hashed dimensions
        for word, count in word_counts.items():
            # Hash word to 3 distinct dimensions to reduce collisions
            for i in range(3):
                h_str = f"{word}_{i}"
                h_val = int(hashlib.md5(h_str.encode('utf-8')).hexdigest(), 16)
                index = h_val % dim
                weight = count * (1.0 + 0.1 * len(word))
                sign = 1 if (h_val % 2 == 0) else -1
                vec[index] += sign * weight

        # Add a small document-specific fingerprint so identical word patterns are slightly unique
        doc_hash = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)
        for i in range(10):
            index = (doc_hash >> i) % dim
            sign = 1 if ((doc_hash >> (i + 10)) % 2 == 0) else -1
            vec[index] += sign * 0.05

        # Normalize to L2 Unit Length
        norm = sum(val * val for val in vec) ** 0.5
        if norm > 0.000001:
            vec = [val / norm for val in vec]
        else:
            vec = [0.0] * dim
            vec[0] = 1.0
            
        return vec

    def get_embedding(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        """
        Generates embedding using Gemini text-embedding-004.
        Fails loudly if the upstream service fails and MOCK_AI=False.
        """
        if self.mock_mode:
            return self._get_pseudo_semantic_embedding(text)

        try:
            res = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type=task_type
            )
            return res['embedding']
        except Exception as e:
            logger.error(f"[EmbeddingService] Failed generating embedding: {e}")
            raise RuntimeError(f"Gemini Embedding API call failed: {e}") from e

    def get_query_embedding(self, query: str) -> List[float]:
        """Specialized task_type for queries in asymmetric retrieval."""
        if self.mock_mode:
            return self._get_pseudo_semantic_embedding(query)
        return self.get_embedding(query, task_type="retrieval_query")
