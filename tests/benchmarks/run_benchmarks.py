"""Benchmark runner entry point.

Runs the full AutoDS pipeline on standard datasets and records results.

Usage:
    python tests/benchmarks/run_benchmarks.py [--dataset NAME ...]
"""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Ensure project root on path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def main(datasets: list[str] | None = None) -> None:
    """Run benchmarks on standard datasets.

    Args:
        datasets: Optional list of dataset names. None = all in catalog.
    """
    from evaluation.benchmarks.benchmark_runner import BenchmarkRunner

    runner = BenchmarkRunner()

    if not runner.catalog:
        logger.error(
            "No benchmark catalog found. Run first:\n"
            "  python scripts/download_sample_datasets.py"
        )
        sys.exit(1)

    logger.info("Starting benchmark suite...")
    results = runner.run_all(datasets=datasets)

    if not results:
        logger.warning("No benchmark results produced.")
        sys.exit(1)

    runner.save_results(results)

    # Print summary
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "error")
    logger.info(
        "Benchmark complete: %d/%d succeeded, %d failed",
        success, len(results), failed,
    )

    for r in results:
        status = "OK" if r["status"] == "success" else "FAIL"
        score = r.get("best_score", 0)
        model = r.get("best_model", "N/A")
        logger.info(
            "  [%s] %-25s score=%.4f  model=%s  (%.1fs)",
            status, r["dataset"], score, model,
            r.get("duration_seconds", 0),
        )

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AutoDS benchmarks")
    parser.add_argument(
        "--dataset", nargs="*", help="Specific datasets to benchmark"
    )
    args = parser.parse_args()
    main(args.dataset)
