# Trains the classifier on the labels

import json

from classify import(
    load_embeddings,
    load_labels,
    build_training_set,
    train_and_evaluate,
    score_all_papers
)

from label import run_labeling_session

PAPERS_FILE = "papers_summarized.json"

# How many of the top-ranked papers to show for labeling in each session
TOP_N = 20

def load_papers(path: str) -> list[dict]:
    with open(path) as f:
        return json.load(f)
    
if __name__ == "__main__":
    embeddings_by_id = load_embeddings() 
    labels = load_labels()
    X, y = build_training_set(embeddings_by_id, labels)

    if len(y) == 0:
        print("No labeled papers yet - run label.py first.")
        raise SystemExit(1)
    
    clf = train_and_evaluate(X, y)
    if clf is None:
        print("Not enough data to train a classifier yet - run label.py first.")
        raise SystemExit(0)
    
    papers = load_papers(PAPERS_FILE)
    scored_papers = score_all_papers(clf, embeddings_by_id, papers)

    already_labeled_ids = {r["arxiv_id"] for r in labels}
    candidates = [(score, paper) for score, paper in scored_papers if paper["arxiv_id"] not in already_labeled_ids][:TOP_N]

    if not candidates:
        print("No new papers to label - all top-ranked papers have already been labeled.")
        raise SystemExit(0)
    
    print(
        f"\nReviewing the top {len(candidates)} unlabeled papers by predicted "
        f"relevance (out of {len(scored_papers)} scored):"
    )

    scores_by_id = {paper["arxiv_id"]: score for score, paper in candidates}
    papers_to_review = [paper for _, paper in candidates]

    run_labeling_session(papers_to_review, scores_by_id)

