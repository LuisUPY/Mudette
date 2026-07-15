"""Eval dataset schema and loaders.

A scenario is a full multi-turn conversation; a single message is a
1-turn scenario. The `label` field is the ONLY ground truth and comes
from provenance (who authored/collected the case), never from MTGuard.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

ATTACK_CATEGORIES = {
    "crescendo",
    "salami",
    "jailbreak",
    "social_engineering",
    "direct_probe",
}
BENIGN_CATEGORIES = {
    "benign_support",
    "benign_topic_shift",
    "benign_admin_vocab",
}
VALID_LABELS = {"attack", "benign"}


@dataclass(frozen=True)
class EvalScenario:
    id: str
    source: str  # legacy | legacy_playbook | mhj | safemt | jbb | domain_gen | hard_benign
    license: str
    category: str
    label: str  # attack | benign — the only ground truth
    turns: tuple[str, ...]
    notes: str = ""


def _validate(raw: dict, path: Path) -> EvalScenario:
    for key in ("id", "source", "license", "category", "label", "turns"):
        if key not in raw:
            raise ValueError(f"{path}: scenario missing '{key}': {raw.get('id', raw)}")
    label = raw["label"]
    category = raw["category"]
    if label not in VALID_LABELS:
        raise ValueError(f"{path}: invalid label '{label}' in {raw['id']}")
    expected = ATTACK_CATEGORIES if label == "attack" else BENIGN_CATEGORIES
    if category not in expected:
        raise ValueError(
            f"{path}: category '{category}' inconsistent with label '{label}' in {raw['id']}"
        )
    turns = raw["turns"]
    if not isinstance(turns, list) or not turns or not all(
        isinstance(t, str) and t.strip() for t in turns
    ):
        raise ValueError(f"{path}: turns must be a non-empty list of non-empty strings in {raw['id']}")
    return EvalScenario(
        id=raw["id"],
        source=raw["source"],
        license=raw["license"],
        category=category,
        label=label,
        turns=tuple(turns),
        notes=raw.get("notes", ""),
    )


def load_scenarios(path: Path) -> list[EvalScenario]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    scenarios = [_validate(item, Path(path)) for item in raw]
    seen: set[str] = set()
    for s in scenarios:
        if s.id in seen:
            raise ValueError(f"{path}: duplicate scenario id '{s.id}'")
        seen.add(s.id)
    return scenarios


def load_corpus(corpus_dir: Path, split: str = "dev") -> list[EvalScenario]:
    """Load attacks_<split>.json + benign_<split>.json. Test split may not exist yet."""
    corpus_dir = Path(corpus_dir)
    scenarios: list[EvalScenario] = []
    missing: list[str] = []
    for stem in (f"attacks_{split}.json", f"benign_{split}.json"):
        path = corpus_dir / stem
        if path.exists():
            scenarios.extend(load_scenarios(path))
        else:
            missing.append(stem)
    if not scenarios:
        raise FileNotFoundError(f"No corpus files for split '{split}' in {corpus_dir} (missing: {missing})")
    ids = [s.id for s in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate ids across corpus files in split '{split}'")
    return scenarios
