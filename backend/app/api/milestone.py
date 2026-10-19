import json
import re
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.report_agent import ReportAgent
from app.db.database import get_db
from app.db.models import ExtractedMetric, RedFlag, ReportSection

router = APIRouter(prefix="/milestone", tags=["Milestone 3"])


class RedFlagResponse(BaseModel):
    id: str
    document_id: str
    company: str
    severity: str
    category: str
    title: str
    details: str
    source_reference: str


class ReportSectionResponse(BaseModel):
    id: str
    section_type: str
    title: str
    content: str
    source_references: List[str]


@router.get("/red-flags/session/{session_id}", response_model=List[RedFlagResponse])
def list_red_flags(session_id: str, db: Session = Depends(get_db)):
    flags = db.query(RedFlag).filter(RedFlag.session_id == session_id).order_by(RedFlag.severity.desc(), RedFlag.company).all()
    return [RedFlagResponse(
        id=flag.id, document_id=flag.document_id, company=flag.company,
        severity=flag.severity, category=flag.category, title=flag.title,
        details=flag.details, source_reference=flag.source_reference
    ) for flag in flags]


@router.get("/comparison/session/{session_id}")
def compare_metrics(session_id: str, metric_name: Optional[str] = None, db: Session = Depends(get_db)) -> dict[str, Any]:
    query = db.query(ExtractedMetric).filter(ExtractedMetric.session_id == session_id)
    if metric_name:
        query = query.filter(ExtractedMetric.metric_name.ilike(f"%{metric_name.strip()}%"))
    metrics = query.order_by(ExtractedMetric.metric_name, ExtractedMetric.company).all()
    grouped: dict[str, list[dict[str, str]]] = {}
    for metric in metrics:
        grouped.setdefault(metric.metric_name, []).append({
            "company": metric.company, "financial_year": metric.financial_year,
            "value": metric.value, "unit": metric.unit, "source_reference": metric.source_reference
        })
    return {"session_id": session_id, "metrics": grouped}


@router.post("/report/session/{session_id}", response_model=List[ReportSectionResponse])
def generate_report(session_id: str, db: Session = Depends(get_db)):
    sections = ReportAgent(db).generate(session_id)
    return [_section_response(section) for section in sections]


@router.get("/report/session/{session_id}", response_model=List[ReportSectionResponse])
def get_report(session_id: str, db: Session = Depends(get_db)):
    sections = db.query(ReportSection).filter(ReportSection.session_id == session_id).order_by(ReportSection.section_type).all()
    return [_section_response(section) for section in sections]


def _section_response(section: ReportSection) -> ReportSectionResponse:
    try:
        sources = json.loads(section.source_references or "[]")
    except json.JSONDecodeError:
        sources = []
    return ReportSectionResponse(
        id=section.id, section_type=section.section_type, title=section.title,
        content=section.content, source_references=sources
    )