"""Render eval results to Markdown + JSON under reports/eval/<timestamp>/."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from mtguard.eval.metrics import ScenarioOutcome, flagged_ids


def _pct(value: float | None) -> str:
    return f"{value * 100:.1f}%" if value is not None else "n/a"


def render_markdown(
    metrics_by_config: dict[str, dict],
    outcomes_by_config: dict[str, list[ScenarioOutcome]],
    split: str,
    manifest: dict | None,
) -> str:
    lines = [
        "# MTGuard — Reporte de evaluación no circular",
        "",
        f"Split: **{split}** · Generado: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Ground truth = etiqueta de procedencia del escenario, nunca la salida del detector. "
        "FLAG = veredicto máximo ≥ ALERT · BLOCK = ≥ CONTAIN (incluye judge DENY).",
        "",
        "## Ablación por configuración",
        "",
        "| Config | recall@FLAG | recall@BLOCK | FP@FLAG | FP@BLOCK | prec@FLAG | Δrecall@FLAG vs l1_only |",
        "|---|---|---|---|---|---|---|",
    ]
    base = metrics_by_config.get("l1_only", {}).get("recall_flag")
    for config, m in metrics_by_config.items():
        delta = (
            f"{(m['recall_flag'] - base) * 100:+.1f}pp"
            if base is not None and m.get("recall_flag") is not None and config != "l1_only"
            else "—"
        )
        lines.append(
            f"| {config} | {_pct(m.get('recall_flag'))} | {_pct(m.get('recall_block'))} "
            f"| {_pct(m.get('fp_flag'))} | {_pct(m.get('fp_block'))} "
            f"| {_pct(m.get('precision_flag'))} | {delta} |"
        )

    # Incremental value of trajectory: attacks flagged by l1_l2 but not l1_only
    if "l1_only" in outcomes_by_config and "l1_l2" in outcomes_by_config:
        only_l2 = flagged_ids(outcomes_by_config["l1_l2"]) - flagged_ids(outcomes_by_config["l1_only"])
        n_attacks = metrics_by_config["l1_l2"]["n_attacks"]
        lines += [
            "",
            f"**Valor incremental de la trayectoria:** {len(only_l2)}/{n_attacks} ataques "
            f"FLAGgeados por L1+L2 que L1 solo NO detectó"
            + (f": `{sorted(only_l2)}`" if only_l2 else "."),
        ]

    lines += ["", "## Atribución de factores en el primer FLAG (¿quién hace el trabajo?)", ""]
    for config, m in metrics_by_config.items():
        attribution = m.get("factor_attribution_at_flag", {})
        lines.append(f"**{config}**: " + (
            " · ".join(f"`{f}` {_pct(r)}" for f, r in attribution.items()) if attribution else "sin FLAGs"
        ))
        lines.append("")

    lines += [
        "## Desglose por fuente (¿generaliza, o solo detecta el dominio propio?)",
        "",
        "Las fuentes externas (`jbb`, `safemt`) son contenido dañino genérico; `domain_gen` "
        "ataca el threat model anunciado de Nexa (credenciales / export / exfil de prompt). "
        "Un recall alto en `domain_gen` con recall bajo en las genéricas indica que el detector "
        "está afinado a su dominio, no que generalice.",
        "",
    ]
    for config, m in metrics_by_config.items():
        lines += [f"### {config}", "", "| Fuente | n | recall@FLAG | recall@BLOCK | FP@FLAG |", "|---|---|---|---|---|"]
        for src, g in m.get("by_source", {}).items():
            n = g["n_attacks"] or g["n_benign"]
            lines.append(
                f"| {src} | {n} | {_pct(g['recall_flag'])} | {_pct(g['recall_block'])} | {_pct(g['fp_flag'])} |"
            )
        lines.append("")

    lines += ["## Desglose por categoría", ""]
    for config, m in metrics_by_config.items():
        lines += [f"### {config}", "", "| Categoría | n | recall@FLAG | recall@BLOCK | FP@FLAG |", "|---|---|---|---|---|"]
        for cat, g in m.get("by_category", {}).items():
            n = g["n_attacks"] or g["n_benign"]
            lines.append(
                f"| {cat} | {n} | {_pct(g['recall_flag'])} | {_pct(g['recall_block'])} | {_pct(g['fp_flag'])} |"
            )
        lines.append("")

    lines += [
        "## Detección temprana (ataques multi-turn)",
        "",
        "| Config | mediana del primer FLAG (turno, 0-idx) |",
        "|---|---|",
    ]
    for config, m in metrics_by_config.items():
        lines.append(f"| {config} | {m.get('median_first_flag_turn_multiturn', 'n/a')} |")

    lines += [
        "",
        "## Limitaciones declaradas",
        "",
        "- Los escenarios `legacy`/`legacy_playbook` fueron escritos por los autores del detector: "
        "viven solo en dev y no sustentan afirmaciones de generalización.",
        "- Las fuentes externas (cuando estén integradas) son de dominio genérico; las regiones L2 "
        "del pack son específicas de IT — leer las métricas por fuente, no solo el agregado.",
        "- CI no impone bandas de recall (anti-circularidad); el número se reporta, no se garantiza.",
    ]
    if manifest:
        lines += ["", "## Procedencia (manifest)", "", "```json", json.dumps(manifest, indent=1, ensure_ascii=False), "```"]
    return "\n".join(lines) + "\n"


def write_report(
    out_dir: Path,
    metrics_by_config: dict[str, dict],
    outcomes_by_config: dict[str, list[ScenarioOutcome]],
    signals_json: list[dict],
    split: str,
    manifest: dict | None,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(
        json.dumps(metrics_by_config, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "signals.json").write_text(
        json.dumps(signals_json, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    report_path = out_dir / "report.md"
    report_path.write_text(
        render_markdown(metrics_by_config, outcomes_by_config, split, manifest), encoding="utf-8"
    )
    return report_path
