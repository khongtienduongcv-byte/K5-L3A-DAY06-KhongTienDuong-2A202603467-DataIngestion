"""Implement fixed-size and structure-aware chunking."""
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Cau hinh A: Cat text thanh cac window co overlap."""
    chunks = []
    text = page.text
    start = 0
    chunk_idx = 1

    while start < len(text):
        end = start + size
        chunk_text = text[start:end]
        chunks.append(Chunk(
            chunk_id=f"{page.document_id}_A_{chunk_idx}",
            document_id=page.document_id,
            source=page.source,
            page=page.page,
            text=chunk_text,
            metadata={},  # Khong filter
        ))
        start += (size - overlap)
        chunk_idx += 1
    return chunks


def by_paragraph(page: DocumentPage, max_size: int, add_metadata: bool = False) -> list[Chunk]:
    """Cau hinh B & C: Nhom theo doan van (paragraph), gioi han max_size."""
    paragraphs = page.text.split("\n\n")
    chunks = []
    current_chunk = ""
    chunk_idx = 1

    chapter = page.metadata.get("chapter", "")

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) > max_size and current_chunk:
            meta = {}
            if add_metadata:
                meta["chapter"] = chapter

            chunks.append(Chunk(
                chunk_id=f"{page.document_id}_BC_{chunk_idx}",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=current_chunk.strip(),
                metadata=meta,
            ))
            current_chunk = para
            chunk_idx += 1
        else:
            current_chunk = "\n\n" + para if current_chunk else para

    if current_chunk:
        meta = {}
        if add_metadata:
            meta["chapter"] = chapter

        chunks.append(Chunk(
            chunk_id=f"{page.document_id}_BC_{chunk_idx}",
            document_id=page.document_id,
            source=page.source,
            page=page.page,
            text=current_chunk.strip(),
            metadata=meta,
        ))

    return chunks
