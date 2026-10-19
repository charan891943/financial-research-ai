import os
import re
from typing import List, Dict, Any
from pypdf import PdfReader
import pandas as pd

class DocumentParser:
    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r'[\r\f]+', '\n', text)
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()

    @classmethod
    def parse_pdf(cls, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        reader = PdfReader(file_path)
        pages = []
        for idx, page in enumerate(reader.pages):
            raw_text = page.extract_text() or ""
            cleaned = cls.clean_text(raw_text)
            if cleaned:
                pages.append({
                    "page_number": f"Page {idx + 1}",
                    "content": cleaned
                })
        return pages

    @classmethod
    def parse_excel(cls, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Spreadsheet file not found: {file_path}")

        excel_data = pd.read_excel(file_path, sheet_name=None)
        sheets = []
        for sheet_name, df in excel_data.items():
            if df.empty:
                continue
            text_repr = f"=== Sheet: {sheet_name} ===\n" + df.fillna("-").to_string(index=False)
            sheets.append({
                "page_number": f"Sheet: {sheet_name}",
                "content": cls.clean_text(text_repr)
            })
        return sheets

    @classmethod
    def parse(cls, file_path: str) -> List[Dict[str, Any]]:
        lower = file_path.lower()
        if lower.endswith(".pdf"):
            return cls.parse_pdf(file_path)
        elif lower.endswith((".xlsx", ".xls")):
            return cls.parse_excel(file_path)
        elif lower.endswith(".csv"):
            df = pd.read_csv(file_path)
            return [{
                "page_number": "CSV Data Sheet",
                "content": cls.clean_text(df.fillna("-").to_string(index=False))
            }]
        elif lower.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return [{
                    "page_number": "Text Document",
                    "content": cls.clean_text(f.read())
                }]
        else:
            raise ValueError(f"Unsupported document format: {file_path}")
