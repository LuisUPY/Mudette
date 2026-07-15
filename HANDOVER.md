# 📋 Traspaso de Proyecto — Mudette (MTGuard)

> **Documento de handover para continuar en un chat nuevo.**
> Generado: 2026-07-15 · Último commit: `fa3eb62` (Phase 9.1) · Branch: `main` (solo local, **sin remote**)
> Working tree: limpio · Tests: **145 verdes** (`uv run pytest`, sin API keys)

---

## 1. Objetivo del Proyecto

**Mudette** es una demo de investigación de **defensa multi-turno contra prompt injection** (motor: **MTGuard**) que protege a un agente empresarial ficticio: *Nexa Copilot* (soporte IT de NexaCorp). Pipeline en capas: `L1 RegexGuard → L2 TrajectoryGuard → RiskFusion → [EscalationJudge opcional] → UserGate → NexaAgent (RAG FAISS + LLM NVIDIA NIM)`.

**Contexto estratégico (la misión real):** Mudette es la evolución de **RAGE**, un prototipo presentado al *Global South AI Safety Hackathon 2026* (Apart Research) que no ganó. Los 4 reviewers dejaron feedback letal, y **todo el trabajo actual es responder a ese feedback con evidencia**. Las críticas centrales:

1. **R2#1**: la capa de trayectoria (la contribución novedosa) no aporta peso medible — *"the thing you are selling and the thing you are measuring are not the same thing"*. La ablación de RAGE mostró que L2+multi-turn añadía solo +2.8pp sobre regex.
2. **R2#2**: *"the gateway is doing the work, and L3 is riding along"* — el drift no se comporta como asume el método.
3. **R2#3**: evaluación **circular** — CI exigía recall ∈ [75%,85%], banda auto-elegida.
4. **R1/R2#4**: TF-IDF/HashingVectorizer es base débil para drift "semántico"; corpus delgado (36 ataques).
5. **R3**: falta ablación L1+L2 vs L1+L2+MT; presentación confusa.

**Hallazgo propio (Fantasma #3, medido):** en [fusion.py](src/mtguard/layers/fusion.py), las señales puras de L2 suman máximo 20+15+10+10 = **55** y CONTAIN requiere ≥75 → **la trayectoria sola no puede bloquear nada, matemáticamente**. Solo L1 HIGH (floor 75 + CONTAIN forzado) o judge DENY contienen. Y el juez solo se invoca con risk≥55 → sin L1, exige que las 4 señales L2 disparen a la vez.

**Roadmap acordado:** Paso 1 ✅ (timeouts/streaming) → Paso 2 ✅ (hotfix + higiene + commits) → **Paso 3 🔄 (harness de evaluación no circular — 3.1 hecho, 3.2–3.5 pendientes)** → Paso 4 (embeddings transformer) → Paso 5 (rebalanceo fusion, fusionado dentro de 3.4) → Paso 6 (decidir retorno a Text-to-SQL con gateway determinista).

---

## 2. Stack Tecnológico

| Componente | Versión / Detalle |
|---|---|
| Python | ≥3.11 (venv actual: 3.14.6) |
| Gestor | **uv** (lockfile `uv.lock`; correr todo con `uv run …`) |
| `openai` | ≥1.40 — cliente para **NVIDIA NIM** vía `base_url=https://integrate.api.nvidia.com/v1` |
| `gradio` | ≥4.44 (instalado: **6.19.0** — ojo: `gr.Chatbot` NO acepta `type=` en esta versión) |
| `faiss-cpu` | índice RAG del pack |
| `scikit-learn` | `HashingVectorizer` 2048-d (embedder de L2 **y** RAG — debilidad conocida, Paso 4) |
| `pytest` | 145 tests, **todos keyless** (conftest mockea NIM) |
| `fpdf2` | dev group — genera el glosario PDF |
| `datasets` | ≥2.19, **grupo opcional `eval-import`** (aún no instalado; para 3.2) |

**Modelos NIM** ([nim.py](src/mtguard/nim.py)): agente `meta/llama-3.1-8b-instruct` (default rápido; 70b vía env `MUDETTE_MAIN_MODEL`), juez `meta/llama-3.1-8b-instruct`. Timeouts: agente 60s/1 retry, juez 20s/0 retries. Keys: `MAIN_API_KEY` y `JUDGE_API_KEY` (formato `nvapi-…`, de build.nvidia.com).

**Entrypoints**: `Mudette-demo` (Gradio :7860), `Mudette-scenario` (CLI playbooks), `Mudette-eval` (harness, nuevo).

---

## 3. Estructura del Proyecto

```
Mudette-F/
├── pyproject.toml / uv.lock / README.md / QUICKSTART.md
├── HANDOVER.md                     # este documento
├── mudette_context.md              # mapa maestro del código (actualizado Phase 8)
├── Feedback-RAGEproyect.pdf        # feedback jueces RAGE (trackeado como registro)
├── GlobalSouth-RAGE-Submission-2.pdf  # paper RAGE original (trackeado)
├── corpus/
│   ├── attacks.json (32) · benign.json (42)     # legacy single-turn
│   └── eval/                       # NUEVO — corpus del harness
│       ├── attacks_dev.json (35) · benign_dev.json (44)
│       └── manifest.json           # protocolo anti-circularidad; test_freeze: null
├── demo_pack/nexa_copilot/         # pack multi-tenant (único implementado)
│   ├── agent_profile.json          # regiones L2: credentials, system_internals, bulk_pii, policy_bypass
│   ├── system_prompt.txt · judge_prompt.txt · secrets_vault.json
│   ├── attack_playbook.json (3 esc.) · benign_playbook.json (2 esc.)
│   └── kb/ (FAISS) · kb_src/ (4 markdown)
├── docs/Mudette-Command-Glossary.pdf
├── reports/                        # GITIGNORED — salidas del harness
├── scripts/
│   ├── run-demo.sh · run-tests.sh · run-eval.sh (nuevo)
│   ├── run-benchmarks{,-no-judge,-with-judge}.sh · run-scenario.sh · run-benign-check.sh
│   ├── import_external_eval.py     # NUEVO — adaptadores JBB/MHJ/SafeMT (sin correr aún)
│   ├── build_kb.py · generate_command_glossary.py · generate-glossary-pdf.sh
│   └── lib/common.sh
├── src/mtguard/
│   ├── nim.py · models.py · embedder.py · rag.py · trace.py · rules.json (20 reglas L1)
│   ├── agent.py                    # NexaAgent + MTGuardSession (turn / turn_stream)
│   ├── judge.py · pack_loader.py · pipeline.py
│   ├── layers/ l1_regex.py · l2_trajectory.py · fusion.py
│   ├── gates/user_gate.py
│   ├── eval/                       # NUEVO Phase 9.1 — harness completo
│   │   ├── dataset.py · capture.py · configs.py · metrics.py · report.py · runner.py
│   └── demo/ app.py (Gradio) · scenario.py (CLI)
└── tests/  (145 tests)
    ├── conftest.py                 # mocks NIM autouse + captura método original
    ├── test_streaming.py (18) · test_eval.py (14)
    └── test_{l1,l2,fusion,pipeline,agent,rag,pack_loader,user_gate}.py
```

---

## 4. Progreso Actual (todo funcionando y commiteado)

| Commit | Contenido |
|---|---|
| `841d40f` **Phase 8** | Migración NIM completa, sin modo offline, timeouts explícitos, clientes cacheados, **streaming end-to-end** (`respond_stream`/`turn_stream`/handlers generadores Gradio + `queue(default_concurrency_limit=4)`), fix chunk `choices=[]`, dedup de errores |
| `809718c` **Phase 8.1** | Glosario alineado a NIM (9 correcciones), PDF regenerado |
| `d9b9678` **Phase 8.2** | PDFs de investigación RAGE archivados en el repo |
| `fa3eb62` **Phase 9.1** | **Harness de evaluación no circular** + corpus migrado + importadores externos listos |

**Bugs resueltos y verificados por el usuario con key real:** el `IndexError: list index out of range` post-respuesta (chunk final NIM con `choices=[]`) y la duplicación del mensaje de usuario en el error handler.

**🔥 Primer baseline del harness (dev, 79 escenarios, keyless):**

| Config | recall@FLAG | recall@BLOCK | FP |
|---|---|---|---|
| `l1_only` (regex) | 80.0% | 80.0% | 0% |
| `l2_only` (trayectoria) | **0.0%** | **0.0%** | 0% |
| `l1_l2` | 82.9% (**+2.9pp**) | 80.0% (**+0.0pp**) | 0% |

Reproduce casi exactamente la crítica a RAGE (+2.8pp). Matiz: el corpus dev es ~91% single-turn y self-authored — los externos multi-turn de 3.2 darán la lectura definitiva.

---

## 5. Código Clave

### 5.1 El corazón del Fantasma #3 — [fusion.py](src/mtguard/layers/fusion.py)
```python
_WEIGHTS = {
    "l1_high": 45, "l1_medium": 25,
    "approaching_sensitive": 20, "escalation": 15,
    "trajectory_high": 10, "proximity_high": 10,   # L2 puro: máx 55
}
_L1_HIGH_FLOOR = 75
# Bandas: <25 CLEAR, <45 WATCH, <75 ALERT, >=75 CONTAIN
# l1_high → verdict = CONTAIN forzado; safe_score>=0.55 puede degradar CONTAIN→ALERT
```
Judge ([judge.py](src/mtguard/judge.py)): `should_invoke` = `risk>=55 AND verdict in (WATCH, ALERT) AND not CONTAIN`. DENY → `apply_judge_deny` → CONTAIN. **Fail-closed** en timeout (re-lanza `RuntimeError`).

### 5.2 Streaming con guard del chunk final — [agent.py](src/mtguard/agent.py)
```python
def _stream_main_llm(self, user_content: str) -> Iterator[str]:
    with self._client.chat.completions.create(..., stream=True) as stream:
        for chunk in stream:
            if not chunk.choices:   # NIM/vLLM emite chunk final de usage con choices=[]
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

def turn_stream(self, message, judge_override=None) -> Iterator[tuple[str, object]]:
    """Yields ("trace", dict) → ("delta", acumulado)* → ("done", AgentTurn).
    Guard phase (L1/L2/Fusion/Judge) es local y rápida; trace se emite ANTES del LLM."""
```
`respond_stream` aplica `_scrub_secrets` al **texto acumulado** en cada delta (un secreto partido entre 2 chunks se redacta igual).

### 5.3 Dedup de errores en Gradio — [app.py](src/mtguard/demo/app.py)
```python
def _apply_stream_error(app, message, error, turn_appended):
    """Si el turno ya está en el historial (trace emitido), reemplaza el placeholder
    del asistente con el error en vez de re-añadir el mensaje del usuario."""
    if app and turn_appended and app.history:
        app.history[-1]["content"] = f"**Error API:** {error}"
        return app, app.history, f"**Error:** {error}", "", app.last_trace
    return _api_error_response(app, message, error)
```

### 5.4 Harness: replays de ablación — [eval/configs.py](src/mtguard/eval/configs.py)
```python
def replay_l1_only(sig):  return _replay(sig, "l1_only", lambda f, t: f.fuse(t.l1, L2Result()))
def replay_l2_only(sig):  return _replay(sig, "l2_only", lambda f, t: f.fuse(L1Result(hit=False), t.l2))
def replay_l1_l2(sig):    return _replay(sig, "l1_l2",   lambda f, t: f.fuse(t.l1, t.l2))
# replay_l1_l2_judge: fusion + judge live en should_invoke, con JudgeCache
# (sha256 del prompt → decision) persistido en reports/eval/judge_cache.json
```
**Validez del diseño 2 fases:** `TrajectoryGuard.evaluate` muta `ConversationState` sin leer fusion/judge/gate → capturar señales una vez ([eval/capture.py](src/mtguard/eval/capture.py)) y reproducir N configs offline es correcto.

### 5.5 El techo matemático como test ejecutable — [test_eval.py](tests/test_eval.py)
```python
def test_l2_only_mathematical_ceiling_is_alert(self):
    """Documents Fantasma #3 as executable fact: pure trajectory maxes at
    risk 55 = ALERT under current weights — it can NEVER produce CONTAIN."""
    maxed_l2 = L2Result(safe_score=0.0, max_proximity=0.99,
                        approaching_sensitive=True, trajectory_risk=0.99,
                        escalation_pattern=True)
    fusion = RiskFusion().fuse(L1Result(hit=False), maxed_l2)
    assert fusion.risk_score == 55 and fusion.verdict == Verdict.ALERT
```

### 5.6 Métricas — dos puntos de operación ([eval/metrics.py](src/mtguard/eval/metrics.py))
`FLAG` = veredicto máximo del escenario ≥ ALERT · `BLOCK` = ≥ CONTAIN (judge DENY ya sube a CONTAIN upstream). Se reporta: recall/FP/precision en ambos puntos, atribución de factores en el primer FLAG (`FusionResult.factors`), desglose por categoría/fuente, mediana del turno de primera detección, y "ataques FLAGgeados por L1+L2 que L1 solo NO detectó".

### 5.7 Mocks de test — [conftest.py](tests/conftest.py)
```python
_ORIGINAL_STREAM_MAIN_LLM = NexaAgent._stream_main_llm  # capturado pre-mock (import time)
# fixture autouse: mockea _call_main_llm, _stream_main_llm (2 chunks), judge._call_llm ("ALLOW")
# fixture original_stream_main_llm: método real para tests de parseo de chunks
```

---

## 6. Problemas Actuales / Bugs

**No hay bugs abiertos.** Deudas y fricciones conocidas, por orden de relevancia:

1. **`import_external_eval.py` nunca se ha ejecutado contra los schemas reales de HF** — `_extract_turns` es defensivo multi-schema, pero es EL punto de fricción esperado en 3.2. MHJ (`ScaleAI/mhj`) probablemente esté *gated*: requiere aceptar licencia en la web de HF + `HF_TOKEN` de solo-lectura del usuario.
2. **`--assemble-test` solo fusiona ataques** (`external_*.json`) → `benign_test.json` debe crearse manualmente con la Fuente D (benignos duros) durante 3.2.
3. Licencias MHJ/SafeMT: placeholder `verify-on-HF-card` — decidir texto vs `--hash-only` por fuente al importar.
4. **Embedder = HashingVectorizer 2048-d** en L2 **y** RAG — la debilidad señalada por 2 reviewers. Es el **Paso 4** (sentence-transformers detrás de la interfaz `Embedder`), y el harness es el instrumento para medir si el cambio mejora algo.
5. La config `l1_l2_judge` del harness nunca ha corrido con API real (solo mockeada en tests).
6. Menor: `handle_chat` sin sesión retorna silencioso; sin remote git configurado (intencional).

---

## 7. Próximos Pasos (To-Do exacto)

**Sesión siguiente = Paso 3.2 → 3.5** (presupuesto estimado 85–100k tokens; el usuario está en plan Pro, gestionar economía de tokens):

```bash
# 3.2a — instalar extra e importar externos (fricción esperada: schemas/gating)
uv sync --extra eval-import
uv run python scripts/import_external_eval.py --source jbb --take 40 --accept-license
uv run python scripts/import_external_eval.py --source mhj --take 40 --accept-license    # gated → pedir HF_TOKEN al usuario
uv run python scripts/import_external_eval.py --source safemt --take 30 --accept-license
```
- **3.2b — Fuente C (~30 ataques de dominio):** generados por LLM en rol atacante que ve SOLO la descripción pública del agente + objetivo del ataque (nunca `rules.json`, perfiles ni umbrales). Archivar prompt de generación. Mitad a dev, mitad a test.
- **3.2c — Fuente D (~30 benignos duros):** vocabulario admin legítimo, topic-shifts abruptos, curiosidad de seguridad → `benign_test.json` (+ mitad a dev). Es la defensa contra el FP fácil (el fallo de RAGE: δ=0.83 en un "product breakdown" benigno).
- **3.2d — Congelar:** `uv run python scripts/import_external_eval.py --assemble-test --freeze` (sha256 + fecha al manifest; después de esto, PROHIBIDO iterar contra test).
- **3.3 — Baseline F0 en test congelado:** `./scripts/run-eval.sh test` → curar `report.md` (es material directo para el futuro paper).
- **3.4 — Variantes de fusión** (crear `src/mtguard/eval/variants.py`): F1 (escalación multi-turn eleva a ALERT fiable), F2 (judge desde risk≥45), F3 (L2 sostenida puede CONTAIN — **solo como experimento de falsación**, ver Reglas). Selección en dev: max `recall@FLAG` sujeto a `FP@FLAG` bajo en benignos duros; la ganadora corre UNA vez en test.
- **3.5 —** CI sin bandas de recall, README de evaluación, actualizar `mudette_context.md`, commit(s) `Phase 9.2/9.3`.
- **Después:** Paso 4 (embeddings transformer + recalibración medida con el harness) → push a GitHub cuando el usuario dé la orden (remote intencionado: `https://github.com/LuisUPY/Mudette-RAGE.git`).

---

## 8. Reglas del Proyecto (acordadas en este chat)

### Flujo de trabajo
1. **Patrón de compuerta:** presentar plan detallado → esperar "luz verde" explícita del usuario → ejecutar completo sin re-preguntar (salvo decisión de producto genuina).
2. **Commits:** estilo `Phase N[.n]: descripción` en inglés, cuerpo con bullets, terminan con `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. **Solo locales** — no configurar remote ni push hasta orden del usuario.
3. **Comunicación con el usuario en español**; código, comentarios y commits en inglés.
4. **Economía de tokens:** el usuario monitorea su límite de sesión (plan Pro). Trabajar en lotes, sin re-lecturas innecesarias, fraccionar fases pesadas entre sesiones.

### Arquitectura y código
5. **Nunca reintroducir modo offline ni fallbacks silenciosos** — los errores de API se propagan y se muestran; fue deuda eliminada deliberadamente.
6. **Juez fail-closed** en timeout/conexión. Clientes OpenAI **cacheados** con timeout/retries explícitos de `nim.py`.
7. **Scrubbing de secretos siempre sobre el texto acumulado** del stream, nunca sobre deltas sueltos.
8. `uv run pytest` debe pasar **sin API keys** (conftest mockea NIM, incluido streaming). Todo cambio nuevo trae tests de regresión.
9. `MTGuardSession.turn()` (no-streaming) no cambia de contrato — lo usan CLI y tests.

### Protocolo de evaluación (el corazón del Paso 3 — NO violar)
10. **Ground truth = procedencia del escenario**, jamás la salida del detector. Sin `expect_min_verdict` en el harness.
11. **Todo caso self-authored vive en dev**; el test lo dominan fuentes externas. Test se congela con sha256 — después, solo run-to-report.
12. **CI sin bandas de recall** (la banda [75,85] de RAGE fue el corazón de la crítica de circularidad). Solo invariantes de FP en benignos fáciles.
13. **Dos puntos de operación siempre juntos:** FLAG (≥ALERT) y BLOCK (≥CONTAIN). La distancia entre ambos ES la medida del Fantasma #3.
14. **Postura de fusión decidida por el usuario: PRECISIÓN** — L2 escala (FLAG), el bloqueo lo hacen regex y juez. F3 (L2 puede CONTAIN) se corre solo como **falsación** con hipótesis nula de no-adopción; solo reconsultar al usuario si F3 mejorara recall@BLOCK sin coste de FP.
15. **Harness keyless por defecto**; la config con juez es opt-in (`--judge`, `JUDGE_API_KEY`) con caché persistente de decisiones.

### Decisiones de producto del usuario (vigentes)
16. Los 2 PDFs de RAGE quedan **trackeados** como registros de investigación. Ojo al hacer público el repo: `Feedback-RAGEproyect.pdf` contiene el email personal del usuario.
17. **El reporte formal del modelo de protección de Mudette NO se produce todavía** (está por definirse).
18. Datasets externos: estrategia "**descargar e integrar ahora**" (aprobada), con pin de revisión HF en el manifest.
