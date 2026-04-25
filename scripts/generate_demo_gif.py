"""Generate a demo GIF for the README.

Uses Playwright to capture the Streamlit dashboard in action.
Requires: pip install playwright pillow
          playwright install chromium

Usage:
    # Start dashboard first: make run
    python scripts/generate_demo_gif.py [--url http://localhost:8501] [--output docs/images/demo.gif]
"""

import argparse
import logging
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_URL = "http://localhost:8501"
_DEFAULT_OUTPUT = Path("docs/images/demo.gif")
_SCREENSHOT_DELAY = 2.0  # seconds between captures
_VIEWPORT = {"width": 1280, "height": 720}


def capture_screenshots(url: str, output_dir: Path) -> list[Path]:
    """Capture sequential screenshots of the dashboard.

    Returns:
        List of screenshot file paths.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error(
            "Playwright not installed. Install with:\n"
            "  pip install playwright && playwright install chromium"
        )
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    screenshots = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=_VIEWPORT)

        # Sequence of pages to capture
        pages_to_capture = [
            ("", "01_home"),
            ("Upload", "02_upload"),
            ("Configure", "03_configure"),
            ("EDA", "04_eda"),
            ("Modeling", "05_modeling"),
            ("Explainability", "06_explain"),
            ("Download", "07_download"),
        ]

        for suffix, name in pages_to_capture:
            page_url = f"{url}/{suffix}" if suffix else url
            try:
                page.goto(page_url, wait_until="networkidle", timeout=15000)
                time.sleep(_SCREENSHOT_DELAY)
                path = output_dir / f"{name}.png"
                page.screenshot(path=str(path))
                screenshots.append(path)
                logger.info("Captured: %s", path)
            except Exception as e:
                logger.warning("Failed to capture %s: %s", name, e)

        browser.close()

    return screenshots


def create_gif(screenshots: list[Path], output_path: Path) -> None:
    """Combine screenshots into an animated GIF."""
    try:
        from PIL import Image
    except ImportError:
        logger.error("Pillow not installed. Install: pip install Pillow")
        sys.exit(1)

    if not screenshots:
        logger.error("No screenshots to combine.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames = [Image.open(p) for p in screenshots]
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=2000,  # ms per frame
        loop=0,
    )
    logger.info("GIF saved: %s (%.1f KB)", output_path, output_path.stat().st_size / 1024)


def main() -> None:
    """Capture dashboard screenshots and create demo GIF."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Generate demo GIF from dashboard")
    parser.add_argument("--url", default=_DEFAULT_URL, help="Dashboard URL")
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT, help="Output GIF path")
    args = parser.parse_args()

    tmp_dir = Path("docs/images/_screenshots")
    screenshots = capture_screenshots(args.url, tmp_dir)

    if screenshots:
        create_gif(screenshots, args.output)
    else:
        logger.error(
            "No screenshots captured. Make sure dashboard is running:\n"
            "  make run"
        )
        logger.info(
            "Alternatively, record manually with a screen recorder and "
            "save to %s", args.output
        )


if __name__ == "__main__":
    main()
