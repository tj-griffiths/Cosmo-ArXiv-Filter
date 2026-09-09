# Sets up interactive command-line tool for building labels.csv for each paper

import csv
import json
import os
from datetime import datetime, timezone

from api import generate as generate_with_api

INPUT_FILE = "papers_summarized.json"
LABELS_FILE = "labels.csv"

CSV_FIELDS = ["arxiv_id", "title", "link", "label", "labeled_at"]

# Load papers

def load_papers(path: str) -> list[dict]:
    with open(path) as f:
        return json.load(f)
    
    # Load labeled arXiv IDs from labels.csv
def load_all_labels(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))
    
def write_labels(path: str, records: list[dict]) -> None:
    # Overwrites labels.csv with exactly the given records (Used instead of append-only)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)


def explain_simply(abstract: str) -> str:
    # Generates a simple explanation of the abstract using Groq API
    from text_utils import clean_latex
    cleaned = clean_latex(abstract)
    prompt = (
        "Explain the following physics research abstract to a curious "
        "non-expert. In 3-5 simple sentences, cover: what problem or "
        "question the researchers were addressing, what they actually "
        "built or found, and why it matters.\n\n"
        f"Abstract: {cleaned}"
    )
    return generate_with_api(prompt)

def explain_result(abstract: str) -> str:
    # Generates a plain-language explanation of the results using Groq API
    from text_utils import clean_latex
    cleaned = clean_latex(abstract)
    prompt = (
        "Explain the key result of the following physics research abstract "
        "to a curious non-expert. In 2-3 simple sentences, cover: what "
        "specifically they found (not the background or method), and why "
        "that result matters.\n\n"
        f"Abstract: {cleaned}"
    )
    return generate_with_api(prompt)

_LABEL_DESCRIPTIONS = {"1": "relevant", "0": "not relevant"}

def prompt_for_label(paper: dict, current_label: str | None) -> str | None:
    """
    
    Shows one paper and asks for a relevance judgement.
    Returns "1" or "0" for a real answer, "skip" to leave it unlabeled,
    "back" to move to previous paper, or "quit" to exit the session.

    "d" and "r" don't return, they print a detailed summary or result explanation and re-prompt for label.
    """

    detail_text: str | None = None
    result_text: str | None = None

    def render() -> None:
        print("\n" + "="*70)
        print(f"Title:    {paper['title']}")
        print(f"Category: {paper.get('category', paper.get('categories', 'unknown'))}")
        print(f"Summary:  {paper['short_description']}")
        print(f"Link:     {paper['link']}")
        if current_label is not None:
            print(f"Current label: {_LABEL_DESCRIPTIONS.get(current_label, 'unknown')} - answering again will change this.")
        print("="*70)
    render()

    while True:
        answer = input("Interested? (y/n/s(kip)/b(ack)/q(uit)/d(etail)/r(esult)): ").strip().lower()
        if answer in ("y", "yes", "ye"):
            return "1"
        elif answer in ("n", "no"):
            return "0"
        elif answer in ("d", "detail"):
            if detail_text is None:
                detail_text = explain_simply(paper["abstract"])
            print(f"\n Detail Explanation: {detail_text}\n")
        elif answer in ("r", "result"):
            if result_text is None:
                result_text = explain_result(paper["abstract"])
            print(f"\n Result Explanation: {result_text}\n")
        elif answer in ("s", "skip"):
            return "skip"
        elif answer in ("b", "back"):
            return "back"
        elif answer in ("q", "quit"):
            return None

        else: 
            print(" Didn't catch that - please enter 'y', 'n', 's', 'b', 'q', 'd', or 'r'.")

def run_labeling_session(papers: list[dict]) -> None:
    pre_existing = load_all_labels(LABELS_FILE)
    pre_existing_ids = {r["arxiv_id"]: r for r in pre_existing}

    unlabeled = [p for p in papers if p["arxiv_id"] not in pre_existing_ids]
    print(f"{len(unlabeled)} unlabeled papers out of {len(papers)} total.")
    if not unlabeled:
        print("Nothing left to label in this file - nice work.")
        return
    
    # Keyed by arxiv_id so relabeling a paper (via "back") overwrites
    session_decision: dict[str, str] = {}

    def flush() -> None:
        write_labels(LABELS_FILE, pre_existing + list(session_decision.values()))

    i = 0
    while i < len(unlabeled):
        paper = unlabeled[i]
        existing = session_decision.get(paper["arxiv_id"])
        current_label = existing["label"] if existing else None
        answer = prompt_for_label(paper, current_label)

        if answer is None: #quit
            break
        if answer == "back":
            if i == 0:
                print(" Already at first paper - can't go back.")
            else:
                i -= 1
            continue

        if answer == "skip":
            session_decision.pop(paper["arxiv_id"], None)  # Remove any existing decision for this paper
            flush()
            i += 1
            continue

        session_decision[paper["arxiv_id"]] = {
            "arxiv_id": paper["arxiv_id"],
            "title": paper["title"],
            "link": paper["link"],
            "label": answer,
            "labeled_at": datetime.now(timezone.utc).isoformat()
        }
        flush()
        i += 1

    session_count = len(session_decision)
    session_positive = sum(1 for d in session_decision.values() if d["label"] == "1")
    print(f"\nSession complete: {session_count} papers labeled, {session_positive} positive.")


# Entry

if __name__ == "__main__":
    papers = load_papers(INPUT_FILE)
    run_labeling_session(papers)

    # Report overall progress across all sessions:
    all_rows = load_all_labels(LABELS_FILE)
    positive = sum(1 for row in all_rows if row["label"] == "1")
    negative = sum(1 for row in all_rows if row["label"] == "0")

    print(f"Total papers labeled: {len(all_rows)} (positive: {positive}, negative: {negative})")