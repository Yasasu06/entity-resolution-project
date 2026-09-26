"""Embedding the source records, and ranking candidates by similarity.

The component-swap experiment (docs/PRE_REGISTRATION.md section 11) keeps the
classical candidate set and replaces only the matcher. That makes one detail
load bearing: the shortlist shown to the language model must **not** be ranked
by the classical match weight, or the model inherits the classical ranking and
is tested on re-ranking a shortlist the classical system already chose.

Ranking is therefore done here, by cosine similarity over embeddings of the
whole record. The classical system supplies the set; this supplies the order.

Nothing here reads labelled data.

Run with ``python -m src.embeddings``.
"""

import json

import numpy as np
import pandas as pd

from src.ai_escalation import require_api_key
from src.data_loading import attribute_columns, load_source_tables
from src.interfaces import LEFT_ID, PROCESSED_DIR, RIGHT_ID, load_candidates

# Fixed in section 11.3. 3-large at 1,024 dimensions: the full 3,072 buys little
# on records this short and triples the memory for the similarity pass.
EMBED_MODEL = "text-embedding-3-large"
EMBED_DIMS = 1024
BATCH = 256

SHORTLIST = 30                      # candidates shown per record (section 11.3)
EMBED_PATH = PROCESSED_DIR / "embeddings.npz"
SHORTLIST_PATH = PROCESSED_DIR / "shortlists.json"


def record_text(row: pd.Series, columns: list[str]) -> str:
    """One string per record, every attribute, in a stable order."""
    return " | ".join(f"{c}: {row[c]}" for c in columns if pd.notna(row[c]))


def embed_all(texts: list[str], client) -> np.ndarray:
    """Embed in batches, L2-normalised so a dot product is the cosine."""
    out = []
    for i in range(0, len(texts), BATCH):
        chunk = texts[i:i + BATCH]
        resp = client.embeddings.create(model=EMBED_MODEL, input=chunk,
                                        dimensions=EMBED_DIMS)
        out.extend(d.embedding for d in resp.data)
        print(f"    embedded {min(i + BATCH, len(texts)):>6,} / {len(texts):,}", flush=True)
    m = np.asarray(out, dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def build_shortlists(
    candidates: pd.DataFrame, ids_a: list[str], ids_b: list[str],
    emb_a: np.ndarray, emb_b: np.ndarray, k: int = SHORTLIST,
) -> dict[str, list[str]]:
    """Top-k candidates per Walmart record, ranked by cosine similarity.

    Only pairs already in the classical candidate set are considered: this
    re-ranks, it does not retrieve.
    """
    ix_a = {v: i for i, v in enumerate(ids_a)}
    ix_b = {v: i for i, v in enumerate(ids_b)}
    shortlists: dict[str, list[str]] = {}
    for left, group in candidates.groupby(LEFT_ID):
        rights = group[RIGHT_ID].tolist()
        rows = np.array([ix_b[r] for r in rights])
        sims = emb_b[rows] @ emb_a[ix_a[left]]
        order = np.argsort(-sims)[:k]
        shortlists[left] = [rights[i] for i in order]
    return shortlists


def main() -> None:
    require_api_key()
    from openai import OpenAI
    client = OpenAI()

    table_a, table_b = load_source_tables()
    columns = attribute_columns(table_a)
    print(f"embedding {len(table_a):,} + {len(table_b):,} records with {EMBED_MODEL}")
    emb_a = embed_all([record_text(r, columns) for _, r in table_a.iterrows()], client)
    emb_b = embed_all([record_text(r, columns) for _, r in table_b.iterrows()], client)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(EMBED_PATH, a=emb_a, b=emb_b,
                        ids_a=table_a["unique_id"].to_numpy(),
                        ids_b=table_b["unique_id"].to_numpy())

    candidates = load_candidates("classical")
    shortlists = build_shortlists(candidates, table_a["unique_id"].tolist(),
                                  table_b["unique_id"].tolist(), emb_a, emb_b)
    SHORTLIST_PATH.write_text(json.dumps(shortlists))

    sizes = [len(v) for v in shortlists.values()]
    print(f"\n  embeddings written to  {EMBED_PATH.name}")
    print(f"  shortlists written to  {SHORTLIST_PATH.name}")
    print(f"  records: {len(shortlists):,}   shortlist size: "
          f"median {int(np.median(sizes))}, max {max(sizes)}")


if __name__ == "__main__":
    main()
