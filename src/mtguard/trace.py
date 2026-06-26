from __future__ import annotations

from typing import Any

from mtguard.models import (
    FusionResult,
    GateResult,
    JudgeResult,
    L1Result,
    L2Result,
    TurnTrace,
)


def l1_to_dict(r: L1Result) -> dict[str, Any]:
    return {
        "hit": r.hit,
        "rule_id": r.rule_id,
        "severity": r.severity.value if r.severity else None,
        "matched_text": r.matched_text,
    }


def l2_to_dict(r: L2Result) -> dict[str, Any]:
    return {
        "safe_score": r.safe_score,
        "proximity": r.proximity,
        "max_proximity": r.max_proximity,
        "max_region": r.max_region,
        "drift_step": r.drift_step,
        "drift_baseline": r.drift_baseline,
        "approaching_sensitive": r.approaching_sensitive,
        "trajectory_risk": r.trajectory_risk,
        "escalation_pattern": r.escalation_pattern,
        "turn_index": r.turn_index,
    }


def fusion_to_dict(r: FusionResult) -> dict[str, Any]:
    return {
        "risk_score": r.risk_score,
        "verdict": r.verdict.value,
        "factors": r.factors,
    }


def judge_to_dict(r: JudgeResult | None) -> dict[str, Any] | None:
    if r is None:
        return None
    return {
        "enabled": r.enabled,
        "invoked": r.invoked,
        "decision": r.decision,
        "reason": r.reason,
    }


def gate_to_dict(r: GateResult) -> dict[str, Any]:
    return {
        "allow_llm": r.allow_llm,
        "show_banner": r.show_banner,
        "block_reason": r.block_reason,
    }


def build_turn_trace(
    turn_index: int,
    user_message: str,
    l1: L1Result,
    l2: L2Result,
    fusion: FusionResult,
    gate: GateResult,
    judge: JudgeResult | None = None,
    latency_ms: float = 0.0,
) -> TurnTrace:
    return TurnTrace(
        turn_index=turn_index,
        user_message=user_message,
        l1=l1_to_dict(l1),
        l2=l2_to_dict(l2),
        fusion=fusion_to_dict(fusion),
        judge=judge_to_dict(judge),
        gate=gate_to_dict(gate),
        latency_ms=round(latency_ms, 2),
    )
