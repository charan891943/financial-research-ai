from typing import List, Dict, Any

class TextChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Splits text into sliding-window chunks while preserving precise page/sheet tags.
        """
        chunks = []
        chunk_idx = 0

        for page in pages:
            text = page["content"]
            page_ref = page["page_number"]

            if len(text) <= self.chunk_size:
                chunks.append({
                    "chunk_index": chunk_idx,
                    "page_number": page_ref,
                    "content": text
                })
                chunk_idx += 1
                continue

            start = 0
            while start < len(text):
                end = start + self.chunk_size
                chunk_slice = text[start:end]

                if end < len(text):
                    last_break = max(chunk_slice.rfind("\n"), chunk_slice.rfind(". "))
                    if last_break > self.chunk_size * 0.5:
                        chunk_slice = chunk_slice[:last_break + 1]
                        start += last_break + 1 - self.chunk_overlap
                    else:
                        start += self.chunk_size - self.chunk_overlap
                else:
                    start = len(text)

                cleaned_slice = chunk_slice.strip()
                if cleaned_slice:
                    chunks.append({
                        "chunk_index": chunk_idx,
                        "page_number": page_ref,
                        "content": cleaned_slice
                    })
                    chunk_idx += 1

        return chunks
