"""Run benchmark suite.

Usage:
    python scripts/run_benchmarks.py [--dataset NAME ...]
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tests.benchmarks.run_benchmarks import main

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run AutoDS benchmarks")
    parser.add_argument(
        "--dataset", nargs="*", help="Specific datasets to benchmark"
    )
    args = parser.parse_args()
    main(args.dataset)
