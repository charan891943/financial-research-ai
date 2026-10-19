import json
import uuid
from typing import List

from sqlalchemy.orm import Session

from app.db.models import ExtractedMetric, RedFlag, ReportSection


class ReportAgent:
    """Builds the first report sections from persisted, source-linked outputs."""

    def __init__(self, db: Session):
        self.db = db

    def generate(self, session_id: str) -> List[ReportSection]:
        metrics = self.db.query(ExtractedMetric).filter(ExtractedMetric.session_id == session_id).order_by(ExtractedMetric.company, ExtractedMetric.metric_name).all()
        flags = self.db.query(RedFlag).filter(RedFlag.session_id == session_id).all()
        self.db.query(ReportSection).filter(ReportSection.session_id == session_id).delete()

        companies = sorted({metric.company for metric in metrics})
        summary = f"This report covers {len(companies)} companies and {len(metrics)} extracted financial observations. "
        summary += f"The red-flag scan identified {len(flags)} review item(s)."
        sources = [flag.source_reference for flag in flags[:8]] + [metric.source_reference for metric in metrics[:8]]
        sections = [ReportSection(
            id=str(uuid.uuid4()), session_id=session_id, section_type="executive_summary",
            title="Executive Summary", content=summary,
            source_references=json.dumps(sources)
        )]

        lines = ["| Company | Metric | Period | Value | Source |", "| --- | --- | --- | --- | --- |"]
        for metric in metrics[:30]:
            lines.append(f"| {metric.company} | {metric.metric_name} | {metric.financial_year} | {metric.value} {metric.unit} | {metric.source_reference} |")
        sections.append(ReportSection(
            id=str(uuid.uuid4()), session_id=session_id, section_type="key_financials",
            title="Key Financials", content="\n".join(lines),
            source_references=json.dumps([metric.source_reference for metric in metrics[:30]])
        ))
        self.db.add_all(sections)
        self.db.commit()
        return sections