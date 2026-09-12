# Comparison script to include a groq results extension to the DistilBART summary
# Run with: python3 test_groq_key_findings.py
import json
import re
import time

from transformers.utils import logging as hf_logging
hf_logging.enable_progress_bar()
import summarize
from api import generate as generate_with_api
from text_utils import clean_latex

SAMPLE_SIZE = 10
BATCH_SIZE = 5

with open("papers_raw.json") as f:
    all_papers = json.load(f)

sample = [dict(p) for p in all_papers[:SAMPLE_SIZE]]

print(f"Summarizing {len(sample)} papers with DistilBART first...")
start = time.perf_counter()
summarize.MODEL_NAME = "sshleifer/distilbart-cnn-6-6"
sample = summarize.summarize_all(sample)
distilbart_time = time.perf_counter() - start
print(f"DistilBART summary completed in {distilbart_time:.1f}s.")


def build_batch_prompt(papers: list[dict]) -> str:
    blocks = []
    for i, p in enumerate(papers, 1):
        abstract = clean_latex(p["abstract"])
        blocks.append(
            f"Paper {i}:\n"
            f"Summary: {p['short_description']}\n"
            f"Abstract: {abstract}\n"
        )
    papers_text = "\n".join(blocks)
    return (
        f"Below are {len(papers)} physics papers, each with a short auto-generated "
        f"summary and the paper's full abstract. For each paper, write ONE additional "
        f"sentence stating the key finding or implication, using ONLY information "
        f"explicitly present in the abstract. Do not repeat the summary, and do NOT "
        f"invent, estimate, or infer any numbers, parameter values, or specific claims "
        f"that are not literally stated in the abstract text. If the abstract does not "
        f"state a specific number or result, describe the finding qualitatively instead "
        f"of guessing one. Respond with ONLY a JSON array of exactly {len(papers)} "
        f"strings, in the same order as the papers below. No markdown, no code fences, "
        f"no extra text.\n\n"
        f"{papers_text}"
    )

def parse_json_array(text: str, expected_len: int) -> list[str]:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f" JSON parse failed: {e}")
        print(f" Raw response was: {text!r}")
        return ["(parse error)"] * expected_len
    if not isinstance(result, list) or len(result) != expected_len:
        print(f" Expected {expected_len} items, got: {result!r}")
        return (list(result) + ["(missing)"] * expected_len)[:expected_len]
    return result

print(f"\nCalling Groq for key findings, in batches of {BATCH_SIZE}...")
key_findings: list[str] = []
groq_start = time.perf_counter()
for start_idx in range(0, len(sample), BATCH_SIZE):
    batch = sample[start_idx:start_idx + BATCH_SIZE]
    prompt = build_batch_prompt(batch)
    response = generate_with_api(prompt)
    findings = parse_json_array(response, len(batch))
    key_findings.extend(findings)
    print(f" Batch {start_idx // BATCH_SIZE + 1}: got {len(findings)} findings")
groq_time = time.perf_counter() - groq_start

for p, finding in zip(sample, key_findings):
    print("=" * 70)
    print(f"Title: {p['title']}")
    print(f"\nSummary: {p['short_description']}")
    print(f"\nKey Finding: {finding}")

print("=" * 70)
print(f"\nDistilBART time: {distilbart_time:.1f}s  ({distilbart_time/len(sample):.2f}s/paper)")
print(f"Groq batch time: {groq_time:.1f}s  ({groq_time/len(sample):.2f}s/paper, batch size {BATCH_SIZE})")
print(f"\nDone — no files were modified. This only printed to your terminal.")