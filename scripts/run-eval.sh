#!/usr/bin/env bash
# Non-circular eval harness — keyless (L1/L2/Fusion never call an API).
# CI policy: NO recall bands asserted here (anti-circularity); numbers are
# reported, not gated. Add JUDGE_API_KEY + --judge for the judge config.
set -euo pipefail
source "$(dirname "$0")/lib/common.sh"

echo "==> MTGuard eval harness (keyless: l1_only, l2_only, l1_l2)…"
uv_run Mudette-eval --split "${1:-dev}" "${@:2}"
