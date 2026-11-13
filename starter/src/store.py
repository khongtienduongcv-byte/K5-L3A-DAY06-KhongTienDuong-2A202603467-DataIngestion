"""Store and search vectors using PostgreSQL + pgvector."""
import psycopg2
from typing import Any
from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        self.conn = psycopg2.connect(database_url)
        self.conn.autocommit = True
        self.dimensions = dimensions

    def create_schema(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS chunks_table (
                    id SERIAL PRIMARY KEY,
                    chunk_id VARCHAR(255),
                    strategy VARCHAR(50),
                    document_id VARCHAR(255),
                    source VARCHAR(255),
                    page INT,
                    chapter VARCHAR(200),
                    character VARCHAR(100),
                    text TEXT,
                    embedding vector({self.dimensions})
                );
            """)

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        with self.conn.cursor() as cur:
            for chunk, vec in zip(chunks, vectors):
                cur.execute("""
                    INSERT INTO chunks_table (chunk_id, strategy, document_id, source, page, chapter, character, text, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    chunk.chunk_id, strategy, chunk.document_id, chunk.source, chunk.page,
                    chunk.metadata.get("chapter"), chunk.metadata.get("character"), chunk.text, vec
                ))

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with self.conn.cursor() as cur:
            query = "SELECT chunk_id, text, embedding <=> %s::vector AS score, page, source, chapter, character FROM chunks_table WHERE strategy = %s"
            params = [query_vector, strategy]

            if filters:
                if "chapter" in filters:
                    query += " AND chapter = %s"
                    params.append(filters["chapter"])
                if "character" in filters:
                    query += " AND character = %s"
                    params.append(filters["character"])

            query += " ORDER BY score ASC LIMIT %s"
            params.append(top_k)

            cur.execute(query, tuple(params))
            results = []
            for row in cur.fetchall():
                results.append({
                    "chunk_id": row[0], "text": row[1], "score": row[2],
                    "metadata": {"page": row[3], "source": row[4], "chapter": row[5], "character": row[6]}
                })
            return results
