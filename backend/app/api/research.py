from typing import List, Optional, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.agents.research_agent import ResearchAgent

router = APIRouter(prefix="/research", tags=["Research Agent Q&A"])

class QueryRequest(BaseModel):
    session_id: str
    question: str
    document_id: Optional[str] = None

class CitationResponse(BaseModel):
    company: str
    page_number: str
    chunk_id: str
    score: float
    excerpt: str

class QueryResponse(BaseModel):
    answer: str
    citations: List[CitationResponse]

@router.post("/query", response_model=QueryResponse)
def ask_research_agent(req: QueryRequest, db: Session = Depends(get_db)):
    """
    Submits user query to ResearchAgent for multi-document RAG retrieval
    and synthesis with citations.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    agent = ResearchAgent(db)
    res = agent.answer_query(
        session_id=req.session_id,
        question=req.question.strip(),
        document_id=req.document_id
    )
    return res
