"""Phase-1 signal capture: run L1+L2 once per scenario, store raw signals.

Validity note: TrajectoryGuard mutates ConversationState independently of
Fusion/Judge/Gate, so signals captured once are identical for every
downstream ablation config — capture once, replay N times.
"""

from __future__ import annotations

from dataclasses import dataclass

from mtguard.embedder import Embedder
from mtguard.eval.dataset import EvalScenario
from mtguard.layers.l1_regex import RegexGuard
from mtguard.layers.l2_trajectory import TrajectoryGuard
from mtguard.models import L1Result, L2Result
from mtguard.pack_loader import DemoPack
from mtguard.trace import l1_to_dict, l2_to_dict


@dataclass(frozen=True)
class TurnSignals:
    message: str
    l1: L1Result
    l2: L2Result


@dataclass(frozen=True)
class ScenarioSignals:
    scenario: EvalScenario
    turns: tuple[TurnSignals, ...]


class SignalCapture:
    def __init__(self, pack: DemoPack, embedder: Embedder | None = None) -> None:
        self._l1 = RegexGuard()
        self._l2 = TrajectoryGuard(pack.agent_profile, embedder=embedder or Embedder())

    def run_scenario(self, scenario: EvalScenario) -> ScenarioSignals:
        state = self._l2.reset()
        turns: list[TurnSignals] = []
        for message in scenario.turns:
            l1 = self._l1.scan(message)
            l2, state = self._l2.evaluate(message, state)
            turns.append(TurnSignals(message=message, l1=l1, l2=l2))
        return ScenarioSignals(scenario=scenario, turns=tuple(turns))

    def run(self, scenarios: list[EvalScenario]) -> list[ScenarioSignals]:
        return [self.run_scenario(s) for s in scenarios]


def signals_to_json(captured: list[ScenarioSignals]) -> list[dict]:
    return [
        {
            "id": cs.scenario.id,
            "label": cs.scenario.label,
            "category": cs.scenario.category,
            "source": cs.scenario.source,
            "turns": [
                {"message": t.message, "l1": l1_to_dict(t.l1), "l2": l2_to_dict(t.l2)}
                for t in cs.turns
            ],
        }
        for cs in captured
    ]
