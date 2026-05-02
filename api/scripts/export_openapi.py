"""Export the FastAPI OpenAPI schema to api/openapi.json.

Usage:
    python -m api.scripts.export_openapi
"""
from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    from api.main import app  # noqa: PLC0415 — intentional late import

    schema = app.openapi()
    out = Path(__file__).parent.parent / "openapi.json"
    out.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"OpenAPI schema written to {out}  ({len(schema['paths'])} paths)")


if __name__ == "__main__":
    main()
