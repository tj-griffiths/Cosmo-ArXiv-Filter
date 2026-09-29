import feedparser  # parses the Atom/RSS XML response into Python objects
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import holidays
import requests
from text_utils import clean_latex

# Config:
# Picks arXiv category codes
# Full taxonomy:
# https://arxiv.org/category_taxonomy
# uses trained scorer (classify.py, once labels.csv has been built) to narrow paper filter over time

RSS_BASE_URL = "http://export.arxiv.org/rss/"
OUTPUT_FILE = "papers_raw.json"

CATEGORIES = [
    "astro-ph.CO",         # Cosmology and Nongalactic Astrophysics
    "astro-ph.EP",         # Earth and Planetary Astrophysics
    "astro-ph.GA",         # Astrophysics of Galaxies
    "astro-ph.HE",         # High Energy Astrophysical Phenomena
    "astro-ph.IM",         # Instrumentation and Methods for Astrophysics
    "astro-ph.SR",         # Solar and Stellar Astrophysics
    "cond-mat.dis-nn",     # Disordered Systems and Neural Networks
    "cond-mat.mes-hall",   # Mesoscale and Nanoscale Physics
    "cond-mat.mtrl-sci",   # Materials Science
    "cond-mat.other",      # Other Condensed Matter
    "cond-mat.quant-gas",  # Quantum Gases
    "cond-mat.soft",       # Soft Condensed Matter
    "cond-mat.stat-mech",  # Statistical Mechanics
    "cond-mat.str-el",     # Strongly Correlated Electrons
    "cond-mat.supr-con",   # Superconductivity
    "gr-qc",               # General Relativity and Quantum Cosmology
    "hep-ex",              # High Energy Physics - Experiment
    "hep-lat",             # High Energy Physics - Lattice
    "hep-ph",              # High Energy Physics - Phenomenology
    "hep-th",              # High Energy Physics - Theory
    "math-ph",             # Mathematical Physics
    "nlin.AO",             # Adaptation and Self-Organizing Systems
    "nlin.CD",             # Chaotic Dynamics
    "nlin.CG",             # Cellular Automata and Lattice Gases
    "nlin.PS",             # Pattern Formation and Solitons
    "nlin.SI",             # Exactly Solvable and Integrable Systems
    "nucl-ex",             # Nuclear Experiment
    "nucl-th",             # Nuclear Theory
    "physics.acc-ph",      # Accelerator Physics
    "physics.ao-ph",       # Atmospheric and Oceanic Physics
    "physics.app-ph",      # Applied Physics
    "physics.atm-clus",    # Atomic and Molecular Clusters
    "physics.atom-ph",     # Atomic Physics
    "physics.bio-ph",      # Biological Physics
    "physics.chem-ph",     # Chemical Physics
    "physics.class-ph",    # Classical Physics
    "physics.comp-ph",     # Computational Physics
    "physics.data-an",     # Data Analysis, Statistics and Probability
    "physics.ed-ph",       # Physics Education
    "physics.flu-dyn",     # Fluid Dynamics
    "physics.gen-ph",      # General Physics
    "physics.geo-ph",      # Geophysics
    "physics.hist-ph",     # History and Philosophy of Physics
    "physics.ins-det",     # Instrumentation and Detectors
    "physics.med-ph",      # Medical Physics
    "physics.optics",      # Optics
    "physics.plasm-ph",    # Plasma Physics
    "physics.pop-ph",      # Popular Physics
    "physics.soc-ph",      # Physics and Society
    "physics.space-ph",    # Space Physics
    "quant-ph",            # Quantum Physics
]

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "astro-ph.CO": [
        "Dark Energy",                 "Dark Matter",
        "Cosmic Microwave Background", "Inflation",
        "Large-Scale Structure",       "Baryon Acoustic Oscillations",
    ],
    "astro-ph.EP": [
        "Exoplanets",           "Planet Formation",
        "Protoplanetary Disks", "Solar System",
        "Habitability",         "Atmospheric Characterization",
    ],
    "astro-ph.GA": [
        "Galaxy Formation",     "Galaxy Clusters",
        "Active Galactic Nuclei", "Interstellar Medium",
        "Stellar Populations",  "Milky Way",
    ],
    "astro-ph.HE": [
        "Black Holes",   "Neutron Stars",   "Gamma-Ray Bursts",
        "Gravitational Waves", "Supernovae", "Cosmic Rays",
    ],
    "astro-ph.IM": [
        "Telescopes",    "Detectors",      "Data Analysis",
        "Calibration",   "Interferometry", "Adaptive Optics",
    ],
    "astro-ph.SR": [
        "Stellar Evolution", "Stellar Structure",
        "Binary Stars",      "Solar Physics",
        "Variable Stars",    "Asteroseismology",
    ],
    "cond-mat.dis-nn": [
        "Spin Glasses",         "Neural Networks",
        "Disordered Systems",   "Anderson Localization",
        "Random Matrix Theory", "Machine Learning",
    ],
    "cond-mat.mes-hall": [
        "Quantum Dots",       "Nanostructures",
        "Quantum Hall Effect", "Spintronics",
        "2D Materials",       "Topological Insulators",
    ],
    "cond-mat.mtrl-sci": [
        "Crystal Structure", "Thin Films",
        "Semiconductors",    "Phase Transitions",
        "Defects",           "First-Principles Calculations",
    ],
    "cond-mat.other": [
        "Emerging Materials", "Novel Phases",
        "Quantum Materials",  "Metamaterials",
        "Emergent Phenomena", "Novel Probes",
    ],
    "cond-mat.quant-gas": [
        "Bose-Einstein Condensate", "Ultracold Atoms",
        "Optical Lattices",         "Fermi Gases",
        "Superfluidity",            "Quantum Simulation",
    ],
    "cond-mat.soft": [
        "Polymers", "Colloids",          "Liquid Crystals",
        "Granular Matter", "Biological Physics", "Active Matter",
    ],
    "cond-mat.stat-mech": [
        "Phase Transitions",  "Critical Phenomena",
        "Nonequilibrium Dynamics", "Thermodynamics",
        "Stochastic Processes", "Entanglement Entropy",
    ],
    "cond-mat.str-el": [
        "Strongly Correlated Electrons", "Mott Insulators",
        "Heavy Fermions",                "Quantum Magnetism",
        "Frustrated Magnetism",          "Topological Order",
    ],
    "cond-mat.supr-con": [
        "Superconductivity",       "Cooper Pairs",
        "High-Tc Superconductors", "Josephson Junctions",
        "Unconventional Superconductivity", "Vortex Dynamics",
    ],
    "gr-qc": [
        "Gravitational Waves",   "Black Holes",
        "General Relativity",    "Numerical Relativity",
        "Quantum Gravity",       "Cosmology",
    ],
    "hep-ex": [
        "Collider Physics",     "Higgs Boson",
        "Dark Matter Detection", "Neutrino Experiments",
        "Particle Detectors",   "Flavor Physics",
    ],
    "hep-lat": [
        "Lattice QCD",          "Monte Carlo Simulation",
        "Confinement",          "Chiral Symmetry",
        "Hadron Spectroscopy",  "Finite Temperature QCD",
    ],
    "hep-ph": [
        "Standard Model",   "Higgs Boson",    "Dark Matter",
        "Neutrino Physics", "Beyond Standard Model", "QCD",
    ],
    "hep-th": [
        "String Theory",         "Quantum Field Theory",
        "Supersymmetry",         "AdS/CFT",
        "Conformal Field Theory", "Black Hole Physics",
    ],
    "math-ph": [
        "Mathematical Physics", "Integrable Systems",
        "Operator Algebras",    "Spectral Theory",
        "Random Matrices",      "Quantum Groups",
    ],
    "nlin.AO": [
        "Self-Organization", "Adaptive Systems",
        "Swarm Dynamics",    "Collective Behavior",
        "Complex Systems",   "Network Dynamics",
    ],
    "nlin.CD": [
        "Chaos Theory", "Nonlinear Dynamics", "Bifurcations",
        "Turbulence",   "Strange Attractors", "Fractals",
    ],
    "nlin.CG": [
        "Cellular Automata",  "Lattice Gases",
        "Discrete Dynamical Systems", "Emergent Computation",
        "Spatial Games",      "Complex Systems",
    ],
    "nlin.PS": [
        "Solitons",         "Pattern Formation",
        "Reaction-Diffusion Systems", "Nonlinear Waves",
        "Rogue Waves",      "Localized Structures",
    ],
    "nlin.SI": [
        "Integrable Systems", "Exact Solutions",
        "Inverse Scattering", "Soliton Equations",
        "Lax Pairs",          "Painlevé Analysis",
    ],
    "nucl-ex": [
        "Heavy-Ion Collisions", "Nuclear Structure",
        "Radioactive Decay",    "Nuclear Detectors",
        "Nuclear Reactions",    "Exotic Nuclei",
    ],
    "nucl-th": [
        "Nuclear Structure",   "Quark-Gluon Plasma",
        "Nuclear Astrophysics", "Effective Field Theory",
        "Nuclear Equation of State", "Neutron Star Matter",
    ],
    "physics.acc-ph": [
        "Particle Accelerators", "Beam Dynamics",
        "RF Cavities",           "Ion Traps",
        "Synchrotron Radiation", "Plasma Wakefield Acceleration",
    ],
    "physics.ao-ph": [
        "Atmospheric Dynamics", "Climate Modeling",
        "Ocean Physics",        "Weather Prediction",
        "Atmospheric Chemistry", "Remote Sensing",
    ],
    "physics.app-ph": [
        "Applied Physics", "Devices",  "Sensors",
        "Photonics",       "Energy Harvesting", "Semiconductor Devices",
    ],
    "physics.atm-clus": [
        "Atomic Clusters",   "Nanoparticles",
        "Molecular Clusters", "Cluster Physics",
        "Van der Waals Clusters", "Fragmentation",
    ],
    "physics.atom-ph": [
        "Atomic Physics",     "Laser Cooling",
        "Precision Spectroscopy", "Rydberg Atoms",
        "Cold Atoms",         "Quantum Metrology",
    ],
    "physics.bio-ph": [
        "Biophysics",     "Protein Folding",
        "Molecular Motors", "Biological Networks",
        "Cell Mechanics", "Neural Dynamics",
    ],
    "physics.chem-ph": [
        "Chemical Physics",  "Molecular Dynamics",
        "Spectroscopy",      "Reaction Dynamics",
        "Photochemistry",    "Quantum Chemistry",
    ],
    "physics.class-ph": [
        "Classical Mechanics", "Fluid Dynamics",
        "Electromagnetism",    "Nonlinear Mechanics",
        "Wave Propagation",    "Acoustics",
    ],
    "physics.comp-ph": [
        "Computational Methods", "Simulation",
        "Machine Learning",      "Numerical Methods",
        "High-Performance Computing", "Monte Carlo Methods",
    ],
    "physics.data-an": [
        "Statistical Methods", "Machine Learning",
        "Data Analysis",       "Bayesian Inference",
        "Uncertainty Quantification", "Signal Processing",
    ],
    "physics.ed-ph": [
        "Physics Education", "Teaching Methods",
        "Conceptual Understanding", "Curriculum Design",
        "Assessment Methods", "Active Learning",
    ],
    "physics.flu-dyn": [
        "Fluid Dynamics", "Turbulence",     "Hydrodynamics",
        "Aerodynamics",   "Vortex Dynamics", "Multiphase Flow",
    ],
    "physics.gen-ph": [
        "General Physics",  "Foundations",
        "Conceptual Physics", "Foundational Questions",
        "Unified Theories", "Physical Principles",
    ],
    "physics.geo-ph": [
        "Geophysics", "Seismology",  "Earth's Interior",
        "Geomagnetism", "Volcanology", "Tectonics",
    ],
    "physics.hist-ph": [
        "History of Physics",    "Philosophy of Physics",
        "Scientific Biography",  "History of Ideas",
        "Science and Society",   "Foundations of Physics",
    ],
    "physics.ins-det": [
        "Detectors",   "Instrumentation", "Sensors",
        "Readout Electronics", "Photodetectors", "Cryogenic Detectors",
    ],
    "physics.med-ph": [
        "Medical Imaging",  "Radiation Therapy", "Dosimetry",
        "Proton Therapy",   "MRI Physics",       "Radiation Detectors",
    ],
    "physics.optics": [
        "Photonics",  "Lasers",           "Nonlinear Optics",
        "Quantum Optics", "Metamaterials", "Fiber Optics",
    ],
    "physics.plasm-ph": [
        "Plasma Physics",     "Fusion",
        "Magnetohydrodynamics", "Space Plasmas",
        "Plasma Instabilities", "Laser-Plasma Interactions",
    ],
    "physics.pop-ph": [
        "Popular Science",     "Science Communication",
        "Public Engagement",   "Science Outreach",
        "Science Journalism",  "Science Literacy",
    ],
    "physics.soc-ph": [
        "Complex Networks", "Social Dynamics", "Econophysics",
        "Opinion Dynamics", "Epidemic Modeling", "Urban Systems",
    ],
    "physics.space-ph": [
        "Space Weather", "Magnetosphere",   "Solar Wind",
        "Heliophysics",  "Radiation Belts", "Ionospheric Physics",
    ],
    "quant-ph": [
        "Quantum Computing",    "Quantum Entanglement",
        "Quantum Field Theory", "Ion Traps",
        "Quantum Information",  "Quantum Error Correction",
    ],
}

# ArXiv holidays (no posted papers)
_ARXIV_OBSERVED_HOLIDAY_NAMES = {
    "New Year's Day",
    "Martin Luther King Jr. Day",
    "Juneteenth National Independence Day",
    "Independence Day",
    "Independence Day (observed)",
    "Labor Day",
    "Thanksgiving Day",
    "Christmas Day"
}
EXTRA_ARXIV_CLOSURE_DATES: set[str] = set()

# Set up user agent for requests to arXiv API (to avoid being blocked):
with open("user_config.txt") as f:
    USER_EMAIL = f.read().strip()
USER_AGENT = "cosmo-arxiv-filter/0.1 (personal research paper filter; contact: {USER_EMAIL})"

# Clean up arXiv's packed feed

def parse_description(raw_description: str) -> tuple[str, str]:
    text = " ".join(raw_description.split())

    abstract_match = re.search(r"Abstract:\s*(.*)", text, re.IGNORECASE)
    if abstract_match:
        return abstract_match.group(1).strip()
    
    # Fallback: strip a leading arXiv ID and announce type if present
    return re.sub(r"^arXiv:\S+\s*Announce Type:\s*\S+\s*", "", text, flags=re.IGNORECASE).strip()

# Holiday Check
def is_arxiv_holiday(date) -> bool:
    if date.isoformat() in EXTRA_ARXIV_CLOSURE_DATES:
        return True
    name = holidays.US(years=date.year).get(date)
    return name in _ARXIV_OBSERVED_HOLIDAY_NAMES if name else False

# Check for weekends before fetching, since arXiv does not post new papers on weekends
def is_arxiv_closed_today() -> bool:
    eastern_now = datetime.now(ZoneInfo("America/New_York"))
    if eastern_now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return True
    return is_arxiv_holiday(eastern_now.date())

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
            "title": clean_latex(" ".join(entry.get("title", "").split())),            
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
    if is_arxiv_closed_today():
        print("Today is a weekend/holiday in arXiv's timezone (US/Eastern). No new papers are posted on weekends.")
        print("Exiting without fetching papers.")
    else:
        papers = fetch_today(CATEGORIES)

        if not papers:
            print(f"\n No papers fetched - leaving {OUTPUT_FILE} unchanged.")
        
        else:
            with open(OUTPUT_FILE, "w") as f:
                json.dump(papers, f, indent=2)

            print(f"\nSaved {len(papers)} papers to {OUTPUT_FILE}.")
