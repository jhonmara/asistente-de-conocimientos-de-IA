import os
import json
from typing import List, Dict, Any, Optional
import numpy as np

try:
    import faiss
except ImportError:  # pragma: no cover
    faiss = None

from openai import OpenAI

class VectorStore:
    def __init__(self, embed_model: str = "text-embedding-3-small", persist_dir: str = "./data"):
        self.embed_model = embed_model
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        self.index_path = os.path.join(self.persist_dir, "index.faiss")
        self.meta_path = os.path.join(self.persist_dir, "meta.jsonl")
        self.client = None
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)

        self.dim = 1536  # default for text-embedding-3-small
        self.index = None
        if faiss is not None:
            self.index = faiss.IndexFlatIP(self.dim)
            if os.path.exists(self.index_path):
                try:
                    self.index = faiss.read_index(self.index_path)
                except Exception:
                    pass

    def _embed(self, texts: List[str]) -> np.ndarray:
        if self.client is None:
            # fallback: random but deterministic embeddings (for demo)
            rng = np.random.default_rng(42)
            return rng.random((len(texts), self.dim), dtype=np.float32)
        resp = self.client.embeddings.create(model=self.embed_model, input=texts)
        vecs = np.array([d.embedding for d in resp.data], dtype=np.float32)
        return vecs

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None):
        if not texts:
            return 0
        if metadatas is None:
            metadatas = [{} for _ in texts]
        embs = self._embed(texts)
        if faiss is None:
            # No FAISS: store in a JSONL file only
            with open(self.meta_path, "a", encoding="utf-8") as fh:
                for t, m, e in zip(texts, metadatas, embs.tolist()):
                    rec = {"text": t, "metadata": m, "embedding": e}
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return len(texts)
        # FAISS path
        self.index.add(embs)
        with open(self.meta_path, "a", encoding="utf-8") as fh:
            for t, m in zip(texts, metadatas):
                rec = {"text": t, "metadata": m}
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        faiss.write_index(self.index, self.index_path)
        return len(texts)

    def search(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        if not query:
            return []
        qvec = self._embed([query])
        if faiss is None or self.index is None or (hasattr(self.index, 'ntotal') and self.index.ntotal == 0):
            # brute-force over JSONL
            if not os.path.exists(self.meta_path):
                return []
            records = []
            with open(self.meta_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    rec = json.loads(line)
                    if "embedding" in rec:
                        sim = float(np.dot(qvec[0], np.array(rec["embedding"], dtype=np.float32)))
                    else:
                        sim = 0.0
                    records.append((sim, rec))
            records.sort(key=lambda x: x[0], reverse=True)
            return [r[1] for r in records[:k]]

        # FAISS search
        D, I = self.index.search(qvec, k)
        # read meta lines
        metas = []
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as fh:
                metas = [json.loads(l) for l in fh if l.strip()]
        out = []
        for idx in I[0]:
            if idx < 0 or idx >= len(metas):
                continue
            out.append(metas[idx] | {"score": float(D[0][len(out)])})
        return out
