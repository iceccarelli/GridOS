#!/usr/bin/env bash
# GridOS Demo Runner
# Runs the quick start demo with proper PYTHONPATH

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "GridOS Demo Runner"
echo "=================="
echo ""

# Set PYTHONPATH
export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:-}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    exit 1
fi

# Check dependencies
python3 -c "import pydantic" 2>/dev/null || {
    echo "Installing base dependencies..."
    pip install -r "${PROJECT_DIR}/requirements/base.txt"
}

# Run demo
echo "Running GridOS quick start demo..."
echo ""
python3 "${PROJECT_DIR}/notebooks/01_quickstart.py"
