# Trains the classifier on the labels

import csv
import json
import pickle

import numpy as np
from sklearn.linear_model import LogisticRegression
# Uses logistic regression as it can learn from the few labeled examples fast

from sklearn.model_selection import cross_val_score

EMBEDDINGS_FILE = "embeddings.npy"
EMBEDDINGS_IDS_FILE = "embeddings_ids.json"
LABELS_FILE = "labels.csv"
PAPERS_FILE = "papers_raw.json"
MODEL_FILE = "classifier.pkl"

# Minimum number of labels required to train the classifier and save it to a file
MIN_LABELS_FOR_CV = 15

# Load embeddings and labels, match them by arXiv ID

def load_embeddings() -> dict[str, np.ndarray]:
    embeddings = np.load(EMBEDDINGS_FILE)
    with open(EMBEDDINGS_IDS_FILE) as f:
        ids = json.load(f)
    return dict(zip(ids, embeddings))

def load_labels() -> list[dict]:
    with open(LABELS_FILE, newline="") as f:
        return list(csv.DictReader(f))
    
def build_training_set(embeddings_by_id: dict, labels: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    X = []
    y = []
    for label in labels:
        embedding = embeddings_by_id.get(label["arxiv_id"])
        if embedding is not None:
            X.append(embedding)
            y.append(label["label"])
    return np.array(X), np.array(y)

# Train the classifier and save it to a file

def train_and_evaluate(X: np.ndarray, y: np.ndarray) -> LogisticRegression:
    n_relevant = int(y.sum())
    n_total = len(y)

    print(f"Training classifier on {n_total} labeled papers ({n_relevant} relevant, {n_total - n_relevant} irrelevant).")

    if n_total < 5:
        print("Not enough labeled papers to train a classifier. Need at least 5.")
        return None
    
    elif len(set(y)) < 2:
        print("Not enough diversity in labels to train a classifier. Need at least one relevant and one irrelevant paper.")
        return None
    
    elif n_total < MIN_LABELS_FOR_CV:
        print(f"Fewer than {MIN_LABELS_FOR_CV} labels — skipping cross-validation (too few for a stable estimate).")
        cv_folds = min(5, n_relevant, n_total - n_relevant)
        scores = cross_val_score(LogisticRegression(max_iter=1000, class_weight = 'balanced'), X, y, cv=cv_folds)
        print(f"Cross-validated accuracy: {scores.mean():.2f} (+/- {scores.std():.2f}) over {cv_folds} folds")
        clf = LogisticRegression(max_iter=1000, class_weight = 'balanced')
        clf.fit(X,y)
        return clf

# Score every paper

def score_all_papers(clf: LogisticRegression, embeddings_by_ids: dict, papers: list[dict]) -> list[tuple[float, dict]]:
    scored = []
    for paper in papers:
        embeddings = embeddings_by_ids.get(paper["arxiv_id"])
        if embeddings is None:
            continue
        relevance_score = clf.predict_proba([embeddings])[0][1] # Probability of being relevant
        scored.append((relevance_score, paper))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored

# Entry Point

if __name__ == "__main__":
    embeddings_by_id = load_embeddings()
    labels = load_labels()
    X, y = build_training_set(embeddings_by_id, labels)

    if len(y) == 0:
        print("No labeled papers found. Please label some papers first.")
        raise SystemExit(1)
    
    clf = train_and_evaluate(X, y)

    with open(MODEL_FILE, "wb") as f:
        pickle.dump(clf, f)
    print(f"Saved trained classifier to {MODEL_FILE}.")

    with open(PAPERS_FILE) as f:
        papers = json.load(f)

    scored_papers = score_all_papers(clf, embeddings_by_id, papers)
    print(f"\nScored {len(scored_papers)} papers from {PAPERS_FILE}. Top 10 papers by relevance score:")
    for score, paper in scored_papers[:10]:
        print(f"{score:.2f} - {paper['title']}")



        