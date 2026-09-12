# Test script to see if api can pool affiliation
# To run: python3 test_affiliation_coverage.py

import feedparser

CATEGORIES_TO_CHECK = ["hep-ph", "astro-ph.CO", "quant-ph", "gr-qc", "cond-mat.mtrl-sci"]
MAX_RESULTS_PER_CATEGORY = 20

total_checked = 0
total_with_affiliation = 0

for cat in CATEGORIES_TO_CHECK:
    url = (
        f"http://export.arxiv.org/api/query?search_query=cat:{cat}"
        f"&sortBy=submittedDate&sortOrder=descending&max_results={MAX_RESULTS_PER_CATEGORY}"
    )
    feed = feedparser.parse(url)
    n_checked = len(feed.entries)
    n_with_aff = 0

    for entry in feed.entries:
        authors = entry.get("authors", [])
        has_aff = any(
            hasattr(a, "arxiv_affiliation") or "affiliation" in a
            for a in authors
        )
        if has_aff:
            n_with_aff += 1

    total_checked += n_checked
    total_with_affiliation += n_with_aff
    print(f"{cat}: {n_with_aff}/{n_checked} entries had at least one author affiliation")

print(f"\nOverall: {total_with_affiliation}/{total_checked} "
      f"({100 * total_with_affiliation / total_checked:.1f}%) had affiliation data present")