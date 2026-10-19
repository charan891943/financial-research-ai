import os
import uuid
import logging
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session
from app.config import settings
from app.db.models import ResearchSession, Document
from app.services.orchestrator import UploadOrchestrator
from app.agents.report_agent import ReportAgent
from app.agents.red_flag_agent import RedFlagAgent
from app.services.seed_data import SEED_COMPANIES

logger = logging.getLogger(__name__)

def generate_pdf_document(file_path: str, pages_text: list[str]):
    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter

    for page_idx, page_content in enumerate(pages_text):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 40, f"DOCUMENT SECTION - PAGE {page_idx + 1}")
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.line(50, height - 48, width - 50, height - 48)

        c.setFont("Helvetica", 9)
        y = height - 70
        for line in page_content.split("\n"):
            if y < 50:
                c.showPage()
                y = height - 40
                c.setFont("Helvetica", 9)
            c.drawString(50, y, line)
            y -= 14

        c.showPage()
    c.save()

class SeedService:
    @classmethod
    def seed_workspace(cls, db: Session) -> ResearchSession:
        session_name = "Indian Corporate Leaders Analysis"
        session = db.query(ResearchSession).filter(ResearchSession.name == session_name).first()

        if not session:
            session = ResearchSession(
                id=str(uuid.uuid4()),
                name=session_name,
                description="Comprehensive multi-document analysis for TCS, Reliance, Infosys, and HDFC Bank."
            )
            db.add(session)
            db.commit()

        orchestrator = UploadOrchestrator(db)

        for comp in SEED_COMPANIES:
            existing_doc = db.query(Document).filter(
                Document.session_id == session.id,
                Document.company == comp["company"]
            ).first()

            if existing_doc and existing_doc.status == "extracted":
                RedFlagAgent(db).scan_document(existing_doc.id)
                continue

            file_path = os.path.join(settings.UPLOAD_DIR, comp["filename"])
            generate_pdf_document(file_path, comp["pages"])

            if not existing_doc:
                doc = Document(
                    id=str(uuid.uuid4()),
                    session_id=session.id,
                    company=comp["company"],
                    filename=comp["filename"],
                    file_path=file_path,
                    financial_year=comp["fy"],
                    document_type="Annual Report",
                    status="uploaded"
                )
                db.add(doc)
                db.commit()
            else:
                doc = existing_doc

            orchestrator.run(doc.id)

        ReportAgent(db).generate(session.id)
        db.refresh(session)
        return session
