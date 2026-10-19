import uuid
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import ResearchSession, Document

router = APIRouter(prefix="/sessions", tags=["Research Sessions"])

class SessionCreate(BaseModel):
    name: str
    description: Optional[str] = None

class SessionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    document_count: int
    created_at: str
    updated_at: str

@router.get("", response_model=List[SessionResponse])
def list_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ResearchSession).order_by(ResearchSession.updated_at.desc()).all()
    results = []
    for s in sessions:
        doc_count = db.query(Document).filter(Document.session_id == s.id).count()
        results.append(SessionResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            document_count=doc_count,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat()
        ))
    return results

@router.post("", response_model=SessionResponse)
def create_session(data: SessionCreate, db: Session = Depends(get_db)):
    new_session = ResearchSession(
        id=str(uuid.uuid4()),
        name=data.name.strip(),
        description=data.description
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return SessionResponse(
        id=new_session.id,
        name=new_session.name,
        description=new_session.description,
        document_count=0,
        created_at=new_session.created_at.isoformat(),
        updated_at=new_session.updated_at.isoformat()
    )

@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    s = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    doc_count = db.query(Document).filter(Document.session_id == s.id).count()
    return SessionResponse(
        id=s.id,
        name=s.name,
        description=s.description,
        document_count=doc_count,
        created_at=s.created_at.isoformat(),
        updated_at=s.updated_at.isoformat()
    )
