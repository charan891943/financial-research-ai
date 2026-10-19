from typing import List
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import ExtractedMetric

router = APIRouter(prefix="/metrics", tags=["Financial Metrics"])

class MetricResponse(BaseModel):
    id: str
    document_id: str
    session_id: str
    company: str
    metric_name: str
    value: str
    unit: str
    financial_year: str
    category: str
    source_reference: str

@router.get("/session/{session_id}", response_model=List[MetricResponse])
def get_session_metrics(session_id: str, db: Session = Depends(get_db)):
    metrics = (
        db.query(ExtractedMetric)
        .filter(ExtractedMetric.session_id == session_id)
        .order_by(ExtractedMetric.company, ExtractedMetric.financial_year.desc())
        .all()
    )
    return [
        MetricResponse(
            id=m.id,
            document_id=m.document_id,
            session_id=m.session_id,
            company=m.company,
            metric_name=m.metric_name,
            value=m.value,
            unit=m.unit,
            financial_year=m.financial_year,
            category=m.category,
            source_reference=m.source_reference
        )
        for m in metrics
    ]
