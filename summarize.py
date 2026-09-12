import json
import re
import torch

from tqdm.std import TqdmDefaultWriteLock
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from text_utils import clean_latex
from transformers.utils import logging as hf_logging
hf_logging.disable_progress_bar()

import logging
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

# Disable tqdm's multiprocessing lock to avoid hanging in some environments
def _noop_create_mp_lock(cls):
    if not hasattr(cls, "mp_lock"):
        cls.mp_lock = None
TqdmDefaultWriteLock.create_mp_lock = classmethod(_noop_create_mp_lock)

"""
HOW THE TRANSFORMERS PIPELINE WORKS
    `pipeline("summarization", model=...)` bundles three things:
    tokenizer (text -> token ids), model (token ids -> token ids), and
    post-processing (token ids -> text) into one callable. It supports
    passing a LIST of texts at once, which batches them for much faster
    throughput than calling it once per paper in a loop.
"""

INPUT_FILE = "papers_raw.json"
OUTPUT_FILE = "papers_summarized.json"

MODEL_NAME = "sshleifer/distilbart-cnn-6-6"
"""
MODEL CHOICE: sshleifer/distilbart-cnn-6-6
    Caveat worth knowing:
    this model was fine-tuned on CNN/DailyMail *news* summarization, not
    scientific abstracts, so it summarizes a summary that's already
    dense and jargon-heavy. It will work, but a natural next iteration
    for this project is fine-tuning a small seq2seq model on a
    scientific-abstract summarization dataset (e.g. SciTLDR) instead of
    relying on an off-the-shelf news summarizer.
"""

# MODEL_NAME = "google/pegasus-arxiv"
# """
# MODEL CHOICE: google/pegasus-arxiv
#     Trained specifically on arXiv paper summarization, so it should
#     handle scientific vocabulary and structure far better than a
#     news-tuned model. Caveat: it was trained on full-paper-to-abstract
#     summarization, not abstract-to-one-liner compression, so output
#     length/shape may behave a bit differently than DistilBART.
# """

MAX_SUMMARY_TOKENS = 100
MIN_SUMMARY_TOKENS = 5
MAX_INPUT_TOKENS = 1024

# Load papers:
def load_papers(path:str) -> list[dict]:
    with open(path) as f:
        return json.load(f)
    

def clean_summary_text(text: str) -> str:
    # Fixes stray spaces before punctuations and cut-off mid-word endings

    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = " ".join(text.split())  # collapse whitespace

    if text:
        text = text[0].upper() + text[1:]  # capitalize first letter

    if text and (text[-1] not in ".!?" or not _parens_balanced(text)):
        candidate_positions = sorted(
            (i for i, ch in enumerate(text) if ch in ".!?"
        ), reverse = True)
        for pos in candidate_positions:
            candidate = text[:pos + 1]
            if _parens_balanced(candidate):
                text = candidate
                break  
        else:
            if candidate_positions:
                text = text[:candidate_positions[0] + 1]
    return text

def _parens_balanced(s: str) -> bool:
    # True if every ( [ { in s has a matching closer and none close early
    depth = 0
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0

# Checks Device for optimal performance

def get_device_and_batch_size() -> tuple[torch.device, int]:
    # Check in order: 1. CUDA (Nvidia GPU), 2. MPS (Apple GPU), 3. CPU
    # Adjusts Batch Size based on device memory (32 for CUDA, 16 for MPS, 8 for CPU)

    if torch.cuda.is_available():
        return torch.device("cuda"), 32
    elif torch.backends.mps.is_available():
        return torch.device("mps"), 16
    else: 
        return torch.device("cpu"), 8

# Summarize abstracts in batches

def summarize_all(papers: list[dict], progress_callback=None, should_continue=None) -> list[dict]:
    device, batch_size = get_device_and_batch_size()
    print(f" Using device: {device}, batch size: {batch_size}")

    print(f" Loading Model '{MODEL_NAME}' (first run downloads ~300MB)...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device)

    abstracts = [p["abstract"] for p in papers]
    abstracts_clean = [clean_latex(a) for a in abstracts]

    print(f" Summarizing {len(abstracts_clean)} abstracts in batches of {batch_size}...")
    summaries = []
    for start in range(0, len(abstracts_clean), batch_size):
        if should_continue is not None and not should_continue():
            print(" Cancelled - stopping before next batch.")
            break

        batch = abstracts_clean[start:start+batch_size]
        inputs = tokenizer(
            batch,
            return_tensors="pt",
            padding=True, # Shortens each batch
            truncation=True, # Truncate long abstracts to fit model input
            max_length=MAX_INPUT_TOKENS
        ).to(device) # Move inputs to the same device as the model

        summary_ids = model.generate(
            **inputs,
            max_length=MAX_SUMMARY_TOKENS, 
            min_length=MIN_SUMMARY_TOKENS,
            num_beams = 4, # beam search for better summaries
            early_stopping=True,
            length_penalty = 2.0, # prefer shorter summaries
            no_repeat_ngram_size=3, # avoid repetition
            )
        
        batch_summaries = tokenizer.batch_decode(summary_ids, skip_special_tokens=True)
        batch_summaries = [s.replace("<n>", " ") for s in batch_summaries] # clean up any <n> tokens
        summaries.extend(batch_summaries)

        done = min(start + batch_size, len(abstracts_clean))
        print(f" Summarized {done}/{len(abstracts_clean)} abstracts...")
        if progress_callback is not None:
            progress_callback(done, len(abstracts_clean))


    for paper, summary in zip(papers, summaries):
        paper["short_description"] = clean_summary_text(summary.strip())

    return papers


# Entry point

if __name__ == "__main__":
    papers = load_papers(INPUT_FILE)
    papers = summarize_all(papers)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(papers, f, indent=2)

    print(f"\nSaved {len(papers)} summarized papers to {OUTPUT_FILE}.")

    # Sanity Check
    if papers:
        print("\n--- Example ---")
        print(f"Title: {papers[0]['title']}")
        print(f"Summary: {papers[0]['short_description']}")
        print(f"Link: {papers[0]['link']}")