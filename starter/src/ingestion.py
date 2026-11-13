"""Read and normalize source data. Reads one DocumentPage per book chapter."""
import json
import re
from pathlib import Path
from .models import DocumentPage


def load_text(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Doc chuong sach tu chapters.json (moi chuong = mot trang/truy vet)."""
    with open(path, "r", encoding="utf-8") as f:
        chapters = json.load(f)

    pages: list[DocumentPage] = []
    for idx, ch in enumerate(chapters, start=1):
        text = normalize_text(ch["text"])
        pages.append(
            DocumentPage(
                document_id=document_id,
                source=source,
                page=idx,
                text=text,
                metadata={"chapter": ch["title"], "chapter_id": ch["id"]},
            )
        )
    return pages


def normalize_text(text: str) -> str:
    """Chuan hoa Unicode va khoang trang."""
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
