from __future__ import annotations

import json
import time
from pathlib import Path

from mtguard.embedder import Embedder
from mtguard.gates.user_gate import UserGate
from mtguard.layers.fusion import RiskFusion
from mtguard.layers.l1_regex import RegexGuard
from mtguard.layers.l2_trajectory import ConversationState, TrajectoryGuard
from mtguard.models import FusionResult, JudgeResult, TurnTrace, Verdict
from mtguard.trace import build_turn_trace


class MTGuardPipeline:
    """L1 → L2 → Fusion → UserGate with TurnTrace per turn."""

    def __init__(
        self,
        l1: RegexGuard,
        l2: TrajectoryGuard,
        fusion: RiskFusion | None = None,
        gate: UserGate | None = None,
    ) -> None:
        self.l1 = l1
        self.l2 = l2
        self.fusion = fusion or RiskFusion()
        self.gate = gate or UserGate()

    @classmethod
    def from_pack(cls, pack_dir: Path, embedder: Embedder | None = None) -> MTGuardPipeline:
        embedder = embedder or Embedder()
        profile_path = pack_dir / "agent_profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        return cls(
            l1=RegexGuard(),
            l2=TrajectoryGuard(profile, embedder=embedder),
        )

    def process_turn(
        self,
        message: str,
        state: ConversationState | None = None,
        judge: JudgeResult | None = None,
    ) -> tuple[TurnTrace, ConversationState, FusionResult]:
        t0 = time.perf_counter()

        l1_result = self.l1.scan(message)
        l2_result, state = self.l2.evaluate(message, state)
        fusion_result = self.fusion.fuse(l1_result, l2_result)

        if judge and judge.invoked and judge.decision == "DENY":
            fusion_result = self.fusion.apply_judge_deny(fusion_result)

        gate_result = self.gate.evaluate(fusion_result, judge)
        latency_ms = (time.perf_counter() - t0) * 1000

        trace = build_turn_trace(
            turn_index=l2_result.turn_index,
            user_message=message,
            l1=l1_result,
            l2=l2_result,
            fusion=fusion_result,
            gate=gate_result,
            judge=judge,
            latency_ms=latency_ms,
        )
        return trace, state, fusion_result

    def reset(self) -> ConversationState:
        return self.l2.reset()
