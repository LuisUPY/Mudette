#!/usr/bin/env python3
"""Import external eval scenarios from public datasets (Phase 9.2).

Prepared in Phase 9.1; DOWNLOADS NOTHING until explicitly run. Requires:
  uv sync --extra eval-import        # installs `datasets`
  uv run python scripts/import_external_eval.py --source jbb --take 40 --accept-license

Sources
  jbb     JailbreakBench/JBB-Behaviors (single-turn seeds, MIT)
  mhj     ScaleAI/mhj (multi-turn human jailbreaks; may be gated → HF_TOKEN)
  safemt  SafeMTData/SafeMTData (ActorAttack multi-turn; verify license on card)

Anti-circularity protocol
  - Stratified take: first N rows in canonical dataset order (no cherry-picking).
  - Dataset revision (commit SHA) pinned into corpus/eval/manifest.json.
  - External cases go to the TEST split via --assemble-test, which freezes
    attacks_test.json (sha256 + date in manifest). After freeze: run-to-report only.
  - If a source's license does not permit redistribution, pass --hash-only to
    store ids+sha256 instead of text (cases rebuilt on demand by re-running).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus" / "eval"


def _require_datasets():
    try:
        import datasets  # noqa: F401

        return datasets
    except ImportError:
        print("Error: falta `datasets`. Instala con: uv sync --extra eval-import", file=sys.stderr)
        raise SystemExit(2)


def _resolve_commit_sha(dataset_name: str) -> str:
    """Real HF commit SHA of the dataset repo (not the declared dataset `version`,
    which is often 0.0.0). Pinning this into the manifest — and loading against it —
    makes the frozen test set reproducible, which the anti-circularity protocol requires."""
    from huggingface_hub import HfApi

    return HfApi().dataset_info(dataset_name).sha


def _extract_turns(row: dict, candidates: tuple[str, ...]) -> list[str] | None:
    """Defensive multi-schema extraction: returns user-turn texts or None."""
    for col in candidates:
        value = row.get(col)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        if isinstance(value, list) and value:
            if all(isinstance(v, str) for v in value):
                return [v.strip() for v in value if v.strip()]
            if all(isinstance(v, dict) for v in value):  # chat-format [{role, content|body}]
                turns = [
                    str(v.get("content") or v.get("body") or "").strip()
                    for v in value
                    if str(v.get("role", "user")).lower() in ("user", "human")
                ]
                return [t for t in turns if t] or None
    return None


def import_jbb(take: int) -> tuple[list[dict], str, str]:
    datasets = _require_datasets()
    name = "JailbreakBench/JBB-Behaviors"
    revision = _resolve_commit_sha(name)
    ds = datasets.load_dataset(name, "behaviors", revision=revision)
    rows = list(ds["harmful"])[:take]
    scenarios = []
    for i, row in enumerate(rows):
        turns = _extract_turns(row, ("Goal", "goal", "prompt"))
        if not turns:
            raise ValueError(f"jbb row {i}: no turns found; columns={list(row)}")
        scenarios.append({
            "id": f"jbb_{i:04d}", "source": "jbb", "license": "MIT",
            "category": "jailbreak", "label": "attack", "turns": turns,
            "notes": f"JBB behavior: {row.get('Behavior', '')}"[:120],
        })
    return scenarios, name, revision


def _mhj_user_turns(row: dict) -> list[str]:
    """MHJ schema: flat message_0..message_N columns, each a JSON string
    {"body": ..., "role": "system"|"user"|"assistant"}. Not a single list/column,
    so the generic _extract_turns candidates don't match — needs its own parse."""
    turns = []
    i = 0
    while True:
        raw = row.get(f"message_{i}")
        if raw is None:
            break
        try:
            msg = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            i += 1
            continue
        if msg.get("role") == "user":
            body = str(msg.get("body", "")).strip()
            if body:
                turns.append(body)
        i += 1
    return turns


def import_mhj(take: int) -> tuple[list[dict], str, str]:
    datasets = _require_datasets()
    name = "ScaleAI/mhj"  # gated: needs HF_TOKEN + license accept on HF
    revision = _resolve_commit_sha(name)
    ds = datasets.load_dataset(name, revision=revision)
    split = ds[next(iter(ds))]
    scenarios = []
    for i, row in enumerate(list(split)[:take]):
        turns = _mhj_user_turns(row)
        if not turns:
            raise ValueError(f"mhj row {i}: no user turns found; columns={list(row)}")
        scenarios.append({
            "id": f"mhj_{i:04d}", "source": "mhj", "license": "verify-on-HF-card",
            "category": "crescendo" if len(turns) > 1 else "jailbreak", "label": "attack",
            "turns": turns, "notes": f"tactic: {row.get('tactic', row.get('Tactic', ''))}"[:120],
        })
    return scenarios, name, revision


def import_safemt(take: int) -> tuple[list[dict], str, str]:
    datasets = _require_datasets()
    name = "SafeMTData/SafeMTData"
    revision = _resolve_commit_sha(name)
    ds = datasets.load_dataset(name, "Attack_600", revision=revision)
    split = ds[next(iter(ds))]
    scenarios = []
    for i, row in enumerate(list(split)[:take]):
        turns = _extract_turns(row, ("multi_turn_queries", "queries", "turns", "conversations"))
        if not turns:
            raise ValueError(f"safemt row {i}: no turns found; columns={list(row)}")
        scenarios.append({
            "id": f"safemt_{i:04d}", "source": "safemt", "license": "verify-on-HF-card",
            "category": "crescendo", "label": "attack", "turns": turns,
            "notes": "ActorAttack multi-turn decomposition",
        })
    return scenarios, name, revision


IMPORTERS = {"jbb": import_jbb, "mhj": import_mhj, "safemt": import_safemt}


def _hash_only(scenarios: list[dict]) -> list[dict]:
    out = []
    for s in scenarios:
        h = hashlib.sha256("\x1e".join(s["turns"]).encode()).hexdigest()
        out.append({**s, "turns": [f"<redacted sha256:{h}>"], "notes": s["notes"] + " [hash-only: license]"})
    return out


def assemble_test(freeze: bool) -> None:
    """Merge external_*.json into attacks_test.json; optionally freeze (sha256+date)."""
    externals = sorted(CORPUS.glob("external_*.json"))
    if not externals:
        raise SystemExit("No hay external_*.json que ensamblar. Corre importadores primero.")
    merged: list[dict] = []
    for path in externals:
        merged.extend(json.loads(path.read_text(encoding="utf-8")))
    test_path = CORPUS / "attacks_test.json"
    manifest_path = CORPUS / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("test_freeze"):
        raise SystemExit(
            f"Test set CONGELADO el {manifest['test_freeze']['date']} — prohibido regenerarlo "
            "(protocolo anti-circularidad). Borra el freeze manualmente solo con justificación escrita."
        )
    test_path.write_text(json.dumps(merged, indent=1, ensure_ascii=False), encoding="utf-8")
    by_source = Counter(s.get("source", "?") for s in merged)
    print(f"attacks_test.json: {len(merged)} escenarios de {len(externals)} fuentes — {dict(by_source)}")
    if freeze:
        # A frozen test set must pin BOTH sides: attacks_test.json AND benign_test.json.
        # Without benigns there is no false-positive denominator (the core reviewer concern).
        benign_path = CORPUS / "benign_test.json"
        if not benign_path.exists():
            raise SystemExit(
                "Falta benign_test.json — un test sin benignos no puede medir FP (R2#2). "
                "Crea la Fuente D antes de congelar."
            )
        benign = json.loads(benign_path.read_text(encoding="utf-8"))
        manifest["test_freeze"] = {
            "date": str(date.today()),
            "sha256_attacks_test": hashlib.sha256(test_path.read_bytes()).hexdigest(),
            "sha256_benign_test": hashlib.sha256(benign_path.read_bytes()).hexdigest(),
            "n_attacks": len(merged),
            "n_benign": len(benign),
            "n_scenarios": len(merged) + len(benign),
            "attacks_by_source": dict(by_source),
        }
        manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
        print(
            f"Test set CONGELADO: {len(merged)} ataques + {len(benign)} benignos "
            "(sha256 de ambos en manifest). Solo run-to-report desde ahora."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=sorted(IMPORTERS))
    parser.add_argument("--take", type=int, default=40)
    parser.add_argument("--accept-license", action="store_true",
                        help="confirma que revisaste la licencia del dataset en su card de HF")
    parser.add_argument("--hash-only", action="store_true",
                        help="guarda ids+sha256 en vez de texto (licencias sin redistribución)")
    parser.add_argument("--assemble-test", action="store_true",
                        help="fusiona external_*.json en attacks_test.json")
    parser.add_argument("--freeze", action="store_true", help="congela el test set (con --assemble-test)")
    args = parser.parse_args()

    if args.assemble_test:
        assemble_test(freeze=args.freeze)
        return 0
    if not args.source:
        parser.error("--source requerido (o usa --assemble-test)")
    if not args.accept_license:
        parser.error(f"Revisa la licencia de '{args.source}' en HuggingFace y pasa --accept-license")

    scenarios, dataset_name, revision = IMPORTERS[args.source](args.take)
    if args.hash_only:
        scenarios = _hash_only(scenarios)
    out = CORPUS / f"external_{args.source}.json"
    out.write_text(json.dumps(scenarios, indent=1, ensure_ascii=False), encoding="utf-8")

    manifest_path = CORPUS / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][args.source] = {
        "dataset": dataset_name, "revision": revision, "take": args.take,
        "hash_only": args.hash_only, "imported": str(date.today()), "split": "test",
    }
    manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{out.name}: {len(scenarios)} escenarios · revision={revision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
