import json
import re

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
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
    Caveat worth knowing (and worth stating explicitly in interviews):
    this model was fine-tuned on CNN/DailyMail *news* summarization, not
    scientific abstracts, so it summarizes a summary that's already
    dense and jargon-heavy. It will work, but a natural next iteration
    for this project is fine-tuning a small seq2seq model on a
    scientific-abstract summarization dataset (e.g. SciTLDR) instead of
    relying on an off-the-shelf news summarizer. Flagging that gap is
    itself a good sign of ML maturity — it's fine to ship v1 with a
    known, named limitation.
"""

BATCH_SIZE =  8
MAX_SUMMARY_TOKENS = 100
MIN_SUMMARY_TOKENS = 20
MAX_INPUT_TOKENS = 1024

# To handle LaTeX math in abstracts:
_GREEK_LETTERS = [
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
    "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi", "rho",
    "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega",
]

def clean_latex(text: str) -> str:
    text = re.sub(r"\\(?:mathrm|mathcal|mathbf|text|rm)\{([^{}]*)\}", r"\1", text)
    for letter in _GREEK_LETTERS:
        text = re.sub(rf"\\{letter}(?![a-zA-Z])", letter, text, flags=re.IGNORECASE)
        text = re.sub(rf"\\{letter.capitalize()}(?![a-zA-Z])", letter.capitalize(), text)

    replacements = {
        r"\\times": "x",
        r"\\pm": "+/-",
        r"\\sim": "~",
        r"\\approx": "~",
        r"\\lesssim": "<~",
        r"\\gtrsim": ">~",
        r"\\odot": "solar",
        r"\\ll": "<<",
        r"\\gg": ">>",
        r"\\rm": "",
        r"\\[,;:!]": " ",  # thin/med/thick spacing commands -> a plain space
    }

    for pattern, repl in replacements.items():
        text = re.sub(pattern, repl, text)

    text = re.sub(r"\^\{([^{}]*)\}", r"^\1", text)  # superscripts
    text = re.sub(r"_\{([^{}]*)\}", r"_\1", text)  # subscripts

    text = text.replace("$", "")  # remove $ math delimiters
    text = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", text) #\cmd{X} -> X
    text = re.sub(r"\\[a-zA-Z]+", "", text)  # \cmd -> ""

    text = " ".join(text.split())  # collapse whitespace
    return text

# Load papers:
def load_papers(path:str) -> list[dict]:
    with open(path) as f:
        return json.load(f)
    

def clean_summary_text(text: str) -> str:
    # Fixes stray spaces before punctuations and cut-off mid-word endings

    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = " ".join(text.split())  # collapse whitespace

    if text and text[-1] not in ".!?":
        last_end = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
        if last_end != -1:
            text = text[:last_end + 1]
    
    return text

# Summarize abstracts in batches

def summarize_all(papers: list[dict]) -> list[dict]:
    print(f" Loading Model '{MODEL_NAME}' (first run downloads ~300MB)...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

    abstracts = [p["abstract"] for p in papers]
    abstracts_clean = [clean_latex(a) for a in abstracts]

    print(f" Summarizing {len(abstracts_clean)} abstracts in batches of {BATCH_SIZE}...")
    summaries = []
    for start in range(0, len(abstracts_clean), BATCH_SIZE):
        batch = abstracts_clean[start:start+BATCH_SIZE]
        inputs = tokenizer(
            batch,
            return_tensors="pt",
            padding=True, # Shortens each batch
            truncation=True, # Truncate long abstracts to fit model input
            max_length=MAX_INPUT_TOKENS
        )

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
        summaries.extend(batch_summaries)

        print(f"  -> {min(start + BATCH_SIZE, len(abstracts_clean))}/{len(abstracts_clean)} abstracts summarized...")

    for paper, summary in zip(papers, summaries):
        paper["short_description"] = summary.strip()

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