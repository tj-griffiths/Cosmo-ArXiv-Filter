# Trains the classifier on the labels

import csv
import json
import pickle

import numpy as np
from sklearn.linear_model import LogisticRegression
# Uses logistic regression as it can learn from the few labeled examples fast

from sklearn.model_selection import cross_val_score

from label import goal_already_met

EMBEDDINGS_FILE = "embeddings.npy"
EMBEDDINGS_IDS_FILE = "embedding_ids.json"
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
    for row in labels:
        embedding = embeddings_by_id.get(row["arxiv_id"])
        if embedding is not None:
            X.append(embedding)
            y.append(int(row["label"]))
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
    else:
        cv_folds = min(5, n_relevant, n_total - n_relevant)
        scores = cross_val_score(LogisticRegression(max_iter=1000, class_weight = 'balanced'), X, y, cv=cv_folds)
        print(f"Cross-validated accuracy: {scores.mean():.2f} (+/- {scores.std():.2f}) over {cv_folds} folds")
    clf = LogisticRegression(max_iter=1000, class_weight = 'balanced')
    clf.fit(X,y)
    return clf

def matching_keywords(paper: dict, preferred_keywords: dict[str, list[str]]) -> list[str]:
    if not preferred_keywords:
        return []
    paper_categories = [c.strip() for c in paper.get("categories", "unknown").split(",")]
    candidate_keywords: set[str] = set()
    for category in paper_categories:
        candidate_keywords.update(preferred_keywords.get(category, []))
    if not candidate_keywords:
        return []
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    return sorted(kw for kw in candidate_keywords if kw.lower() in text)


def _keyword_boost(paper: dict, preferred_keywords: dict[str, list[str]], boost_per_match: float = 0.01) -> float:
    return boost_per_match * len(matching_keywords(paper, preferred_keywords))

# Score every paper

def score_all_papers(clf: LogisticRegression, embeddings_by_ids: dict, papers: list[dict], preferred_keywords: dict[str, list[str]] | None = None) -> list[tuple[float, dict]]:
    scored = []
    apply_boost = not goal_already_met()
    for paper in papers:
        embeddings = embeddings_by_ids.get(paper["arxiv_id"])
        if embeddings is None:
            continue
        relevance_score = clf.predict_proba([embeddings])[0][1]
        if apply_boost:
            relevance_score = min(1.0, relevance_score + _keyword_boost(paper, preferred_keywords or {}))
        scored.append((relevance_score, paper))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored

def cross_val_accuracy(X: np.ndarray, y: np.ndarray) -> float | None:
    n_total = len(y)
    if n_total < MIN_LABELS_FOR_CV or len(set(y)) < 2:
        return None
    n_relevant = int(y.sum())
    cv_folds = min(5, n_relevant, n_total - n_relevant)
    if cv_folds < 2:
        return None
    scores = cross_val_score(LogisticRegression(max_iter=1000, class_weight='balanced'), X, y, cv=cv_folds)
    return float(scores.mean())

# Adds Uncertainty Selection

def select_most_uncertain(embeddings_by_id: dict, papers: list[dict], labeled_ids: set, clf: LogisticRegression, n: int = 5) -> list[tuple[float, dict]]:
    scored = []
    for paper in papers:
        if paper["arxiv_id"] in labeled_ids:
            continue
        embedding = embeddings_by_id.get(paper["arxiv_id"])
        if embedding is None:
            continue
        score = clf.predict_proba([embedding])[0][1]
        uncertainty = abs(score - 0.5)
        scored.append((uncertainty, score, paper))
    scored.sort(key=lambda triple: triple[0])  # Sort by uncertainty (lowest first) 
    return [(score, paper) for _, score, paper in scored[:n]]

# Entry Point

if __name__ == "__main__":
    embeddings_by_id = load_embeddings()
    labels = load_labels()
    X, y = build_training_set(embeddings_by_id, labels)

    if len(y) == 0:
        print("No labeled papers found. Please label some papers first.")
        raise SystemExit(1)
    
    clf = train_and_evaluate(X, y)

    if clf is None:
        print("Not enough data to save a classifier yet - nothing else to do this run.")
        raise SystemExit(0)

    with open(MODEL_FILE, "wb") as f:
        pickle.dump(clf, f)
    print(f"Saved trained classifier to {MODEL_FILE}.")

    with open(PAPERS_FILE) as f:
        papers = json.load(f)

    scored_papers = score_all_papers(clf, embeddings_by_id, papers)
    print(f"\nScored {len(scored_papers)} papers from {PAPERS_FILE}. Top 10 papers by relevance score:")
    for score, paper in scored_papers[:10]:
        print(f"{score:.2f} - {paper['title']}")

