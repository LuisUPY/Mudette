"""Shared pytest fixtures — mock NVIDIA NIM for CI without real API keys."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from mtguard.agent import NexaAgent
from mtguard.judge import EscalationJudge

TEST_MAIN_API_KEY = "nvapi-test-main-mock"
TEST_JUDGE_API_KEY = "nvapi-test-judge-mock"

# Captured at import time, before the autouse mock replaces it on the class —
# lets chunk-parsing tests exercise the real implementation.
_ORIGINAL_STREAM_MAIN_LLM = NexaAgent._stream_main_llm


@pytest.fixture
def original_stream_main_llm():
    """Real (un-mocked) NexaAgent._stream_main_llm for chunk-parsing tests."""
    return _ORIGINAL_STREAM_MAIN_LLM


@pytest.fixture
def main_api_key() -> str:
    return TEST_MAIN_API_KEY


@pytest.fixture
def judge_api_key() -> str:
    return TEST_JUDGE_API_KEY


@pytest.fixture(autouse=True)
def mock_llm_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_main_llm(self: NexaAgent, user_content: str) -> str:
        if "INC-48291" in user_content:
            return "Ticket INC-48291 is In Progress. Check the self-service portal."
        if "vpn" in user_content.lower():
            return "Try restarting the NexaVPN client from the menu bar."
        return "Mocked Nexa Copilot response powered by API."

    def fake_stream_main_llm(self: NexaAgent, user_content: str) -> Iterator[str]:
        """Mock streaming — yields response in 2 chunks for testing."""
        base_response = fake_main_llm(self, user_content)
        # Split response into 2 chunks
        mid = len(base_response) // 2
        yield base_response[:mid]
        yield base_response[mid:]

    def fake_judge_llm(self: EscalationJudge, user_prompt: str) -> str:
        return "ALLOW — mocked judge evaluation"

    monkeypatch.setattr(NexaAgent, "_call_main_llm", fake_main_llm)
    monkeypatch.setattr(NexaAgent, "_stream_main_llm", fake_stream_main_llm)
    monkeypatch.setattr(EscalationJudge, "_call_llm", fake_judge_llm)
