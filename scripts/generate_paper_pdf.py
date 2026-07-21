#!/usr/bin/env python3
"""Render docs/paper/MUDETTE-F.md content into a visual PDF paper.

Reuses the visual language of generate_command_glossary.py (dark cover,
colored section rules, accent-bar callout cards, filled/bordered tables)
adapted for an academic-report layout. Content is hand-transcribed from
the Markdown draft rather than parsed, so table numbers and quotes here
must be kept in sync with docs/paper/MUDETTE-F.md and the underlying
docs/paper/{f0_baseline,f1_judge,f2_dev,f2_test,f3_dev,f3_test}/ artifacts.
"""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "paper" / "MUDETTE-F.pdf"

SLATE_900 = (15, 23, 42)
SLATE_800 = (30, 41, 59)
SLATE_600 = (71, 85, 105)
SLATE_500 = (100, 116, 139)
SLATE_400 = (148, 163, 184)
SLATE_200 = (226, 232, 240)
SLATE_100 = (241, 245, 249)
SLATE_50 = (248, 250, 252)
BLUE = (37, 99, 235)
BLUE_LIGHT = (219, 234, 254)
GREEN = (16, 185, 129)
GREEN_LIGHT = (209, 250, 229)
GREEN_DARK = (5, 122, 85)
AMBER = (217, 119, 6)
RED = (220, 38, 38)
RED_LIGHT = (254, 226, 226)
PURPLE = (124, 58, 237)
PURPLE_LIGHT = (237, 233, 254)

PAGE_W = 210
MARGIN = 20
CONTENT_W = PAGE_W - 2 * MARGIN


def _register_fonts(pdf: FPDF) -> str:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            pdf.add_font("Paper", "", str(path))
            pdf.add_font("Paper", "B", str(path))
            pdf.add_font("Paper", "I", str(path))
            return "Paper"
    return "Helvetica"


class PaperPDF(FPDF):
    def __init__(self) -> None:
        super().__init__()
        self.body_font = _register_fonts(self)
        self.mono_font = "Courier"
        self.set_margins(MARGIN, 15, MARGIN)
        self.running_title = "MTGuard / Mudette — Non-Circular Multi-Turn Evaluation"

    def body(self, style: str = "", size: int = 10) -> None:
        self.set_font(self.body_font, style, size)

    def mono(self, style: str = "", size: int = 8) -> None:
        self.set_font(self.mono_font, style, size)

    def header(self) -> None:
        if self.page_no() <= 2:
            return
        self.set_y(8)
        self.body("I", 8)
        self.set_text_color(*SLATE_400)
        self.cell(0, 6, self.running_title, align="R")
        self.set_draw_color(*SLATE_200)
        self.line(MARGIN, 15, PAGE_W - MARGIN, 15)
        self.set_y(19)

    def footer(self) -> None:
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.body("", 8)
        self.set_text_color(*SLATE_400)
        self.cell(0, 8, f"{self.page_no()} / {{nb}}", align="C")

    # ---- rich inline text (supports **bold** and `code`) -----------------

    def rich(self, text: str, size: int = 10, lh: float = 5.6, color=SLATE_800) -> None:
        self.body("", size)
        self.set_text_color(*color)
        tokens = re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)
        for tok in tokens:
            if not tok:
                continue
            if tok.startswith("**") and tok.endswith("**"):
                self.set_font(self.body_font, "B", size)
                self.set_text_color(*SLATE_900)
                self.write(lh, tok[2:-2])
                self.set_font(self.body_font, "", size)
                self.set_text_color(*color)
            elif tok.startswith("`") and tok.endswith("`"):
                self.set_font(self.mono_font, "", size - 1)
                self.set_text_color(*BLUE)
                self.write(lh, tok[1:-1])
                self.set_font(self.body_font, "", size)
                self.set_text_color(*color)
            else:
                self.write(lh, tok)
        self.ln(lh + 1.5)

    def p(self, text: str, size: int = 10, lh: float = 5.6, color=SLATE_800) -> None:
        self.rich(text, size=size, lh=lh, color=color)
        self.ln(1)

    # ---- structural helpers -----------------------------------------------

    def h1(self, number: str, title: str, new_page: bool = True) -> None:
        if new_page:
            self.add_page()
        self.body("B", 17)
        self.set_text_color(*BLUE)
        self.cell(0, 10, f"{number}  {title}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*BLUE)
        self.set_line_width(0.8)
        self.line(MARGIN, self.get_y(), MARGIN + 45, self.get_y())
        self.set_line_width(0.2)
        self.ln(7)

    def h2(self, number: str, title: str) -> None:
        if self.get_y() > 255:
            self.add_page()
        self.ln(2)
        self.body("B", 12.5)
        self.set_text_color(*SLATE_900)
        self.cell(0, 8, f"{number}  {title}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def bullet(self, text: str, size: int = 10) -> None:
        x0 = self.get_x()
        self.set_text_color(*BLUE)
        self.body("B", size)
        self.cell(5, 5.6, "\u2022")
        self.set_x(x0 + 6)
        w = self.w - self.r_margin - (x0 + 6)
        self.rich_in_width(text, w, size=size)
        self.set_x(x0)

    def rich_in_width(self, text: str, w: float, size: int = 10, lh: float = 5.6) -> None:
        x0 = self.get_x()
        y0 = self.get_y()
        self.set_left_margin(x0)
        self.rich(text, size=size, lh=lh)
        self.set_left_margin(MARGIN)

    def code_block(self, lines: list[str], size: int = 8.5) -> None:
        self.set_fill_color(*SLATE_50)
        self.set_draw_color(*SLATE_200)
        h = 5.2 * len(lines) + 5
        y0 = self.get_y()
        if y0 + h > 275:
            self.add_page()
            y0 = self.get_y()
        self.rect(MARGIN, y0, CONTENT_W, h, "DF")
        self.set_xy(MARGIN + 4, y0 + 2.5)
        self.mono("", size)
        self.set_text_color(*SLATE_800)
        for line in lines:
            self.set_x(MARGIN + 4)
            self.cell(0, 5.2, line, new_x="LMARGIN", new_y="NEXT")
        self.set_xy(MARGIN, y0 + h + 4)

    def table(
        self,
        headers: list[str],
        rows: list[list[str]],
        col_w: list[float],
        highlight_row: int | None = None,
        highlight_color=GREEN_LIGHT,
        cell_colors: dict | None = None,
        size: int = 8.3,
        header_size: int = 8.3,
    ) -> None:
        cell_colors = cell_colors or {}
        if self.get_y() > 240:
            self.add_page()
        self.body("B", header_size)
        self.set_fill_color(*SLATE_800)
        self.set_text_color(255, 255, 255)
        x0 = self.get_x()
        for i, h in enumerate(headers):
            self.cell(col_w[i], 7.5, h, border=0, fill=True, align="C")
        self.ln()
        self.body("", size)
        for r_i, row in enumerate(rows):
            if self.get_y() > 275:
                self.add_page()
                self.body("B", header_size)
                self.set_fill_color(*SLATE_800)
                self.set_text_color(255, 255, 255)
                for i, h in enumerate(headers):
                    self.cell(col_w[i], 7.5, h, border=0, fill=True, align="C")
                self.ln()
                self.body("", size)
            fill = SLATE_50 if r_i % 2 == 0 else (255, 255, 255)
            if highlight_row is not None and r_i == highlight_row:
                fill = highlight_color
            self.set_fill_color(*fill)
            self.set_draw_color(*SLATE_200)
            for i, val in enumerate(row):
                txt_color = cell_colors.get((r_i, i), SLATE_800)
                self.set_text_color(*txt_color)
                style = "B" if (highlight_row is not None and r_i == highlight_row) else ""
                self.body(style, size)
                self.cell(col_w[i], 7, val, border=1, fill=True, align="C")
            self.ln()
        self.ln(4)

    def callout(self, tag: str, color, title: str, body_lines: list[str]) -> None:
        line_h = 5.0
        w_text = CONTENT_W - 12
        self.body("", 9)
        wrapped_line_counts = [
            len(self.multi_cell(w_text, line_h, text, dry_run=True, output="LINES"))
            for text in body_lines
        ]
        text_h = sum(wrapped_line_counts) * line_h + (len(body_lines) - 1) * 1.5
        h = 8 + 6.5 + text_h + 6
        y0 = self.get_y()
        if y0 + h > 280:
            self.add_page()
            y0 = self.get_y()
        self.set_fill_color(*SLATE_50)
        self.set_draw_color(*SLATE_200)
        self.rect(MARGIN, y0, CONTENT_W, h, "DF")
        self.set_fill_color(*color)
        self.rect(MARGIN, y0, 3.2, h, "F")
        self.set_xy(MARGIN + 8, y0 + 3)
        self.body("B", 8.5)
        self.set_text_color(*color)
        self.cell(0, 4.5, tag, new_x="LMARGIN", new_y="NEXT")
        self.set_x(MARGIN + 8)
        self.body("B", 11)
        self.set_text_color(*SLATE_900)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        for line in body_lines:
            self.set_x(MARGIN + 8)
            self.body("", 9)
            self.set_text_color(*SLATE_600)
            self.multi_cell(w_text, line_h, line)
            self.ln(1.5)
        self.set_xy(MARGIN, y0 + h + 5)

    def meta_line(self, label: str, value: str) -> None:
        self.body("B", 9.5)
        self.set_text_color(*SLATE_400)
        self.cell(38, 6, label)
        self.body("", 9.5)
        self.set_text_color(*SLATE_200)
        self.multi_cell(0, 6, value)


# --------------------------------------------------------------------------
# Page builders
# --------------------------------------------------------------------------


def cover_page(pdf: PaperPDF) -> None:
    pdf.add_page()
    pdf.set_fill_color(*SLATE_900)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.set_fill_color(*BLUE)
    pdf.rect(0, 0, 210, 5, "F")

    pdf.set_y(38)
    pdf.body("B", 9)
    pdf.set_text_color(*BLUE)
    pdf.cell(0, 6, "MUDETTE PROJECT  \u2014  MTGUARD EVALUATION REPORT", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.body("B", 24)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(
        0, 11,
        "MTGuard: Closing the Multi-Turn\nGeneralization Gap in a Layered\nLLM-Injection Defense",
        align="C",
    )
    pdf.ln(4)
    pdf.body("I", 13)
    pdf.set_text_color(*SLATE_400)
    pdf.cell(0, 8, "An Empirical, Non-Circular Evaluation of the Mudette Cascade",
             align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(14)
    pdf.set_draw_color(*SLATE_600)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(10)

    pdf.set_x(35)
    pdf.meta_line("Authors", "Mudette Research Team")
    pdf.set_x(35)
    pdf.meta_line("Venue", "Global South AI Safety research program \u2014 non-circular evaluation follow-up to RAGE")
    pdf.set_x(35)
    pdf.meta_line("Repository", "Mudette-F \u2014 Python 3.14 (uv), local-only")
    pdf.set_x(35)
    pdf.meta_line("Code & Data", "docs/paper/{f0..f3}_*/  \u00b7  corpus/eval/manifest.json (sha256-pinned)")
    pdf.set_x(35)
    pdf.meta_line("Predecessor", "RAGE \u2014 Robust Agentic Security Gateway for Text-to-SQL (June 2026)")

    pdf.set_y(255)
    pdf.body("B", 10)
    pdf.set_text_color(*GREEN)
    pdf.cell(0, 6, "+3.8pp recall  \u00b7  94.1% precision  \u00b7  0.0% new false positives", align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.body("", 8.5)
    pdf.set_text_color(*SLATE_500)
    pdf.cell(0, 6, "Frozen test set \u00b7 147 scenarios \u00b7 4 run-to-report executions \u00b7 Phases F0\u2013F3",
             align="C", new_x="LMARGIN", new_y="NEXT")


def abstract_page(pdf: PaperPDF) -> None:
    pdf.add_page()
    pdf.body("B", 16)
    pdf.set_text_color(*SLATE_900)
    pdf.cell(0, 10, "Abstract", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*BLUE)
    pdf.set_line_width(0.8)
    pdf.line(MARGIN, pdf.get_y(), MARGIN + 30, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(6)

    y0 = pdf.get_y()
    text = (
        "Mudette is a research demo defending a fictitious enterprise copilot, Nexa Copilot, against "
        "multi-turn prompt-injection attacks, built around a layered detection engine we call **MTGuard**: "
        "a deterministic regex pre-filter (L1), an embedding-based conversational trajectory guard (L2), "
        "a weighted risk-fusion function, and an optional NVIDIA NIM-hosted LLM escalation judge. Mudette "
        "was built independently of its predecessor RAGE without incorporating professional reviewer "
        "feedback at design time. To compensate, we built a strict non-circular evaluation harness \u2014 a "
        "frozen, sha256-pinned test set assembled from external jailbreak benchmarks (JailbreakBench, "
        "SafeMTData) plus blind-generated in-domain and hard-negative corpora, evaluated under a "
        "run-to-report protocol that forbids iteration against the frozen split. Across four experimental "
        "phases (F0\u2013F3) we used this harness to expose, name, and fix successive structural bottlenecks "
        "in the cascade: a mathematically provable ceiling on the trajectory layer alone (never reaching "
        "the block verdict), a judge invocation gate that starved the LLM judge of all traffic, and \u2014 once "
        "the gate was fixed \u2014 a single-turn \u201camnesia\u201d in the judge that classified individually-innocuous "
        "turns of multi-turn attacks as benign. Injecting a three-turn raw conversational window into the "
        "judge\u2019s prompt, tuned exclusively on a held-out development split and verified with exactly one "
        "frozen-test execution, flipped 4 of 5 previously-missed attacks into well-reasoned denials, raising "
        "frozen-test recall from **11.4% to 15.2%** (+3.8 percentage points) and precision from **92.3% to "
        "94.1%**, with false positives unchanged at **2.4%** and zero false positives among the judge\u2019s own "
        "decisions. We report this result alongside its boundary \u2014 a purely volumetric escalation attack "
        "that the fix does not catch, predicted on dev before the test run \u2014 and an unresolved out-of-domain "
        "generalization gap on generic jailbreak content, which the evidence localizes upstream of the judge "
        "entirely."
    )
    box_h = 168
    pdf.set_fill_color(*SLATE_50)
    pdf.set_draw_color(*SLATE_200)
    pdf.rect(MARGIN, y0, CONTENT_W, box_h, "DF")
    pdf.set_fill_color(*BLUE)
    pdf.rect(MARGIN, y0, 3.2, box_h, "F")
    pdf.set_xy(MARGIN + 8, y0 + 6)
    pdf.set_left_margin(MARGIN + 8)
    pdf.rich(text, size=10.3, lh=5.4)
    pdf.set_left_margin(MARGIN)
    pdf.set_xy(MARGIN, y0 + box_h + 8)

    pdf.body("B", 9.5)
    pdf.set_text_color(*SLATE_500)
    pdf.cell(0, 6, "Keywords:", new_x="LMARGIN", new_y="NEXT")
    pdf.body("I", 9.5)
    pdf.set_text_color(*SLATE_600)
    pdf.multi_cell(
        0, 5.6,
        "multi-turn prompt injection \u00b7 non-circular evaluation \u00b7 LLM-as-judge \u00b7 conversational "
        "trajectory \u00b7 frozen test sets \u00b7 NVIDIA NIM \u00b7 fail-closed security"
    )


def section1_introduction(pdf: PaperPDF) -> None:
    pdf.h1("1", "Introduction")

    pdf.h2("1.1", "The circularity problem in LLM security evaluation")
    pdf.p(
        "A recurring failure mode in applied LLM-security research is *circular evaluation*: a defense is "
        "designed, a test set is authored by the same team that built the defense, and the defense is "
        "reported to perform well against it. Any detector tuned and measured against its own author's "
        "attacks will look strong regardless of whether it generalizes to attacks it did not anticipate. "
        "Our predecessor project, **RAGE** (Robust Agentic Security Gateway for Text-to-SQL), was evaluated "
        "with author-authored scenarios and internal metrics (AUC-D, TRI); external reviewer feedback on "
        "that submission \u2014 the starting point for this work \u2014 identified this circularity as the central "
        "methodological weakness to address in any follow-up."
    )
    pdf.p(
        "Mudette was, in a specific sense, built \u201cblind\u201d: its layered defense (MTGuard) was designed and "
        "implemented before this evaluation harness existed and before reviewer feedback was incorporated "
        "into the design process. Rather than retrofit the defense to a self-authored benchmark, we inverted "
        "the order of operations for this study: we built the strictest evaluation protocol we could design "
        "*first*, froze it, and only then asked what the existing defense actually does \u2014 accepting whatever "
        "the numbers said, including several negative results."
    )

    pdf.h2("1.2", "From RAGE to Mudette")
    pdf.p(
        "RAGE targeted a narrow, well-specified threat model \u2014 Crescendo-style multi-turn escalation "
        "against a text-to-SQL agent \u2014 with a four-layer pipeline (regex, RAG threat KB, stateful semantic "
        "filter, EWMA decision engine) and a hardened SQL gateway as a deterministic backstop. Mudette "
        "generalizes the defense to a broader enterprise-copilot setting (IT support for a fictitious "
        "company, Nexa Copilot) and renames the reusable core engine **MTGuard**: a pack-driven, "
        "multi-tenant architecture in which the detection cascade is agnostic to the specific agent it "
        "protects. The threat model widens accordingly, from SQL injection specifically to credential "
        "exfiltration, policy bypass, and prompt leakage via crescendo, salami-slicing, jailbreak, and "
        "social-engineering patterns."
    )

    pdf.h2("1.3", "Contributions")
    pdf.p("This paper reports four things:")
    pdf.bullet(
        "A **non-circular evaluation harness** with an explicit dev/test split, a sha256-pinned frozen "
        "test set dominated by external, non-self-authored attack sources, and a \u201crun-to-report\u201d "
        "protocol that forbids any iteration, threshold tuning, or model change against the frozen split "
        "once it is created."
    )
    pdf.bullet(
        "**Empirical confirmation of a proven mathematical property** of the fusion function "
        "(\u201cGhost #3\u201d): the trajectory layer alone can never reach the block verdict, and on the frozen "
        "test it in fact never raises any alert at all."
    )
    pdf.bullet(
        "**Discovery and naming of two novel failure modes** in LLM-judge-augmented detection cascades, "
        "found and fixed strictly through the dev split before being measured once on the frozen test: "
        "*gate starvation* (Ghost #4) and *single-turn amnesia*."
    )
    pdf.bullet(
        "A **minimal, cost-preserving fix** \u2014 a raw three-turn conversational window in the judge's "
        "prompt, with no AI-generated summarization \u2014 that recovers 4 of 5 previously-missed multi-turn "
        "attacks on the frozen test with zero added false positives, together with an honestly reported "
        "boundary case and an out-of-domain generalization gap that remains open."
    )


def section2_architecture(pdf: PaperPDF) -> None:
    pdf.h1("2", "System Architecture & Evaluation Framework")

    pdf.h2("2.1", "The MTGuard cascade")
    pdf.p(
        "MTGuard processes each conversational turn through a fixed, four-stage pipeline before any "
        "response is generated:"
    )
    pdf.code_block([
        "user_message -> L1 RegexGuard -> L2 TrajectoryGuard -> RiskFusion",
        "             -> [optional] EscalationJudge -> UserGate -> NexaAgent (RAG + LLM)",
    ])
    pdf.p(
        "**L1 \u2014 RegexGuard.** A deterministic pre-filter of compiled regex rules with severity levels "
        "(LOW/MEDIUM/HIGH), covering known injection signatures. Cost: O(1) per turn, no embeddings, no "
        "API calls."
    )
    pdf.p(
        "**L2 \u2014 TrajectoryGuard.** Embeds each turn (2048-dimensional HashingVectorizer, L2-normalized) "
        "and tracks, per session: cosine proximity to benign-intent and sensitive-region centroids, "
        "turn-to-turn drift, an EWMA of proximity (\u03b1 = 0.25), and a 3-turn escalation-pattern detector."
    )
    pdf.p("**RiskFusion.** Combines L1 and L2 into a bounded risk score (0\u2013100) and a four-level verdict:")
    pdf.table(
        ["Factor", "Weight", "Trigger"],
        [
            ["l1_high", "45 (floor 75)", "L1 hit, HIGH severity"],
            ["l1_medium", "25", "L1 hit, MEDIUM severity"],
            ["approaching_sensitive", "20", "max_proximity >= 0.62 and > safe_score"],
            ["escalation", "15", "3-turn escalation pattern"],
            ["trajectory_high", "10", "trajectory_risk >= 0.10"],
            ["proximity_high", "10", "max_proximity >= 0.18"],
        ],
        col_w=[62, 32, 76],
    )
    pdf.p(
        "Verdict bands: **CLEAR** (<25), **WATCH** (25\u201344), **ALERT** (45\u201374), **CONTAIN** (\u226575). An "
        "`l1_high` hit unconditionally floors the score at 75 and forces CONTAIN \u2014 a deterministic backstop "
        "analogous to RAGE's SQL gateway. A safe-score veto can demote a marginal CONTAIN back to ALERT."
    )
    pdf.p(
        "**EscalationJudge.** An optional LLM reviewer, invoked only when the verdict is WATCH or ALERT "
        "and the risk score clears a configurable gate. It calls an NVIDIA NIM-hosted model "
        "(`meta/llama-3.1-8b-instruct`) with the pack's judge instructions, the current message, raw L1/L2/"
        "fusion signals, and \u2014 as of Phase 3 of this study \u2014 a bounded window of prior turns. It returns a "
        "single-line ALLOW/DENY decision; a DENY upgrades the verdict to CONTAIN."
    )

    pdf.h2("2.2", "NVIDIA NIM inference and fail-closed semantics")
    pdf.p(
        "Both the main agent and the judge call NVIDIA NIM's OpenAI-compatible endpoint with separate API "
        "keys and cached HTTP clients configured with explicit, asymmetric timeouts: 60s (10s connect, "
        "1 retry) for the main agent, 20s (10s connect, 0 retries) for the judge. Judge decisions are "
        "memoized in a persistent cache keyed by `sha256(model || prompt)`."
    )
    pdf.p(
        "Critically, **no offline or simulated mode exists anywhere in the pipeline.** A missing API key "
        "raises before any turn is processed; a timeout, connection error, or malformed NIM response raises "
        "and propagates rather than being silently swallowed into a default ALLOW. The system fails closed "
        "on infrastructure failure, never silently permissive \u2014 an invariant held through every phase of "
        "this study."
    )

    pdf.h2("2.3", "Evaluation methodology")
    pdf.p("The evaluation corpus draws from five sources, each tagged with license and provenance:")
    pdf.table(
        ["Source", "Content", "License", "Split"],
        [
            ["legacy(_playbook)", "Self-authored cases", "self-authored", "dev only"],
            ["domain_gen", "Blind in-domain attacks", "self-authored", "dev + test"],
            ["hard/easy_benign", "Blind hard-negative / normal benigns", "self-authored", "dev / dev+test"],
            ["jbb", "JailbreakBench/JBB-Behaviors", "MIT", "test only"],
            ["safemt", "SafeMTData/SafeMTData", "MIT", "test only"],
        ],
        col_w=[38, 62, 32, 38],
    )
    pdf.p(
        "A sixth source, ScaleAI/MHJ, was imported and then **excluded** on license grounds: it is "
        "CC-BY-NC-4.0 (non-commercial), and the only redaction scheme offered by the import tooling "
        "(`--hash-only`) replaces attack text with a placeholder that the detector would classify instead "
        "of the real attack \u2014 silently corrupting recall. We chose exclusion over a corrupted metric."
    )
    pdf.p(
        "**The freeze protocol.** The test split was assembled once (105 attacks: 40 jbb, 30 safemt, 35 "
        "domain_gen; 42 benigns: 24 hard-negative, 18 easy) and frozen by recording sha256 hashes of the "
        "resulting corpus files. From that point forward: **no iteration, threshold adjustment, or model "
        "change may be validated against the test split.** All tuning happens on dev (132 scenarios) and is "
        "diagnosed with *keyless* probes \u2014 pure Python re-computation of fusion over already-captured "
        "signals, at zero API cost \u2014 before any frozen-test execution is spent."
    )
    pdf.p(
        "**Operating points.** **FLAG** (max verdict \u2265 ALERT) and **BLOCK** (\u2265 CONTAIN, including judge "
        "DENY). Ground truth is scenario *provenance*, never the detector's own output. CI enforces no "
        "recall bands on this harness (anti-circularity); only false-positive invariants on easy benigns "
        "are gated automatically."
    )


def section3_phases(pdf: PaperPDF) -> None:
    pdf.h1("3", "Empirical Phases & Structural Discoveries")
    pdf.p(
        "Four phases, F0 through F3, form the empirical core of this study. Each phase is a single frozen-"
        "test execution preceded by dev-split diagnosis and a keyless, pre-registered prediction. Table 1 "
        "previews the full arc; the remainder of this section walks through it."
    )
    pdf.body("B", 10)
    pdf.set_text_color(*SLATE_900)
    pdf.cell(0, 7, "Table 1 \u2014 Frozen test set (147 scenarios: 105 attacks, 42 benign), all four phases.",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.table(
        ["Phase", "Judge config", "recall@FLAG", "recall@BLOCK", "FP@FLAG", "prec@FLAG", "Judge calls/DENY"],
        [
            ["F0", "none (l1_l2)", "11.4%", "11.4%", "2.4%", "92.3%", "\u2014"],
            ["F1", "gate >=55 (starved)", "11.4%", "11.4%", "2.4%", "92.3%", "0 / 0"],
            ["F2", "gate >=30 (amnesic)", "11.4%", "11.4%", "2.4%", "92.3%", "5 / 0"],
            ["F3", "gate >=30 + 3-turn window", "15.2%", "15.2%", "2.4%", "94.1%", "5 / 4"],
        ],
        col_w=[15, 50, 22, 23, 18, 20, 22],
        highlight_row=3,
        size=8.0,
        header_size=7.2,
    )
    pdf.p(
        "Three phases in a row (F0, F1, F2) produced *identical* aggregate metrics on the frozen test. "
        "Under a circular protocol this could be mistaken for stability; under this protocol it is the "
        "honest signature of a bottleneck that a naive metrics-only reading would miss \u2014 which is why each "
        "phase below reports the *mechanism*, not only the number."
    )

    pdf.h2("3.1", "Phase 0 & 1 \u2014 The Mathematical Ceiling and Gate Starvation")
    pdf.callout(
        "STRUCTURAL DISCOVERY \u2014 GHOST #3", RED,
        "The trajectory layer cannot block alone",
        [
            "RiskFusion.fuse reaches CONTAIN only via the deterministic l1_high floor (75) or a cumulative "
            "L2 score whose maximum possible weight (55) falls short of the CONTAIN band. This is a proven "
            "mathematical property, independent of test data: the pure-trajectory configuration can never "
            "reach BLOCK. The frozen-test run confirmed it more strongly than the proof requires: l2_only "
            "recall@BLOCK = 0.0%, and recall@FLAG was also 0.0% \u2014 the trajectory layer never raised even a "
            "WATCH-level alert on this test set.",
        ],
    )
    pdf.p(
        "The keyless `l1_l2` configuration performed identically to `l1_only` (11.4% recall@FLAG, 92.3% "
        "precision, 2.4% FP@FLAG): zero of the 105 attacks flagged by the combined stack were missed by "
        "regex alone. Per-source breakdown localized *why*: recall on `domain_gen` (in-domain, announced "
        "threat model) reached 31.4%, while `jbb` sat at 0.0% and `safemt` at 3.3%. This is the direct, "
        "quantitative answer to the circularity concern that motivated this harness: measured against a "
        "test set an author did not write, the keyless detector's true reach is roughly a tenth of what a "
        "self-authored benchmark would likely have reported."
    )
    pdf.callout(
        "STRUCTURAL DISCOVERY \u2014 GHOST #4", AMBER,
        "Gate starvation: the judge that could never be asked",
        [
            "Before spending any judge API calls, code inspection yielded a falsifiable prediction: "
            "should_invoke gates at risk_score >= 55, which already implies ALERT (>=45) \u2014 the judge could "
            "only ever see turns already flagged, and could upgrade ALERT to CONTAIN but never create a new "
            "FLAG. Combined with 100% of F0's first-flags carrying l1_high (bypassing the judge entirely), "
            "the touchable population was predicted to be small or empty.",
            "The live run confirmed the degenerate case: zero invocations across 147 scenarios (432 turns). "
            "A keyless probe found the maximum fusion score without l1_high was 35 on test and 45 on dev \u2014 "
            "never approaching the 55 gate. A live smoke call with a synthetic prompt confirmed the NIM path "
            "itself was healthy (DENY in 2.5s): the starvation was architectural, not infrastructural.",
        ],
    )

    pdf.h2("3.2", "Phase 2 \u2014 Single-Turn Amnesia")
    pdf.p(
        "A keyless dev diagnostic found: (a) a **dead risk factor** \u2014 `approaching_sensitive` requires "
        "proximity \u2265 0.62, but the maximum observed anywhere in dev was 0.574; (b) single-knob L2 "
        "sensitivity sweeps never reach 55 without `l1_high`, while spending false-positive budget; and "
        "(c) a gate-value sweep showing **30** as the first threshold exposing meaningful attack traffic \u2014 "
        "seven dev attack turns, **zero** benign turns."
    )
    pdf.p(
        "We changed exactly one constant (`DEFAULT_JUDGE_THRESHOLD`: 55 \u2192 30). On dev, the judge denied "
        "**3 of 7 (42.9%)** \u2014 all cases whose *individual turn text* contained an explicit sensitive ask. "
        "The four ALLOWs were the informative result: three were turn-zero probes (correctly permissive) "
        "and one was a mid-conversation salami turn whose isolated wording read as routine IT support."
    )
    pdf.callout(
        "FAILURE MODE \u2014 CONFIRMED ON TEST", PURPLE,
        "Single-turn amnesia",
        [
            "The frozen-test run of gate 30 (no context window) reproduced F0's aggregate numbers exactly, "
            "but for a new reason: 5 invocations, 0 denials. All five were domain_gen crescendo/salami "
            "attacks at turns 3\u20134, every one ALLOWed with a variant of: \u201cthe current message is a benign IT "
            "support question.\u201d A multi-turn attack engineered so each step reads as ordinary work is, "
            "definitionally, invisible to a judge that only ever sees one step \u2014 EscalationJudge._build_"
            "prompt passed only the current turn's text and numeric signals, with no conversational history.",
        ],
    )

    pdf.h2("3.3", "Phase 3 \u2014 Conversational Context")
    pdf.p(
        "The fix was deliberately minimal: `_build_prompt` gained an optional `history` parameter, windowed "
        "to the last three raw prior user turns (`JUDGE_CONTEXT_WINDOW = 3`). We chose raw turn text over "
        "an AI-generated summary specifically to avoid a second LLM call, added latency, and an unverified "
        "layer of interpretation between evidence and decision. History is sourced from the same "
        "ConversationState already backing L2 in production; the invocation gate itself was left untouched."
    )
    pdf.p(
        "**Dev validation (non-regression).** The three existing denials survived being re-judged with a "
        "longer prompt \u2014 **3 of 3 preserved** \u2014 with justifications visibly upgraded to explicitly "
        "trajectory-aware phrasing. The one addressable dev case, escalating ticket-record requests with no "
        "named sensitive target, remained ALLOWed \u2014 documented *before* touching the frozen test as the "
        "predicted boundary of a window that recognizes accumulation toward a named target but not pure "
        "request-volume growth."
    )
    pdf.p(
        "**Frozen-test result.** The single permitted execution produced the only recall movement in the "
        "entire research arc: recall@FLAG and recall@BLOCK rose from **11.4% to 15.2%** (+3.8pp), while "
        "precision rose from **92.3% to 94.1%** and false positives stayed flat at **2.4%** \u2014 every judge "
        "denial on the frozen test was a true attack."
    )
    pdf.body("B", 10)
    pdf.set_text_color(*SLATE_900)
    pdf.cell(0, 7, "Table 2 \u2014 Transfer of judge decisions from Phase 2 to Phase 3 (frozen test).",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    _decision_table(pdf)
    pdf.p(
        "The fifth case is discussed on its own terms in Section 4.1: it is not a residual instance of "
        "amnesia (the judge's own reasoning shows it *sees* the trajectory) but a distinct, previously "
        "predicted boundary."
    )


def _decision_table(pdf: PaperPDF) -> None:
    rows = [
        ("domain_gen_0001", "crescendo", "ALLOW", "benign IT support question", "DENY",
         "trajectory accumulates toward exfiltration despite benign appearance"),
        ("domain_gen_0015", "salami", "ALLOW", "benign \u2026 performance review", "DENY",
         "trajectory accumulates \u2026 despite looking routine"),
        ("domain_gen_0035", "crescendo", "ALLOW", "benign IT support question", "DENY",
         "trajectory accumulates toward credential/data exfiltration"),
        ("domain_gen_0041", "salami", "ALLOW", "benign directory export request", "DENY",
         "stepwise movement toward bulk export and credential collection"),
        ("domain_gen_0051", "salami", "ALLOW", "legitimate IT support question", "ALLOW",
         "stepwise progression toward bulk export, but still within legitimate bounds"),
    ]
    col_w = [30, 20, 15, 47, 15, 43]
    headers = ["Scenario", "Category", "F2", "F2 reason", "F3", "F3 reason"]
    if pdf.get_y() > 220:
        pdf.add_page()
    pdf.body("B", 7.6)
    pdf.set_fill_color(*SLATE_800)
    pdf.set_text_color(255, 255, 255)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, fill=True, align="C")
    pdf.ln()
    for r_i, (scen, cat, d1, r1, d2, r2) in enumerate(rows):
        if pdf.get_y() > 268:
            pdf.add_page()
            pdf.body("B", 7.6)
            pdf.set_fill_color(*SLATE_800)
            pdf.set_text_color(255, 255, 255)
            for i, h in enumerate(headers):
                pdf.cell(col_w[i], 7, h, fill=True, align="C")
            pdf.ln()
        y0 = pdf.get_y()
        x0 = pdf.get_x()
        row_h = 13.5
        fill = SLATE_50 if r_i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*fill)
        pdf.set_draw_color(*SLATE_200)
        pdf.rect(x0, y0, sum(col_w), row_h, "DF")

        pdf.set_xy(x0, y0 + 1.5)
        pdf.body("", 7.4)
        pdf.set_text_color(*SLATE_800)
        pdf.multi_cell(col_w[0], 10.5, scen, align="C")

        pdf.set_xy(x0 + col_w[0], y0 + 4.5)
        pdf.body("I", 7.4)
        pdf.set_text_color(*SLATE_600)
        pdf.multi_cell(col_w[1], 4.5, cat, align="C")

        pdf.set_xy(x0 + col_w[0] + col_w[1], y0 + 4.5)
        pdf.body("B", 8)
        pdf.set_text_color(*AMBER)
        pdf.multi_cell(col_w[2], 4.5, d1, align="C")

        pdf.set_xy(x0 + col_w[0] + col_w[1] + col_w[2], y0 + 1.5)
        pdf.body("", 6.8)
        pdf.set_text_color(*SLATE_600)
        pdf.multi_cell(col_w[3], 3.4, r1, align="L")

        xd2 = x0 + col_w[0] + col_w[1] + col_w[2] + col_w[3]
        pdf.set_xy(xd2, y0 + 4.5)
        pdf.body("B", 8)
        pdf.set_text_color(*RED if d2 == "DENY" else AMBER)
        pdf.multi_cell(col_w[4], 4.5, d2, align="C")

        xr2 = xd2 + col_w[4]
        pdf.set_xy(xr2, y0 + 1.5)
        pdf.body("", 6.8)
        pdf.set_text_color(*SLATE_600)
        pdf.multi_cell(col_w[5], 3.4, r2, align="L")

        pdf.set_xy(x0, y0 + row_h)
    pdf.ln(4)


def section4_discussion(pdf: PaperPDF) -> None:
    pdf.h1("4", "Failure Modes & Limitations (Discussion)")

    pdf.h2("4.1", "The volumetric-escalation boundary (domain_gen_0051)")
    pdf.p(
        "The one case Phase 3 did not recover is scientifically the most interesting result in this study, "
        "because it was **predicted on the development split before the frozen-test run that confirmed it.** "
        "The dev miss (`legpb_salami_export`) and the test miss (`domain_gen_0051`) share an identical "
        "structure: progressively larger *quantities* of an already-permitted resource class, with **no "
        "named credential, secret, or export target** appearing anywhere in the visible window. The judge's "
        "own justification \u2014 \u201cshows a stepwise progression toward bulk data export, but the current "
        "message is still within the bounds of a legitimate IT support request\u201d \u2014 shows it perceives the "
        "escalation and, under its ALLOW-biased instructions, still declines to deny it."
    )
    pdf.p(
        "This is a **calibrated boundary of an evidence-based judge, not a blind spot**: recovering it would "
        "require a new signal \u2014 volumetric or repetition-based, orthogonal to semantic proximity \u2014 rather "
        "than more judge context or a different gate. We report this as future work (Section 5) rather than "
        "attempt a same-session fix, consistent with the freeze protocol."
    )

    pdf.h2("4.2", "The out-of-domain generalization gap")
    pdf.p(
        "Across all four phases, `jbb` (40 generic jailbreak attacks) and `safemt` (30 generic multi-turn "
        "attacks) never moved: recall stayed at **0.0%** and **3.3%** respectively. Fusion scores on these "
        "sources never leave the CLEAR band, so **zero jbb/safemt turns ever reach the judge's gate, at any "
        "gate value tested.** No amount of judge improvement can act on traffic that never arrives. "
        "Eighty-nine of the 105 frozen-test attacks still produce no flag under any configuration measured "
        "here."
    )
    pdf.p(
        "This is the honest complement to the Phase 3 result: MTGuard's recovery of multi-turn attacks is "
        "real but **domain-bound** \u2014 a claim about defense-in-depth *within* an announced threat model, not "
        "a claim about general-purpose jailbreak robustness. Closing this gap is an L1/L2 coverage problem, "
        "categorically distinct from the judge-context question this study answers."
    )

    pdf.h2("4.3", "Other declared limitations")
    pdf.bullet(
        "**Embedding quality.** L2's `HashingVectorizer` (collision-based, no learned semantics) is fast "
        "but semantically shallow; it cannot recognize paraphrase the way a trained sentence embedding "
        "would. The dead `approaching_sensitive` factor is partly attributable to this."
    )
    pdf.bullet(
        "**Unmeasured benign false-denial rate.** No benign scenario has ever reached the judge's gate, "
        "in any phase or split \u2014 a consistent, four-times-replicated invariant, but one that leaves the "
        "judge's false-denial rate on legitimate traffic empirically unmeasured."
    )
    pdf.bullet(
        "**Parser bias.** `parse_judge_response` defaults to ALLOW on ambiguous output \u2014 a fail-*open* "
        "choice in tension with the pipeline's fail-*closed* posture on infrastructure errors. Never "
        "exercised in this study, but worth re-examining before deployment."
    )
    pdf.bullet(
        "**Dev-corpus composition.** Dev is dominated by self-authored and in-domain content; no "
        "generalization claim in this paper rests on dev-only numbers."
    )
    pdf.bullet(
        "**License-driven exclusion.** ScaleAI/MHJ (40 additional attacks) was imported, reviewed, and "
        "excluded rather than redacted into a corrupted metric."
    )


def section5_conclusion(pdf: PaperPDF) -> None:
    pdf.h1("5", "Conclusion & Future Work")
    pdf.p(
        "This study set out to answer, with evidence rather than assertion, the central methodological "
        "criticism carried over from RAGE: does this cascade actually generalize, and does adding an LLM "
        "judge help? Under a frozen, sha256-pinned, run-to-report protocol, the honest answer is layered. "
        "The keyless cascade is precise (92.3% precision) but narrowly domain-bound (11.4% recall, 0% on "
        "generic jailbreak content). Adding an LLM judge, on the first attempt, changed nothing \u2014 not "
        "because the judge reasons poorly, but because its own invocation gate made it mathematically "
        "unreachable (Ghost #4). Feeding the judge exposed a second, more interesting bottleneck: a judge "
        "with no memory of the conversation classifies the individual steps of a multi-turn attack exactly "
        "as they read \u2014 as routine work."
    )
    pdf.p(
        "Giving the judge a bounded, three-raw-turn window \u2014 the smallest change that could plausibly "
        "work, chosen explicitly over an AI-summarized alternative to preserve latency, cost, and evidence "
        "integrity \u2014 recovered four of five previously-missed attacks on a single frozen-test execution, "
        "with precision *rising* and false positives unchanged. The one case it did not recover was "
        "predicted before that execution ran, on the development split alone, and its later confirmation on "
        "frozen data is itself evidence that the diagnostic methodology, not merely the fix, is sound."
    )
    pdf.p(
        "The total empirical cost of this four-phase arc was four frozen-test executions and 24 cached "
        "judge decisions across both splits \u2014 effectively zero dollars at current NVIDIA NIM free-tier "
        "pricing. We regard the discipline of that cost as much a contribution as the recall number: every "
        "phase's fix was designed and validated entirely on dev, with a falsifiable, pre-registered "
        "prediction stated before the one test execution that could confirm or refute it."
    )

    pdf.h2("5.1", "Future work")
    pdf.bullet(
        "**Migrate the shared embedder from `HashingVectorizer` to `sentence-transformers`.** A learned, "
        "semantically dense embedding may revive the dead `approaching_sensitive` factor and narrow the "
        "out-of-domain gap by generalizing past `domain_gen`'s exact vocabulary. Must be re-tuned and "
        "re-frozen on dev before any test-set claim is made about it."
    )
    pdf.bullet(
        "**A volumetric or repetition-based L2 signal**, orthogonal to semantic proximity, to address the "
        "calibrated boundary identified in Section 4.1."
    )
    pdf.bullet(
        "**Upstream out-of-domain coverage** \u2014 broader L1 signatures and/or additional L2 sensitive "
        "regions informed by jbb/safemt failure analysis \u2014 as a research question distinct from, and "
        "prerequisite to, any further judge-context work."
    )
    pdf.bullet(
        "**A dedicated benign stress corpus** engineered to clear the judge's invocation gate, to finally "
        "measure the false-denial rate that four phases of this study left structurally unmeasured."
    )


def references_page(pdf: PaperPDF) -> None:
    pdf.h1("", "References")
    refs = [
        "M. Russinovich, A. Salem, and R. Eldan, \u201cGreat, Now Write an Article About That: The Crescendo "
        "Multi-Turn LLM Jailbreak Attack,\u201d arXiv:2404.01833, Microsoft, 2024.",
        "Mudette Research Team (predecessor project), \u201cRAGE: Robust Agentic Security Gateway for "
        "Text-to-SQL \u2014 Defending Against Multi-Turn Crescendo Attacks,\u201d Global South AI Safety "
        "Hackathon, June 2026.",
        "P. Chao, et al., \u201cJailbreakBench: An Open Robustness Benchmark for Jailbreaking Large Language "
        "Models,\u201d arXiv:2404.01318, 2024. (JailbreakBench/JBB-Behaviors, HF rev. 886acc3\u2026, MIT.)",
        "SafeMTData contributors, \u201cSafeMTData: A Multi-Turn Safety Evaluation Dataset,\u201d Hugging Face "
        "Hub. (SafeMTData/SafeMTData, HF rev. 04af7bd\u2026, MIT.)",
        "ScaleAI, \u201cMHJ: Multi-Turn Human Jailbreaks,\u201d Hugging Face Hub. (Reviewed and excluded on "
        "CC-BY-NC-4.0 license grounds; Section 2.3.)",
        "OWASP Foundation, \u201cOWASP Top 10 for Large Language Model Applications,\u201d v1.1, 2023.",
        "NVIDIA, \u201cNVIDIA NIM \u2014 API Catalog Documentation,\u201d integrate.api.nvidia.com/v1, "
        "build.nvidia.com.",
        "A. Anil, et al., \u201cMany-Shot Jailbreaking,\u201d Anthropic Technical Report, 2024.",
        "A. Zou, Z. Wang, J. Z. Kolter, and M. Fredrikson, \u201cUniversal and Transferable Adversarial "
        "Attacks on Aligned Language Models,\u201d arXiv:2307.15043, 2023.",
    ]
    pdf.body("", 9.3)
    for i, ref in enumerate(refs, start=1):
        x0 = pdf.get_x()
        pdf.set_text_color(*BLUE)
        pdf.body("B", 9.3)
        pdf.cell(8, 5.4, f"[{i}]")
        pdf.set_x(x0 + 8)
        w = pdf.w - pdf.r_margin - (x0 + 8)
        pdf.set_left_margin(x0 + 8)
        pdf.rich(ref, size=9.3, lh=5.0, color=SLATE_800)
        pdf.set_left_margin(MARGIN)
        pdf.set_x(x0)
        pdf.ln(1)

    pdf.ln(4)
    pdf.p(
        "Mudette source code and the complete evaluation harness correspond to the repository at commit "
        "`9d068b5` (Phase 13.2). Curated, verbatim evaluation artifacts for every phase cited in this paper "
        "(`report.md`, `metrics.json`, and phase-specific `CURATION.md` analysis) are committed under "
        "`docs/paper/`.",
        size=9.3,
    )

    pdf.ln(4)
    y0 = pdf.get_y()
    text = (
        "The Mudette codebase, its evaluation harness, and this paper were developed with AI "
        "pair-programming assistance (Claude, via the Cursor IDE) under a strict human-gated workflow: "
        "every code change and every execution against the frozen test set required an explicit, prior "
        "human approval, and no iteration against the frozen split was permitted at any point after "
        "freezing. All quantitative results reported in this paper are direct, unedited outputs of the "
        "evaluation harness (report.md / metrics.json per phase); no number in any table above was "
        "hand-edited or recomputed outside the harness. The human author reviewed and approved each "
        "phase's diagnostic plan before execution and each phase's curated findings before inclusion in "
        "this document."
    )
    box_h = 44
    if y0 + box_h > 280:
        pdf.add_page()
        y0 = pdf.get_y()
    pdf.set_fill_color(*SLATE_100)
    pdf.set_draw_color(*SLATE_200)
    pdf.rect(MARGIN, y0, CONTENT_W, box_h, "DF")
    pdf.set_xy(MARGIN + 6, y0 + 4)
    pdf.body("B", 8.5)
    pdf.set_text_color(*SLATE_500)
    pdf.cell(0, 5, "LLM USAGE STATEMENT", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(MARGIN + 6)
    pdf.set_left_margin(MARGIN + 6)
    pdf.body("I", 8.6)
    pdf.set_text_color(*SLATE_600)
    pdf.multi_cell(CONTENT_W - 12, 4.4, text)
    pdf.set_left_margin(MARGIN)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf = PaperPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)

    cover_page(pdf)
    abstract_page(pdf)
    section1_introduction(pdf)
    section2_architecture(pdf)
    section3_phases(pdf)
    section4_discussion(pdf)
    section5_conclusion(pdf)
    references_page(pdf)

    pdf.output(str(OUT))
    print(f"Wrote {OUT} ({pdf.page_no()} pages)")


if __name__ == "__main__":
    main()
