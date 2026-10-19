import uuid, json, logging
from typing import List, Dict, Any, Set
import google.generativeai as genai
from sqlalchemy.orm import Session
from app.config import settings
from app.db.models import Document, DocumentChunk, ExtractedMetric
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore
from app.agents.seed_metrics import (
    get_dynamic_mock_metrics,
    EXTRACTION_SYSTEM_PROMPT,
    TARGET_FINANCIAL_RETRIEVAL_QUERIES
)

logger = logging.getLogger(__name__)

class ExtractionAgent:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.mock_mode = settings.MOCK_AI
        self.model_name = settings.GEMINI_MODEL
        if not self.mock_mode:
            genai.configure(api_key=settings.GEMINI_API_KEY)

    def _retrieve_relevant_financial_chunks(self, document_id: str, session_id: str) -> List[DocumentChunk]:
        seen = set()
        chunks = []
        for q in TARGET_FINANCIAL_RETRIEVAL_QUERIES:
            vec = self.embedding_service.get_query_embedding(q)
            matches = VectorStore.similarity_search(self.db, vec, session_id, document_id, 2)
            for chunk, _ in matches:
                if chunk.id not in seen:
                    seen.add(chunk.id)
                    chunks.append(chunk)
        chunks.sort(key=lambda c: c.chunk_index)
        return chunks

    def _call_gemini_json(self, prompt: str, company: str, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        if self.mock_mode:
            return {"metrics": get_dynamic_mock_metrics(company, chunks)}
        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=EXTRACTION_SYSTEM_PROMPT,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(model.generate_content(prompt).text)
        except Exception as e:
            fallback = "gemini-1.5-flash" if self.model_name != "gemini-1.5-flash" else "gemini-2.5-flash"
            logger.warning(f"Primary model {self.model_name} failed: {e}. Trying {fallback}...")
            try:
                model = genai.GenerativeModel(
                    model_name=fallback,
                    system_instruction=EXTRACTION_SYSTEM_PROMPT,
                    generation_config={"response_mime_type": "application/json"}
                )
                return json.loads(model.generate_content(prompt).text)
            except Exception as fe:
                raise RuntimeError(f"Gemini API failed. Primary: {e}. Fallback: {fe}") from fe

    def extract_from_document(self, document_id: str) -> List[ExtractedMetric]:
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")
        doc.status = "extracting"
        self.db.commit()
        try:
            relevant = self._retrieve_relevant_financial_chunks(doc.id, doc.session_id)
            if not relevant:
                relevant = self.db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).limit(10).all()

            ctx = "\n".join(f"--- [Section: {c.page_number}] ---\n{c.content}\n" for c in relevant)
            prompt = f"Company: {doc.company}\nFilename: {doc.filename}\n\nExcerpts:\n{ctx}\n\nExtract financial metrics."

            raw_metrics = self._call_gemini_json(prompt, doc.company, relevant).get("metrics", [])
            self.db.query(ExtractedMetric).filter(ExtractedMetric.document_id == doc.id).delete()

            saved = []
            for m in raw_metrics:
                rec = ExtractedMetric(
                    id=str(uuid.uuid4()),
                    document_id=doc.id,
                    session_id=doc.session_id,
                    company=doc.company,
                    metric_name=m.get("metric_name", "Unknown"),
                    value=str(m.get("value", "N/A")),
                    unit=m.get("unit", "Cr INR"),
                    financial_year=m.get("financial_year", doc.financial_year),
                    category=m.get("category", "Financial Highlights"),
                    source_reference=m.get("source_reference", f"{doc.filename} - Extracted Section")
                )
                self.db.add(rec)
                saved.append(rec)
            doc.status = "extracted"
            self.db.commit()
            return saved
        except Exception as e:
            doc.status = "failed"
            doc.error_message = f"Extraction failed: {str(e)}"
            self.db.commit()
            raise e
