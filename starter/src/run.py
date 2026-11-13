"""Pipeline entry point."""
import os
from pathlib import Path
from dotenv import load_dotenv
from src.ingestion import load_text, normalize_text
from src.chunking import fixed_size, by_paragraph
from src.embeddings import DynamicPoolEmbedder
from src.store import PgVectorStore


def main() -> None:
    load_dotenv()

    data_path = Path("data/chapters.json")
    pages = load_text(data_path, "fifty_famous", "Fifty Famous People")

    print("Dang cat chunk...")
    all_chunks_A = []
    all_chunks_B = []
    all_chunks_C = []

    for page in pages:
        all_chunks_A.extend(fixed_size(page, size=3000, overlap=300))
        all_chunks_B.extend(by_paragraph(page, max_size=5000, add_metadata=False))
        all_chunks_C.extend(by_paragraph(page, max_size=5000, add_metadata=True))

    print(f"  Tong so chunks: A={len(all_chunks_A)}, B={len(all_chunks_B)}, C={len(all_chunks_C)}")

    print("Dang khoi tao Embedder...")
    embedder = DynamicPoolEmbedder()

    db_url = "postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab"
    store = PgVectorStore(database_url=db_url, dimensions=embedder.dimensions)

    # Reset bang de chay lai tu dau (tranh loi sai so chi luu vector)
    with store.conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS chunks_table;")
    store.create_schema()

    print(f"\n[BAT DAU] Luu Cau hinh A: {len(all_chunks_A)} chunks...")
    store.upsert("strategy_A", all_chunks_A, embedder.embed_documents([c.text for c in all_chunks_A]))

    print(f"\n[BAT DAU] Luu Cau hinh B: {len(all_chunks_B)} chunks...")
    store.upsert("strategy_B", all_chunks_B, embedder.embed_documents([c.text for c in all_chunks_B]))

    print(f"\n[BAT DAU] Luu Cau hinh C: {len(all_chunks_C)} chunks...")
    store.upsert("strategy_C", all_chunks_C, embedder.embed_documents([c.text for c in all_chunks_C]))

    print("\nHOAN TAT INGESTION PIPELINE THANH CONG!")


if __name__ == "__main__":
    main()
