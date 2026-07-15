# Mudette — Contexto Maestro de Ingeniería (Codebase Map)

> **Generado para migración de planificación/arquitectura hacia Claude 5 Sonnet.**  
> **Fuente de verdad:** estado del workspace en disco al momento de generación.  
> **Actualización Phase 8 (2026-07-14):** el refactor NVIDIA NIM + timeouts explícitos + streaming Gradio quedó **commiteado en `main`**. Las secciones 5.5–5.8 y 6.3 reflejan el estado post-Phase 8; las referencias históricas a `a0f5d78` se conservan como contexto de lo eliminado.

---

## 1. Resumen Ejecutivo y Propósito del Sistema

### Qué es Mudette

**Mudette** es una demo de investigación de **defensa multi-turno contra prompt injection** que protege un agente empresarial ficticio: **Nexa Copilot** (soporte IT de NexaCorp). El motor de defensa se llama **MTGuard**.

| Dimensión | Descripción |
|-----------|-------------|
| **Seguridad LLM** | Pipeline en capas (regex + trayectoria vectorial + fusión de riesgo + compuerta + juez opcional) que detecta jailbreak, crescendo y salami slicing **antes** de permitir respuesta del LLM. |
| **Multi-turn** | `ConversationState` en L2 persiste embeddings, historial de proximidad, drift y EWMA entre turnos. |
| **Multi-tenant (pack-driven)** | Cada tenant es un `demo_pack/` con `agent_profile.json`, `secrets_vault.json`, KB FAISS, playbooks y prompts. El motor `mtguard` es agnóstico al pack; hoy solo existe `demo_pack/nexa_copilot/`. |
| **Agente** | `NexaAgent` responde vía **RAG (FAISS)** + **LLM** cuando `UserGate` permite (`allow_llm=True`). |
| **Demo** | Gradio (`:7860`), CLI de escenarios (`Mudette-scenario`), scripts shell documentados. |

### Pipeline fijo (orden inmutable)

```
user_message
  → L1 RegexGuard
  → L2 TrajectoryGuard
  → RiskFusion
  → [opcional] EscalationJudge (si risk≥55 y verdict WATCH|ALERT)
  → UserGate
  → [si allow_llm] NexaAgent (RAG + NVIDIA NIM LLM)
```

### Estado actual y objetivo de refactorización

| Aspecto | Commit `a0f5d78` (remoto/local HEAD) | Working tree (disco actual) |
|---------|--------------------------------------|-----------------------------|
| LLM backend | OpenAI API directa (`gpt-4o` / `gpt-4o-mini`) | **NVIDIA NIM** (`integrate.api.nvidia.com/v1`) |
| Modo offline | Activo si no hay API key; respuestas RAG hardcodeadas | **Eliminado** — API key obligatoria |
| Secretos | Tupla global `_SECRET_PATTERNS` | **Dinámico** desde `secrets_vault.json` del pack |
| Errores API | `try/except` redirige a offline | Excepciones **propagan** (sin fallback) |
| Tests | Sin `conftest` mock global | `tests/conftest.py` mockea NIM |

**Deuda operativa — RESUELTA en Phase 8:**

- ✅ Timeouts NIM explícitos: agente 60s (connect 10s, 1 retry), juez 20s (0 retries) — `nim.py`
- ✅ Modelo demo rápido: default `llama-3.1-8b-instruct`; 70b opt-in vía `MUDETTE_MAIN_MODEL`
- ✅ Streaming Gradio: `turn_stream` emite trace inmediato + deltas; cola `default_concurrency_limit=4`
- ✅ Fix chunk final NIM (`choices=[]` → IndexError) y deduplicación de mensaje en error handler
- ✅ Commit del refactor + artefacto `https:/` eliminado
- ✅ `generate_command_glossary.py` alineado con NIM

**Nota de nomenclatura:** No existe `agents.py`. El módulo del agente es **`src/mtguard/agent.py`**.

---

## 2. Topología del Repositorio

```
Mudette-F/
├── mudette_context.md          # Este documento (mapa maestro)
├── pyproject.toml              # Proyecto Python, entrypoints Mudette-demo / Mudette-scenario
├── uv.lock                     # Lockfile de dependencias (uv)
├── README.md                   # Documentación principal
├── QUICKSTART.md               # Guía rápida (parcialmente actualizada a NIM en working tree)
├── .gitignore
│
├── corpus/                     # Corpus de evaluación offline de capas L1/L2/Fusion
│   ├── benign.json             # Mensajes benignos (no deben producir CONTAIN)
│   └── attacks.json            # Mensajes de ataque con hits L1 esperados
│
├── demo_pack/                  # Packs multi-tenant (un pack = un agente demo)
│   └── nexa_copilot/           # Pack NexaCorp IT — único pack implementado
│       ├── agent_profile.json  # Regiones sensibles L2, ejemplos de intención benigna
│       ├── system_prompt.txt   # System prompt del LLM Nexa Copilot
│       ├── secrets_vault.json  # Secretos simulados (scrub + reglas L1)
│       ├── judge_prompt.txt    # Instrucciones del EscalationJudge
│       ├── attack_playbook.json# Escenarios red team (crescendo, salami, jailbreak)
│       ├── benign_playbook.json# Escenarios usuario benigno
│       ├── kb/                 # Índice FAISS preconstruido
│       │   ├── index.faiss
│       │   ├── chunks.json
│       │   └── manifest.json
│       └── kb_src/             # Fuentes Markdown para regenerar KB
│           ├── vpn_troubleshooting.md
│           ├── ticket_management.md
│           ├── mdm_enrollment.md
│           └── it_policies.md
│
├── scripts/                    # Automatización documentada
│   ├── lib/common.sh           # uv_run, require_env
│   ├── setup.sh                # uv sync
│   ├── run-demo.sh             # Lanza Gradio :7860
│   ├── run-tests.sh            # pytest (NIM mockeado)
│   ├── run-benchmarks-no-judge.sh   # Escenarios ataque, requiere MAIN_API_KEY
│   ├── run-benchmarks-with-judge.sh # + JUDGE_API_KEY
│   ├── run-benchmarks.sh         # Alias no-judge
│   ├── run-scenario.sh         # Un escenario por ID
│   ├── run-benign-check.sh     # Corpus benigno
│   ├── build_kb.py             # Regenera FAISS desde kb_src/
│   ├── build-kb.sh
│   ├── generate_command_glossary.py  # PDF de comandos (⚠ aún menciona offline/OpenAI)
│   └── generate-glossary-pdf.sh
│
├── docs/                       # PDF generado (glosario de comandos)
│
├── src/mtguard/                # Motor MTGuard + agente + demo
│   ├── __init__.py             # __version__ = "0.1.0"
│   ├── nim.py                  # Constantes NVIDIA NIM (NUEVO, sin commit)
│   ├── agent.py                # NexaAgent + MTGuardSession
│   ├── judge.py                # EscalationJudge
│   ├── pack_loader.py          # DemoPack, playbooks, compile_secret_patterns
│   ├── pipeline.py             # MTGuardPipeline.process_turn
│   ├── models.py               # Dataclasses y enums compartidos
│   ├── embedder.py             # HashingVectorizer 2048-d (L2 + RAG)
│   ├── rag.py                  # KnowledgeBase FAISS
│   ├── trace.py                # Serialización TurnTrace + formateo UI
│   ├── rules.json              # 20 reglas L1 RegexGuard
│   ├── layers/
│   │   ├── l1_regex.py         # RegexGuard
│   │   ├── l2_trajectory.py    # TrajectoryGuard + ConversationState
│   │   └── fusion.py           # RiskFusion
│   ├── gates/
│   │   └── user_gate.py        # UserGate
│   └── demo/
│       ├── app.py              # Gradio UI
│       └── scenario.py         # CLI Mudette-scenario
│
└── tests/                      # 113 tests (working tree, con conftest mock)
    ├── conftest.py             # Mock _call_main_llm / _call_llm (NUEVO)
    ├── test_l1.py
    ├── test_l2.py
    ├── test_fusion.py
    ├── test_pipeline.py
    ├── test_agent.py
    ├── test_rag.py
    ├── test_pack_loader.py
    └── test_user_gate.py
```

**Omisiones intencionales:** `.venv/`, `__pycache__/`, `.pytest_cache/`, `.git/`, artefacto basura `https:/` (sin trackear).

---

## 3. Firmas de Código e Interfaces Técnicas

### 3.1 `src/mtguard/nim.py` (estado actual)

```python
NIM_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
DEFAULT_MAIN_MODEL: str = "meta/llama-3.3-70b-instruct"
DEFAULT_JUDGE_MODEL: str = "meta/llama-3.1-8b-instruct"
```

### 3.2 `src/mtguard/models.py`

```python
class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Verdict(str, Enum):
    CLEAR = "CLEAR"
    WATCH = "WATCH"
    ALERT = "ALERT"
    CONTAIN = "CONTAIN"

@dataclass
class L1Result:
    hit: bool
    rule_id: str | None = None
    severity: Severity | None = None
    matched_text: str | None = None

@dataclass
class L2Result:
    safe_score: float = 0.0
    proximity: dict[str, float] = field(default_factory=dict)
    max_proximity: float = 0.0
    max_region: str | None = None
    drift_step: float = 0.0
    drift_baseline: float = 0.0
    approaching_sensitive: bool = False
    trajectory_risk: float = 0.0
    escalation_pattern: bool = False
    turn_index: int = 0

@dataclass
class FusionResult:
    risk_score: int = 0
    verdict: Verdict = Verdict.CLEAR
    factors: list[str] = field(default_factory=list)

@dataclass
class JudgeResult:
    enabled: bool = False
    invoked: bool = False
    decision: str | None = None  # ALLOW | DENY
    reason: str | None = None

@dataclass
class GateResult:
    allow_llm: bool = True
    show_banner: bool = False
    block_reason: str | None = None

@dataclass
class TurnTrace:
    turn_index: int
    user_message: str
    l1: dict[str, Any]
    l2: dict[str, Any] | None = None
    fusion: dict[str, Any] | None = None
    judge: dict[str, Any] | None = None
    gate: dict[str, Any] | None = None
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]: ...
```

### 3.3 `src/mtguard/agent.py` (estado actual — **no** `agents.py`)

```python
@dataclass
class AgentTurn:
    trace: TurnTrace
    response: str
    fusion: FusionResult
    gate: GateResult

def _require_main_api_key(api_key: str | None) -> str: ...

@dataclass
class NexaAgent:
    pack: DemoPack
    kb: KnowledgeBase
    main_api_key: str
    main_model: str = DEFAULT_MAIN_MODEL
    system_prompt: str = field(init=False)
    secret_patterns: list[re.Pattern[str]] = field(init=False, repr=False)

    def __post_init__(self) -> None: ...
    @classmethod
    def from_pack(
        cls,
        pack: DemoPack,
        embedder: Embedder | None = None,
        main_api_key: str | None = None,
        main_model: str = DEFAULT_MAIN_MODEL,
    ) -> NexaAgent: ...
    def respond(
        self,
        message: str,
        gate: GateResult,
        fusion: FusionResult | None = None,
    ) -> str: ...
    def _block_message(self) -> str: ...
    def _compose_online(self, message: str) -> str: ...
    def _call_main_llm(self, user_content: str) -> str: ...
    def _scrub_secrets(self, text: str) -> str: ...

class MTGuardSession:
    def __init__(
        self,
        pack: DemoPack,
        embedder: Embedder | None = None,
        pipeline: MTGuardPipeline | None = None,
        agent: NexaAgent | None = None,
        judge: EscalationJudge | None = None,
        main_api_key: str | None = None,
        judge_api_key: str | None = None,
        judge_enabled: bool = False,
        main_model: str = DEFAULT_MAIN_MODEL,
        judge_model: str = DEFAULT_JUDGE_MODEL,
    ) -> None: ...
    @classmethod
    def from_pack_dir(
        cls,
        pack_dir: Path | str,
        main_api_key: str | None = None,
        judge_api_key: str | None = None,
        judge_enabled: bool = False,
        main_model: str = DEFAULT_MAIN_MODEL,
        judge_model: str = DEFAULT_JUDGE_MODEL,
    ) -> MTGuardSession: ...
    def _build_pipeline(self) -> MTGuardPipeline: ...
    def reset(self) -> None: ...
    def turn(self, message: str, judge_override: JudgeResult | None = None) -> AgentTurn: ...
```

### 3.4 `src/mtguard/judge.py`

```python
DEFAULT_JUDGE_THRESHOLD: int = 55

@dataclass
class EscalationJudge:
    pack: DemoPack
    api_key: str
    model: str = DEFAULT_JUDGE_MODEL
    threshold: int = DEFAULT_JUDGE_THRESHOLD
    enabled: bool = True

    def __post_init__(self) -> None: ...
    def should_invoke(self, fusion: FusionResult) -> bool: ...
    def evaluate(
        self,
        message: str,
        l1: L1Result,
        l2: L2Result,
        fusion: FusionResult,
    ) -> JudgeResult: ...
    def _build_prompt(
        self, message: str, l1: L1Result, l2: L2Result, fusion: FusionResult
    ) -> str: ...
    def _call_llm(self, user_prompt: str) -> str: ...

def parse_judge_response(text: str) -> tuple[str, str]: ...
```

### 3.5 `src/mtguard/pack_loader.py`

```python
REQUIRED_FILES: tuple[str, ...]  # agent_profile, system_prompt, secrets_vault, judge_prompt, playbooks
REQUIRED_KB_FILES: tuple[str, ...]  # index.faiss, chunks.json, manifest.json

@dataclass(frozen=True)
class DemoPack:
    pack_id: str
    pack_dir: Path
    agent_profile: dict
    system_prompt: str
    secrets_vault: dict
    judge_prompt: str
    attack_playbook: dict
    benign_playbook: dict
    kb_dir: Path

    @classmethod
    def load(cls, pack_dir: Path) -> DemoPack: ...
    @property
    def display_name(self) -> str: ...
    def validate(self) -> list[str]: ...

def compile_secret_patterns(
    secrets_vault: dict, min_length: int = 2
) -> list[re.Pattern[str]]: ...

def playbook_for_mode(pack: DemoPack, mode: str) -> dict: ...
def playbook_choices(pack: DemoPack, mode: str) -> list[tuple[str, str]]: ...
def get_playbook_scenario(pack: DemoPack, mode: str, scenario_id: str) -> dict | None: ...
def nexa_summary_markdown(pack: DemoPack) -> str: ...
```

### 3.6 `src/mtguard/pipeline.py`

```python
class MTGuardPipeline:
    def __init__(
        self,
        l1: RegexGuard,
        l2: TrajectoryGuard,
        fusion: RiskFusion | None = None,
        gate: UserGate | None = None,
    ) -> None: ...
    @classmethod
    def from_pack(cls, pack_dir: Path, embedder: Embedder | None = None) -> MTGuardPipeline: ...
    def process_turn(
        self,
        message: str,
        state: ConversationState | None = None,
        judge: JudgeResult | None = None,
        auto_judge: EscalationJudge | None = None,
    ) -> tuple[TurnTrace, ConversationState, FusionResult]: ...
    def reset(self) -> ConversationState: ...
```

### 3.7 Capas L1 / L2 / Fusion / Gate

```python
# l1_regex.py
class RegexGuard:
    def __init__(self, rules_path: Path | None = None) -> None: ...
    def scan(self, message: str) -> L1Result: ...

# l2_trajectory.py
@dataclass
class ConversationState:
    turn_index: int = -1
    turn_embeddings: list[np.ndarray] = field(default_factory=list)
    proximity_history: list[dict[str, float]] = field(default_factory=list)
    drift_history: list[float] = field(default_factory=list)
    trajectory_ewma: float = 0.0

class TrajectoryGuard:
    def __init__(self, agent_profile: dict, embedder: Embedder | None = None) -> None: ...
    def reset(self) -> ConversationState: ...
    def evaluate(
        self, message: str, state: ConversationState | None = None
    ) -> tuple[L2Result, ConversationState]: ...

# fusion.py
class RiskFusion:
    def fuse(self, l1: L1Result, l2: L2Result) -> FusionResult: ...
    def apply_judge_deny(self, fusion: FusionResult) -> FusionResult: ...

# user_gate.py
class UserGate:
    def evaluate(
        self, fusion: FusionResult, judge: JudgeResult | None = None
    ) -> GateResult: ...
```

### 3.8 RAG y Embedder

```python
# embedder.py — EMBED_DIM = 2048
class Embedder:
    def embed(self, text: str) -> np.ndarray: ...
    def embed_many(self, texts: list[str]) -> np.ndarray: ...
    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray) -> float: ...
    def centroid(self, texts: list[str]) -> np.ndarray: ...

# rag.py
@dataclass
class RetrievedChunk:
    text: str
    source: str
    score: float

class KnowledgeBase:
    def __init__(self, kb_dir: Path, embedder: Embedder | None = None) -> None: ...
    @classmethod
    def from_pack_dir(cls, pack_dir: Path, embedder: Embedder | None = None) -> KnowledgeBase: ...
    def search(self, query: str, top_k: int = 3) -> list[RetrievedChunk]: ...
```

### 3.9 Demo Gradio (`src/mtguard/demo/app.py`)

```python
@dataclass
class AppSession:
    mtguard: MTGuardSession
    main_api_key: str = ""
    judge_api_key: str = ""
    judge_enabled: bool = False
    mode: str = "benign"
    playbook_id: str | None = None
    playbook_step: int = 0
    last_trace: dict | None = None
    history: list[dict[str, str]] = field(default_factory=list)

def start_session(
    main_api_key: str, judge_api_key: str, mode_label: str, judge_enabled: bool
) -> tuple[AppSession, str, gr.update, gr.update, list, str, str, gr.update]: ...

def handle_chat(
    message: str, app: AppSession | None
) -> tuple[AppSession | None, list, str, str, dict | None]: ...

def build_ui() -> gr.Blocks: ...
def main() -> None: ...
```

### 3.10 CLI (`src/mtguard/demo/scenario.py`)

```python
def run_scenario(
    pack_dir: Path,
    scenario_id: str,
    mode: str = "redteam",
    main_api_key: str | None = None,
    judge_api_key: str | None = None,
    judge_enabled: bool = False,
) -> dict: ...

def run_all_attack_scenarios(pack_dir: Path, **kwargs) -> list[dict]: ...
def main() -> None: ...
```

---

## 4. Flujo de Datos y Gestión del Estado (Multi-Turn)

### 4.1 Inicio de sesión Gradio

```
Usuario → start_session(main_api_key, judge_api_key, mode, judge_enabled)
  → MTGuardSession.from_pack_dir(PACK_DIR, main_api_key, judge_api_key, judge_enabled)
      → DemoPack.load(pack_dir)
      → NexaAgent.from_pack(pack, embedder, main_api_key)  # exige key
      → [si judge_enabled] EscalationJudge(pack, api_key=judge_key)
      → pipeline.reset() → ConversationState vacío
  → AppSession(mtguard=session, history=[], ...)
  → gr.State(app_state) persiste AppSession entre eventos Gradio
```

**Parámetros clave:** API keys solo en RAM (`AppSession`); no se persisten a disco.

### 4.2 Un turno de chat (`handle_chat` → `MTGuardSession.turn`)

```
1. Gradio: handle_chat(message, app: AppSession)
   └─ app.mtguard.turn(message.strip())

2. MTGuardPipeline.process_turn(message, state, auto_judge=self.judge)
   ├─ L1: l1_result = RegexGuard.scan(message)
   ├─ L2: l2_result, state = TrajectoryGuard.evaluate(message, state)
   │     state.turn_index++, embeddings y proximity_history actualizados
   ├─ Fusion: fusion_result = RiskFusion.fuse(l1, l2)
   │     risk_score 0–100 → Verdict (CLEAR<25, WATCH<45, ALERT<75, CONTAIN≥75)
   ├─ Judge [condicional]:
   │     si auto_judge.should_invoke(fusion):
   │       fusion.verdict in (WATCH, ALERT) AND risk_score >= 55 AND not CONTAIN
   │       → judge_result = EscalationJudge.evaluate(message, l1, l2, fusion)
   │       → LLM NIM con judge_prompt.txt + CONTEXT JSON
   │       → parse ALLOW/DENY
   │     si decision == DENY → fusion = apply_judge_deny → CONTAIN
   ├─ Gate: gate_result = UserGate.evaluate(fusion, judge_result)
   │     CONTAIN o judge DENY → allow_llm=False
   │     ALERT → allow_llm=True, show_banner=True
   └─ TurnTrace construido (l1, l2, fusion, judge, gate, latency_ms)

3. GateResult reconstruido desde trace.gate dict

4. NexaAgent.respond(message, gate, fusion)
   ├─ si not gate.allow_llm → _block_message() + _scrub_secrets
   └─ si allow_llm:
         _compose_online(message):
           chunks = kb.search(message, top_k=3)  # FAISS + HashingVectorizer
           user_content = "Knowledge base excerpts:\n{context}\n\nEmployee question:\n{message}"
           _call_main_llm(user_content):
             OpenAI(base_url=NIM_BASE_URL, api_key=main_api_key)
             messages=[system: pack.system_prompt, user: user_content]
             model=main_model (default llama-3.3-70b-instruct)
         [si show_banner] prepend _ALERT_BANNER
         _scrub_secrets(response)  # secret_patterns desde vault

5. AgentTurn(trace, response, fusion, gate) → Gradio actualiza history + trace_panel
```

### 4.3 Estado multi-turn: qué persiste dónde

| Estado | Ubicación | Reset |
|--------|-----------|-------|
| `ConversationState` (L2) | `MTGuardSession.state` | `mtguard.reset()` |
| Historial chat UI | `AppSession.history` | `reset_conversation()` |
| Último trace | `AppSession.last_trace` | reset conversación |
| Playbook step | `AppSession.playbook_step` | reset playbook / conversación |
| API keys | `AppSession` + objetos agent/judge | nueva sesión |

**Importante:** El historial de chat Gradio **no** se inyecta al prompt LLM. Solo el mensaje del turno actual + RAG top-3. La memoria defensiva multi-turn está en **L2 `ConversationState`**, no en el contexto del LLM.

### 4.4 Formato del prompt final al LLM principal

```
[System]
{contents of demo_pack/nexa_copilot/system_prompt.txt}

[User]
Knowledge base excerpts:
{chunk1.text}

---

{chunk2.text}

---

{chunk3.text}

Employee question:
{user message del turno actual}
```

### 4.5 Formato del prompt del Juez

```
{contents of judge_prompt.txt}

CONTEXT (JSON):
{
  "user_message": "...",
  "l1": { hit, rule_id, severity, matched_text },
  "l2": { safe_score, proximity, max_proximity, ... },
  "fusion": { risk_score, verdict, factors }
}

Decision:
```

---

## 5. Mapeo de Puntos de Fricción y Deuda Técnica

### 5.1 Estado en disco vs commit `a0f5d78`

Los bloques listados en la especificación del prompt (`_compose_offline`, `_FALLBACK`, `_SECRET_PATTERNS`, fallback `try/except`) **ya no existen en el working tree**. Fueron eliminados localmente. A continuación: **código legacy en `a0f5d78`** (referencia histórica) y **deuda restante en código actual**.

---

### 5.2 ELIMINADO — Modo offline (`a0f5d78:src/mtguard/agent.py`)

**En disco actual:** `grep` no encuentra `_compose_offline`, `_ticket_response`, `_topic_response`, `_generic_response`, `_FALLBACK`.

**Legacy en commit `a0f5d78` (para entender qué se quitó):**

```python
_FALLBACK = (
    "I can help with VPN connectivity, ticket status (INC-*), MDM enrollment, and access requests. "
    "Visit the IT self-service portal or open a ticket for further assistance."
)

# En respond():
if self.main_api_key:
    body = self._compose_online(message)
else:
    body = self._compose_offline(message)

# En _compose_online — supresión que ocultaba fallos API:
try:
    return self._call_main_llm(user_content)
except Exception:  # noqa: BLE001
    return self._compose_offline(message)

# En _call_main_llm — fallback silencioso a texto hardcodeado:
return (response.choices[0].message.content or _FALLBACK).strip()

def _compose_offline(self, message: str) -> str:
    chunks = self.kb.search(message, top_k=3)
    if not chunks:
        return _FALLBACK
    lower = message.lower()
    if re.search(r"INC-\d+", message, re.IGNORECASE):
        return self._ticket_response(message, chunks)
    if any(kw in lower for kw in ("vpn", "wi-fi", "wifi", "network")):
        return self._topic_response(chunks, "vpn_troubleshooting.md")
    # ... más ramas keyword ...
    return self._generic_response(chunks[0])

def _ticket_response(self, message: str, chunks: list[RetrievedChunk]) -> str: ...
def _topic_response(self, chunks: list[RetrievedChunk], source: str) -> str: ...
def _generic_response(self, chunk: RetrievedChunk) -> str: ...
```

**Estado actual equivalente:**

```python
def _compose_online(self, message: str) -> str:
    _require_main_api_key(self.main_api_key)
    chunks = self.kb.search(message, top_k=3)
    # ...
    return self._call_main_llm(user_content)  # sin try/except, sin offline
```

---

### 5.3 ELIMINADO — Secretos hardcodeados (`a0f5d78`)

**Legacy:**

```python
_SECRET_PATTERNS = (
    r"GW-7k9mN2pQ8xR4vL6w",
    r"\b8842\b",
    r"whsec_nexa_sim",
    r"it-admins@nexacorp\.internal",
)

@staticmethod
def _scrub_secrets(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
    return text
```

**Estado actual (`agent.py` `__post_init__`):**

```python
vault = json.loads(vault_path.read_text(encoding="utf-8"))
secrets = vault.get("secrets", {})
self.secret_patterns = [
    re.compile(re.escape(str(v)), re.IGNORECASE) for v in secrets.values() if v
]
```

**Deuda:** `pack_loader.compile_secret_patterns()` sigue existiendo (split por comas, `min_length`) pero **`NexaAgent` no la usa** — lógica duplicada/inconsistente entre módulos.

---

### 5.4 ELIMINADO — Supresión de errores API en agente (`a0f5d78`)

**Legacy (OpenAI, con redirección offline):**

```python
try:
    return self._call_main_llm(user_content)
except Exception:  # noqa: BLE001
    return self._compose_offline(message)
```

**Estado actual (`agent.py`):** sin `try/except` en `_compose_online` ni `_call_main_llm`. Excepciones de `openai` propagan hasta Gradio:

```python
# app.py handle_chat
try:
    result = app.mtguard.turn(message.strip())
except Exception as exc:
    return _api_error_response(app, message, str(exc))
```

---

### 5.5 RESUELTO (Phase 8) — Timeouts NIM explícitos

Clientes OpenAI **cacheados** en `__post_init__` con timeout/retries explícitos:

```python
# agent.py
self._client = OpenAI(base_url=NIM_BASE_URL, api_key=..., timeout=MAIN_TIMEOUT, max_retries=MAIN_MAX_RETRIES)
# judge.py — JUDGE_TIMEOUT (20s), JUDGE_MAX_RETRIES (0)
```

Constantes en `nim.py`: `MAIN_TIMEOUT = httpx.Timeout(60.0, connect=10.0)`, `JUDGE_TIMEOUT = httpx.Timeout(20.0, connect=10.0)`.

---

### 5.6 RESUELTO (Phase 8) — Streaming y cola Gradio

- `NexaAgent._stream_main_llm` (stream=True, salta chunks con `choices=[]` del cierre NIM/vLLM)
- `NexaAgent.respond_stream` — scrubbing aplicado al texto **acumulado** en cada delta
- `MTGuardSession.turn_stream` — emite `("trace", dict)` inmediato → `("delta", str)*` → `("done", AgentTurn)`
- `handle_chat`/`playbook_next_turn`/`_send` son generadores; `demo.queue(default_concurrency_limit=4)`
- Errores mid-stream: `_apply_stream_error` reemplaza el placeholder del asistente **sin duplicar** el mensaje del usuario

**Deuda menor restante:** `handle_chat` sin sesión sigue retornando silencioso (sin aviso al usuario).

---

### 5.7 RESUELTO (Phase 8) — Juez con timeout

`judge._call_llm` captura `APITimeoutError`/`APIConnectionError` y re-lanza `RuntimeError` con contexto; el handler de Gradio lo muestra en chat. Timeout 20s, 0 retries. Sigue sin modo simulado (correcto por diseño).

---

### 5.8 RESUELTO (Phase 8) — Documentación y scripts alineados

- `scripts/generate_command_glossary.py`: alineado a NIM (`nvapi-…`, llama, MAIN_API_KEY obligatoria) y PDF regenerado.
- Refactor NIM + streaming: **commiteado** en `main`.
- Artefacto `https:/`: eliminado (era esqueleto de clone fallido, 0 objetos git).

---

### 5.9 DEUDA ACTIVA — Historial LLM

`AppSession.history` es solo UI. El LLM no recibe turnos anteriores del chat. Comportamiento intencional para la demo de defensa, pero limita coherencia conversacional del agente.

---

## 6. Configuración de Entorno e Infraestructura Actual

### 6.1 Dependencias (`pyproject.toml`)

| Paquete | Uso |
|---------|-----|
| `openai>=1.40.0` | Cliente OpenAI-compatible → **NVIDIA NIM** vía `base_url` |
| `gradio>=4.44.0` | UI demo (instalado ~6.19 en venv) |
| `faiss-cpu` | Índice RAG |
| `scikit-learn` | HashingVectorizer embedder |
| `numpy` | Vectores L2/RAG |

**Entrypoints:**

```toml
Mudette-demo = "mtguard.demo.app:main"
Mudette-scenario = "mtguard.demo.scenario:main"
```

### 6.2 Variables de entorno

| Variable | Consumidor | Obligatoria |
|----------|------------|-------------|
| `MAIN_API_KEY` | `scenario.py`, scripts benchmark | Sí (demo, benchmarks, agente) |
| `JUDGE_API_KEY` | `run-benchmarks-with-judge.sh`, Gradio si juez ON | Solo con juez activo |

**No se usa:** `OPENAI_API_KEY` (el código pasa `api_key` explícitamente).

**Formato esperado:** NVIDIA API key (`nvapi-…`) desde [build.nvidia.com](https://build.nvidia.com).

### 6.3 Cliente LLM actual (NIM, post-Phase 8)

```python
# src/mtguard/nim.py
NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MAIN_MODEL = os.environ.get("MUDETTE_MAIN_MODEL", "meta/llama-3.1-8b-instruct")
DEFAULT_JUDGE_MODEL = os.environ.get("MUDETTE_JUDGE_MODEL", "meta/llama-3.1-8b-instruct")
MAIN_TIMEOUT = httpx.Timeout(60.0, connect=10.0);  MAIN_MAX_RETRIES = 1
JUDGE_TIMEOUT = httpx.Timeout(20.0, connect=10.0); JUDGE_MAX_RETRIES = 0

# Clientes cacheados en __post_init__ (agent.py / judge.py) con timeout+max_retries
```

| Rol | Modelo default | max_tokens | temperature | timeout |
|-----|----------------|------------|-------------|---------|
| Agente principal | `meta/llama-3.1-8b-instruct` (70b vía `MUDETTE_MAIN_MODEL`) | 500 | 0.3 | 60s |
| Juez | `meta/llama-3.1-8b-instruct` | 120 | 0 | 20s |

### 6.4 Tests sin API real

`tests/conftest.py` — fixture `autouse`:

```python
monkeypatch.setattr(NexaAgent, "_call_main_llm", fake_main_llm)
monkeypatch.setattr(EscalationJudge, "_call_llm", fake_judge_llm)
```

`uv run pytest` → 113 tests verdes sin keys NVIDIA.

### 6.5 Comandos operativos

```bash
./scripts/setup.sh              # uv sync
./scripts/run-tests.sh          # pytest mockeado
export MAIN_API_KEY='nvapi-…'
./scripts/run-demo.sh           # http://localhost:7860
./scripts/run-benchmarks-no-judge.sh
export JUDGE_API_KEY='nvapi-…'
./scripts/run-benchmarks-with-judge.sh
```

### 6.6 Pack demo `nexa_copilot`

Secretos simulados en `secrets_vault.json` (ej. `gateway_token`, `break_glass_pin`, `webhook_signing_secret`). Usados por L1 rules y scrubbing dinámico.

Playbooks de ataque con `expect_min_verdict`:

- `jailbreak_direct` → CONTAIN
- `crescendo_credentials` → ALERT+
- `salami_export` → ALERT+

---

## Apéndice A — Umbrales de decisión (referencia rápida)

| Componente | Umbral / regla |
|------------|----------------|
| L2 `APPROACH_THRESHOLD` | 0.62 |
| Fusion verdict bands | 0–24 CLEAR, 25–44 WATCH, 45–74 ALERT, 75+ CONTAIN |
| Judge `should_invoke` | `risk_score >= 55` AND verdict WATCH\|ALERT AND not CONTAIN |
| L1 HIGH floor | score mínimo 75 si L1 HIGH |
| Safe score veto | `safe_score > 0.55` puede cap CONTAIN → ALERT |

---

## Apéndice B — Estado git (post-Phase 8)

Refactor NIM + streaming + hotfix commiteados en `main` (local, **sin remote configurado aún** — push pendiente de decisión). PDFs de investigación RAGE (`GlobalSouth-RAGE-Submission-2.pdf`, `Feedback-RAGEproyect.pdf`) trackeados como registros históricos. Artefacto `https:/` eliminado.

---

*Fin del mapa. No incluye soluciones propuestas; solo estado factual del código para guiar refactorización en Claude.*
