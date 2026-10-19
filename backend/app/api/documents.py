import os
import uuid
import shutil
import logging
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from app.config import settings
from app.db.database import get_db, SessionLocal
from app.db.models import Document, ResearchSession
from app.agents.document_agent import DocumentAgent
from app.services.orchestrator import UploadOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

class DocumentResponse(BaseModel):
    id: str
    session_id: str
    company: str
    filename: str
    financial_year: str
    document_type: str
    status: str
    chunk_count: int
    error_message: Optional[str]
    created_at: str

def execute_pipeline_task(document_id: str):
    """Worker task executing the sequential Milestone 3 agent pipeline."""
    db = SessionLocal()
    try:
        UploadOrchestrator(db).run(document_id)
    except Exception as e:
        logger.error(f"Pipeline error for document {document_id}: {e}", exc_info=True)
    finally:
        db.close()

@router.get("/session/{session_id}", response_model=List[DocumentResponse])
def get_session_documents(session_id: str, db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.session_id == session_id).order_by(Document.created_at.desc()).all()
    return [
        DocumentResponse(
            id=d.id,
            session_id=d.session_id,
            company=d.company,
            filename=d.filename,
            financial_year=d.financial_year,
            document_type=d.document_type,
            status=d.status,
            chunk_count=d.chunk_count,
            error_message=d.error_message,
            created_at=d.created_at.isoformat()
        )
        for d in docs
    ]

@router.post("/upload", response_model=DocumentResponse)
def upload_document(
    background_tasks: BackgroundTasks,
    session_id: str = Form(...),
    company: str = Form(...),
    financial_year: str = Form("FY2025"),
    document_type: str = Form("Annual Report"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Research session does not exist")

    safe_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        session_id=session_id,
        company=company.strip(),
        filename=file.filename,
        file_path=file_path,
        financial_year=financial_year.strip(),
        document_type=document_type.strip(),
        status="uploaded"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(execute_pipeline_task, doc_id)

    return DocumentResponse(
        id=doc.id,
        session_id=doc.session_id,
        company=doc.company,
        filename=doc.filename,
        financial_year=doc.financial_year,
        document_type=doc.document_type,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_at=doc.created_at.isoformat()
    )
