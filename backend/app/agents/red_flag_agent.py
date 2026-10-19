import re
import uuid
from typing import List

from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk, ExtractedMetric, RedFlag


class RedFlagAgent:
    """Finds explainable risks from extracted metrics and indexed source text."""

    def __init__(self, db: Session):
        self.db = db

    def scan_document(self, document_id: str) -> List[RedFlag]:
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        chunks = self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index).all()
        metrics = self.db.query(ExtractedMetric).filter(ExtractedMetric.document_id == document_id).all()
        self.db.query(RedFlag).filter(RedFlag.document_id == document_id).delete()
        flags: List[RedFlag] = []

        def add_flag(severity: str, category: str, title: str, details: str, source: str):
            flags.append(RedFlag(
                id=str(uuid.uuid4()), document_id=document.id, session_id=document.session_id,
                company=document.company, severity=severity, category=category,
                title=title, details=details, source_reference=source
            ))

        debt = next((metric for metric in metrics if metric.metric_name.lower() in {"total debt", "net debt"}), None)
        if debt:
            debt_value = self._number(debt.value)
            if debt_value > 100000:
                add_flag("high", "Debt", "Material debt load", f"Reported {debt.metric_name.lower()} of {debt.value} {debt.unit} exceeds the 100,000 Cr review threshold.", debt.source_reference)

        full_text = "\n".join(chunk.content for chunk in chunks)
        for match in re.finditer(r"(?:auditor|audit opinion)[^\n.]{0,100}(?:qualified|adverse|disclaimer|emphasis of matter)", full_text, re.IGNORECASE):
            source_chunk = next((chunk for chunk in chunks if match.group(0)[:30].lower() in chunk.content.lower()), chunks[0] if chunks else None)
            add_flag("high", "Audit", "Auditor qualification detected", match.group(0).strip(), self._source(source_chunk))

        margin_match = re.search(r"(?:margin|nim)[^\n]*?(\d+(?:\.\d+)?)%[^\n]*?(\d+(?:\.\d+)?)%", full_text, re.IGNORECASE)
        if margin_match and float(margin_match.group(2)) < float(margin_match.group(1)):
            source_chunk = next((chunk for chunk in chunks if "margin" in chunk.content.lower() or "nim" in chunk.content.lower()), None)
            add_flag("medium", "Margins", "Falling reported margin", f"The source shows a decline from {margin_match.group(1)}% to {margin_match.group(2)}% across the reported periods.", self._source(source_chunk))

        unusual_terms = re.search(r"(?:restatement|related party|one[- ]off|impairment|exceptional loss|irregular)", full_text, re.IGNORECASE)
        if unusual_terms:
            source_chunk = next((chunk for chunk in chunks if unusual_terms.group(0).lower() in chunk.content.lower()), None)
            add_flag("medium", "Unusual pattern", "Unusual financial disclosure", f"The indexed document contains the unusual disclosure term '{unusual_terms.group(0)}'.", self._source(source_chunk))

        self.db.add_all(flags)
        self.db.commit()
        return flags

    @staticmethod
    def _number(value: str) -> float:
        try:
            return float(re.sub(r"[^0-9.]", "", value) or 0)
        except ValueError:
            return 0

    @staticmethod
    def _source(chunk: DocumentChunk | None) -> str:
        return f"{chunk.page_number} - {chunk.content[:220]}" if chunk else "Indexed document text"