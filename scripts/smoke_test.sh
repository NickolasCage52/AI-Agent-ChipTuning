#!/usr/bin/env sh
set -eu

docker compose up -d --build

echo "Run smoke on Windows with:"
echo "  powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1"
echo ""
echo "Or run 'make smoke' (if make is installed)."

