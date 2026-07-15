"""MTGuard non-circular evaluation harness (Phase 9).

Ground truth is scenario provenance (attack/benign labels from dataset origin),
never the detector's own output. Two operating points are always reported:
FLAG (max verdict >= ALERT) and BLOCK (max verdict >= CONTAIN / judge DENY).
"""

from mtguard.eval.dataset import EvalScenario, load_corpus, load_scenarios

__all__ = ["EvalScenario", "load_corpus", "load_scenarios"]
