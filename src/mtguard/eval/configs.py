"""Phase-2 ablation configs: pure replays of captured signals through fusion.

Configs:
  l1_only     — regex baseline (L2 zeroed)
  l2_only     — trajectory alone (L1 forced no-hit); mathematically capped at
                risk 55 = ALERT under current weights (documented Fantasma #3)
  l1_l2       — current production fusion, no judge
  l1_l2_judge — l1_l2 plus live EscalationJudge where should_invoke (cached)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from mtguard.eval.capture import ScenarioSignals
from mtguard.judge import EscalationJudge, parse_judge_response
from mtguard.layers.fusion import RiskFusion
from mtguard.models import FusionResult, L1Result, L2Result, Verdict

VERDICT_RANK = {Verdict.CLEAR: 0, Verdict.WATCH: 1, Verdict.ALERT: 2, Verdict.CONTAIN: 3}
KEYLESS_CONFIGS = ("l1_only", "l2_only", "l1_l2")


@dataclass
class ConfigResult:
    config: str
    scenario_id: str
    label: str
    category: str
    source: str
    n_turns: int
    verdicts: list[Verdict]
    factors_per_turn: list[list[str]]
    judge_invocations: int = 0
    judge_denies: int = 0


class JudgeCache:
    """Persistent (prompt-hash → decision) cache so judge calls are paid once."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._data: dict[str, dict] = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))

    @staticmethod
    def key(prompt: str, model: str) -> str:
        return hashlib.sha256(f"{model}|{prompt}".encode()).hexdigest()

    def get(self, key: str) -> tuple[str, str] | None:
        hit = self._data.get(key)
        return (hit["decision"], hit["reason"]) if hit else None

    def put(self, key: str, decision: str, reason: str) -> None:
        self._data[key] = {"decision": decision, "reason": reason}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=1), encoding="utf-8")


def _replay(sig: ScenarioSignals, config: str, fuse_turn) -> ConfigResult:
    fusion = RiskFusion()
    verdicts: list[Verdict] = []
    factors: list[list[str]] = []
    for turn in sig.turns:
        result: FusionResult = fuse_turn(fusion, turn)
        verdicts.append(result.verdict)
        factors.append(list(result.factors))
    return ConfigResult(
        config=config,
        scenario_id=sig.scenario.id,
        label=sig.scenario.label,
        category=sig.scenario.category,
        source=sig.scenario.source,
        n_turns=len(sig.turns),
        verdicts=verdicts,
        factors_per_turn=factors,
    )


def replay_l1_only(sig: ScenarioSignals) -> ConfigResult:
    return _replay(sig, "l1_only", lambda f, t: f.fuse(t.l1, L2Result()))


def replay_l2_only(sig: ScenarioSignals) -> ConfigResult:
    return _replay(sig, "l2_only", lambda f, t: f.fuse(L1Result(hit=False), t.l2))


def replay_l1_l2(sig: ScenarioSignals) -> ConfigResult:
    return _replay(sig, "l1_l2", lambda f, t: f.fuse(t.l1, t.l2))


def replay_l1_l2_judge(
    sig: ScenarioSignals, judge: EscalationJudge, cache: JudgeCache
) -> ConfigResult:
    """Full fusion + live judge on should_invoke turns (decisions cached).

    Mirrors EscalationJudge.evaluate internals so cached decisions can be
    injected before paying an API call.
    """
    fusion_engine = RiskFusion()
    verdicts: list[Verdict] = []
    factors: list[list[str]] = []
    invocations = 0
    denies = 0
    for i, turn in enumerate(sig.turns):
        fusion = fusion_engine.fuse(turn.l1, turn.l2)
        if judge.should_invoke(fusion):
            invocations += 1
            history = tuple(t.message for t in sig.turns[:i])
            prompt = judge._build_prompt(turn.message, turn.l1, turn.l2, fusion, history)
            key = JudgeCache.key(prompt, judge.model)
            cached = cache.get(key)
            if cached is None:
                raw = judge._call_llm(prompt)
                decision, reason = parse_judge_response(raw)
                cache.put(key, decision, reason)
            else:
                decision, _reason = cached
            if decision == "DENY":
                denies += 1
                fusion = fusion_engine.apply_judge_deny(fusion)
        verdicts.append(fusion.verdict)
        factors.append(list(fusion.factors))
    result = ConfigResult(
        config="l1_l2_judge",
        scenario_id=sig.scenario.id,
        label=sig.scenario.label,
        category=sig.scenario.category,
        source=sig.scenario.source,
        n_turns=len(sig.turns),
        verdicts=verdicts,
        factors_per_turn=factors,
    )
    result.judge_invocations = invocations
    result.judge_denies = denies
    return result


KEYLESS_REPLAYS = {
    "l1_only": replay_l1_only,
    "l2_only": replay_l2_only,
    "l1_l2": replay_l1_l2,
}
