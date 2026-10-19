import numpy as np
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from app.db.models import DocumentChunk

class VectorStore:
    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    @classmethod
    def similarity_search(
        cls,
        db: Session,
        query_vector: List[float],
        session_id: str,
        document_id: Optional[str] = None,
        top_k: int = 4
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Calculates cosine similarity of query_vector against document chunks.
        Scoped to session_id and optional document_id.
        """
        query_np = np.array(query_vector, dtype=np.float32)

        q = db.query(DocumentChunk).filter(DocumentChunk.session_id == session_id)
        if document_id:
            q = q.filter(DocumentChunk.document_id == document_id)

        all_chunks = q.all()
        scored: List[Tuple[DocumentChunk, float]] = []

        for chunk in all_chunks:
            emb = chunk.get_embedding()
            if not emb:
                continue
            emb_np = np.array(emb, dtype=np.float32)
            score = cls.cosine_similarity(query_np, emb_np)
            scored.append((chunk, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
