#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then
  uv venv
  uv pip install -r requirements.txt
fi
PYTHONUNBUFFERED=1 .venv/bin/python test_proxies.py "$@"