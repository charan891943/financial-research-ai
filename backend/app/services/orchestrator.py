import logging

from sqlalchemy.orm import Session

from app.agents.document_agent import DocumentAgent
from app.agents.extraction_agent import ExtractionAgent
from app.agents.red_flag_agent import RedFlagAgent

logger = logging.getLogger(__name__)


class UploadOrchestrator:
    """Runs the upload contract in order and leaves each stage persisted."""

    def __init__(self, db: Session):
        self.db = db

    def run(self, document_id: str):
        DocumentAgent(self.db).process_document(document_id)
        ExtractionAgent(self.db).extract_from_document(document_id)
        RedFlagAgent(self.db).scan_document(document_id)
        logger.info("[Orchestrator] Document, Extraction, and Red Flag agents completed for %s", document_id)