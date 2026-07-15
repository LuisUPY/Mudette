"""NVIDIA NIM (build.nvidia.com) — OpenAI-compatible LLM endpoints + timeout config."""

import os

import httpx

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Demo model fast by default; 70b opt-in via MUDETTE_MAIN_MODEL env var
DEFAULT_MAIN_MODEL = os.environ.get("MUDETTE_MAIN_MODEL", "meta/llama-3.1-8b-instruct")
DEFAULT_JUDGE_MODEL = os.environ.get("MUDETTE_JUDGE_MODEL", "meta/llama-3.1-8b-instruct")

# Timeout configuration for API calls
MAIN_TIMEOUT = httpx.Timeout(60.0, connect=10.0)  # 60s total, 10s connect
JUDGE_TIMEOUT = httpx.Timeout(20.0, connect=10.0)  # 20s total, 10s connect
MAIN_MAX_RETRIES = 1
JUDGE_MAX_RETRIES = 0
