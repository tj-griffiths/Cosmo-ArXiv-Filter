# Standalone Mailing Automation for Cosmo Papers

import json
import os
import smtplib
import subprocess
from datetime import date
from email.mime.text import MIMEText

from fetch import CATEGORIES, fetch_today, is_arxiv_closed_today
from summarize import summarize_all
from embed import embed_all, load_existing_embeddings, EMBEDDINGS_FILE, EMBEDDING_IDS_FILE
from classify import load_embeddings, load_labels, build_training_set, train_and_evaluate, score_all_papers
import numpy as np
import html
from collections import defaultdict

RAW_FILE = "papers_raw.json"
SUMMARIZED_FILE = "papers_summarized.json"
PREFERENCES_FILE = "preferences.json"
GMAIL_CREDENTIALS_FILE = "gmail_credentials.txt"
COSMO_PAPERS_COUNT = 10

CATEGORY_GROUPS = {
    "astro-ph.CO": "Astrophysics",
    "astro-ph.EP": "Astrophysics",
    "astro-ph.GA": "Astrophysics",
    "astro-ph.HE": "Astrophysics",
    "astro-ph.IM": "Astrophysics",
    "astro-ph.SR": "Astrophysics",
    "cond-mat.dis-nn": "Condensed Matter",
    "cond-mat.mes-hall": "Condensed Matter",
    "cond-mat.mtrl-sci": "Condensed Matter",
    "cond-mat.other": "Condensed Matter",
    "cond-mat.quant-gas": "Condensed Matter",
    "cond-mat.soft": "Condensed Matter",
    "cond-mat.stat-mech": "Condensed Matter",
    "cond-mat.str-el": "Condensed Matter",
    "cond-mat.supr-con": "Condensed Matter",
    "gr-qc": "General Relativity & Quantum Cosmology",
    "hep-ex": "High Energy Physics",
    "hep-lat": "High Energy Physics",
    "hep-ph": "High Energy Physics",
    "hep-th": "High Energy Physics",
    "math-ph": "Mathematical Physics",
    "nlin.AO": "Nonlinear Sciences",
    "nlin.CD": "Nonlinear Sciences",
    "nlin.CG": "Nonlinear Sciences",
    "nlin.PS": "Nonlinear Sciences",
    "nlin.SI": "Nonlinear Sciences",
    "nucl-ex": "Nuclear Physics",
    "nucl-th": "Nuclear Physics",
    "physics.acc-ph": "Accelerator Physics",
    "physics.ao-ph": "Atmospheric and Oceanic Physics",
    "physics.app-ph": "Applied Physics",
    "physics.atm-clus": "Atomic and Molecular Clusters",
    "physics.atom-ph": "Atomic Physics",
    "physics.bio-ph": "Biological Physics",
    "physics.chem-ph": "Chemical Physics",
    "physics.class-ph": "Classical Physics",
    "physics.comp-ph": "Computational Physics",
    "physics.data-an": "Data Analysis, Statistics and Probability",
    "physics.ed-ph": "Physics Education",
    "physics.flu-dyn": "Fluid Dynamics",
    "physics.gen-ph": "General Physics",
    "physics.geo-ph": "Geophysics",
    "physics.hist-ph": "History and Philosophy of Physics",
    "physics.ins-det": "Instrumentation and Detectors",
    "physics.med-ph": "Medical Physics",
    "physics.optics": "Optics",
    "physics.plasm-ph": "Plasma Physics",
    "physics.pop-ph": "Popular Physics",
    "physics.soc-ph": "Physics and Society",
    "physics.space-ph": "Space Physics",
    "quant-ph": "Quantum Physics",
}

def should_send_today(prefs: dict) -> bool:
    frequency = prefs.get("email_frequency", "daily")
    if frequency == "daily":
        return True
    target_weekday = prefs.get("email_weekday", 0)
    return date.today().weekday() == target_weekday

try:
    from plyer import notification as plyer_notification
except ImportError:
    plyer_notification = None

def notify_desktop(title: str, message: str) -> None:
    prefs = load_preferences()
    if not prefs.get("desktop_notifications", True):
        return
    if plyer_notification is None:
        return
    try:
        plyer_notification.notify(title=title, message=message, timeout=5)
    except Exception:
        pass # Notification are a nice-to-have

def load_preferences() -> dict:
    if not os.path.exists(PREFERENCES_FILE):
        return {}
    try:
        with open(PREFERENCES_FILE) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}

def save_preferences(prefs: dict) -> None:
    with open(PREFERENCES_FILE, "w") as f:
        json.dump(prefs, f, indent=2)

def load_saved_categories() -> list[str]:
    prefs = load_preferences()
    saved = prefs.get("categories")
    return [c for c in saved if c in CATEGORIES] if saved else list(CATEGORIES)

def get_gmail_credentials() -> tuple[str, str] | None:
    if not os.path.exists(GMAIL_CREDENTIALS_FILE):
        return None
    with open(GMAIL_CREDENTIALS_FILE) as f:
        lines = [line.strip() for line in f if line.strip()]
    if len(lines) < 2:
        return None
    return lines[0], lines[1]

def send_digest_email(recipient: str, papers: list[tuple[float, dict]]) -> bool:
    creds = get_gmail_credentials()
    if creds is None:
        print("No gmail_credentials.txt found - skipping email.")
        return False
    sender, app_password = creds

    by_category: dict[str, list[dict]] = defaultdict(list)
    for score, paper in papers:
        primary_category = paper.get("categories", "unknown").split(",")[0].strip()
        group_names = CATEGORY_GROUPS.get()
        by_category[group_name].append(paper)

    parts = [f"<p>Cosmo's top {len(papers)} picks for {date.today().isoformat()}:</p>"]
    for group_name in sorted(by_category):
        parts.append(f"<h3>{html.escape(group_name)}</h3>")
        for paper in by_category[group_name]:
            title = html.escape(paper["title"])
            summary = html.escape(paper["short_description"])
            link = html.escape(paper["link"])
            parts.append(
                f'<p><b>Title:</b> <u>{title}</u><br>'
                f'<b>Summary:</b> {summary}<br>'
                f'<a href="{link}">{link}</a></p>'
            )
    body = "".join(parts)

    msg = MIMEText(body, "html")
    msg["Subject"] = f"Cosmo Papers - {date.today().isoformat()}"
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_password)
            server.sendmail(sender, [recipient], msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
    
def maybe_send_daily_email(papers: list[dict]) -> None:
    prefs = load_preferences()
    if not prefs.get("email_opt_in") or not prefs.get("email"):
        return
    if prefs.get("last_email_sent_date") == date.today().isoformat():
        return
    if not should_send_today(prefs):
        return

    from classify import load_embeddings, load_labels, build_training_set, train_and_evaluate, score_all_papers
    embeddings_by_id = load_embeddings()
    labels = load_labels()
    X, y = build_training_set(embeddings_by_id, labels)
    clf = train_and_evaluate(X, y)
    if clf is None:
        return

    labeled_ids = {row["arxiv_id"] for row in labels}
    scored_all = score_all_papers(clf, embeddings_by_id, papers)
    unlabeled_scored = [(score, p) for score, p in scored_all if p["arxiv_id"] not in labeled_ids]
    email_count = prefs.get("email_paper_count", COSMO_PAPERS_COUNT)
    top_papers = unlabeled_scored[:email_count]

    sent = send_digest_email(prefs["email"], top_papers)
    prefs["last_email_sent_date"] = date.today().isoformat()
    save_preferences(prefs)

    if sent:
        notify_desktop("Cosmo", f"Sent today's {len(top_papers)} picks to {prefs['email']}.")
    
def run_daily_pipeline() -> None:
    prefs = load_preferences()

    if prefs.get("last_auto_run_date") == date.today().isoformat():
        print("Already ran today - exiting.")
        return

    if is_arxiv_closed_today():
        print("arXiv is closed today (weekend/holiday) — nothing to fetch.")
        return

    categories = load_saved_categories()
    print("Fetching today's papers...")
    papers = fetch_today(categories)
    if not papers:
        print("No papers fetched - exiting.")
        return
    with open(RAW_FILE, "w") as f:
        json.dump(papers, f, indent=2)

    print("Summarizing...")
    papers = summarize_all(papers)
    with open(SUMMARIZED_FILE, "w") as f:
        json.dump(papers, f, indent=2)

    print("Embedding...")
    existing_embeddings, existing_ids = load_existing_embeddings()
    existing_ids_set = set(existing_ids)
    new_papers = [p for p in papers if p["arxiv_id"] not in existing_ids_set]
    if new_papers:
        new_embeddings = embed_all(new_papers, show_progress=False)
        if existing_embeddings is not None:
            embeddings = np.concatenate([existing_embeddings, new_embeddings])
            arxiv_ids = existing_ids + [p["arxiv_id"] for p in new_papers]
        else:
            embeddings = new_embeddings
            arxiv_ids = [p["arxiv_id"] for p in new_papers]
        np.save(EMBEDDINGS_FILE, embeddings)
        with open(EMBEDDING_IDS_FILE, "w") as f:
            json.dump(arxiv_ids, f, indent=2)

    prefs["last_auto_run_date"] = date.today().isoformat()
    save_preferences(prefs)

    maybe_send_daily_email(papers)

if __name__ == "__main__":
    run_daily_pipeline()