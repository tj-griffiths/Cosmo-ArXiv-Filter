# Creates Cosmo's TUI front end (v1: category selection -> fetch -> label)

import json
import os
import random
import numpy as np
import webbrowser
from datetime import datetime, timezone
from history import get_today_in_history

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # Ensure working directory is the script's directory

import pyfiglet
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll, Horizontal
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, Checkbox, Button, Static, Label, Input, ProgressBar, Log, Collapsible, RadioSet, RadioButton
from textual.worker import get_current_worker
from textual.binding import Binding

from fetch import CATEGORIES, fetch_today, is_arxiv_closed_today
from summarize import summarize_all
from embed import embed_all, load_existing_embeddings, EMBEDDINGS_FILE, EMBEDDING_IDS_FILE
from label import(
    interleave_by_category,
    load_all_labels,
    write_labels,
    explain_simply,
    explain_result,
    LABELS_FILE,
)

# Utility Functions
def escape_markup(text: str) -> str:
    return text.replace("[", "\\[").replace("]", "\\]")

RAW_FILE = "papers_raw.json"
SUMMARIZED_FILE = "papers_summarized.json"
PREFERENCES_FILE = "preferences.json"

DEFAULT_GOAL_POS = 50
DEFAULT_GOAL_NEG = 50

# Human-readable descriptions for the category check boxes:

CATEGORY_LABELS = {
    "astro-ph.CO": "astro-ph.CO — Cosmology and Nongalactic Astrophysics",
    "astro-ph.EP": "astro-ph.EP — Earth and Planetary Astrophysics",
    "astro-ph.GA": "astro-ph.GA — Astrophysics of Galaxies",
    "astro-ph.HE": "astro-ph.HE — High Energy Astrophysical Phenomena",
    "astro-ph.IM": "astro-ph.IM — Instrumentation and Methods for Astrophysics",
    "astro-ph.SR": "astro-ph.SR — Solar and Stellar Astrophysics",
    "cond-mat.dis-nn": "cond-mat.dis-nn — Disordered Systems and Neural Networks",
    "cond-mat.mes-hall": "cond-mat.mes-hall — Mesoscale and Nanoscale Physics",
    "cond-mat.mtrl-sci": "cond-mat.mtrl-sci — Materials Science",
    "cond-mat.other": "cond-mat.other — Other Condensed Matter",
    "cond-mat.quant-gas": "cond-mat.quant-gas — Quantum Gases",
    "cond-mat.soft": "cond-mat.soft — Soft Condensed Matter",
    "cond-mat.stat-mech": "cond-mat.stat-mech — Statistical Mechanics",
    "cond-mat.str-el": "cond-mat.str-el — Strongly Correlated Electrons",
    "cond-mat.supr-con": "cond-mat.supr-con — Superconductivity",
    "gr-qc": "gr-qc — General Relativity and Quantum Cosmology",
    "hep-ex": "hep-ex — High Energy Physics, Experiment",
    "hep-lat": "hep-lat — High Energy Physics, Lattice",
    "hep-ph": "hep-ph — High Energy Physics, Phenomenology",
    "hep-th": "hep-th — High Energy Physics, Theory",
    "math-ph": "math-ph — Mathematical Physics",
    "nlin.AO": "nlin.AO — Adaptation and Self-Organizing Systems",
    "nlin.CD": "nlin.CD — Chaotic Dynamics",
    "nlin.CG": "nlin.CG — Cellular Automata and Lattice Gases",
    "nlin.PS": "nlin.PS — Pattern Formation and Solitons",
    "nlin.SI": "nlin.SI — Exactly Solvable and Integrable Systems",
    "nucl-ex": "nucl-ex — Nuclear Experiment",
    "nucl-th": "nucl-th — Nuclear Theory",
    "physics.acc-ph": "physics.acc-ph — Accelerator Physics",
    "physics.ao-ph": "physics.ao-ph — Atmospheric and Oceanic Physics",
    "physics.app-ph": "physics.app-ph — Applied Physics",
    "physics.atm-clus": "physics.atm-clus — Atomic and Molecular Clusters",
    "physics.atom-ph": "physics.atom-ph — Atomic Physics",
    "physics.bio-ph": "physics.bio-ph — Biological Physics",
    "physics.chem-ph": "physics.chem-ph — Chemical Physics",
    "physics.class-ph": "physics.class-ph — Classical Physics",
    "physics.comp-ph": "physics.comp-ph — Computational Physics",
    "physics.data-an": "physics.data-an — Data Analysis, Statistics and Probability",
    "physics.ed-ph": "physics.ed-ph — Physics Education",
    "physics.flu-dyn": "physics.flu-dyn — Fluid Dynamics",
    "physics.gen-ph": "physics.gen-ph — General Physics",
    "physics.geo-ph": "physics.geo-ph — Geophysics",
    "physics.hist-ph": "physics.hist-ph — History and Philosophy of Physics",
    "physics.ins-det": "physics.ins-det — Instrumentation and Detectors",
    "physics.med-ph": "physics.med-ph — Medical Physics",
    "physics.optics": "physics.optics — Optics",
    "physics.plasm-ph": "physics.plasm-ph — Plasma Physics",
    "physics.pop-ph": "physics.pop-ph — Popular Physics",
    "physics.soc-ph": "physics.soc-ph — Physics and Society",
    "physics.space-ph": "physics.space-ph — Space Physics",
    "quant-ph": "quant-ph — Quantum Physics"
}

# Fetching Paper Messages (Terraria-like)

FLAVOR_MESSAGES = [
    "Untangling entangled qubits...",
    "Reticulating field lines...",
    "Aligning spin axes...",
    "Colliding beams for luck...",
    "Cooling down superconductors...",
    "Renormalizing infinities...",
    "Diagonalizing the Hamiltonian...",
    "Waving hands (semiclassically)...",
    "Averaging over ensembles...",
    "Coarse-graining the microstates...",
    "Checking for negative probabilities...",
    "Wick-rotating to imaginary time...",
    "Summing over Feynman diagrams...",
    "Gauge-fixing the vacuum...",
    "Measuring wavefunction collapse...",
    "Polishing the mirror cavity...",
    "Quenching the flux lines...",
    "Annealing the spin glass...",
    "Untwisting the Möbius resonator...",
    "Sorting eigenvalues by vibe...",
    "Degaussing the detector...",
    "Chasing runaway solitons...",
    "Bootstrapping the S-matrix...",
    "Integrating out heavy fields...",
    "Tuning the RF cavity...",
    "Calibrating the dark matter detector (again)...",
    "Solving Schrödinger's equation by eye...",
    "Herding photons into a beam...",
    "Debating interpretations of quantum mechanics...",
    "Symmetry-breaking on purpose...",
    "Cross-checking with dimensional analysis...",
    "Baking the cryostat...",
    "Venting excess entropy...",
    "Perturbing the perturbation theory...",
    "Rotating into the interaction picture...",
    "Consulting the Standard Model...",
    "Fitting a power law to everything...",
    "Filtering out cosmic ray hits...",
    "Waiting for the wavefunction to decide...",
    "Recalibrating the flux capacitor (unphysical)...",
    "Convincing electrons to cooperate...",
    "Double-checking units (again)...",
    "Deriving from first principles...",
    "Linearizing the nonlinear terms...",
    "Padding the error bars...",
]

# --- Helper Functions --- #

def _safe_id(category_code: str) -> str:
    return f"cb-{category_code.replace('.', '-')}"

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

def load_saved_categories() -> list[str] | None:
    prefs = load_preferences()
    saved = prefs.get("categories")
    return [c for c in saved if c in CATEGORIES] if saved else None


def save_categories(categories: list[str]) -> None:
    prefs = load_preferences()
    prefs["categories"] = categories
    save_preferences(prefs)
    
def summarized_file_is_fresh() -> bool:
    if not os.path.exists(SUMMARIZED_FILE):
        return False
    mtime_date = datetime.fromtimestamp(os.path.getmtime(SUMMARIZED_FILE)).date()
    return mtime_date == datetime.now().date()

def goal_already_met() -> bool:
    rows = load_all_labels(LABELS_FILE)
    n_pos = sum(1 for r in rows if r["label"] == "1")
    n_neg = sum(1 for r in rows if r["label"] == "0")
    return n_pos >= DEFAULT_GOAL_POS and n_neg >= DEFAULT_GOAL_NEG

DAILY_LABEL_GOAL = 5
COSMO_PAPERS_COUNT = 10
STAR_WEIGHT = 3

def get_daily_progress() -> int:
    from datetime import date
    prefs = load_preferences()
    if prefs.get("daily_progress_date") != date.today().isoformat():
        return 0
    return prefs.get("daily_progress_count", 0)

def set_daily_progress(count: int) -> None:
    from datetime import date
    prefs = load_preferences()
    prefs["daily_progress_date"] = date.today().isoformat()
    prefs["daily_progress_count"] = count
    save_preferences(prefs)

def record_daily_completion() -> dict:
    from datetime import date, timedelta
    prefs = load_preferences()
    today_str = date.today().isoformat()
    last_str = prefs.get("last_daily_label_date")
    streak = prefs.get("daily_streak", 0)
    total = prefs.get("total_daily_completions", 0)

    if last_str != today_str:
        if last_str == (date.today() - timedelta(days=1)).isoformat():
            streak += 1
        else:
            streak = 1
        total += 1
        prefs["last_daily_label_date"] = today_str
        prefs["daily_streak"] = streak
        prefs["total_daily_completions"] = total
        save_preferences(prefs)
    return {"streak": streak, "total": total}

def load_cosmo_papers() -> list[tuple[float, dict]] | None:
    from datetime import date
    prefs = load_preferences()
    if prefs.get("cosmo_papers_date") != date.today().isoformat():
        return None
    entries = prefs.get("cosmo_papers", [])
    if not entries:
        return None
    
    with open(SUMMARIZED_FILE) as f:
        papers = json.load(f)
    papers_by_id = {p["arxiv_id"]: p for p in papers}

    result = []
    for entry in entries:
        paper = papers_by_id.get(entry["arxiv_id"])
        if paper is not None:
            result.append((entry["score"], paper))
    return result if result else None

def save_cosmo_papers_cache(scored_papers: list[tuple[float, dict]]) -> None:
    from datetime import date
    prefs = load_preferences()
    prefs["cosmo_papers_date"] = date.today().isoformat()
    prefs["cosmo_papers"] = [
        {"arxiv_id": paper["arxiv_id"], "score": score}
        for score, paper in scored_papers
    ]
    save_preferences(prefs)

# --- Screen: Help --- #

# Can be opened at any time to show the keybindings for the current screen
class HelpModal(ModalScreen):
    # Generic modal listing the active screen's keybindings and their descriptions

    BINDINGS = [("escape", "dismiss", "Close"), ("h", "dismiss", "Close")]

    CSS = """
    HelpModal { align: center middle; background: rgba(0, 0, 0, 0.6); }
    #help-box { border: round #414868; padding: 1 2; width: 60; background: #1a1b26; color: #a9b1d6; }
    #help-desc { color: #7dcfff; margin-bottom: 1; }
    #help-binding-key { color: #e0af68; text-style: bold; }
    """

    def __init__(self, description: str, bindings: list[tuple[str, str]]) -> None:
        super().__init__()
        self.description = description
        self.bindings = bindings

    def compose(self) -> ComposeResult:
        lines = [f"[#e0af68 bold]{key}[/#e0af68 bold]  {desc}" for key, desc in self.bindings]
        with Vertical(id="help-box"):
            yield Static(f"[#7dcfff]{self.description}[/#7dcfff]\n\n" + "\n".join(lines))

    def action_dismiss(self) -> None:
        self.app.pop_screen()

# --- Screen: Welcome Art --- #

# Opens the program with a "COSMO" Banner
def render_welcome_art(canvas_width: int = 60, canvas_height: int = 13, star_density: float = 0.035) -> str:
    banner_lines = pyfiglet.figlet_format("COSMO", font="ansi_shadow").rstrip("\n").split("\n")
    banner_height = len(banner_lines)
    banner_width = max(len(line) for line in banner_lines)

    canvas_width = max(canvas_width, banner_width)
    canvas_height = max(canvas_height, banner_height)

    top_pad = (canvas_height - banner_height) // 2
    left_pad = (canvas_width - banner_width) // 2

    canvas = [[" " for _ in range(canvas_width)] for _ in range(canvas_height)]
    star_chars  = ["*", ".", "+"]
    for row in range(canvas_height):
        for col in range(canvas_width):
            in_banner_region = (
                top_pad <= row < top_pad + banner_height
                and left_pad <= col < left_pad + banner_width
            )
            if not in_banner_region and random.random() < star_density:
                canvas[row][col] = random.choice(star_chars)

    for i, line in enumerate(banner_lines):
        for j, ch in enumerate(line):
            if ch != " ":
                canvas[top_pad + i][left_pad + j] = ch
    
    banner_chars = set("".join(banner_lines)) - {" "}

    def style_of(ch: str) -> str:
        if ch in banner_chars:
            return "bold cyan"
        if ch in star_chars:
            return "dim white"
        return None
    
    lines_out = []
    for row in canvas:
        parts = []
        run_style = style_of(row[0])
        run_chars = [row[0]]
        for ch in row[1:]:
            style = style_of(ch)
            if style == run_style:
                run_chars.append(ch)
            else:
                text = "".join(run_chars)
                parts.append(f"[{run_style}]{text}[/{run_style}]" if run_style else text)
                run_style, run_chars = style, [ch]
        text = "".join(run_chars)
        parts.append(f"[{run_style}]{text}[/{run_style}]" if run_style else text)
        lines_out.append("".join(parts))

    return "\n".join(lines_out)


def render_starfield(width: int = 80, height: int = 8, star_density: float = 0.035) -> str:
    star_chars = ["*", ".", "+"]

    canvas = [[" " for _ in range(width)] for _ in range(height)]
    for row in range(height):
        for col in range(width):
            if random.random() < star_density:
                canvas[row][col] = random.choice(star_chars)
    
    lines_out = []
    for row in canvas:
        parts = []
        run_is_star = row[0] != " "
        run_chars = [row[0]]
        for ch in row[1:]:
            is_star = ch != " "
            if is_star == run_is_star:
                run_chars.append(ch)
            else:
                text = "".join(run_chars)
                style = "dim white" if run_is_star else None
                parts.append(f"[{style}]{text}[/{style}]" if style else text)
                run_is_star, run_chars = is_star, [ch]
        text = "".join(run_chars)
        style = "dim white" if run_is_star else None
        parts.append(f"[{style}]{text}[/{style}]" if style else text)
        lines_out.append("".join(parts))
    return "\n".join(lines_out)


class WelcomeScreen(Screen):
    BINDINGS = [
        ("enter", "continue_smart", "Continue"),
        ("c", "edit_categories", "Edit Categories"),
        ("q", "quit", "Quit"),
        ("h", "help", "Help")
    ]

    CSS = """
    #art { content-align: center middle; height: 1fr; }
    #status { content-align: center middle; height: 3; }
    """

    def compose(self) -> ComposeResult:
        yield Static(id="art")
        yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        art_width = max(self.size.width - 4, 60)
        art_height = max(self.size.height - 8, 13)
        self.query_one("#art", Static).update(render_welcome_art(art_width, art_height))

        if summarized_file_is_fresh():
            with open(SUMMARIZED_FILE) as f:
                papers = json.load(f)
            n = len(papers)
            from cosmo_email import maybe_send_daily_email
            maybe_send_daily_email(papers)
            if goal_already_met():
                self.query_one("#status", Static).update(
                    f"Today's Papers are Ready — {n} Papers Waiting to be Labeled.\n"
                    "Enter: Continue to Choices   [bold]C[/bold]: Fetch New Papers"
                )
            else:
                self.query_one("#status", Static).update(
                    f"Today's Papers are Ready — {n} Papers Waiting to be Labeled.\n"
                    "Enter: Continue to Labels    [bold]C[/bold]: Fetch New Papers"
                )
        else:
            saved = load_saved_categories()
            if saved:
                self.query_one("#status", Static).update(
                    f"Ready to Fetch Today's Papers using {len(saved)} Previously Selected Categories.\n"
                    "Enter: Fetch Papers    [bold]C[/bold]: Edit Category Selection"
                )
            else:
                self.query_one("#status", Static).update(
                f"Ready to Fetch Today's Papers — No Saved Category Preference yet, will use all {len(CATEGORIES)}.\n"
                    "Enter: Fetch Papers    [bold]C[/bold]: Choose Categories"
                )
    def action_continue_smart(self) -> None:
        if summarized_file_is_fresh():
            if goal_already_met():
                self.app.push_screen(ChoiceScreen())
            else:
                self.app.push_screen(LabelScreen(DEFAULT_GOAL_POS, DEFAULT_GOAL_NEG))
        else:
            categories = load_saved_categories() or list(CATEGORIES)
            self.app.push_screen(FetchScreen(categories))

    def action_edit_categories(self) -> None:
        self.app.push_screen(CategoryScreen())

    def action_quit(self) -> None:
        self.app.exit()

    def action_help(self) -> None:
        self.app.push_screen(HelpModal(
            "This is Cosmo's home screen. If today's papers are already "
            "fetched, Enter takes you straight to choice menu (or to a labeling "
            ", if you haven't hit your labeling goal on a previous "
            "day). If they haven't been fetched yet, Enter starts today's "
            "fetch using whichever arXiv categories you last selected — "
            "or all categories, if you've never chosen any.",
            [("enter", "Continue"), ("c", "Edit Categories"), ("q", "Quit")]
        ))

class SettingsScreen(ModalScreen):
    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("up", "focus_previous", "Focus Previous"),
        ("down", "focus_next", "Focus Next"),
        ("c", "close", "Close"),
        ("s", "save", "Save")
        ]

    CSS = """
    SettingsScreen { align: center middle; background: rgba(0, 0, 0, 0.6); }
    #settings-box { border: round #414868; padding: 1 3; width: 60; background: #1a1b26; color: #a9b1d6; }
    #settings-title { color: #7dcfff; text-style: bold; margin-bottom: 1; }
    #settings-box Label { color: #a9b1d6; margin-top: 1; }

    #settings-box Checkbox { width: 1fr; padding: 0 1; background: #1a1b26; color: #565f89; border: none; }
    #settings-box Checkbox > .toggle--button { color: #414868; background: #1a1b26; }
    #settings-box Checkbox.-on > .toggle--button { color: #9ece6a; background: #1a1b26; }
    #settings-box Checkbox > .toggle--label { color: #565f89; }
    #settings-box Checkbox.-on > .toggle--label { color: #c0caf5; }
    #settings-box Checkbox:focus { background: #1a1b26; border: none; }
    #settings-box Checkbox:focus > .toggle--label { color: #e0af68; text-style: bold; background: #1a1b26; }
    #settings-box Checkbox:focus > .toggle--button { color: #e0af68; text-style: bold; background: #1a1b26; }

    #settings-box RadioSet { border: none; background: #1a1b26; padding: 0; }
    #settings-box RadioSet:focus { border: none; background: #1a1b26; }
    #settings-box RadioButton { background: #1a1b26; color: #565f89; }
    #settings-box RadioButton > .toggle--button { color: #414868; background: #1a1b26; }
    #settings-box RadioButton.-on > .toggle--button { color: #9ece6a; background: #1a1b26; }
    #settings-box RadioButton.-selected > .toggle--label { color: #e0af68; text-style: bold; background: #1a1b26; }

    #settings-box Input { border: round #3b4261; background: #16161e; color: #c0caf5; }
    #settings-box Input:focus { border: round #7dcfff; }
    #email-note { color: #565f89; text-style: italic; text-align: center; margin-top: 1; }
    #settings-buttons { margin-top: 1; align: center middle; height: auto; }
    #settings-buttons Button { margin: 0 1; }
    #save-settings-btn { background: #41a6b5; color: #1a1b26; border: none; }
    #close-settings-btn { background: #3b4261; color: #c0caf5; border: none; }
    .hidden { display: none; }
    """

    WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def __init__(self) -> None:
        super().__init__()
        prefs = load_preferences()
        self.initial_email = prefs.get("email", "")
        self.initial_email_opt_in = prefs.get("email_opt_in", False)
        self.initial_frequency = prefs.get("email_frequency", "daily")
        self.initial_weekday = prefs.get("email_weekday", 0)
        self.initial_count = prefs.get("email_paper_count", COSMO_PAPERS_COUNT)
        self.initial_notifications = prefs.get("desktop_notifications", True)

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-box"):
            yield Static("Settings", id="settings-title")
            yield Checkbox("Opt in to Email Address", value=self.initial_email_opt_in, id="email-opt-in-checkbox")
            yield Label("Email Address:")
            yield Input(value=self.initial_email, placeholder="you@example.com", id="email-input")

            yield Label("Email frequency:")
            with RadioSet(id="frequency-radioset"):
                yield RadioButton("Daily", value=(self.initial_frequency == "daily"), id="freq-daily")
                yield RadioButton("Weekly", value=(self.initial_frequency == "weekly"), id="freq-weekly")

            with Vertical(id="weekday-block", classes="" if self.initial_frequency == "weekly" else "hidden"):
                yield Label("Weekly on:")
                with RadioSet(id="weekday-radioset"):
                    for i, day in enumerate(self.WEEKDAYS):
                        yield RadioButton(day, value=(i == self.initial_weekday), id=f"weekday-{i}")

            yield Label("Number of papers to email:")
            yield Input(value=str(self.initial_count), placeholder="10", id="email-count-input")
            yield Checkbox("Desktop notifications when Cosmo runs automatically", value=self.initial_notifications, id="notifications-checkbox")

            yield Static(
                "Sends automatically in the background — no need to have Cosmo open.",
                id="email-note"
            )
            with Horizontal(id="settings-buttons"):
                yield Button("Save", id="save-settings-btn", variant="primary")
                yield Button("Close", id="close-settings-btn")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "frequency-radioset":
            is_weekly = event.pressed.id == "freq-weekly"
            weekday_block = self.query_one("#weekday-block", Vertical)
            if is_weekly:
                weekday_block.remove_class("hidden")
            else:
                weekday_block.add_class("hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-settings-btn":
            self._save()
        elif event.button.id == "close-settings-btn":
            self.app.pop_screen()

    def _save(self) -> None:
        email_opt_in = self.query_one("#email-opt-in-checkbox", Checkbox).value
        email = self.query_one("#email-input", Input).value.strip()

        freq_set = self.query_one("#frequency-radioset", RadioSet)
        frequency = "weekly" if freq_set.pressed_button and freq_set.pressed_button.id == "freq-weekly" else "daily"

        weekday = 0
        if frequency == "weekly":
            weekday_set = self.query_one("#weekday-radioset", RadioSet)
            if weekday_set.pressed_button is not None:
                weekday = int(weekday_set.pressed_button.id.split("-")[1])

        count_raw = self.query_one("#email-count-input", Input).value.strip()
        try:
            paper_count = max(1, int(count_raw))
        except ValueError:
            paper_count = COSMO_PAPERS_COUNT
        notifications_on = self.query_one("#notifications-checkbox", Checkbox).value


        prefs = load_preferences()
        prefs["email_opt_in"] = email_opt_in
        prefs["email"] = email
        prefs["email_frequency"] = frequency
        prefs["email_weekday"] = weekday
        prefs["email_paper_count"] = paper_count
        prefs["desktop_notifications"] = notifications_on
        save_preferences(prefs)

        self.notify("Settings saved.", severity="information")
        self.app.pop_screen()

    def action_dismiss(self) -> None:
        self.app.pop_screen()

    def action_focus_previous(self) -> None:
        self.app.action_focus_previous()

    def action_focus_next(self) -> None:
        self.app.action_focus_next()

    def action_save(self) -> None:
        self._save()

    def action_close(self) -> None:
        self.app.pop_screen()

# Category Groupings:

GROUP_LABELS = {
    "astro-ph": "astro-ph — Astrophysics",
    "cond-mat": "cond-mat — Condensed Matter",
    "nlin": "nlin — Nonlinear Sciences",
    "physics": "physics — Physics (general)",
}

STANDALONE_CATEGORIES = [
    "gr-qc", "hep-ex", "hep-lat", "hep-ph", "hep-th",
    "math-ph", "nucl-ex", "nucl-th", "quant-ph",
]

def grouped_categories() -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {label: [] for label in GROUP_LABELS.values()}
    groups["Other Core Categories"] = []
    for code in CATEGORIES:
        prefix = code.split(".")[0]
        if prefix in GROUP_LABELS:
            groups[GROUP_LABELS[prefix]].append(code)
        elif code in STANDALONE_CATEGORIES:
            groups["Other Core Categories"].append(code)
    return groups

# Screen: Category Selection
class CategoryScreen(Screen):
    """
    Checkbox multi-select over arXiv categories
    """

    BINDINGS = [
        ("up", "focus_previous", "Up"),
        ("w", "focus_previous", "Up"),
        ("down", "focus_next", "Down"),
        ("s", "focus_next", "Down"),
        ("c", "try_continue", "Continue"),
        ("h", "help", "Help"),
        ("q", "quit", "Quit"),
        ("escape", "back", "Back"),
    ]

    CSS = """
    #category-title { padding: 1 2; text-style: bold; color: #7dcfff; }
    #category-list { padding: 0 2; background: #1a1b26; }

    Collapsible { background: #1a1b26; border-top: none; }
    Collapsible > CollapsibleTitle { background: #1a1b26; }
    Collapsible > Contents { background: #1a1b26; }

    CollapsibleTitle { color: #565f89; }
    CollapsibleTitle:hover { background: #1a1b26; color: #7dcfff; }
    CollapsibleTitle:focus { background: #1a1b26; color: #ff9e64; text-style: bold underline; }

    Checkbox { width: 1fr; padding: 0 1; background: #1a1b26; color: #565f89; border: none; }
    Checkbox > .toggle--button { color: #414868; background: #1a1b26; }
    Checkbox.-on > .toggle--button { color: #9ece6a; background: #1a1b26; }
    Checkbox > .toggle--label { color: #565f89; }
    Checkbox.-on > .toggle--label { color: #c0caf5; }

    Checkbox:focus { background: #1a1b26; border: none; }
    Checkbox:focus > .toggle--label { background: #1a1b26; color: #e0af68; text-style: bold; }
    Checkbox:focus > .toggle--button { background: #1a1b26; color: #e0af68; text-style: bold; }

    #continue-btn { margin: 1 2; background: #41a6b5; color: #1a1b26; border: none; }
    #continue-btn:focus { background: #7dcfff; color: #1a1b26; border: none; }
    """


    def compose(self) -> ComposeResult:
        yield Static("Select arXiv categories to fetch papers from:", id="category-title")
        saved = load_saved_categories()
        default_selected = set(saved) if saved else set()
        with VerticalScroll(id="category-list"):
            for group_label, codes in grouped_categories().items():
                if not codes:
                    continue
                with Collapsible(title = group_label, collapsed=True):
                    for code in codes:
                        yield Checkbox(CATEGORY_LABELS.get(code, code), value = (code in default_selected), id = _safe_id(code))
        yield Button("Continue", id="continue-btn", variant = "primary")
        yield Footer()

    def action_try_continue(self) -> None:
        selected = [
            code for code in CATEGORIES
            if self.query_one(f"#{_safe_id(code)}", Checkbox).value
        ]
        if not selected:
            self.notify("Select at least one category.", severity = "warning")
            return
        save_categories(selected)
        self.app.push_screen(FetchScreen(selected))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue-btn":
            self.action_try_continue()

    def on_key(self, event) -> None:
        from textual.widgets._collapsible import CollapsibleTitle
        if event.key == "space" and isinstance(self.focused, CollapsibleTitle):
            event.stop()
            self.focused.action_toggle_collapsible()

    def action_help(self) -> None:
        self.app.push_screen(HelpModal(
            "Choose which arXiv subject categories fetch should "
            "pull papers from, grouped by broad subject area (astro-ph, "
            "cond-mat, nlin, physics, and other core categories). Expand a "
            "group to see and toggle its individual categories. Your "
            "selection is saved and reused automatically on future days "
            "until you change it here again.",
            [("space", "Toggle checkbox / expand group"), ("w/s or ↑/↓", "Move focus"), ("c", "Continue"), ("escape", "Back"), ("q", "Quit")]
        ))
    
    def action_quit(self) -> None:
        self.app.exit()
    
    def action_back(self) -> None:
        self.app.pop_screen()

    def action_focus_previous(self) -> None:
        self.app.action_focus_previous()

    def action_focus_next(self) -> None:
        self.app.action_focus_next()


# Screen: Fetching Papers

class FetchScreen(Screen):

    BINDINGS = [
        ("c", "continue_to_label", "Continue"),
        ("h", "help", "Help"),
        ("q", "quit", "Quit"),
    ]
        
    CSS = """
    #fetch-panel { border: round #414868; margin: 1 2; background: #1a1b26; }
    #fetch-log { height: auto; border: none; background: #1a1b26; color: #a9b1d6; }
    #fetch-art { content-align: center top; height: 1fr; }
    #flavor-text { text-align: center; color: #a9b1d6; text-style: italic; }
    #progress-stack { align: center middle; height: auto; margin: 1 2; }
    #summary-progress-block { align: center middle; height: auto; width: auto; }
    #fetch-progress { width: auto; }
    Bar > .bar--bar { color: #7aa2f7; background: #1a1b26; }
    Bar > .bar--complete { color: #9ece6a; background: #1a1b26; }
    #to-label-btn { margin: 1 2; background: #41a6b5; color: #1a1b26; border: none; }
    #to-label-btn:focus { background: #7dcfff; color: #1a1b26; border: none; }
    """


    def __init__(self, categories: list[str]) -> None:
        super().__init__()
        self.categories = categories
        self._fetch_done = False
        

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="fetch-panel"):
            yield Log(id="fetch-log")
            yield Static(id='fetch-art')
            yield Static("", id="flavor-text")
            with Vertical(id="progress-stack"):
                with Vertical(id="summary-progress-block"):
                    yield ProgressBar(total=100, id="fetch-progress", show_eta=True)
        yield Footer()

    def on_mount(self) -> None:
        art_width = max(self.size.width - 4, 60)
        art_height = max(self.size.height - 22, 8)
        self.query_one("#fetch-art", Static).update(render_welcome_art(art_width, art_height))
        self._flavor_queue: list[str] = []
        self._flavor_timer = self.set_interval(4.5, self._cycle_flavor)
        self.run_fetch_and_summarize()

    def _cycle_flavor(self)-> None:
        if not self._flavor_queue:
            self._flavor_queue = FLAVOR_MESSAGES.copy()
            random.shuffle(self._flavor_queue)
        text = self._flavor_queue.pop()
        self.query_one("#flavor-text", Static).update(text)

    @work(thread=True)
    def run_fetch_and_summarize(self) -> None:
        log = self.query_one("#fetch-log", Log)
        progress = self.query_one("#fetch-progress", ProgressBar)
        worker = get_current_worker()

        def log_line(text: str) -> None:
            if not worker.is_cancelled:
                self.app.call_from_thread(log.write_line, text)
        
        if is_arxiv_closed_today():
            log_line("It's the weekend/holiday — no new papers are posted. Exiting.")
            self.app.call_from_thread(self._show_continue_button)
            return
        
        log_line(f"Fetching today's feed for categories...")
        papers = fetch_today(self.categories)

        if not papers:
            log_line("No papers fetched. If it's a weekday/holiday, something may be wrong.")
            self.app.call_from_thread(self._show_continue_button)
            return
        
        log_line(f"Fetched {len(papers)} papers.")
        with open(RAW_FILE, "w") as f:
            json.dump(papers, f, indent=2)

        log_line("Summarizing papers abstracts (this may take a while)...")

        def on_progress(done: int, total: int) -> None:
            if not worker.is_cancelled:
                self.app.call_from_thread(progress.update, total=total, progress = done)

        papers = summarize_all(papers, progress_callback = on_progress, should_continue = lambda: not worker.is_cancelled)
        if worker.is_cancelled:
            return

        with open(SUMMARIZED_FILE, "w") as f:
            json.dump(papers, f, indent=2)
        log_line(f"Done - {len(papers)} papers summarized.")

        log_line("Generating embeddings for classifier training...")
        existing_embeddings, existing_ids = load_existing_embeddings()
        existing_ids_set = set(existing_ids)
        new_papers = [p for p in papers if p["arxiv_id"] not in existing_ids_set]

        if not new_papers:
            log_line("No new papers to embed - all papers already have embeddings.")
        else:
            new_embeddings = embed_all(new_papers, show_progress = False)
            if existing_embeddings is not None:
                embeddings = np.concatenate([existing_embeddings, new_embeddings])
                arxiv_ids = existing_ids + [p["arxiv_id"] for p in new_papers]
            else:
                embeddings = new_embeddings
                arxiv_ids = [p["arxiv_id"] for p in new_papers]

            np.save(EMBEDDINGS_FILE, embeddings)
            from cosmo_email import maybe_send_daily_email
            maybe_send_daily_email(papers)
            with open(EMBEDDING_IDS_FILE, "w") as f:
                json.dump(arxiv_ids, f, indent=2)
            log_line(f"Done - {embeddings.shape[0]} embeddings saved total.")

        self.app.call_from_thread(self._show_continue_button)

    def _show_continue_button(self) -> None:
        self._flavor_timer.stop()
        self.query_one("#flavor-text", Static).update("")
        self._fetch_done = True
        self.mount(Button("Continue", id = "to-label-btn", variant = "primary"))

    def action_continue_to_label(self) -> None:
        if not self._fetch_done:
            return
        if goal_already_met():
            self.app.push_screen(ChoiceScreen())
        else:
            self.app.push_screen(LabelScreen(DEFAULT_GOAL_POS, DEFAULT_GOAL_NEG))

    def action_quit(self) -> None:
        self.workers.cancel_all()
        self.app.exit()

    def action_help(self) -> None:
        self.app.push_screen(HelpModal(
            "This screen runs automatically — no input needed. It fetches "
            "today's new papers from arXiv for your selected categories, "
            "summarizes each abstract into a short blurb using a local AI "
            "model on your device, and generates embeddings (a numeric "
            "fingerprint of each paper's topic) used later to train your "
            "Cosmo on personal preference. A Continue option appears once "
            "all three steps finish.",
            [("c", "Continue (once fetching finishes)"), ("q", "Quit")]
        ))
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "to-label-btn":
            if goal_already_met():
                self.app.push_screen(ChoiceScreen())
            else:
                self.app.push_screen(LabelScreen(DEFAULT_GOAL_POS, DEFAULT_GOAL_NEG))

# Screen: Set a Labeling Goal

# class GoalScreen(Screen):

#     BINDINGS = [("h", "help", "Help")]

#     CSS = """
#     #goal-form { padding: 2 4; }
#     #goal-form Input { margin-bottom: 1; }
#     """

#     def compose(self) -> ComposeResult:
#         yield Header()
#         with Vertical(id="goal-form"):
#             yield Label("Target number of Interested Papers:")
#             yield Input(placeholder = "e.g. 50 (blank = no goal)", id = "goal-pos")
#             yield Label("Target number of Uninterested Papers:")
#             yield Input(placeholder = "e.g. 50 (blank = no goal)", id = "goal-neg")
#             yield Static("[dim]Suggested: 150+ each, kept roughly balanced, for a usable baseline classifier.[/]",
#                         id = "goal-hint")
#             yield Button("Start Labeling", id="start-btn", variant = "primary")
#         yield Footer()

#     def on_button_pressed(self, event: Button.Pressed) -> None:
#         if event.button.id == "start-btn":
#             pos_raw = self.query_one("#goal-pos", Input).value.strip()
#             neg_raw = self.query_one("#goal-neg", Input).value.strip()
#             goal_pos = int(pos_raw) if pos_raw.isdigit() else None
#             goal_neg = int(neg_raw) if neg_raw.isdigit() else None
#             self.app.push_screen(LabelScreen(DEFAULT_GOAL_POS, DEFAULT_GOAL_NEG))

#     def action_continue_to_label(self) -> None:
#         if not self._fetch_done:
#             return
#         self.app.push_screen(LabelScreen(DEFAULT_GOAL_POS, DEFAULT_GOAL_NEG))

#     def action_quit(self) -> None:
#         self.app.exit()

#     def action_help(self) -> None:
#         self.app.push_screen(HelpModal(
#             "Fetching, summarizing, and embedding today's papers happens automatically here.",
#             [("c", "Continue (once fetching finishes)"), ("q", "Quit")]
#        ))


# Screen: Choices
# Used to select between labeling and Cosmo papers

class ChoiceScreen(Screen):
    BINDINGS = [
        ("up", "focus_previous", "Up"),
        ("w", "focus_previous", "Up"),
        ("down", "focus_next", "Down"),
        ("s", "focus_next", "Down"),
        ("h", "help", "Help"),
        ("q", "quit", "Quit")
    ]

    CSS = """
    #choice-stars-top, #choice-stars-bottom { height: 1fr; content-align: center middle; color: #565f89; }
    #choice-row { height: auto; align: center middle; }
    #choice-stars-left, #choice-stars-right { width: 1fr; height: 100%; content-align: center middle; color: #565f89; }
    #choice-panel { border: round #414868; padding: 1 4; background: #1a1b26; width: auto; height: auto; }
    #choice-title { text-align: center; text-style: bold; color: #7dcfff; margin-bottom: 1; text_style: underline; }

    #choice-panel Button { width: 30; height: 1; border: none; background: #1a1b26; color: #565f89; margin: 0; }
    #choice-panel Button:focus { background: #1a1b26; color: #e0af64; text-style: bold; border: none; }
    """


    def compose(self) -> ComposeResult:
        yield Static(id="choice-stars-top")
        with Horizontal(id="choice-row"):
            yield Static(id="choice-stars-left")
            with Vertical(id="choice-panel"):
                yield Static("Choose:", id="choice-title")
                yield Button("Cosmo Papers", id="cosmo-paper-btn")
                yield Button("Daily Labeling", id="daily-btn")
                yield Button("Indefinite Labeling", id="keep-labeling-btn")
            yield Static(id="choice-stars-right")
        yield Static(id="choice-stars-bottom")
        yield Footer()

    def on_mount(self) -> None:
        self.call_after_refresh(self._render_stars)

    def _render_stars(self) -> None:
        top = self.query_one("#choice-stars-top", Static)
        bottom = self.query_one("#choice-stars-bottom", Static)
        left = self.query_one("#choice-stars-left", Static)
        right = self.query_one("#choice-stars-right", Static)

        top.update(render_starfield(top.size.width, top.size.height))
        bottom.update(render_starfield(bottom.size.width, bottom.size.height))
        left.update(render_starfield(left.size.width, left.size.height))
        right.update(render_starfield(right.size.width, right.size.height))

    def on_key(self, event) -> None:
        if event.key == "space" and isinstance(self.focused, Button):
            event.stop()
            self.focused.action_press()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cosmo-paper-btn":
            self.action_pick_cosmo_papers()
        elif event.button.id == "daily-btn":
            self.action_pick_daily()
        elif event.button.id == "keep-labeling-btn":
            self.action_pick_keep_labeling()

    def action_pick_cosmo_papers(self) -> None:
        cached = load_cosmo_papers()
        if cached is not None:
            self.app.push_screen(CosmoPaperScreen(cached))
            return

        from classify import load_embeddings, load_labels, build_training_set, train_and_evaluate, score_all_papers
        embeddings_by_id = load_embeddings()
        labels = load_labels()
        X, y = build_training_set(embeddings_by_id, labels)
        clf = train_and_evaluate(X, y)
        if clf is None:
            self.notify("Not enough labeled data yet to train a classifier.", severity = "warning")
            return
        
        with open(SUMMARIZED_FILE) as f:
            papers = json.load(f)
        labeled_ids = {row["arxiv_id"] for row in labels}
        scored_all = score_all_papers(clf, embeddings_by_id, papers)
        unlabeled_scored = [(score, paper) for score, paper in scored_all if paper["arxiv_id"] not in labeled_ids]
        top_papers = unlabeled_scored[:COSMO_PAPERS_COUNT]

        if not top_papers:
            self.notify("No unlabeled papers with embeddings available right now.", severity = "warning")
            return
        
        save_cosmo_papers_cache(top_papers)
        self.app.push_screen(CosmoPaperScreen(top_papers))

    def action_pick_daily(self) -> None:
        if get_daily_progress() >= DAILY_LABEL_GOAL:
            prefs = load_preferences()
            streak = prefs.get("daily_streak", 0)
            total = prefs.get("total_daily_completions", 0)
            from classify import load_embeddings, load_labels, build_training_set, cross_val_accuracy
            embeddings_by_id = load_embeddings()
            labels = load_labels()
            X, y = build_training_set(embeddings_by_id, labels)
            accuracy = cross_val_accuracy(X, y)
            n_labels = len(labels)
            on_this_day = get_today_in_history()
            self.app.push_screen(CongratsModal(streak, total, accuracy, n_labels, on_this_day))
            return

        from classify import load_embeddings, load_labels, build_training_set, train_and_evaluate, cross_val_accuracy, select_most_uncertain
        embeddings_by_id = load_embeddings()
        labels = load_labels()
        X, y = build_training_set(embeddings_by_id, labels)
        clf = train_and_evaluate(X, y)
        if clf is None:
            self.notify("Not enough labeled data yet to train a classifier.", severity = "warning")
            return
        baseline_accuracy = cross_val_accuracy(X, y)

        with open(SUMMARIZED_FILE) as f:
            papers = json.load(f)
        labeled_ids = {row["arxiv_id"] for row in labels}
        scored = select_most_uncertain(embeddings_by_id, papers, labeled_ids, clf, n = DAILY_LABEL_GOAL)
        selected_papers = [paper for _, paper in scored]

        if not selected_papers:
            self.notify("No unlabeled papers with embeddings available right now.", severity = "warning")
            return

        self.app.push_screen(DailyLabelScreen(selected_papers, baseline_accuracy))

    def action_pick_keep_labeling(self) -> None:
        self.app.push_screen(LabelScreen(DEFAULT_GOAL_POS, DEFAULT_GOAL_NEG, return_to_choice = True))

    def action_help(self) -> None:
        self.app.push_screen(HelpModal(
            "Now that you've hit your labeling goal, you can choose how to " 
            "spend your sessions. Cosmo Papers will show your classifier's "
            "top-scored picks from today's arXiv fetch. Daily Labeling will "
            "ask you to label just a handful of the papers your classifier "
            "is least confident about, completing it gives a daily reward. "
            "Indefinite Labeling lets you keep manually labeling papers with "
            "no set goal — your running totals are shown instead of progress bars. ",
            [("w/s or ↑/↓", "Move focus"), ("space/enter", "Select"), ("q", "Quit")]
        ))

    def action_quit(self) -> None:
        self.app.exit()

    def action_focus_previous(self) -> None:
        self.app.action_focus_previous()

    def action_focus_next(self) -> None:
        self.app.action_focus_next()


# Screen: Labeling Papers
# Used to train classifier on user's preferences

class LabelScreen(Screen):
    BINDINGS = [
        ("y", "answer('1')", "Interesting"),
        ("n", "answer('0')", "Not Interesting"),
        ("s", "skip()", "Skip"),
        ("b", "back()", "Back"),
        ("d", "detail()", "Detail"),
        ("r", "result()", "Result"),
        ("o", "open_link()", "Open Link"),
        Binding("escape", "back_to_choice", "Back to Menu", show=False),
        ("h", "help()", "Help"),
        ("q", "quit_labeling()", "Quit")
    ]

    CSS = """
    #paper-box { border: round #414868; padding: 1 2; margin: 1 2; height: 1fr; background: #1a1b26; color: #a9b1d6; }
    #paper-header { height: auto; }
    #paper-title { width: 1fr; }
    #session-count { width: auto; color: #565f89; }
    #goal-progress-row { height: 4; margin: 1 2; }
    #pos-progress-col, #neg-progress-col { width: 1fr; padding: 0 1; }
    #pos-label, #neg-label { color: #7dcfff; text-style: underline; }
    #goal-hint { margin: 0 2 1 2; color: #565f89; text-style: italic; }
    #progress-pos > Bar > .bar--bar { color: #9ece6a; background: #1a1b26; }
    #progress-pos > Bar > .bar--complete { color: #9ece6a; background: #1a1b26; }
    #progress-neg > Bar > .bar--bar { color: #f7768e; background: #1a1b26; }
    #progress-neg > Bar > .bar--complete { color: #f7768e; background: #1a1b26; }
    #explanation { border: round #3b4261; padding: 1 2; margin: 0 2 1 2; background: #16161e; color: #9aa5ce; }
    #pos-count { color: #9ece6a; text-style: bold; }
    #neg-count { color: #f7768e; text-style: bold; }
    .hidden { display: none; }
    """

    def __init__(self, goal_pos: int | None, goal_neg: int | None, return_to_choice: bool = False) -> None:
        super().__init__()
        self.goal_pos = goal_pos
        self.goal_neg = goal_neg
        self.return_to_choice = return_to_choice
        self.papers: list[dict] = []
        self.index = 0
        self.pre_existing: list[dict] = []
        self.session_decisions: dict[str, dict] = {}
        self.explanation_cache: dict[str, dict[str, str]] = {}
        self.goal_announced = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="goal-progress-row"):
            with Vertical(id="pos-progress-col"):
                yield Static("Interesting Papers", id="pos-label")
                yield ProgressBar(total=self.goal_pos, id="progress-pos", show_eta=False)
                yield Static("", id = "pos-count", classes="hidden")
            with Vertical(id="neg-progress-col"):
                yield Static("Not Interesting Papers", id="neg-label")
                yield ProgressBar(total=self.goal_neg, id="progress-neg", show_eta=False)
                yield Static("", id = "neg-count", classes="hidden")
        if goal_already_met():
            yield Static(
                "Label Goal Reached! Continued Labeling Improves Cosmo.",
                id="goal-hint"
            )
        else:
            yield Static(
                f"Aim for at least {self.goal_pos} Interesting and {self.goal_neg} Not Interesting papers, for a balanced baseline classifier. ", id="goal-hint"
            )
        with Vertical(id="paper-box"):
            with Horizontal(id="paper-header"):
                yield Static("", id="paper-title")
                yield Static("", id="session-count")
            yield Static(id="paper-body")
        yield Static(id="explanation")
        yield Footer()

    def on_mount(self) -> None:
        with open(SUMMARIZED_FILE) as f:
            self.papers = json.load(f)
        all_papers = interleave_by_category(self.papers)

        self.pre_existing = load_all_labels(LABELS_FILE)
        pre_ids = {r["arxiv_id"] for r in self.pre_existing}
        self.papers = [p for p in all_papers if p["arxiv_id"] not in pre_ids]

        if not self.papers:
            self.query_one("#paper-body", Static).update("No new papers to label. All papers labeled for today.")
            return
        
        self.render_paper()

    def current_label(self) -> str | None:
        if not self.papers or self.index >= len(self.papers):
            return None
        arxiv_id = self.papers[self.index]["arxiv_id"]
        existing = self.session_decisions.get(arxiv_id)
        return existing["label"] if existing else None
    
    def _cumulative_count(self, label: str) -> int:
        pre_count = sum(1 for r in self.pre_existing if r["label"] == label)
        session_count = sum(1 for r in self.session_decisions.values() if r["label"] == label)
        return pre_count + session_count
    
    def _update_progress(self)-> None:
        n_pos = self._cumulative_count("1")
        n_neg = self._cumulative_count("0")
        reached = self.goal_reached()

        progress_pos = self.query_one("#progress-pos", ProgressBar)
        progress_neg = self.query_one("#progress-neg", ProgressBar)
        count_pos = self.query_one("#pos-count", Static)
        count_neg = self.query_one("#neg-count", Static)

        if reached:
            progress_pos.add_class("hidden")
            progress_neg.add_class("hidden")
            count_pos.remove_class("hidden")
            count_neg.remove_class("hidden")
            count_pos.update(f"{n_pos}")
            count_neg.update(f"{n_neg}")
        else:
            progress_pos.remove_class("hidden")
            progress_neg.remove_class("hidden")
            count_pos.add_class("hidden")
            count_neg.add_class("hidden")
            progress_pos.update(progress = min(n_pos, self.goal_pos))
            progress_neg.update(progress = min(n_neg, self.goal_neg))
    
    def render_paper(self) -> None:
        self.query_one("#explanation", Static).update("")
        self._update_progress()

        paper = self.papers[self.index]
        current = self.current_label()
        label_note = ""
        if current is not None:
            desc = "Interesting" if current == "1" else "Not interesting"
            label_note = f"\n[#e0af68](Currently labeled: {desc} - answering again changes this)[/]"

        self.query_one("#paper-title", Static).update(f"[#7dcfff]Title:[/#7dcfff] {escape_markup(paper['title'])}")
        self.query_one("#session-count", Static).update(f"({self.index + 1}/{len(self.papers)})")
        self.query_one("#paper-body", Static).update(
            f"[#7dcfff]Category:[/#7dcfff] {escape_markup(paper.get('categories', 'unknown'))}\n\n"
            f"[#7dcfff]Summary:[/#7dcfff]\n{escape_markup(paper['short_description'])}\n\n"
            f"[#7dcfff]Link:[/#7dcfff] [link='{paper['link']}'][#7aa2f7 underline]{paper['link']}[/#7aa2f7 underline][/link]"
            f"{label_note}"
        )

    def goal_reached(self) -> bool:
        n_pos = self._cumulative_count("1")
        n_neg = self._cumulative_count("0")
        return n_pos >= self.goal_pos and n_neg >= self.goal_neg
        
    def flush(self) -> None:
        write_labels(LABELS_FILE, self.pre_existing + list(self.session_decisions.values()))

    def advance(self) -> None:
        self.index += 1
        self._update_progress()


        if self.goal_reached() and not self.goal_announced:
            self.goal_announced = True
            self.notify(
                "Goal reached! Keep labeling any time - press q whenever you're done.",
                severity = "information",
                timeout = 6,
            )

        if self.index >=(self.papers):
            self.query_one("#paper-title", Static).update("")
            self.query_one("#session-count", Static).update("")
            self.query_one("#paper-body", Static).update(
            "No more papers to review this session."
            )
            return
        self.render_paper()

    def action_answer(self, label: str) -> None:
        if not self.papers or self.index >= len(self.papers):
            return
        paper = self.papers[self.index]
        self.session_decisions[paper["arxiv_id"]] = {
            "arxiv_id": paper["arxiv_id"],
            "title": paper["title"],
            "link": paper["link"],
            "label": label,
            "labeled_at": datetime.now(timezone.utc).isoformat()
        }
        self.flush()
        self.advance()

    def action_skip(self) -> None:
        if not self.papers or self.index >= len(self.papers):
            return
        paper = self.papers[self.index]
        self.session_decisions.pop(paper["arxiv_id"], None)
        self.flush()
        self.advance()

    def action_back(self) -> None:
        if self.index == 0:
            self.notify("Already at first paper - can't go back.", severity = "warning")
            return
        self.index -= 1
        self.render_paper()

    def action_detail(self) -> None:
        self.show_explanation("detail", explain_simply, "Detail Explanation")

    def action_result(self) -> None:
        self.show_explanation("result", explain_result, "Key Result")

    def show_explanation(self, kind: str, fn, label_prefix: str) -> None:
        paper = self.papers[self.index]
        cached = self.explanation_cache.get(paper["arxiv_id"], {}).get(kind)
        if cached is not None:
            self.query_one("#explanation", Static).update(f"{label_prefix}: {cached}")
        else:
            self.run_explanation(paper["arxiv_id"], kind, fn, label_prefix)

    @work(thread=True)
    def run_explanation(self, arxiv_id: str, kind: str, fn, label_prefix: str) -> None:
        paper = self.papers[self.index]
        text = fn(paper["abstract"])
        self.explanation_cache.setdefault(arxiv_id, {})[kind] = text
        self.app.call_from_thread(
            self.query_one("#explanation", Static).update,
            f"{label_prefix}: {text}"
        )
    
    def action_open_link(self) -> None:
        if self.papers and self.index < len(self.papers):
            webbrowser.open(self.papers[self.index]["link"])

    def action_quit_labeling(self) -> None:
        self.app.exit()

    def action_back_to_choice(self) -> None:
        if self.return_to_choice:
            self.app.pop_screen()

    def action_help(self) -> None:
        bindings = [("y", "Interesting"), ("n", "Not interesting"), ("s", "Skip"), ("b", "Back"), ("d", "Detail Explanation"), ("r", "Key Result Explanation"), ("o", "Open's Paper in Browser")]
        if self.return_to_choice:
            bindings.append(("esc", "Back to Menu"))
        bindings.append(("q", "Quit"))
        self.app.push_screen(HelpModal(
            "Label each paper as Interesting or Not Interesting to build "
            "training data for your classifier — every answer saves "
            "immediately, so it's always safe to quit and resume later. "
            "While you're still working toward your baseline goal, two "
            "progress bars track how close you are to each target; once "
            "the goal is reached, those switch to plain running counts "
            "instead. Detail and Key Result generate short explanations "
            "of the current paper on demand.",
            bindings
        ))

PHYSICS_PUNS = [
    "You've got a lot of potential... energy, that is.",
    "That labeling session had real gravity to it.",
    "You're operating at peak efficiency — no entropy wasted.",
    "Nice work — that's a positive result at high confidence.",
    "You brought the noise down and the signal up.",
    "That was a stellar session, no dark matter involved.",
    "You just did some serious heavy lifting — Newton would approve.",
    "Your consistency is basically a conserved quantity at this point.",
    "That's what I call a well-calibrated detector.",
    "You're clearly in your ground state of focus.",
]

class CongratsModal(ModalScreen):
    BINDINGS = [("escape", "dismiss", "Close"), ("enter", "dismiss", "Close"), ("space", "dismiss", "Close")]

    CSS = """
    CongratsModal { align: center middle; background: rgba(0, 0, 0, 0.6); }
    #congrats-box { border: round #e0af68; padding: 1 3; width: 60; background: #1a1b26; color: #a9b1d6; text-align: center; }
    #congrats-title { color: #e0af68; text-style: bold; margin-bottom: 1; }
    #history-title { color: #7dcfff; text-style: bold; margin-top: 1; }
    #history-text { color: #9aa5ce; text-style: italic; }
    #pun-line { color: #565f89; margin-top: 1; }
    """

    def __init__(self, streak: int, total: int, accuracy: float | None, n_labels: int,  on_this_day: dict | None) -> None:
        super().__init__()
        self.streak = streak
        self.total = total
        self.accuracy = accuracy
        self.n_labels = n_labels
        self.on_this_day = on_this_day

    def compose(self) -> ComposeResult:
        with Vertical(id="congrats-box"):
            yield Static("Daily Goal Complete!", id="congrats-title")
            streak_line = f"{self.streak}-day streak!" if self.streak > 1 else "First one in the books!"
            yield Static(streak_line)
            yield Static(f"{self.total} daily sessions completed all-time.")

            if self.accuracy is not None:
                yield Static(f"Current Cosmo Accuracy: {self.accuracy:.1%}")
            if self.on_this_day:
                yield Static(f"On this day in {self.on_this_day['year']}:", id="history-title")
                yield Static(escape_markup(self.on_this_day["event"]), id="history-text")

            yield Static(random.choice(PHYSICS_PUNS), id="pun-line")
            yield Static("\nPress enter or escape to continue.")

    def action_dismiss(self) -> None:
        self.app.pop_screen()

class DailyLabelScreen(Screen):
    BINDINGS = [
        ("y", "answer('1')", "Interesting"),
        ("n", "answer('0')", "Not Interesting"),
        ("s", "skip()", "Skip"),
        ("d", "detail()", "Detail"),
        ("r", "result()", "Result"),
        ("o", "open_link()", "Open Link"),
        Binding("escape", "back_to_choice", "Back to Menu", show=False),
        ("h", "help()", "Help"),
        ("q", "quit_labeling()", "Quit"),
    ]

    CSS = """
    #daily-progress-col { height: auto; margin: 1 2; align: center middle; }
    #daily-progress-label { color: #7dcfff; text-style: underline; }
    Bar > .bar--bar { color: #e0af68; background: #1a1b26; }
    Bar > .bar--complete { color: #9ece6a; background: #1a1b26; }
    #paper-box { border: round #414868; padding: 1 2; margin: 1 2; height: 1fr; background: #1a1b26; color: #a9b1d6; }
    #paper-header { height: auto; }
    #paper-title { width: 1fr; }
    #session-count { width: auto; color: #565f89; }
    #explanation { border: round #3b4261; padding: 1 2; margin: 0 2 1 2; background: #16161e; color: #9aa5ce; }
    """

    def __init__(self, papers: list[dict], baseline_accuracy: float | None) -> None:
        super().__init__()
        self.papers = papers
        self.baseline_accuracy = baseline_accuracy
        self.index = 0
        self.session_decisions: dict[str, dict] = {}
        self.explanation_cache: dict[str, dict[str, str]] = {}
        self.labeled_count = get_daily_progress()

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="daily-progress-col"):
            yield Static("Daily Progress", id="daily-progress-label")
            yield ProgressBar(total=DAILY_LABEL_GOAL, id="daily-progress", show_eta=False)
        with Vertical(id="paper-box"):
            with Horizontal(id="paper-header"):
                yield Static("", id="paper-title")
                yield Static("", id="session-count")
            yield Static(id="paper-body")
        yield Static(id="explanation")
        yield Footer()

    def on_mount(self) -> None:
        if not self.papers:
            self.query_one("#paper-body", Static).update(
                "No uncertain papers available right now — try Indefinite Labeling instead."
            )
            return
        self.render_paper()

    def render_paper(self) -> None:
        self.query_one("#explanation", Static).update("")
        self.query_one("#daily-progress", ProgressBar).update(progress=self.labeled_count)

        paper = self.papers[self.index]
        self.query_one("#paper-title", Static).update(f"[#7dcfff]Title:[/#7dcfff] {escape_markup(paper['title'])}")
        self.query_one("#session-count", Static).update(f"({self.index + 1}/{len(self.papers)})")
        self.query_one("#paper-body", Static).update(
            f"[#7dcfff]Category:[/#7dcfff] {escape_markup(paper.get('categories', 'unknown'))}\n\n"
            f"[#7dcfff]Summary:[/#7dcfff]\n{escape_markup(paper['short_description'])}\n\n"
            f"[#7dcfff]Link:[/#7dcfff] [link='{paper['link']}'][#7aa2f7 underline]{paper['link']}[/#7aa2f7 underline][/link]"
        )

    def flush(self) -> None:
        pre_existing = load_all_labels(LABELS_FILE)
        write_labels(LABELS_FILE, pre_existing + list(self.session_decisions.values()))

    def advance(self) -> None:
        self.index += 1
        self.query_one("#daily-progress", ProgressBar).update(progress=self.labeled_count)

        if self.labeled_count >= DAILY_LABEL_GOAL:
            from classify import load_embeddings, load_labels, build_training_set, cross_val_accuracy
            result = record_daily_completion()

            embeddings_by_id = load_embeddings()
            labels = load_labels()
            X, y = build_training_set(embeddings_by_id, labels)
            accuracy = cross_val_accuracy(X, y)
            n_labels = len(labels)

            on_this_day = get_today_in_history()
            self.app.pop_screen()
            self.app.push_screen(CongratsModal(result["streak"], result["total"], accuracy, n_labels, on_this_day))
            return

        if self.index >= len(self.papers):
            self.query_one("#paper-title", Static).update("")
            self.query_one("#session-count", Static).update("")
            self.query_one("#paper-body", Static).update("No more papers available for today's daily set.")
            return
        self.render_paper()

    def action_answer(self, label: str) -> None:
        if not self.papers or self.index >= len(self.papers):
            return
        paper = self.papers[self.index]
        self.session_decisions[paper["arxiv_id"]] = {
            "arxiv_id": paper["arxiv_id"],
            "title": paper["title"],
            "link": paper["link"],
            "label": label,
            "labeled_at": datetime.now(timezone.utc).isoformat()
        }
        self.labeled_count += 1
        set_daily_progress(self.labeled_count)
        self.flush()
        self.advance()

    def action_skip(self) -> None:
        if not self.papers or self.index >= len(self.papers):
            return
        self.index += 1
        if self.index >= len(self.papers):
            self.query_one("#paper-title", Static).update("")
            self.query_one("#session-count", Static).update("")
            self.query_one("#paper-body", Static).update("No more papers available for today's daily set.")
            return
        self.render_paper()

    def action_detail(self) -> None:
        if not self.papers or self.index >= len(self.papers):
            return
        self.show_explanation("detail", explain_simply, "Detail Explanation")

    def action_result(self) -> None:
        if not self.papers or self.index >= len(self.papers):
            return
        self.show_explanation("result", explain_result, "Key Result")

    def show_explanation(self, kind: str, fn, label_prefix: str) -> None:
        paper = self.papers[self.index]
        cached = self.explanation_cache.get(paper["arxiv_id"], {}).get(kind)
        if cached is not None:
            self.query_one("#explanation", Static).update(f"{label_prefix}: {cached}")
        else:
            self.run_explanation(paper["arxiv_id"], kind, fn, label_prefix)

    @work(thread=True)
    def run_explanation(self, arxiv_id: str, kind: str, fn, label_prefix: str) -> None:
        paper = self.papers[self.index]
        text = fn(paper["abstract"])
        self.explanation_cache.setdefault(arxiv_id, {})[kind] = text
        self.app.call_from_thread(
            self.query_one("#explanation", Static).update,
            f"{label_prefix}: {text}"
        )

    def action_open_link(self) -> None:
        if not self.papers or self.index >= len(self.papers):
            return
        webbrowser.open(self.papers[self.index]["link"])

    def action_back_to_choice(self) -> None:
        self.app.pop_screen()

    def action_quit_labeling(self) -> None:
        self.app.exit()

    def action_help(self) -> None:
        self.app.push_screen(HelpModal(
            "Daily Labeling picks the handful of papers your classifier is "
            "currently least confident about, so labeling just a few of "
            "them gives outsized improvement for minimal effort. Completing "
            "all 5 shows a congratulations screen and updates your streak.",
            [("y", "Interesting"), ("n", "Not interesting"), ("s", "Skip"), ("d", "Detail Explanation"), ("r", "Key Result Explanation"), ("o", "Open's Paper in Browser"), ("esc", "Back to Menu"), ("q", "Quit")]
        ))

class CosmoPaperScreen(Screen):
    BINDINGS = [
        ("n", "next_paper()", "Next Paper"),
        ("up", "next_paper()", "Next Paper"),
        ("p", "prev_paper()", "Previous Paper"),
        ("down", "prev_paper()", "Previous Paper"),
        ("s", "star()", "Star Paper"),
        ("x", "reject()", "Not Interesting"),
        ("d", "detail()", "Detail"),
        ("r" , "result()", "Result"),
        ("o", "open_link()", "Open Link"),
        Binding("escape", "back_to_choice", "Back to Menu", show=False),
        ("h", "help()", "Help"),
        ("q", "quit()", "Quit")
    ]

    CSS = """
    #cosmo-header { height: auto; margin: 1 2; color: #7dcfff; text-style: underline; }
    #paper-box { border: round #414868; padding: 1 2; margin: 1 2; height: 1fr; background: #1a1b26; color: #a9b1d6; }
    #paper-header { height: auto; }
    #paper-title { width: 1fr; }
    #session-count { width: auto; color: #565f89; }
    #explanation { border: round #3b4261; padding: 1 2; margin: 0 2 1 2; background: #16161e; color: #9aa5ce; }
    """

    def __init__(self, scored_papers: list[tuple[float, dict]]) -> None:
        super().__init__()
        self.scored_papers = scored_papers
        self.index = 0
        self.starred_ids: set[str] = set()
        self.star_timestamps: dict[str, str] = {}
        self.rejected_ids: set[str] = set()
        self.reject_timestamps: dict[str, str] = {}
        self.explanation_cache: dict[str, dict[str, str]] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Cosmo Papers - Today's Top Picks", id="cosmo-header")
        with Vertical(id="paper-box"):
            with Horizontal(id="paper-header"):
                yield Static("", id="paper-title")
                yield Static("", id="session-count")
            yield Static(id="paper-body")
        yield Static(id="explanation")
        yield Footer()

    def on_mount(self) -> None:
        if not self.scored_papers:
            self.query_one("#paper-body", Static).update("No scored papers available right now.")
            return
        self.render_paper()

    def render_paper(self) -> None:
        self.query_one("#explanation", Static).update("")
        score, paper = self.scored_papers[self.index]
        arxiv_id = paper["arxiv_id"]
        if arxiv_id in self.starred_ids:
            status_note = "  [#e0af68 bold]★ Starred[/#e0af68 bold]"
        elif arxiv_id in self.rejected_ids:
            status_note = "  [#f7768e bold]✗ Not Interesting[/#f7768e bold]"
        else:
            status_note = ""

        self.query_one("#paper-title", Static).update(f"[#7dcfff]Title:[/#7dcfff] {escape_markup(paper['title'])}{status_note}")
        self.query_one("#session-count", Static).update(f"({self.index + 1}/{len(self.scored_papers)}) Score: {score:.0%}")
        self.query_one("#paper-body", Static).update(
            f"[#7dcfff]Category:[/#7dcfff] {escape_markup(paper.get('categories', 'unknown'))}\n\n"
            f"[#7dcfff]Summary:[/#7dcfff]\n{escape_markup(paper['short_description'])}\n\n"
            f"[#7dcfff]Link:[/#7dcfff] [link='{paper['link']}'][#7aa2f7 underline]{paper['link']}[/#7aa2f7 underline][/link]"
        )

    def action_next_paper(self) -> None:
        if self.index < len(self.scored_papers) - 1:
            self.index += 1
            self.render_paper()

    def action_prev_paper(self) -> None:
        if self.index > 0:
            self.index -= 1
            self.render_paper()

    def action_star(self) -> None:
        if not self.scored_papers:
            return
        _, paper = self.scored_papers[self.index]
        arxiv_id = paper["arxiv_id"]

        if paper["arxiv_id"] in self.starred_ids:
            self._clear_star(arxiv_id)
        else:
            if arxiv_id in self.rejected_ids:
                self._clear_reject(arxiv_id)
            
            now = datetime.now(timezone.utc).isoformat()
            pre_existing = load_all_labels(LABELS_FILE)
            new_rows = [
                {
                    "arxiv_id": paper["arxiv_id"],
                    "title": paper["title"],
                    "link": paper["link"],
                    "label": "1",
                    "labeled_at": now
                }
                for _ in range(STAR_WEIGHT)
            ]
            write_labels(LABELS_FILE, pre_existing + new_rows)
            self.starred_ids.add(arxiv_id)
            self.star_timestamps[arxiv_id] = now

        self.render_paper()

    def _clear_star(self,arxiv_id: str) -> None:
        timestamp = self.star_timestamps.get(arxiv_id)
        self.starred_ids.discard(arxiv_id)
        if timestamp is not None:
            pre_existing = load_all_labels(LABELS_FILE)
            filtered = [
                row for row in pre_existing
                if not (row["arxiv_id"] == arxiv_id and row["label"] == "1" and row["labeled_at"] == timestamp)
            ]
            write_labels(LABELS_FILE, filtered)

    def action_reject(self) -> None:
        if not self.scored_papers:
            return
        _, paper = self.scored_papers[self.index]
        arxiv_id = paper["arxiv_id"]

        if arxiv_id in self.rejected_ids:
            self._clear_reject(arxiv_id)
        else:
            if arxiv_id in self.starred_ids:
                self._clear_star(arxiv_id)

            now = datetime.now(timezone.utc).isoformat()
            pre_existing = load_all_labels(LABELS_FILE)
            new_row = {
                "arxiv_id": paper["arxiv_id"],
                "title": paper["title"],
                "link": paper["link"],
                "label": "0",
                "labeled_at": now
            }
            write_labels(LABELS_FILE, pre_existing + [new_row])
            self.rejected_ids.add(arxiv_id)
            self.reject_timestamps[arxiv_id] = now
        self.render_paper()

    def _clear_reject(self, arxiv_id: str) -> None:
        timestamp = self.reject_timestamps.get(arxiv_id)
        self.rejected_ids.discard(arxiv_id)
        if timestamp is not None:
            pre_existing = load_all_labels(LABELS_FILE)
            filtered = [
                row for row in pre_existing
                if not (row["arxiv_id"] == arxiv_id and row["label"] == "0" and row["labeled_at"] == timestamp)
            ]
            write_labels(LABELS_FILE, filtered)

    def action_detail(self)-> None:
        self.show_explanation("detail", explain_simply, "Detail Explanation")

    def action_result(self) -> None:
        self.show_explanation("result", explain_result, "Key Result")

    def show_explanation(self, kind: str, fn, label_prefix: str) -> None:
        if not self.scored_papers:
            return
        _, paper = self.scored_papers[self.index]
        cached = self.explanation_cache.get(paper["arxiv_id"], {}).get(kind)
        if cached is not None:
            self.query_one("#explanation", Static).update(f"{label_prefix}: {cached}")
        else:
            self.run_explanation(paper["arxiv_id"], kind, fn, label_prefix)

    @work(thread=True)
    def run_explanation(self, arxiv_id: str, kind: str, fn, label_prefix: str) -> None:
        paper = next(p for _, p in self.scored_papers if p["arxiv_id"] == arxiv_id)
        text = fn(paper["abstract"])
        self.explanation_cache.setdefault(arxiv_id, {})[kind] = text
        self.app.call_from_thread(
            self.query_one("#explanation", Static).update,
            f"{label_prefix}: {text}"
        )

    def action_open_link(self) -> None:
        if self.scored_papers:
            _, paper = self.scored_papers[self.index]
            webbrowser.open(paper["link"])

    def action_back_to_choice(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()

    def action_help(self) -> None:
        self.app.push_screen(HelpModal(
            "Cosmo Papers shows the top papers Cosmo learned as the "
            "papers most likely to interest you, based on everything "
            "you've labeled so far. Browse through them and star any that "
            "genuinely stand out — starring adds it to your training data "
            "with extra weight, helping the classifier learn faster from "
            "your strongest signals.",
            [("n", "Next"), ("b", "Previous"), ("s", "Star"), ("x", "Not Interesting"), ("d", "Detail Explanation"), ("r", "Key Result Explanation"), ("o", "Open Link"), ("esc", "Back to Menu"), ("q", "Quit")]
        ))

    
class CosmoApp(App):
    # Entry Point

    TITLE = "Cosmo"

    BINDINGS = [
        Binding("g", "open_settings", "Settings", priority=True),
    ]

    CSS = """
    Footer > .footer-key--key,
    FooterKey > .footer-key--key,
    Footer .footer-key--key {
        color: #7dcfff;
        text-style: bold;
    }

    ToastRack { dock: top; align: right top; margin-top: 1; margin-bottom: 0; }

    Toast { background: #1a1b26; color: #a9b1d6; padding: 1 2; }
    .toast--title { color: #7dcfff; text-style: bold; }
    Toast.-information { border: round #7dcfff; }
    Toast.-information .toast--title { color: #7dcfff; }
    Toast.-warning { border-left: thick #e0af68; }
    Toast.-warning .toast--title { color: #e0af68; }
    Toast.-error { border-left: thick #f7768e; }
    Toast.-error .toast--title { color: #f7768e; }
    """

    def on_mount(self) -> None:
        prefs = load_preferences()
        self.theme = "tokyo-night"
        try:
            from scheduler_setup import ensure_scheduler_installed
            ensure_scheduler_installed()
        except Exception:
            pass
        self.push_screen(WelcomeScreen())

    def action_open_settings(self) -> None:
        if isinstance(self.screen, SettingsScreen):
            return
        self.push_screen(SettingsScreen())

if __name__ == "__main__":
    CosmoApp().run()