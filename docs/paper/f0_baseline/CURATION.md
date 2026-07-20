# F0 Baseline — Curation Notes (frozen test set, single run)

**Status:** curated paper material. The raw artifacts in this directory
(`report.md`, `metrics.json`) are verbatim copies of the harness output at
`reports/eval/20260720-072032/` (gitignored). Numbers below are quoted, never
edited. Per the freeze protocol, no re-runs or tuning against the test set are
permitted; this is a run-to-report result.

## Run provenance

- Command: `./scripts/run-eval.sh test` (keyless configs: `l1_only`, `l2_only`, `l1_l2`; no judge, no API calls)
- Corpus commit: `ece1d5a` (Phase 9.6 freeze)
- Test set: 147 scenarios = 105 attacks (jbb 40, safemt 30, domain_gen 35) + 42 benigns (24 hard, 18 easy)
- Freeze hashes: `attacks_test.json` = `8f92d178…7df26c`, `benign_test.json` = `db769a67…81f62d` (full values in `report.md` manifest section)
- `signals.json` (per-scenario raw signals, ~300 KB) is not committed; it is
  deterministically reproducible from the frozen corpus at the commit above.

## Table 1 candidate — keyless ablation on frozen test

| Config | recall@FLAG | recall@BLOCK | FP@FLAG | FP@BLOCK | prec@FLAG |
|---|---|---|---|---|---|
| l1_only | 11.4% | 11.4% | 2.4% | 2.4% | 92.3% |
| l2_only | 0.0% | 0.0% | 0.0% | 0.0% | n/a |
| l1_l2 | 11.4% | 11.4% | 2.4% | 2.4% | 92.3% |

This is the floor against which the judge config (F1) will be measured.

## Finding 1 — Ghost #3 confirmed empirically

The fusion analysis (`fusion.py`) proves the pure trajectory layer can never
reach CONTAIN on its own. The frozen test run confirms it: `l2_only`
recall@BLOCK = **0.0%** on all 105 attacks. The empirical result is in fact
stronger than the mathematical bound: `l2_only` never even reached FLAG
(recall@FLAG = 0.0%), i.e. on this test set the trajectory layer alone raised
no alert whatsoever.

## Finding 2 — zero incremental value of trajectory at FLAG (keyless)

0/105 attacks were flagged by `l1_l2` that `l1_only` missed; Δrecall@FLAG =
+0.0pp. Factor attribution shows trajectory factors co-fire on 75% of
`l1_l2` flags but never fire independently. In the keyless stack, L2 currently
adds corroborating signal, not coverage. This motivates (a) the judge layer
and (b) any future L2 sensitivity work — which must happen on dev only.

## Finding 3 — keyless layers do not generalize beyond the announced domain

Per-source recall@FLAG (l1_l2): domain_gen **31.4%**, safemt **3.3%**,
jbb **0.0%**. Detection is concentrated on attacks matching Nexa's announced
threat model (credentials / export / prompt exfil); generic harmful-content
attacks from external benchmarks pass the keyless layers almost untouched.
This is the honest negative result that answers the RAGE reviewers'
circularity concern: with self-authored cases quarantined in dev and the test
set dominated by external sources, the keyless detector's true reach is ~11%,
not the flattering numbers a self-authored test would have produced.

## Finding 4 — false positives are low and concentrated where expected

FP@FLAG = 2.4% overall: 0% on easy benigns (18), 4.2% on hard-negative
benigns (24; category `benign_admin_vocab` at 11.1%, i.e. 1/9). Median first
FLAG on detected multi-turn attacks: turn 3 (0-indexed).

## Framing for the paper

F0 establishes that cheap, deterministic layers buy high precision (92.3%)
and near-zero FP on normal traffic, but only domain-tuned recall. The research
question for F1 is whether the escalation judge closes the generalization gap
(jbb/safemt recall) without sacrificing the FP profile — measured on this same
frozen set, run-to-report, fail-closed on timeouts.
