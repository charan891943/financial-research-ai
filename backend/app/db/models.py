from datetime import datetime
import json
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="session", cascade="all, delete-orphan")
    metrics = relationship("ExtractedMetric", back_populates="session", cascade="all, delete-orphan")
    red_flags = relationship("RedFlag", back_populates="session", cascade="all, delete-orphan")
    report_sections = relationship("ReportSection", back_populates="session", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    company = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    document_type = Column(String(50), default="Annual Report")
    financial_year = Column(String(20), default="FY2025")
    status = Column(String(50), default="uploaded", index=True)  # uploaded, parsing, chunking, embedding, indexed, extracting, extracted, failed
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ResearchSession", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    metrics = relationship("ExtractedMetric", back_populates="document", cascade="all, delete-orphan")
    red_flags = relationship("RedFlag", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), nullable=False, index=True)
    company = Column(String(255), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")

    def set_embedding(self, vector: list[float]):
        self.embedding_json = json.dumps(vector)

    def get_embedding(self) -> list[float]:
        if not self.embedding_json:
            return []
        return json.loads(self.embedding_json)


class ExtractedMetric(Base):
    __tablename__ = "extracted_metrics"

    id = Column(String(36), primary_key=True, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    value = Column(String(100), nullable=False)
    unit = Column(String(50), default="Cr INR")
    financial_year = Column(String(20), nullable=False, index=True)
    category = Column(String(50), default="Income Statement")
    source_reference = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="metrics")
    session = relationship("ResearchSession", back_populates="metrics")


class RedFlag(Base):
    __tablename__ = "red_flags"

    id = Column(String(36), primary_key=True, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="medium")
    category = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    details = Column(Text, nullable=False)
    source_reference = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="red_flags")
    session = relationship("ResearchSession", back_populates="red_flags")


class ReportSection(Base):
    __tablename__ = "report_sections"

    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("research_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    section_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    source_references = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ResearchSession", back_populates="report_sections")
