"""Evaluate retrieved evidence and preserve per-query traces."""
from typing import Any


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Kiem tra evidence_quote co xuat hien trong text cua top hits khong."""
    evidence_quote = question.get("evidence_quote", "").strip()

    hit_1 = False
    hit_3 = False

    if not evidence_quote:
        gold_page = str(question.get("gold_page"))
        if len(hits) > 0 and str(hits[0]["metadata"].get("page")) == gold_page:
            hit_1 = True
        for hit in hits[:3]:
            if str(hit["metadata"].get("page")) == gold_page:
                hit_3 = True
                break
    else:
        quote_snippet = evidence_quote[:50].lower()

        if len(hits) > 0 and quote_snippet in hits[0]["text"].lower():
            hit_1 = True

        for hit in hits[:3]:
            if quote_snippet in hit["text"].lower():
                hit_3 = True
                break

    return {
        "question_id": question.get("id"),
        "question": question.get("question"),
        "split": question.get("split"),
        "hit_1": hit_1,
        "hit_3": hit_3,
        "hits": hits
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Tinh ty le Hit@1 va Hit@3 tong the."""
    total = len(traces)
    if total == 0:
        return {"total": 0, "hit_1_rate": 0.0, "hit_3_rate": 0.0}

    hit_1_count = sum(1 for t in traces if t.get("hit_1"))
    hit_3_count = sum(1 for t in traces if t.get("hit_3"))

    return {
        "total": total,
        "hit_1_rate": round((hit_1_count / total) * 100, 2),
        "hit_3_rate": round((hit_3_count / total) * 100, 2),
        "hit_1_n": hit_1_count,
        "hit_3_n": hit_3_count,
    }


# ---------------------------------------------------------------------------
# 5 khia canh danh gia theo GUIDE.md / BENCHMARK.md
# ---------------------------------------------------------------------------

def label_coherence(chunks: list[dict[str, Any]], positions: list[str]) -> dict[str, Any]:
    """
    Cham chunk coherence cho 10 vi tri ngoai truc, thang 0-2.
    positions: danh sach 10 chapter_id hoac vi tri can kiem tra.
    chunks: danh sach chunk (co text, metadata) bao phu cac vi tri do.
    """
    labels = []
    for pos in positions:
        best_chunk = None
        for ch in chunks:
            meta = ch.get("metadata", {})
            if meta.get("chapter_id") == pos or meta.get("chapter") == pos:
                best_chunk = ch
                break
        if best_chunk is None and chunks:
            best_chunk = chunks[0]

        text = best_chunk.get("text", "") if best_chunk else ""
        if len(text) >= 200:
            score = 2
        elif len(text) >= 80:
            score = 1
        else:
            score = 0
        labels.append({"position": pos, "coherence": score, "text_preview": text[:120]})

    avg = round(sum(l["coherence"] for l in labels) / len(labels), 2) if labels else 0.0
    return {"labels": labels, "average": avg, "n": len(labels)}


def label_metadata(hits: list[dict[str, Any]], n_test: int = 5) -> dict[str, Any]:
    """
    Kiem tra metadata source, page, chapter du va dung tren top-3.
    Tra lai so ban ghi du va dung / tong da kiem tra.
    """
    checked = hits[:n_test]
    ok = 0
    details = []
    for hit in checked:
        meta = hit.get("metadata", {})
        has_source = bool(meta.get("source"))
        has_page = bool(meta.get("page"))
        has_chapter = bool(meta.get("chapter"))
        full = has_source and has_page and has_chapter
        if full:
            ok += 1
        details.append({
            "chunk_id": hit.get("chunk_id"),
            "source": meta.get("source"),
            "page": meta.get("page"),
            "chapter": meta.get("chapter"),
            "full": full,
        })
    return {"ok": ok, "total": len(checked), "details": details}


def label_grounding(hits: list[dict[str, Any]], evidence_quote: str) -> dict[str, Any]:
    """
    Chat chat vat lieu tro cho mot cau hoi test (top-3), thang 0-2.
    0 = khong co by chung; 1 = co nhung thieu dieu kien/ngu canh;
    2 = du de tra loi va truy xuat nguon.
    """
    quote_snippet = evidence_quote[:50].lower() if evidence_quote else ""
    found = any(quote_snippet and quote_snippet in h.get("text", "").lower() for h in hits[:3])
    if not found:
        score = 0
    elif any(h.get("metadata", {}).get("source") for h in hits[:3]):
        score = 2
    else:
        score = 1
    return {"score": score, "hits": hits[:3]}


def compare_strategies(results_a: dict, results_b: dict, results_c: dict) -> dict[str, Any]:
    """So sanh tac dong cua chien luoc du lieu A-B va B-C."""
    def rate(r):
        return r.get("summary", {})

    a = rate(results_a)
    b = rate(results_b)
    c = rate(results_c)

    return {
        "A_to_B": {
            "hit_1_delta": round(b.get("hit_1_rate", 0) - a.get("hit_1_rate", 0), 2),
            "hit_3_delta": round(b.get("hit_3_rate", 0) - a.get("hit_3_rate", 0), 2),
        },
        "B_to_C": {
            "hit_1_delta": round(c.get("hit_1_rate", 0) - b.get("hit_1_rate", 0), 2),
            "hit_3_delta": round(c.get("hit_3_rate", 0) - b.get("hit_3_rate", 0), 2),
        },
        "chunk_counts": {
            "A": results_a.get("chunk_count", "?"),
            "B": results_b.get("chunk_count", "?"),
            "C": results_c.get("chunk_count", "?"),
        },
    }
