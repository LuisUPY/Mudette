"""Orchestration + CLI for the eval harness (entrypoint: Mudette-eval).

Keyless by default (L1/L2/Fusion never call an API). The judge config is
opt-in via --judge and requires JUDGE_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from mtguard.eval.capture import SignalCapture, signals_to_json
from mtguard.eval.configs import (
    KEYLESS_REPLAYS,
    JudgeCache,
    replay_l1_l2_judge,
)
from mtguard.eval.dataset import load_corpus
from mtguard.eval.metrics import aggregate, outcome_from_result
from mtguard.eval.report import write_report
from mtguard.judge import EscalationJudge
from mtguard.pack_loader import DemoPack

DEFAULT_CONFIGS = ("l1_only", "l2_only", "l1_l2")


def run_eval(
    pack_dir: Path,
    corpus_dir: Path,
    split: str = "dev",
    configs: tuple[str, ...] = DEFAULT_CONFIGS,
    judge: EscalationJudge | None = None,
    out_dir: Path | None = None,
    judge_cache_path: Path | None = None,
) -> dict:
    pack = DemoPack.load(Path(pack_dir))
    scenarios = load_corpus(Path(corpus_dir), split=split)
    captured = SignalCapture(pack).run(scenarios)

    metrics_by_config: dict[str, dict] = {}
    outcomes_by_config: dict = {}
    for name in configs:
        if name == "l1_l2_judge":
            if judge is None:
                raise ValueError("config 'l1_l2_judge' requires an EscalationJudge (use --judge)")
            cache = JudgeCache(judge_cache_path or Path("reports/eval/judge_cache.json"))
            results = [replay_l1_l2_judge(sig, judge, cache) for sig in captured]
            cache.save()
        elif name in KEYLESS_REPLAYS:
            results = [KEYLESS_REPLAYS[name](sig) for sig in captured]
        else:
            raise ValueError(f"Unknown config '{name}' (valid: {list(KEYLESS_REPLAYS) + ['l1_l2_judge']})")
        outcomes = [outcome_from_result(r) for r in results]
        outcomes_by_config[name] = outcomes
        metrics_by_config[name] = aggregate(outcomes)
        if name == "l1_l2_judge":
            metrics_by_config[name]["judge_invocations"] = sum(r.judge_invocations for r in results)
            metrics_by_config[name]["judge_denies"] = sum(r.judge_denies for r in results)

    manifest_path = Path(corpus_dir) / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None

    if out_dir is None:
        out_dir = Path("reports/eval") / datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = write_report(
        Path(out_dir), metrics_by_config, outcomes_by_config, signals_to_json(captured), split, manifest
    )
    return {"metrics": metrics_by_config, "report_path": str(report_path), "n_scenarios": len(scenarios)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MTGuard non-circular evaluation harness")
    parser.add_argument("--pack", default="demo_pack/nexa_copilot")
    parser.add_argument("--corpus", default="corpus/eval")
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    parser.add_argument("--configs", default=",".join(DEFAULT_CONFIGS),
                        help="comma-separated: l1_only,l2_only,l1_l2,l1_l2_judge")
    parser.add_argument("--judge", action="store_true", help="add l1_l2_judge config (needs JUDGE_API_KEY)")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    configs = tuple(c.strip() for c in args.configs.split(",") if c.strip())
    judge = None
    if args.judge or "l1_l2_judge" in configs:
        key = os.environ.get("JUDGE_API_KEY", "")
        if not key:
            print("Error: JUDGE_API_KEY requerida para la config con juez.", file=sys.stderr)
            return 2
        judge = EscalationJudge(pack=DemoPack.load(Path(args.pack)), api_key=key)
        if "l1_l2_judge" not in configs:
            configs = (*configs, "l1_l2_judge")

    result = run_eval(
        pack_dir=Path(args.pack),
        corpus_dir=Path(args.corpus),
        split=args.split,
        configs=configs,
        judge=judge,
        out_dir=Path(args.out) if args.out else None,
    )
    print(f"Escenarios: {result['n_scenarios']} · split={args.split}")
    for config, m in result["metrics"].items():
        print(
            f"  {config:12s} recall@FLAG={m['recall_flag']} recall@BLOCK={m['recall_block']} "
            f"FP@FLAG={m['fp_flag']} FP@BLOCK={m['fp_block']}"
        )
    print(f"Reporte: {result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
