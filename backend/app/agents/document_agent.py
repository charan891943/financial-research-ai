import uuid
import logging
from sqlalchemy.orm import Session
from app.db.models import Document, DocumentChunk
from app.services.document_parser import DocumentParser
from app.services.chunker import TextChunker
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class DocumentAgent:
    def __init__(self, db: Session):
        self.db = db
        self.chunker = TextChunker(chunk_size=1100, chunk_overlap=150)
        self.embedding_service = EmbeddingService()

    def process_document(self, document_id: str) -> Document:
        """
        Executes strict document indexing:
        Parse -> Clean -> Chunk -> Embed -> Index -> Update Status
        """
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document ID {document_id} not found")

        try:
            logger.info(f"[DocumentAgent] Stage 1/4: Parsing file '{doc.filename}'")
            doc.status = "parsing"
            doc.error_message = None
            self.db.commit()

            pages = DocumentParser.parse(doc.file_path)
            if not pages:
                raise ValueError("Parsed document yielded zero readable text.")

            logger.info(f"[DocumentAgent] Stage 2/4: Chunking {len(pages)} pages...")
            doc.status = "chunking"
            self.db.commit()

            raw_chunks = self.chunker.chunk_pages(pages)

            logger.info(f"[DocumentAgent] Stage 3/4: Generating vector embeddings for {len(raw_chunks)} chunks...")
            doc.status = "embedding"
            self.db.commit()

            # Clear any previously generated chunks for clean re-processing
            self.db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()

            for item in raw_chunks:
                vector = self.embedding_service.get_embedding(item["content"])
                chunk_obj = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc.id,
                    session_id=doc.session_id,
                    company=doc.company,
                    chunk_index=item["chunk_index"],
                    page_number=item["page_number"],
                    content=item["content"]
                )
                chunk_obj.set_embedding(vector)
                self.db.add(chunk_obj)

            doc.chunk_count = len(raw_chunks)
            doc.status = "indexed"
            self.db.commit()
            logger.info(f"[DocumentAgent] Stage 4/4: Successfully indexed '{doc.filename}' ({doc.chunk_count} chunks).")
            return doc

        except Exception as e:
            logger.error(f"[DocumentAgent] Ingestion failed for document '{doc.filename}': {e}", exc_info=True)
            doc.status = "failed"
            doc.error_message = str(e)
            self.db.commit()
            raise e
