import feedparser  # parses the Atom/RSS XML response into Python objects
import json
import re
import requests

# Config:
# Picks arXiv category codes
# Full taxonomy:
# https://arxiv.org/category_taxonomy
# uses trained scorer (classify.py, once labels.csv has been built) to narrow paper filter over time

RSS_BASE_URL = "http://export.arxiv.org/rss/"
OUTPUT_FILE = "papers_raw.json"

CATEGORIES = [
    "astro-ph.CO",       # Cosmology and Nongalactic Astrophysics
    "astro-ph.GA",        # Astrophysics of Galaxies
    "astro-ph.HE",        # High Energy Astrophysical Phenomena
    "astro-ph.IM",         # Instrumentation and Methods for Astrophysics
    "gr-qc",              # General Relativity and Quantum Cosmology
    "hep-ex",             # High Energy Physics - Experiment
    "hep-ph",             # High Energy Physics - Phenomenology
    "physics.acc-ph",     # Accelerator Physics
    "physics.comp-ph",    # Computational Physics
    "physics.data-an",    # Data Analysis, Statistics and Probability
    "physics.space-ph",   # Space Physics
    "quant-ph",           # Quantum Physics
]

# Set up user agent for requests to arXiv API (to avoid being blocked):
USER_AGENT = "cosmo-arxiv-filter/0.1 (personal research paper filter; contact: tjamesgriffiths2002@gmail.com)"

# Clean up arXiv's packed feed

def parse_description(raw_description: str) -> tuple[str, str]:
    text = " ".join(raw_description.split())

    abstract_match = re.search(r"Abstract:\s*(.*)", text, re.IGNORECASE)
    if abstract_match:
        return abstract_match.group(1).strip()
    
    # Fallback: strip a leading arXiv ID and announce type if present
    return re.sub(r"^arXiv:\S+\s*Announce Type:\s*\S+\s*", "", text, flags=re.IGNORECASE).strip()

# Fetch Today's feed for all categories

def fetch_today(categories: list[str]) -> list[dict]:
    url = f"{RSS_BASE_URL}/{'+'.join(categories)}"
    print(f"Fetching: {url}\n")

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout = 30)

    if response.status_code != 200:
        print(f" !! HTTP {response.status_code} error fetching feed. Exiting.")
        print(f"    Response snippet: {response.text[:200]!r}")
        return []
    
    feed = feedparser.parse(response.content)
    if feed.bozo:
        print(f" !! feedparser warning: {feed.bozo_exception}")
    
    print(f"{len(feed.entries)} entries found in today's feed.")

    if not feed.entries:
        print(
            "This is Expected on Saturdays/Sundays - arXiv does not post new papers on weekends."
            "Try again on a weekday."
        )
        return []
    
    # print the first raw entry for inspection
    print("\n--- First raw entry (for inspection) ---")
    print(feed.entries[0])
    print("--- End Raw Entry ---\n")

    papers = []
    for entry in feed.entries:
        raw_id = entry.get("id", entry.get("guid", ""))
        arxiv_id = raw_id.replace("oai:arXiv.org:", "")

        raw_description = entry.get("summary", "") or entry.get("description", "")
        abstract = parse_description(raw_description)
        announce_type = entry.get("arxiv_announce_type", "unknown")

        # Creator comes through as a single comma-sep. string
        authors_raw = entry.get("author", "")
        authors = [a.strip() for a in authors_raw.split(",")] if authors_raw else []

        # Category tags: feedparser exposes these as entry.tags
        categories_found = [t.term for t in entry.get("tags", [])] if entry.get("tags") else []

        papers.append({
            "arxiv_id": arxiv_id,
            "title": " ".join(entry.title.split()), # clean up whitespace
            "abstract": abstract,
            "authors": authors,
            "categories": ", ".join(categories_found) if categories_found else "unknown",
            "announce_type": announce_type,
            "published": entry.get("published", entry.get("pubDate", "")),
            "link": entry.get("link", f"https://arxiv.org/abs/{arxiv_id}"),
        })
    
    return papers

# Entry point

if __name__ == "__main__":
    today_papers = fetch_today(CATEGORIES)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(today_papers, f, indent=2)

    print(f"\nSaved {len(today_papers)} papers to {OUTPUT_FILE}.")
