import json
import numpy as np
from sentence_transformers import SentenceTransformer   

INPUT_FILE = "papers_summarized.json"
EMBEDDINGS_FILE = "embeddings.npy"
EMBEDDING_IDS_FILE  = "embedding_ids.json"

MODEL_NAME = "sentence-transformers/allenai-specter" # A model for scientific text embeddings

BATCH_SIZE = 16  # Number of abstracts to process in each batch

# Load Papers
def load_papers(path:str) -> list[dict]:
    with open(path) as f:
        return json.load(f)
    
# Build SPECTER's expected input format
def build_specter_input(paper: dict, sep_token: str) -> str:
    title = " ".join(paper["title"].split())  # collapse whitespace
    abstract = " ".join(paper["abstract"].split())  # collapse whitespace
    return f"{title} {sep_token} {abstract}"

# Embed abstracts in batches

def embed_all(papers: list[dict]) -> np.ndarray:
    print(f" Loading embedding model '{MODEL_NAME}' (first run downloads the model)...")
    model = SentenceTransformer(MODEL_NAME)
    sep_token = model.tokenizer.sep_token  # Get the model's separator token

    texts = [build_specter_input(p, sep_token) for p in papers]
    print(f"Embedding {len(texts)} papers in batches of {BATCH_SIZE}...")
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    return embeddings

# Entry point:

if __name__ == "__main__":
    papers = load_papers(INPUT_FILE)
    embeddings = embed_all(papers)

    np.save(EMBEDDINGS_FILE, embeddings)

    arxiv_ids = [p["arxiv_id"] for p in papers]
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