# Cosmo

A personal arXiv paper filter. Cosmo fetches new papers from a set of physics
and quantum-information categories, summarizes and embeds them, and learns
what I actually want to read — so eventually it can just email me the papers
worth reading instead of me scrolling arXiv every day.

## Why

I have a physics background (ion traps, MR-TOF-MS instrumentation, ATLAS/Higgs
detector work) and wanted something better than manually skimming arXiv listings
across a dozen categories every day. Cosmo is both a practical daily tool to stay in touch with academia across multiple fields.

## Categories tracked

`astro-ph.CO`, `astro-ph.GA`, `astro-ph.HE`, `astro-ph.IM`, `gr-qc`, `hep-ex`,
`hep-ph`, `physics.acc-ph`, `physics.comp-ph`, `physics.data-an`,
`physics.space-ph`, `quant-ph`

## Pipeline

```
fetch → summarize → embed → label
```

| Stage | Script | What it does |
|---|---|---|
| Fetch | `fetch.py` | Pulls new papers from arXiv's daily RSS feed for each tracked category. |
| Summarize | `summarize.py` | Generates a short plain-language summary of each abstract using a seq2seq model, with LaTeX cleanup so equations don't garble output. |
| Embed | `embed.py` | Computes a SPECTER embedding (`sentence-transformers/allenai-specter`) for each paper's title + abstract, for similarity/classification use. |
| Label | `label.py` | Interactive CLI for reviewing papers and marking them relevant / not relevant, building up a personal training set. |

**Planned next stages:** once enough labels exist, `classify.py` will train on
`labels.csv` and score new papers automatically, and `send_email.py` will mail
the top-N each day — replacing manual labeling with automated filtering.

## Running it

```bash
python run_pipeline.py                  # run the full pipeline
python run_pipeline.py --skip fetch     # reuse already-fetched data
python run_pipeline.py --only embed     # run a single stage
```

`run_pipeline.py` runs each stage in order and stops if any stage fails. The
stage list is a single list at the top of the file, so swapping `label.py` for
`classify.py` + `send_email.py` later is a one-line edit.

## Setup

```bash
pip install -r requirements.txt
```

Create a `user_config.txt` file (gitignored) containing your email, used to
build a polite `User-Agent` string for arXiv API requests:

```
your_email@example.com
```

## Project structure

```
Cosmo/
├── fetch.py            # Stage 1: pull papers from arXiv
├── summarize.py        # Stage 2: summarize abstracts
├── embed.py            # Stage 3: compute SPECTER embeddings
├── label.py            # Stage 4: manually label relevance
├── run_pipeline.py      # Orchestrates all stages
├── requirements.txt
└── user_config.txt      # gitignored — your email for the User-Agent header
```

Generated data files (`papers_raw.json`, `papers_summarized.json`,
`embedding_ids.json`) are gitignored since they're fully regenerable by
rerunning the pipeline. `labels.csv` is tracked, since it's hand-labeled data
that can't be regenerated.

## Status

Actively in development. Fetch, summarize, embed, and label stages are working
end to end. Next up: `classify.py` and automated email delivery.