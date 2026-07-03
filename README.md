# DentAI — Oral Pathology Assessment Platform

An AI-powered clinical training system for dental education. Students work through oral pathology cases in a simulated clinical environment; a hybrid AI pipeline interprets their actions, scores them against clinical rules, and adapts future case selection to their demonstrated competency profile — all in Turkish.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Next.js 16 / React 19                            │
│  Chat UI · 3D Oral Simulator (R3F) · Analytics · Instructor Dashboard   │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ REST / JSON
┌──────────────────────────────▼──────────────────────────────────────────┐
│                          FastAPI Gateway                                 │
│                                                                          │
│  POST /chat ──► DentalEducationAgent                                     │
│                  ├─ Stage 1: Gemini 2.5 Flash Lite  (action classifier)  │
│                  ├─ Stage 2: AssessmentEngine       (rule-based scorer)  │
│                  └─ Stage 3: MedGemmaService        (silent validator)   │
│                                                                          │
│  GET  /recommendations ──► RecommendationEngine v2                       │
│                              ├─ XGBoost rank:pairwise (37 features)      │
│                              ├─ IRT 2PL ability estimation               │
│                              └─ BKT mastery posteriors                   │
│                                                                          │
│  GET  /analytics/mastery-trajectory ──► MasteryTrajectoryService         │
│  GET  /analytics/learning-curve     ──► LearningCurveService             │
│  GET  /analytics/outcome-correlation ──► OutcomeCorrelationService       │
│  GET  /instructor/cohort/mastery-heatmap ──► CohortAnalyticsService      │
│                                                                          │
│  /analytics · /quiz · /cases · /auth · /instructor · /admin             │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ SQLAlchemy 2 / psycopg3
                    ┌──────────▼──────────┐
                    │   PostgreSQL 16      │
                    │  (SQLite for dev)    │
                    └─────────────────────┘
```

---

## Three-Stage Silent Evaluator Pipeline

Every student message passes through three sequential stages defined in `backend/app/agent.py`. The output of each stage is non-blocking to the conversational flow — the student receives a response immediately after Stage 1 while Stages 2 and 3 operate concurrently.

### Stage 1 — Action Interpretation (Gemini 2.5 Flash Lite)

`DentalEducationAgent.interpret_action()` wraps the sanitized student input in an untrusted payload envelope and submits it to Gemini with a structured system prompt enforcing strict JSON output. The model must return:

```json
{
  "intent_type": "ACTION | CHAT",
  "action_key": "check_allergies_meds",
  "clinical_category": "anamnesis | examination | diagnosis | treatment | diagnostic_tests",
  "priority": "high | medium | low",
  "safety_concern": true | false,
  "response_tr": "..."
}
```

The allowed `action_key` set is fixed to 26 keys at prompt injection time. `_normalize_interpretation_payload()` validates all enum fields and coerces any out-of-vocabulary key to `unspecified_action`. The model never receives raw student text; `llm_safety.build_untrusted_student_payload()` wraps it in a labelled data envelope prior to the API call.

Prompt injection detection (`llm_safety.detect_prompt_injection`) runs before the LLM call and evaluates input against five compiled regex families:

| Pattern Family | Example Trigger |
|---|---|
| Instruction override | `ignore previous instructions` |
| Role override | `you are now`, `act as` |
| Exfiltration | `show me your prompt`, `print your system` |
| Jailbreak | `DAN`, `hypothetically`, `pretend` |
| System-role injection | `<system>`, `[INST]` |

Detected signals are logged and attached to the response payload but do not block the pipeline.

### Stage 2 — Rule-Based Scoring (AssessmentEngine)

`AssessmentEngine.evaluate_action()` (`backend/app/assessment_engine.py`) loads per-case scoring rules from `CaseDefinition.rules_json` in PostgreSQL. Each rule is a JSON object:

```json
{
  "action_key": "check_allergies_meds",
  "expected_outcome": "completed",
  "score_delta": 10,
  "safety_category": "anamnesis_completeness",
  "is_critical_safety_rule": false,
  "state_updates": { "allergy_check_done": true }
}
```

Safety-critical rules (`is_critical_safety_rule: true`) surface structured violation flags:

- `contraindication_violation` — prescribed treatment contradicted by patient history
- `wrong_medication` — incorrect drug class or dosage
- `premature_treatment` — treatment initiated before diagnostic workup completed
- `missed_critical_step` — mandatory safety check bypassed

These flags are passed as deterministic signals into Stage 3 and persisted in `validator_audit_log` regardless of MedGemma availability. A JSON fallback (`backend/data/scoring_rules.json`) is available behind `DENTAI_ALLOW_RULE_JSON_FALLBACK=true`.

### Stage 3 — Silent Validation (MedGemma)

`MedGemmaService` (`backend/app/services/med_gemma_service.py`) wraps `betuldanismaz/dentai-gemma2-9b-oral-pathology` — a Gemma 2 9B model fine-tuned via SFT on 50 multi-turn oral pathology assessment examples, deployed on Hugging Face Inference API.

The validator runs *after* the student response is already composed. It never adds latency to the conversational turn. The service enforces a **10-second hard timeout** and retries twice with **0.5 s exponential backoff**. On any failure it emits a fail-closed result (`validator_unavailable: true`) rather than silently returning null.

MedGemma output schema:

```json
{
  "safety_flags": ["premature_treatment"],
  "missing_critical_steps": ["periapical_radiograph"],
  "clinical_accuracy": "high | medium | low",
  "faculty_notes": "..."
}
```

Deterministic flags from Stage 2 are merged with MedGemma's probabilistic output before the `validator_audit_log` record is committed. The union ensures safety violations cannot be suppressed by LLM hallucination or service unavailability.

---

## Fine-Tuning: Gemma 2 9B on Oral Pathology

`finetuning/gemma2_finetune.ipynb` trains `betuldanismaz/dentai-gemma2-9b-oral-pathology` using Hugging Face `trl` (SFT) + `peft` (LoRA).

**Dataset** (`finetuning/finetune_dataset.jsonl`): 50 multi-turn conversations across 5 oral pathology cases. Each example contains a Turkish-language patient scenario paired with a JSON ground-truth assessment. Labels include:

- Priority: `high / medium / low`
- Safety flags: `premature_treatment`, `wrong_medication`, `missed_critical_safety_check`
- Clinical accuracy: categorical ground truth per student action

The SFT objective teaches the model to produce structured JSON assessment reports from Turkish clinical vignettes, not to generate free-form dental knowledge. The small dataset size (50 examples) is intentional — the base Gemma 2 9B already encodes clinical knowledge; SFT adapts its *output format and safety flag vocabulary* to the DentAI schema.

---

## Adaptive Learning Engine

### Bayesian Knowledge Tracing (BKT)

`backend/app/services/bkt_service.py` implements the four-parameter Corbett & Anderson (1995) BKT model. Per-(user, topic) mastery probability is tracked as a hidden Markov state with parameters:

| Symbol | Parameter | Default |
|---|---|---|
| P(L₀) | `p_init` — initial mastery prior | 0.20 |
| P(T) | `p_transit` — probability of learning after one opportunity | 0.10 |
| P(S) | `p_slip` — P(wrong \| mastered) | 0.10 |
| P(G) | `p_guess` — P(correct \| not mastered) | 0.20 |

**Update equations:**

```
Emission:  P(obs=1 | L_n) = P(L_n)·(1 - P(S)) + (1 - P(L_n))·P(G)

Posterior: P(L_n | obs=1) = P(L_n)·(1 - P(S)) / P(obs=1 | L_n)
           P(L_n | obs=0) = P(L_n)·P(S)       / P(obs=0 | L_n)

Transition: P(L_{n+1}) = P(L_n | obs) + (1 - P(L_n | obs))·P(T)
```

BKT states update on every graded quiz answer and feed directly into the 37-feature matrix for the recommendation ranker. The nightly job `backend/app/jobs/refresh_bkt_states.py` replays all historical answers in chronological order to self-heal any states corrupted by out-of-order ingestion.

### Item Response Theory (IRT) — 2PL Calibration

`backend/app/services/irt_calibration.py` fits a **2-Parameter Logistic** model via `scipy.optimize.minimize` (L-BFGS-B, bounded MLE).

**Item Characteristic Curve:**

```
P(correct | θ, a, b) = σ( a · (θ - b) )

σ(x) = 1 / (1 + e^{-x})

where:
  θ ∈ ℝ      student latent ability (standard normal scale)
  a ∈ [0.05, 5.0]    discrimination
  b ∈ [-4.0, 4.0]    difficulty (in θ units)
```

**Ability estimation:** `θ̂ = logit(p_correct)`, clipped to (0.01, 0.99) before logit to prevent ±∞.

The calibration service operates in two modes based on sample size:

- **Real-data mode** (≥200 graded responses per item): fits actual 2PL; records `is_synthetic=False`
- **Synthetic bootstrap** (<200 responses): generates N(0,1) abilities and binomial responses seeded by the instructor-assigned difficulty label as a b-prior; records `is_synthetic=True`

Fitted parameters are stored in `irt_parameters` (one row per question with log-likelihood). The nightly job `backend/app/jobs/recalibrate_irt.py` runs on a 90-day rolling window with a minimum of 200 samples per item. IRT difficulty estimates for case-mapped questions are aggregated as `irt_mean_b` and `irt_mean_a` features in the recommendation feature store.

### XGBoost Learning-to-Rank (Recommendation Engine v2)

`backend/app/services/recommendation_trainer.py` trains an XGBoost `rank:pairwise` model on labeled `recommendation_snapshots`. A snapshot is labeled positive (`outcome_score=1`) when the student completed the recommended case within 14 days with a composite score ≥70% of `max_score`.

**Hyperparameters:**

```python
{
    "objective":          "rank:pairwise",
    "n_estimators":       500,
    "max_depth":          6,
    "learning_rate":      0.05,
    "subsample":          0.8,
    "colsample_bytree":   0.8,
    "early_stopping_rounds": 30,
    "tree_method":        "hist",
}
```

Training groups are keyed by `(user_id, asof_ts)` so pairwise comparisons are only drawn within the same recommendation context. Validation uses a 21-day holdout evaluated on NDCG@5, Hit-rate@5, and MAP@10. The model bundle — `model.json`, `scaler.joblib`, `feature_schema.json`, `metadata.json` — is atomically promoted via `backend/app/jobs/promote_recommendation_model.py`. The active bundle is loaded lazily at module level and cached for the process lifetime.

---

## Feature Store — 37-Dimensional Input to the Ranker

`backend/app/services/feature_store.py` constructs the feature matrix with an `asof` parameter to prevent future leakage during training.

| Group | Count | Features |
|---|---|---|
| User-global | 5 | `mean_composite_score_30d`, `n_sessions_total`, `n_sessions_last_7d`, `days_since_last_session`, `cold_start_flag` |
| User-mastery (BKT) | 4 | `mean_mastery_prob_all_topics`, `min_mastery_prob`, `n_topics_below_60pct`, `n_topics_above_80pct` |
| User-cognitive | 3 | `avg_response_latency_ms_session`, `hint_usage_rate`, `reasoning_deviation_rate` |
| User-safety | 2 | `safety_reaction_time_p50`, `safety_action_completion_rate` |
| Case-static | 9 | `case_difficulty_ordinal`, `estimated_duration_minutes`, `n_competency_tags`, `n_safety_critical_rules`, `irt_mean_b_mapped_questions`, `irt_mean_a_mapped_questions`, `n_prerequisite_competencies`, `n_learning_objectives`, `n_mapped_questions` |
| Case-historical | 4 | `historical_avg_completion_score`, `historical_completion_rate`, `historical_avg_session_length_min`, `historical_n_unique_users_attempted` |
| Cross (user × case) | 6 | `mastery_gap_on_case_topics`, `n_prior_attempts_on_case`, `is_completed`, `is_in_progress`, `days_since_last_attempt_on_case`, `competency_overlap_with_weak_areas` |
| Reasoning pattern | 4 | `reasoning_pattern_0..3` (one-hot) |

Cold-start users receive imputed feature defaults. SHAP values are computed per-recommendation and logged to `recommendation_feature_logs` for offline debugging and explanation of ranking decisions.

### Dispatch Logic (Hybrid v1/v2)

`backend/app/services/recommendation_engine_v2.py` selects algorithm at inference time:

1. No active XGBoost bundle **or** `DENTAI_RECOMMENDATION_ALGORITHM="v1_competency_based"` → rule-based v1
2. Active bundle exists **and** user has <3 sessions (cold-start) → v1 rules, labeled `"v2_hybrid_xgb_irt_bkt_coldstart"`
3. Otherwise → full XGBoost + SHAP inference

An **ε-greedy exploration** policy (ε=0.10, configurable via `DENTAI_EXPLORATION_EPSILON`) injects a random unattempted case at rank 3 of the top-5 list to prevent distribution collapse.

---

## Research Analytics

Four services added in Sprint 14B provide publication-grade analytics for JDE / Wiley venues. All endpoints require instructor or admin role unless noted.

### Mastery Trajectory (`mastery_trajectory_service.py`)

`GET /analytics/mastery-trajectory` (student-auth) replays every graded `QuizAnswer` for the authenticated student in chronological order and returns the BKT posterior P(L_n) time series per topic with **95% Wilson-score confidence intervals**:

```
CI_half = 1.96 × √( p × (1−p) / max(1, n) )
lower   = max(0,  p − CI_half)
upper   = min(1,  p + CI_half)
```

Response shape per topic: `{ topic_id, label, current_mastery, n_observations, points: [{n, mastery, ci_lower, ci_upper, correct, timestamp}] }`. Visualised in `frontend/app/student/analytics/page.tsx`.

### Learning Curve Fitting (`learning_curve_service.py`)

`GET /analytics/learning-curve` (student-auth) fits a parametric curve to each topic's cumulative-accuracy trajectory and projects the trial count to cross the 0.70 mastery threshold (capped at 200). Two models are competed via `scipy.optimize.curve_fit`; the higher-R² fit is returned:

| Model | Equation | Reference |
|---|---|---|
| Exponential saturation | `acc(n) = L - (L - p0) × exp(-k × n)` | Anderson 1982 |
| Power-law of learning | `acc(n) = L - b × n^(-c)` | Newell & Rosenbloom 1981 |

Requires ≥3 observations per topic. Returns `model`, `params`, `r_squared`, `projected_trials_to_mastery`, and `fitted_curve` (observed range + projection horizon) per topic.

### Cohort Mastery Heatmap (`cohort_analytics_service.py`)

`GET /instructor/cohort/mastery-heatmap` returns a **student × topic BKT matrix** — each cell is the current P(L_n) in [0, 1]; `null` indicates the student has not yet attempted that topic. Also returns per-topic cohort averages and per-student average mastery and mastered-topic count. Rendered as a colour-coded heatmap in `frontend/app/instructor/cohort/page.tsx`.

### Outcome Correlation (`outcome_correlation_service.py`)

`GET /analytics/outcome-correlation` computes **Pearson r** between theory performance (MCQ + published OE quiz scores) and clinical performance (case simulation composite scores) across the student cohort. Provides construct-validity evidence — a significant positive r supports the claim that quiz and simulation measure a unified clinical competency construct. Displayed in `frontend/app/instructor/research/page.tsx`. Minimum 3 paired data points required per cohort.

### Research Export (10 CSVs)

`build_export_zip()` (`backend/app/services/research_export_service.py`) now bundles **10 KVKK-anonymised CSVs** (user IDs hashed with SHA-256 + deployment salt):

| CSV | Content |
|---|---|
| `chat_logs` | Session chat history |
| `quiz_attempts` | Attempt metadata |
| `quiz_answers` | Per-answer grading |
| `recommendation_snapshots` | 37-feature vectors + outcomes |
| `mastery_states` | Current BKT posteriors |
| `irt_parameters` | 2PL a, b per item |
| `review_schedules` | SM-2 state per student/question |
| `mastery_trajectories` | Full P(L_n) time series per (student, topic) |
| `learning_curve_fits` | Model, params, R², projection per (student, topic) |
| `outcome_correlation` | Cohort-level Pearson r with sample size |

The research snapshot (`research_snapshot_service.py`) v2 schema adds an `analytics_summary` block containing BKT prior summary, cohort mastery distribution, and outcome correlation coefficient.

---

## 3D Oral Cavity Simulator

`frontend/components/OralSimulator/` implements an interactive intraoral viewer using **React Three Fiber 9.6.1** (React renderer for Three.js 0.160.0) with Drei 10.7.7 for higher-level primitives.

**GLB model:** `backend/assets/models/oral_cavity_base.glb` (2.5 MB, CC-licensed — see `ATTRIBUTIONS.md`) is the base oral cavity mesh served at `GET /cases/oral-model`. When loaded, `<Center>` from Drei auto-centers the model bounding box at the scene origin. A procedural fallback (torus arch + extruded tooth boxes + bezier tongue) renders when the GLB is unavailable.

**Scene setup:**

```tsx
<Canvas camera={{ position: [0, 0, 1.4], fov: 45 }}>
  <ambientLight intensity={0.6} />
  <directionalLight position={[2, 4, 3]} intensity={1.2} />
  <Environment preset="studio" />
  <OrbitControls enablePan={false} minDistance={0.8} maxDistance={2.5} />
  {glbLoaded
    ? <Center><primitive object={glb.scene} /></Center>
    : <FallbackGeometry />}
  {revealedLesions.map(l => <LesionHighlight key={l.id} {...l} />)}
</Canvas>
```

**Lesion coordinate system:** Origin at arch center, +Z anterior, +Y superior, ±X lateral. `LesionHighlight` renders a pulsing `<mesh>` sphere at each lesion's coordinates with a raycaster `onClick` handler. Position resolution order: `lesion.position` (case-defined override) → `DEFAULT_LESION_POSITIONS[region_id]` → `[0, 0, 0.2]`.

Anatomical regions covered by `DEFAULT_LESION_POSITIONS`:

| Region group | Keys |
|---|---|
| Buccal mucosa | `bukkal_mukoza_sag`, `bukkal_mukoza_sol`, `bukkal_mukoza_eritroplaki` |
| Tongue | `dil_ucu`, `dil_lateral`, `dil_dorsum` |
| Palate | `damak`, `yumusak_damak` |
| Gingiva | `dis_eti`, `dis_eti_ust`, `dis_eti_ust_arka`, `dis_eti_alt`, `dis_eti_alt_on`, `dis_eti_nekrotik` |
| Lips | `dudak_cinvar`, `dudak_ici` |
| Bone / posterior | `kemik_ekspoze_alt`, `tonsil` |

**Reveal mechanism:** The same `beklenen_eylemler` (expected-actions) field that unlocks 2D clinical images also gates 3D lesion highlights. When `AssessmentEngine` marks an action as completed and the action key appears in a lesion's `reveal_on` list, the session state updates and the React component re-renders with the new overlay.

**ToothMap** (`frontend/components/OralSimulator/ToothMap.tsx`) renders an FDI quadrant grid (quadrants 1–4, teeth 1–8) and highlights teeth linked to the currently revealed lesions.

---

## Composite Scoring

`backend/app/services/composite_score_service.py` computes the final session score as a weighted average over three components:

| Component | Default Weight |
|---|---|
| MCQ (theory quiz) | 35% |
| Open-ended answers | 40% |
| Case simulation actions | 25% |

Weights are redistributed proportionally when a component has no associated questions for a given case. The composite score feeds the 30-day rolling average feature in the recommendation feature store and determines the BKT mastery label for answer-graded interactions.

### Open-Ended Scoring (AI-Assisted)

`backend/app/services/oe_scoring_service.py` submits student open-ended answers to Gemma 2 9B via Hugging Face Inference API. The model returns a structured draft:

```json
{ "score": 8, "rationale": "Hasta anamnezi eksiksiz alınmış ancak..." }
```

The AI score is stored as `ai_score_suggestion` and is **never auto-promoted**. An instructor must review and explicitly set `instructor_score` via `PATCH /instructor/answers/{id}`. Rubric snapshots are versioned in `rubric_versions` (immutable, per-question counter) so score reviews remain auditable even if the rubric changes.

---

## Spaced Repetition (SM-2)

`backend/app/services/spaced_repetition.py` implements the SuperMemo 2 algorithm for quiz review scheduling. Per-student per-question state tracks `interval` (days), `ease_factor` (initial 2.5), and next `due_date`. The ease factor updates on each review:

```
EF' = EF + (0.1 - (5 - q) · (0.08 + (5 - q) · 0.02))

where q ∈ {0..5} is the quality of recall
```

Intervals reset to 1 day on poor recall (q < 3), then grow by `EF'` on subsequent correct responses. Review schedules are stored in `review_schedules` and surfaced via the student's quiz dashboard.

---

## LLM Safety Layer

`backend/app/services/llm_safety.py` provides four independent sanitization and detection utilities:

| Function | Behavior |
|---|---|
| `sanitize_student_text` | Strips control characters, normalises Unicode whitespace, truncates at 2,000 chars |
| `sanitize_model_feedback` | Truncates at 500 chars, removes blocked tokens (`api key`, `token`, `password`, `system prompt`) via compiled regex |
| `build_untrusted_student_payload` | Wraps student text in a labelled data envelope; model is instructed in the system prompt to treat content between delimiters as untrusted input, not instructions |
| `detect_prompt_injection` | Returns `{ detected: bool, risk_level: low/medium/high, signals: [...] }` |

Detection does not block the pipeline; instead, signals are attached to `llm_interaction_logs` with `injection_detected: true` for operator review.

---

## LLM Audit Trail

Every LLM API call — Gemini interpretations, MedGemma validations, OE scoring drafts — is recorded in `llm_interaction_logs` via `backend/app/services/llm_tracker.py`:

```
provider          gemini | huggingface
model_id          gemini-2.5-flash-lite | betuldanismaz/dentai-gemma2-9b-oral-pathology
call_type         interpretation | validation | oe_scoring | coaching
prompt_tokens     int
completion_tokens int
latency_ms        int
estimated_cost_usd decimal
injection_detected bool
```

The full audit trail supports EU AI Act Article 13 transparency requirements and operator cost accounting per model per call type.

---

## Data Model

```
users              ──< student_sessions    ──< chat_logs
users              ──< mastery_states                       (BKT P(L_n) per topic)
users              ──< review_schedules                     (SM-2 per question)
users              ──< experiment_assignments               (A/B SHA-256 bucketing)
users              ──< notifications

case_definitions   ──< case_media
case_definitions   ──< student_sessions
case_definitions   ──< recommendation_snapshots

questions          ──< quiz_answers        ──< quiz_attempts
questions          ──< irt_parameters                       (2PL a, b per item)
questions          ──< rubric_versions                      (immutable snapshots)

recommendation_snapshots ──< recommendation_feature_logs   (37-dim vector + SHAP)
recommendation_model_versions                               (XGBoost bundle registry)

llm_interaction_logs                                        (every LLM API call)
validator_audit_log                                         (MedGemma per-action)
system_snapshots                                            (research reproducibility)
research_exports                                            (KVKK-compliant anonymised bundles — 10 CSVs)
```

Schema is managed by Alembic with versioned migrations covering initial schema, quiz models, IRT tables, BKT mastery states, recommendation feature logging, rubric versioning, and research analytics tables.

---

## Case Library

200+ clinical scenarios with **progressive information disclosure**: patient history → oral examination findings → radiographic evidence is gated behind student actions. Students must commit to a working diagnosis before additional data unlocks.

| Pathology | Discriminating Features |
|---|---|
| Oral Lichen Planus | Wickham striae; reticular / erosive variants; Koebner phenomenon |
| Primary Herpetic Gingivostomatitis | Vesicle clusters on attached gingiva; systemic fever; lymphadenopathy |
| Behçet Disease | Pathergy test; recurrent oral + genital aphthae; HLA-B51 association |
| Secondary Syphilis | Mucous patches; snail-track ulcers; positive VDRL / RPR serology |
| Mucous Membrane Pemphigoid | Positive Nikolsky sign; desquamative gingivitis; DIF IgG at BMZ |
| Periapical Pathology | Periapical radiolucency; percussion sensitivity; EPT response |
| Periodontal Disease | Probing depths; attachment loss patterns; furcation involvement |

Cases are stored in `CaseDefinition` (DB-backed) with a JSON fallback at `backend/data/case_scenarios.json`. `case_publish_history` tracks content versions with `published_by` and `published_at` audit fields.

---

## Competency Analytics

`backend/app/analytics_engine.py` maps action keys to five competency categories and computes per-category accuracy from the student's full action history using pandas:

| Category | Example Actions |
|---|---|
| `anamnesis` | chief complaint, medical history, allergy check |
| `examination` | extraoral exam, lymph node palpation, Nikolsky test |
| `diagnosis` | provisional diagnosis, differential diagnosis |
| `diagnostic_tests` | periapical radiograph, CBC, biopsy referral |
| `treatment` | prescription, referral, follow-up plan |

The engine surfaces the weakest category with a Turkish-language remediation recommendation string. This signal also feeds `competency_overlap_with_weak_areas` in the ranker feature store, creating a closed feedback loop from session scoring through to case selection.

---

## Role-Based Access Control

JWT tokens carry role claims (`student / instructor / admin`). `backend/app/api/deps.py` exposes `get_current_user` and role-guard dependencies injected at the FastAPI router level.

| Role | Capabilities |
|---|---|
| `student` | Submit actions, take quizzes, view own recommendations and analytics |
| `instructor` | Grade open-ended answers, manage rubrics, publish/archive cases, view cohort-level analytics |
| `admin` | Full user management, case CRUD, rule management, research exports, system health |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Primary LLM | Gemini 2.5 Flash Lite (`google-generativeai`) |
| Clinical Validator | Gemma 2 9B SFT (`betuldanismaz/dentai-gemma2-9b-oral-pathology`) via Hugging Face Inference API |
| Fine-tuning stack | `trl` (SFT) · `peft` (LoRA) · Gemma 2 9B base |
| Rule engine | PostgreSQL-backed `rules_json` + `AssessmentEngine` |
| Knowledge tracing | `bkt_service.py` (Corbett & Anderson 1995, 4-param) |
| IRT calibration | `scipy` L-BFGS-B MLE · 2PL model |
| Ranking | `xgboost` `rank:pairwise` · `shap` · `scikit-learn` · `joblib` |
| Spaced repetition | SM-2 (`spaced_repetition.py`) |
| Backend | FastAPI · Python 3.11 · Uvicorn |
| Database | PostgreSQL 16 · SQLAlchemy 2 · psycopg3 · Alembic |
| Frontend | Next.js 16 · React 19 · TypeScript 5 · Tailwind CSS 4 |
| 3D visualization | React Three Fiber 9 · Three.js 0.160 · Drei 10 |
| Auth | JWT (`python-jose`) · bcrypt (`passlib`) |
| Deployment | Docker Compose (dev / prod variants) |
