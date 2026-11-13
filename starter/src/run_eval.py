"""Evaluation entry point."""
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from src.embeddings import DynamicPoolEmbedder
from src.store import PgVectorStore
from src.evaluation import evaluate_query, summarize


def main() -> None:
    load_dotenv()

    # 1. Tim va doc file dataset.json (ho tro ca 2 cap thu muc)
    dataset_path = Path("benchmark/dataset.json")
    if not dataset_path.exists():
        dataset_path = Path("../benchmark/dataset.json")

    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)
    except FileNotFoundError:
        print(f"[!] Khong tim thay file dataset.json tai {dataset_path}!")
        return

    # 2. Khoi tao Embedder va Database
    print("Dang khoi tao Embedder cho qua routine danh gia...")
    embedder = DynamicPoolEmbedder()
    db_url = "postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab"
    store = PgVectorStore(database_url=db_url, dimensions=embedder.dimensions)

    strategies = ["strategy_A", "strategy_B", "strategy_C"]
    chunk_counts = {"strategy_A": 0, "strategy_B": 0, "strategy_C": 0}
    all_results = {}

    # 3. Vong lap test qua tung chien luoc
    for strategy in strategies:
        print(f"\nDang truy xuat va danh gia chien luoc: {strategy}...")
        traces = []

        for q in dataset:
            q_vec = embedder.embed_query(q["question"])

            # Xu ly metadata filter neu la chien luoc C
            filters = None
            if strategy == "strategy_C" and q.get("filter") and q["filter"].get("chapter"):
                filters = {"chapter": q["filter"]["chapter"]}

            # Lay Top 3 ket qua tu Database
            hits = store.search(strategy=strategy, query_vector=q_vec, top_k=3, filters=filters)

            # Cham diem
            trace = evaluate_query(q, hits)
            traces.append(trace)

        # Tong ket chi so
        summary = summarize(traces)
        # Dem so chunk cua strategy trong DB
        with store.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM chunks_table WHERE strategy = %s", (strategy,))
            chunk_counts[strategy] = cur.fetchone()[0]

        all_results[strategy] = {
            "summary": summary,
            "chunk_count": chunk_counts[strategy],
            "traces": traces,
        }
        print(f"Ket qua {strategy}: Hit@1 = {summary['hit_1_rate']}% | Hit@3 = {summary['hit_3_rate']}%")

    # 4. Luu trace ket qua ra file JSON phuc vu viet bao cao
    os.makedirs("results", exist_ok=True)
    with open("results/evaluation_traces.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print("\nDa luu toan bo lich su truy xuat va danh gia vao results/evaluation_traces.json!")


if __name__ == "__main__":
    main()
