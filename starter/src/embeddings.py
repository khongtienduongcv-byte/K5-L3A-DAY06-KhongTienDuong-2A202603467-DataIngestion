"""Choose a real embedding provider (API or local) and implement this contract."""
import os
import sys
import time
import queue
from typing import Protocol
from concurrent.futures import ThreadPoolExecutor


class Embedder(Protocol):
    model_name: str
    dimensions: int
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, question: str) -> list[float]: ...


class DynamicPoolEmbedder:
    def __init__(self) -> None:
        self.clients_pool = queue.Queue()
        self.active_keys_count = 0
        self.provider = None
        self._initialize_pool()

    def _initialize_pool(self):
        print("Scanning OpenRouter API keys...")
        try:
            from openai import OpenAI
        except ImportError:
            OpenAI = None

        # 1. Scan OpenRouter first
        or_keys = [val for key, val in os.environ.items() if key.startswith("OPENROUTER_KEY_")]
        if OpenAI and or_keys:
            for idx, key in enumerate(or_keys):
                try:
                    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
                    client.embeddings.create(input="test", model="openai/text-embedding-3-small")
                    self.clients_pool.put((f"OR_Key_{idx+1}", client))
                    self.active_keys_count += 1
                    print(f"  OpenRouter Key {idx+1} ALIVE.")
                except Exception as e:
                    print(f"  OpenRouter Key {idx+1} DEAD. ({str(e)[:80]})")

        if self.active_keys_count > 0:
            self.provider = "openrouter"
            self.model_name = "openai/text-embedding-3-small"
            self.dimensions = 1536
            print(f"Selected OpenRouter provider with {self.active_keys_count} keys!\n")
            return

        # 2. If OpenRouter all dead, scan Gemini
        print("OpenRouter all dead. Switching to Gemini...")
        try:
            import google.generativeai as genai
        except ImportError:
            print("[!] Missing google-generativeai library. Cannot use Gemini.")
            sys.exit(1)

        gemini_keys = [val for key, val in os.environ.items() if key.startswith("GEMINI_KEY_")]
        for idx, key in enumerate(gemini_keys):
            try:
                genai.configure(api_key=key)
                res = genai.embed_content(model="models/embedding-001", content="test", task_type="retrieval_document")
                _ = res["embedding"]
                self.clients_pool.put((f"Gemini_Key_{idx+1}", key))
                self.active_keys_count += 1
                print(f"  Gemini Key {idx+1} ALIVE.")
            except Exception as e:
                print(f"  Gemini Key {idx+1} DEAD. ({str(e)[:80]})")

        if self.active_keys_count > 0:
            self.provider = "gemini"
            self.model_name = "models/embedding-001"
            self.dimensions = 768
            print(f"Selected Gemini provider with {self.active_keys_count} keys! (model: {self.model_name})\n")
            return

        print("[!] CRITICAL ERROR: All API keys (OpenRouter and Gemini) are dead!")
        sys.exit(1)

    def _embed_batch(self, key_name, client_or_key, texts):
        """Embed a batch of texts using the pooled client/key."""
        if self.provider == "openrouter":
            # OpenAI SDK may not accept list input in some versions; embed one by one
            vectors = []
            for t in texts:
                res = client_or_key.embeddings.create(input=t, model=self.model_name)
                vectors.append(list(res.data[0].embedding))
            return vectors
        else:
            import google.generativeai as genai
            genai.configure(api_key=client_or_key)
            res = genai.embed_content(model=self.model_name, contents=texts, task_type="retrieval_document")
            return [list(e) for e in res["embedding"]]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        total = len(texts)
        results = [None] * total
        BATCH = 5  # gui 5 chunks len 1 lenh API de giam so lan goi

        print(f"Embedding {total} chunks using {self.provider.upper()} (batch={BATCH}, 1 thread)...")
        for batch_start in range(0, total, BATCH):
            batch_end = min(batch_start + BATCH, total)
            batch_texts = texts[batch_start:batch_end]
            key_name, client_or_key = self.clients_pool.get()
            try:
                vectors = self._embed_batch(key_name, client_or_key, batch_texts)
                self.clients_pool.put((key_name, client_or_key))
                for i, v in enumerate(vectors):
                    results[batch_start + i] = v
                print(f"     Progress: {batch_end}/{total} chunks done", end="\r")
                if self.provider == "gemini":
                    time.sleep(0.5)  # tranh rate limit Gemini

            except Exception as e:
                print(f"\n[WARNING] {key_name} error at batch {batch_start}-{batch_end}: {e}")
                self.clients_pool.put((key_name, client_or_key))
                time.sleep(1)
                # fallback: mark as zero vectors
                for j in range(batch_start, batch_end):
                    results[j] = [0.0] * self.dimensions

        print("\nEmbedding complete!")
        return results

    def embed_query(self, question: str) -> list[float]:
        key_name, client_or_key = self.clients_pool.get()
        try:
            if self.provider == "openrouter":
                res = client_or_key.embeddings.create(input=question, model=self.model_name)
                vector = res.data[0].embedding
            else:
                import google.generativeai as genai
                genai.configure(api_key=client_or_key)
                res = genai.embed_content(model=self.model_name, content=question, task_type="retrieval_query")
                vector = res["embedding"]

            self.clients_pool.put((key_name, client_or_key))
            return list(vector)
        except Exception as e:
            print(f"\n[!] QUERY EMBEDDING ERROR: {e}")
            sys.exit(1)
