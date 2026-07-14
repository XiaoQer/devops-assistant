#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT_DIR/backend/.venv/bin/python}"

if [[ ! -x "$PYTHON" ]]; then
  PYTHON="${PYTHON_FALLBACK:-python3}"
fi

if ! "$PYTHON" -c "import pytest" >/dev/null 2>&1; then
  echo "Backend verification dependency missing."
  echo "Install it with: $PYTHON -m pip install -r backend/requirements-dev.txt"
  exit 2
fi

echo "Running backend tests"
(
  cd "$ROOT_DIR/backend"
  "$PYTHON" -m pytest tests -q
)

echo "Running frontend tests"
npm --prefix "$ROOT_DIR/frontend" test

echo "Building frontend"
npm --prefix "$ROOT_DIR/frontend" run build

echo "Verification passed"
