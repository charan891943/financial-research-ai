import logging
import re
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from sqlalchemy.orm import Session
from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

RESEARCH_PROMPT_TEMPLATE = """
You are an expert Equity Research Analyst.
Answer the user's financial question strictly using the provided document excerpts.

Rules:
1. Every single claim or number in your answer MUST be cited with the page/section reference provided in the context (e.g. [Page 2, TCS Annual Report]).
2. If the context does not contain the answer, explicitly state that the documents do not provide this information.
3. Compare metrics clearly across financial years or companies when requested.
4. Format your answer with clear markdown tables or bullet points where appropriate.

Context Excerpts:
{context}

User Question:
{question}
"""

class ResearchAgent:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.mock_mode = settings.MOCK_AI
        self.model_name = settings.GEMINI_MODEL

        if not self.mock_mode:
            genai.configure(api_key=settings.GEMINI_API_KEY)

    def answer_query(self, session_id: str, question: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Embeds the user query, retrieves top relevant chunks across the session,
        and uses Gemini 2.5 Flash to synthesize an answer with citations.
        """
        # Split explicit sub-questions without breaking company comparisons such as "TCS and Infosys".
        query_parts = [part.strip() for part in re.split(r"[?;\n]+", question) if part.strip()] or [question]
        evidence = {}
        for query_part in query_parts[:4]:
            query_vector = self.embedding_service.get_query_embedding(query_part)
            for chunk, score in VectorStore.similarity_search(self.db, query_vector, session_id, document_id, top_k=12):
                evidence[chunk.id] = (chunk, score)

        query_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
        scored_chunks = []
        for chunk, score in evidence.values():
            content_terms = set(re.findall(r"[a-z0-9]+", f"{chunk.company} {chunk.content}".lower()))
            lexical_overlap = len(query_terms & content_terms) / max(len(query_terms), 1)
            scored_chunks.append((chunk, score + lexical_overlap * 0.25))
        scored_chunks.sort(key=lambda item: item[1], reverse=True)

        named_companies = []
        for chunk, _ in scored_chunks:
            company_terms = set(re.findall(r"[a-z0-9]+", chunk.company.lower()))
            if company_terms & query_terms and chunk.company not in named_companies:
                named_companies.append(chunk.company)
        prioritized = [next(item for item in scored_chunks if item[0].company == company) for company in named_companies]
        prioritized_ids = {chunk.id for chunk, _ in prioritized}
        scored_chunks = prioritized + [item for item in scored_chunks if item[0].id not in prioritized_ids]
        scored_chunks = scored_chunks[:8]

        if not scored_chunks:
            return {
                "answer": "No indexed document chunks found in this research session to answer your question.",
                "citations": []
            }

        context_lines = []
        citations = []
        for chunk, score in scored_chunks:
            citation_tag = f"[{chunk.company} | {chunk.page_number}]"
            citations.append({
                "company": chunk.company,
                "page_number": chunk.page_number,
                "chunk_id": chunk.id,
                "score": round(score, 4),
                "excerpt": chunk.content[:200] + "..."
            })
            context_lines.append(f"{citation_tag}:\n{chunk.content}\n")

        context_str = "\n".join(context_lines)
        prompt = RESEARCH_PROMPT_TEMPLATE.format(context=context_str, question=question)

        if self.mock_mode:
            snippet_summary = ""
            for chunk, _ in scored_chunks[:3]:
                snippet_summary += f"\n- **{chunk.company} ({chunk.page_number})**: \"{chunk.content[:220].strip()}...\""
            mock_answer = (
                f"I decomposed the question into {len(query_parts)} retrieval step(s) and grounded the response in the indexed excerpts below.\n"
                f"{snippet_summary}\n\n"
                f"Every factual claim in this offline response should be checked against the cited excerpts; the indexed documents do not support claims beyond them."
            )
            return {
                "answer": mock_answer,
                "citations": citations
            }

        try:
            model = genai.GenerativeModel(model_name=self.model_name)
            response = model.generate_content(prompt)
            return {
                "answer": response.text,
                "citations": citations
            }
        except Exception as e:
            logger.error(f"[ResearchAgent] Query generation failed: {e}")
            return {
                "answer": f"Error generating research answer from Gemini: {str(e)}",
                "citations": citations
            }
