# Comparison script that doesn't run on pipeline
# Tests the summary quality between DistilBART and pegasus-arxiv
# Run with: python3 test_pegasus_summary.py

import json
import summarize
import time
from transformers.utils import logging as hf_logging

hf_logging.enable_progress_bar()

SAMPLE_SIZE = 20

with open("papers_raw.json") as f:
    all_papers = json.load(f)

sample = all_papers[:SAMPLE_SIZE]

def timed_run(model_name: str, papers: list[dict]) -> tuple[list[dict], float]:
    summarize.MODEL_NAME = model_name
    start = time.perf_counter()
    results = summarize.summarize_all([dict(p) for p in papers])
    elapsed = time.perf_counter() - start
    return results, elapsed

print(f"Running DistilBART on {len(sample)} papers...")
old_results, old_time = timed_run("sshleifer/distilbart-cnn-6-6", sample)

print(f"\nRunning pegasus-arxiv on {len(sample)} papers...")
new_results, new_time = timed_run("google/pegasus-arxiv", sample)

old_by_id = {p["arxiv_id"]: p["short_description"] for p in old_results}
new_by_id = {p["arxiv_id"]: p["short_description"] for p in new_results}

for p in sample:
    print("=" * 70)
    print(f"Title: {p['title']}")
    print(f"\nOld (DistilBART): {old_by_id.get(p['arxiv_id'], '(missing)')}")
    print(f"\nNew (pegasus-arxiv): {new_by_id.get(p['arxiv_id'], '(missing)')}")

print("=" * 70)
print(f"\nDistilBART total time:    {old_time:.1f}s  ({old_time/len(sample):.2f}s/paper)")
print(f"pegasus-arxiv total time: {new_time:.1f}s  ({new_time/len(sample):.2f}s/paper)")
print(f"\nDone — no files were modified. This only printed to your terminal.")