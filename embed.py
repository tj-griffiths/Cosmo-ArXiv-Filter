import json
import os
import numpy as np
from tqdm.std import TqdmDefaultWriteLock
from sentence_transformers import SentenceTransformer   

import logging
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

# Disable tqdm's multiprocessing lock to avoid hanging in some environments
def _noop_create_mp_lock(cls):
    if not hasattr(cls, "mp_lock"):
        cls.mp_lock = None
TqdmDefaultWriteLock.create_mp_lock = classmethod(_noop_create_mp_lock)

INPUT_FILE = "papers_summarized.json"
EMBEDDINGS_FILE = "embeddings.npy"
EMBEDDING_IDS_FILE  = "embedding_ids.json"

MODEL_NAME = "sentence-transformers/allenai-specter" # A model for scientific text embeddings

BATCH_SIZE = 16  # Number of abstracts to process in each batch

# Load Papers
def load_papers(path:str) -> list[dict]:
    with open(path) as f:
        return json.load(f)
    
# Load existing embeddings and their corresponding arXiv IDs if they exist
def load_existing_embeddings() -> tuple[np.ndarray | None, list[str]]:
    if not (os.path.exists(EMBEDDINGS_FILE) and os.path.exists(EMBEDDING_IDS_FILE)):
        return None, []
    try:
        embeddings = np.load(EMBEDDINGS_FILE)
        with open(EMBEDDING_IDS_FILE) as f:
            ids = json.load(f)
    except (EOFError, ValueError, OSError, json.JSONDecodeError) as e:
        print(f"Warning: exiting embeddings file looks corrupted ({e}) - starting fresh.")
        return None, []
    return embeddings, ids
    
# Build SPECTER's expected input format
def build_specter_input(paper: dict, sep_token: str) -> str:
    title = " ".join(paper["title"].split())  # collapse whitespace
    abstract = " ".join(paper["abstract"].split())  # collapse whitespace
    return f"{title} {sep_token} {abstract}"

# Embed abstracts in batches

def embed_all(papers: list[dict], show_progress: bool = True) -> np.ndarray:
    print(f" Loading embedding model '{MODEL_NAME}' (first run downloads the model)...")
    model = SentenceTransformer(MODEL_NAME)
    sep_token = model.tokenizer.sep_token  # Get the model's separator token

    texts = [build_specter_input(p, sep_token) for p in papers]
    print(f"Embedding {len(texts)} papers in batches of {BATCH_SIZE}...")
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=show_progress,
        convert_to_numpy=True
    )

    return embeddings

# Entry point:

if __name__ == "__main__":
    papers = load_papers(INPUT_FILE)

    existing_embeddings, existing_ids = load_existing_embeddings()
    existing_ids_set = set(existing_ids)
    new_papers = [p for p in papers if p["arxiv_id"] not in existing_ids_set]

    if not new_papers:
        print("No new papers to embed - all papers already have embeddings.")
    else:
        new_embeddings = embed_all(new_papers)
        if existing_embeddings is not None:
            embeddings = np.concatenate([existing_embeddings, new_embeddings])
            arxiv_ids = existing_ids + [p["arxiv_id"] for p in new_papers]
        else:
            embeddings = new_embeddings
            arxiv_ids = [p["arxiv_id"] for p in new_papers]

        np.save(EMBEDDINGS_FILE, embeddings)
        with open(EMBEDDING_IDS_FILE, "w") as f:
            json.dump(arxiv_ids, f, indent=2)

        print(f"\nSaved {embeddings.shape[0]} embeddings of dimension {embeddings.shape[1]} to {EMBEDDINGS_FILE}.")
        print(f"Saved matching arXiv IDs to {EMBEDDING_IDS_FILE}.")

        # Quick Sanity Check:
        if len(papers) > 1:
            norms = embeddings/ np.linalg.norm(embeddings, axis=1, keepdims=True)
            similarities = norms @ norms[0]
            similarities[0] = -1
            nearest_idx = int(np.argmax(similarities))

            print(f"\n--- Nearest Neighbor Check ---")
            print(f"Query Paper: {papers[0]['title']}")
            print(f"Nearest Neighbor: {papers[nearest_idx]['title']}")
            print(f"Cosine Sim: {round(float(similarities[nearest_idx]), 3)}")