#!/bin/bash
# Generate Dart API client from OpenAPI specification
# Uses openapi-generator-cli (pip package)

set -e

# Project root is parent of scripts/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

OPENAPI_SPEC="$PROJECT_ROOT/cli/api/openapi.json"
OUTPUT_DIR="$PROJECT_ROOT/cli/lib/src/generated/api/divvy"

# Check prerequisites
if ! command -v java &> /dev/null; then
    echo "Error: Java is required but not installed."
    echo "Please install Java JDK 11 or higher."
    exit 1
fi

if ! command -v openapi-generator-cli &> /dev/null; then
    echo "Error: openapi-generator-cli not found."
    echo "Please install it: pip install openapi-generator-cli"
    exit 1
fi

echo "Generating Dart API client..."
echo "Spec: $OPENAPI_SPEC"
echo "Output: $OUTPUT_DIR"

# Clean output directory
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Generate client
openapi-generator-cli generate \
    -i "$OPENAPI_SPEC" \
    -g dart-dio \
    -o "$OUTPUT_DIR" \
    --additional-properties=pubName=divvy_api_client,pubDescription="Divvy API Client",pubVersion="0.0.1"

echo "✅ API client generated."

echo "Running build_runner in generated client..."
cd "$OUTPUT_DIR"
dart pub get
dart run build_runner build --delete-conflicting-outputs

echo "✅ Client build complete."

