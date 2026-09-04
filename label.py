import csv
import json
import os
from datetime import datetime, timezone

INPUT_FILE = "papers_summarized.json"
LABELS_FILE = "labels.csv"

CSV_FIELDS = ["arxiv_id", "title", "link", "label", "labeled_at"]

DETAIL_MODEL_NAME = "google/flan-t5-base"   # Model for generating detailed summaries
DETAIL_MAX_TOKENS = 150  # Max tokens for detailed summary

# Cache so the model loads at most once per session, not once per "d"/"r" press
_detail_tokenizer = None
_detail_model = None  

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

def _ensure_detail_model_loaded() -> None:
    # Loads Flan-T5 for first time it's needed and caches it in modeule
    global _detail_tokenizer, _detail_model
    if _detail_model is not None:
        return
    
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    print(f" (loading {DETAIL_MODEL_NAME} for detailed summaries - first run downloads ~1GB)...")
    _detail_tokenizer = AutoTokenizer.from_pretrained(DETAIL_MODEL_NAME)
    _detail_model = AutoModelForSeq2SeqLM.from_pretrained(DETAIL_MODEL_NAME)

def _generate_with_flan(prompt: str) -> str:   
    _ensure_detail_model_loaded()
    inputs = _detail_tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
    output_ids = _detail_model.generate(**inputs, max_length=DETAIL_MAX_TOKENS, num_beams=4, early_stopping=True)
    return _detail_tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()

def explain_simply(abstracts: str) -> str:
    # Generates a simple explanation of the abstract using Flan-T5
    from summarize import clean_latex
    cleaned = clean_latex(abstracts)
    prompt = (
        "Explain the following physics research abstract in 2-4 plain-language "
        "sentences for a physicist working in a different subfield. Keep the "
        "explanation scientifically accurate and preserve the key physical "
        "meaning, but avoid unnecessary technical jargon.\n\n"
        f"Abstract: {cleaned}\n\n"
        "Plain-language explanation:"
    )
    return _generate_with_flan(prompt)

def explain_result(abstracts: str) -> str:
    # Plain-language explanation for results
    from summarize import clean_latex
    cleaned = clean_latex(abstracts)
    prompt = ("Read the following physics research abstract. In 2-3 plain-language "
        "sentences, explain specifically what the key result or finding was — "
        "not the background, motivation, or methodology. Avoid unnecessary "
        "technical jargon.\n\n"
        f"Abstract: {cleaned}\n\n"
        "Key result:")
    
    return _generate_with_flan(prompt)

# Interactive labeling loop:

_LABEL_DESCRIPTIONS = {"1": "relevant", "0": "not relevant"}

def prompt_for_label(paper: dict, current_label: str | None) -> str | None:
    """
    
    Shows one paper and asks for a relevance judgement.
    Returns "1" or "0" for a real answer, "skip" to leave it unlabeled,
    "back" to move to previous paper, or "quit" to exit the session.

    "d" and "r" don't return, they print a detailed summary or result explanation and re-prompt for label.
    """

    print("\n" + "="*70)
    print(f"Title:    {paper['title']}")
    print(f"Category: {paper.get('category', paper.get('categories', 'unknown'))}")
    print(f"Summary:  {paper['short_description']}")
    print(f"Link:     {paper['link']}")
    if current_label is not None:
        print(f"Current label: {_LABEL_DESCRIPTIONS.get(current_label, 'unknown')} - answering again will change this.")
    print("="*70)


    while True:
        answer = input("Interested? (y/n/s(kip)/b(ack)/q(uit)/d(etail)/r(esult)): ").strip().lower()
        if answer in ("y", "yes", "ye"):
            return "1"
        elif answer in ("n", "no"):
            return "0"
        elif answer in ("s", "skip"):
            return "skip"
        elif answer in ("b", "back"):
            return "back"
        elif answer in ("q", "quit"):
            return None
        elif answer in ("d", "detail"):
            explanation = explain_simply(paper["abstract"])
            print("\n--- Detailed Explanation ---")
            print(f"\n Plain-language explanation: {explanation}\n")
        elif answer in ("r", "result"):
            explanation = explain_result(paper["abstract"])
            print("\n--- Key Result Explanation ---")
            print(f"\n Key result: {explanation}\n")

        else: 
            print(" Did'nt catch that - please enter 'y', 'n', 's', 'b', 'q', 'd', or 'r'.")

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