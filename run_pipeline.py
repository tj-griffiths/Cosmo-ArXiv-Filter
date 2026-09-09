# Orchestrates the Cosmo pipeline from end to end
# To run the entire pipeline, simply run: "python run_pipeline.py"

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

PIPELINE = [
    ("fetch", "fetch.py"),
    ("summarize", "summarize.py"),
    ("embed", "embed.py"),
    ("label", "label.py"),
    # when done manually labeling, add:
    #("classify", "classify.py")
    #("email", "email.py") 
]

def run_stage(name: str, script: str) -> None:
    script_path = PROJECT_DIR / script
    if not script_path.exists():
        print(f"Error: Script '{script}' not found in project directory, skipping.")
        return
    
    print(f"\n{'=' * 60}")
    print(f"STAGE: {name} ({script})")
    print(f"{'=' * 60}\n")

    start = time.time()
    result = subprocess.run([sys.executable, str(script_path)], cwd=PROJECT_DIR)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"Error: Stage '{name}' failed with return code {result.returncode} after {elapsed:.1f}s. Exiting pipeline.")
        sys.exit(result.returncode)

    print(f"Stage '{name}' completed successfully in {elapsed:.1f}s.")

def main() -> None:
    parser = argparse.ArgumentParser(description="Run Cosmo")
    parser.add_argument(
        "--skip",
        nargs="*",
        default=[],
        metavar ="STAGE",
        help="Stage names to skip, e.g. --skip fetch",
    ) # Ex: python run_pipeline --skip fetch summarize
    parser.add_argument(
        "--only",
        metavar="STAGE",
        help="Run only the specified stage, e.g. --only summarize",
    ) # Ex: python run_pipeline --only summarize

    args = parser.parse_args()
    stage_names = [name for name, _ in PIPELINE]

    if args.only:
        if args.only not in stage_names:
            print(f"Error: Unknown stage '{args.only}'. Valid stages are: {', '.join(stage_names)}")
            sys.exit(1)
        stages_to_run = [(name, script) for name, script in PIPELINE if name == args.only]
    else: 
        unknown = set(args.skip) - set(stage_names)
        if unknown:
            print(f"Unknown stage(s) in --skip: {unknown}. Choices: {stage_names}")
            sys.exit(1)
        stages_to_run = [(name, script) for name, script in PIPELINE if name not in args.skip]

    if not stages_to_run:
        print("Nothing to run (all stages skipped).")
        return
    
    print(f"Running stages: {[n for n, _ in stages_to_run]}")

    overall_start = time.time()
    for name, script in stages_to_run:
        run_stage(name, script)
    total = time.time() - overall_start

    print(f"\nPipeline completed successfully in {total:.1f}s.")

if __name__ == "__main__":
    main()

