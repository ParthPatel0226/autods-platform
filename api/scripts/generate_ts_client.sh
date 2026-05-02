#!/usr/bin/env bash
# Generate typed TypeScript fetch client from the OpenAPI schema.
# Run from the repo root:  bash api/scripts/generate_ts_client.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

INPUT="$REPO_ROOT/api/openapi.json"
OUTPUT="$REPO_ROOT/frontend/lib/api-client"

if [[ ! -f "$INPUT" ]]; then
  echo "ERROR: $INPUT not found. Run python -m api.scripts.export_openapi first." >&2
  exit 1
fi

echo "Generating TypeScript client..."
echo "  Input : $INPUT"
echo "  Output: $OUTPUT"

npx --yes openapi-typescript-codegen \
    --input "$INPUT" \
    --output "$OUTPUT" \
    --client fetch \
    --useOptions \
    --useUnionTypes

echo "Done. Generated files:"
find "$OUTPUT" -type f | sort
