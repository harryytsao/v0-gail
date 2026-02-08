# PRD: Gail — Adaptive Behavioral Profiling Agent System

## Context

**Problem:** Raw conversation logs contain rich behavioral signals about users — their temperament, communication patterns, frustration triggers, responsiveness — but this information is trapped in unstructured text. There's no system that extracts these signals, builds evolving profiles, and uses them to adapt live conversations in real time.

**Dataset:** ~4M JSONL records, ~23.5K unique users, ~24.5K conversations, 104 languages. Each record contains `user_id`, `conversation_id`, `model`, `language`, `conversation_turn`, `message_index`, `role`, `content`, `redacted`. Conversations range from 2–212 messages (avg 4.0). Data lives at `/Users/harry/Desktop/code/v0-gail/conversations_merged.json`.

**Outcome:** A system that ingests conversation history, builds living behavioral profiles, scores users on actionable dimensions, and powers a live agent that demonstrably adapts its behavior per user.

---

## Architecture Overview

```
                    conversations_merged.json
                              │
                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│   Ingestion Layer    │───▶│    Profile Engine    │
│   (batch + stream)   │    │  (trait extraction)  │
└──────────────────────┘    └──────────┬───────────┘
                                       │
                                       ▼
                           ┌──────────────────────┐
                           │    Profile Store     │
                           │    (PostgreSQL)      │
                           └──────────┬───────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
   │   Fit Scoring    │    │     Profile      │    │    Live Agent    │
   │      Engine      │    │    Evolution     │    │  (conversation)  │
   └──────────────────┘    └──────────────────┘    └──────────────────┘
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │      REST API        │
                           │      (FastAPI)       │
                           └──────────────────────┘
```

---

## Tech Stack

| Layer         | Technology                              | Rationale                                                       |
| ------------- | --------------------------------------- | --------------------------------------------------------------- |
| Language      | Python 3.12                             | ML/AI ecosystem, rapid prototyping                              |
| API Framework | FastAPI                                 | Async support, auto OpenAPI docs, Pydantic validation           |
| Database      | PostgreSQL 16 + pgvector                | Structured profiles + vector similarity for behavioral matching |
| Cache         | Redis                                   | Fast profile lookups during live conversations                  |
| LLM           | Claude API (claude-sonnet-4-5-20250929) | Trait extraction, live agent responses, reasoning               |
| Task Queue    | Celery + Redis                          | Async batch processing of conversation history                  |
| Migrations    | Alembic                                 | Schema versioning                                               |
| Testing       | pytest + pytest-asyncio                 | Unit + integration tests                                        |

---

## Component 1: Profile Engine

### Purpose

Extract structured behavioral traits from raw conversation text.

### Extracted Trait Categories

| Trait                | Description                                                            | Extraction Method                               |
| -------------------- | ---------------------------------------------------------------------- | ----------------------------------------------- |
| Temperament          | Patient/impatient, agreeable/confrontational, calm/reactive            | LLM classification per conversation → aggregate |
| Communication Style  | Verbose/terse, formal/casual, technical/layperson, structured/freeform | Rule-based (msg length, vocabulary) + LLM       |
| Sentiment Trend      | Emotional arc across conversations over time                           | LLM sentiment scoring per message → time series |
| Follow-through       | Does user return to topics? Complete multi-step tasks?                 | Pattern matching across conversation chains     |
| Life-stage Signals   | Student, professional, parent, domain expertise indicators             | LLM extraction from content topics and language |
| Language & Locale    | Primary language, multilingual capability                              | Direct from language field + content analysis   |
| Topic Interests      | Domains the user engages with (tech, legal, math, etc.)                | LLM topic classification per conversation       |
| Interaction Patterns | Avg conversation length, question depth, reformulation habits          | Statistical analysis of conversation metadata   |

### Processing Pipeline

**Batch Processing (existing dataset):**

1. Read JSONL in chunks of 1000 records
2. Group messages by `user_id` → `conversation_id`
3. Reconstruct full conversations (ordered by `message_index`)
4. For each conversation, call Claude API with extraction prompt
5. Store extracted signals in `behavioral_signals` table
6. Aggregate signals into `user_profiles` table

**Real-time Processing (new conversations):**

1. On conversation completion, trigger extraction
2. Extract signals from new conversation
3. Update profile with new signals (merge, don't replace)

### Key Extraction Prompt Structure

```
Given this conversation, extract behavioral signals:

- Temperament (1-10 scale + label + evidence quote)
- Communication style (dimensions: formality, verbosity, technicality)
- Sentiment (per-message scores + overall arc)
- Life-stage indicators (with confidence)
- Topic categories

Return as structured JSON.
```

### Files

- `src/profile_engine/__init__.py`
- `src/profile_engine/extractor.py` — LLM-based trait extraction
- `src/profile_engine/aggregator.py` — Combine signals into profiles
- `src/profile_engine/batch_processor.py` — Process existing JSONL dataset
- `src/profile_engine/prompts.py` — Extraction prompt templates

---

## Component 2: Dynamic Fit Scoring

### Purpose

Score users on actionable dimensions that predict outcomes. Scores update with new data and include reasoning.

### Scoring Dimensions

| Dimension          | Scale | Signals Used                                                        |
| ------------------ | ----- | ------------------------------------------------------------------- |
| Responsiveness     | 0–100 | Conversation frequency, reply depth, follow-up rate                 |
| Escalation Risk    | 0–100 | Sentiment volatility, confrontational language, repeated complaints |
| Engagement Quality | 0–100 | Question depth, topic diversity, multi-turn persistence             |
| Cooperation Level  | 0–100 | Follows instructions, provides requested info, polite interaction   |
| Expertise Level    | 0–100 | Technical vocabulary, question complexity, domain knowledge         |

### Scoring Algorithm

Each score is computed as a weighted recency blend:

```
score = Σ (signal_value × recency_weight × confidence)
recency_weight = exp(-λ × days_since_signal)  # λ = 0.03 (half-life ~23 days)
```

### Score Update Flow

1. New behavioral signal arrives
2. Retrieve existing score + component signals
3. Compute new weighted score
4. Generate reasoning: "Escalation risk increased from 35→52: user showed frustration in 3 of last 5 conversations (was 1 of 5 previously)"
5. Store new score + reasoning + timestamp in `score_history`

### Files

- `src/scoring/__init__.py`
- `src/scoring/calculator.py` — Score computation with recency weighting
- `src/scoring/dimensions.py` — Dimension definitions and thresholds
- `src/scoring/reasoning.py` — Human-readable score change explanations

---

## Component 3: Live Agent

### Purpose

A conversational agent that references the user's profile in real time and demonstrably adapts its behavior.

### Adaptation Dimensions

| Profile Signal                      | Agent Adaptation                                                  |
| ----------------------------------- | ----------------------------------------------------------------- |
| High formality score                | Use professional language, avoid colloquialisms                   |
| Low patience / high escalation risk | Be concise, acknowledge frustration early, offer direct solutions |
| Technical expertise: high           | Skip basic explanations, use domain terminology                   |
| Technical expertise: low            | Use analogies, step-by-step explanations, avoid jargon            |
| Sentiment trend: declining          | Proactively check in, offer escalation paths                      |
| Communication style: terse          | Match brevity, use bullet points                                  |
| Communication style: verbose        | Provide detailed explanations, engage with nuance                 |
| Preferred language ≠ English        | Respond in preferred language or offer to switch                  |

### System Prompt Construction

The live agent builds a dynamic system prompt per user:

```python
def build_system_prompt(profile: UserProfile, scores: Dict[str, Score]) -> str:
    base = "You are Gail, an adaptive conversational agent."

    profile_context = f"""
    ## User Profile for {profile.user_id}
    - Temperament: {profile.temperament.label} ({profile.temperament.score}/10)
    - Communication style: {profile.communication_style.summary}
    - Expertise level: {scores['expertise'].value}/100
    - Escalation risk: {scores['escalation_risk'].value}/100
    - Recent sentiment trend: {profile.sentiment_trend.direction}
    - Behavioral arc: {profile.evolution.current_arc}
    """

    adaptation_rules = generate_adaptation_rules(profile, scores)

    return f"{base}\n{profile_context}\n{adaptation_rules}"
```

### Conversation Flow

1. User sends message with `user_id`
2. Load profile from Redis cache (fallback to PostgreSQL)
3. Build adapted system prompt
4. Send to Claude API with profile-aware system prompt
5. Return response
6. Async: extract signals from this new exchange, update profile

### Files

- `src/agent/__init__.py`
- `src/agent/live_agent.py` — Core agent with profile-aware prompting
- `src/agent/prompt_builder.py` — Dynamic system prompt construction
- `src/agent/adaptation_rules.py` — Profile → behavior mapping rules

---

## Component 4: Profile Evolution

### Purpose

Handle conflicting signals, detect behavioral shifts, and maintain coherent profiles that reflect growth rather than averaging contradictions.

### Evolution Mechanisms

#### 1. Temporal Decay Windows

| Window              | Weight |
| ------------------- | ------ |
| Recent (0–30 days)  | 1.0    |
| Medium (30–90 days) | 0.6    |
| Old (90–180 days)   | 0.3    |
| Ancient (180+ days) | 0.1    |

#### 2. Behavioral Arc Detection

Track transitions between behavioral states:

- `hostile → neutral → cooperative` = "rehabilitation arc"
- `engaged → declining → disengaged` = "churn arc"
- `casual → technical → expert` = "growth arc"

**Detection:** Compare trait clusters across time windows. If the current 30-day window differs significantly (>2 std dev) from the 90-day window, flag a behavioral shift.

#### 3. Conflict Resolution Strategy

When signals contradict (e.g., user is polite in one conversation, hostile in the next):

```python
def resolve_conflict(signals: List[Signal]) -> ResolvedTrait:
    # 1. Check for temporal pattern (is this a trend or noise?)
    recent = signals_in_window(signals, days=30)
    older = signals_in_window(signals, days=90)

    # 2. If recent signals are consistent, trust the trend
    if std_dev(recent) < CONSISTENCY_THRESHOLD:
        return ResolvedTrait(
            value=weighted_mean(recent),
            confidence=HIGH,
            arc=detect_arc(older, recent),
            note="Consistent recent behavior diverges from historical"
        )

    # 3. If recent signals are inconsistent, flag volatility
    return ResolvedTrait(
        value=weighted_mean(signals),
        confidence=LOW,
        volatility=HIGH,
        note="User shows inconsistent behavior — context-dependent"
    )
```

#### 4. Profile Snapshots

Store weekly profile snapshots to enable:

- Viewing profile evolution over time
- Detecting long-term trends
- Rolling back if data quality issues are discovered

### Files

- `src/evolution/__init__.py`
- `src/evolution/arc_detector.py` — Behavioral arc detection
- `src/evolution/conflict_resolver.py` — Contradictory signal handling
- `src/evolution/snapshot.py` — Profile snapshot management
- `src/evolution/temporal.py` — Time-based weighting functions

---

## Data Model (PostgreSQL)

### Tables

```sql
-- Core user profile (current state)
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY,
    temperament JSONB,           -- {score: 7, label: "patient", evidence: [...]}
    communication_style JSONB,   -- {formality: 0.8, verbosity: 0.3, technicality: 0.9}
    sentiment_trend JSONB,       -- {direction: "improving", recent_avg: 0.6}
    life_stage JSONB,            -- {stage: "professional", confidence: 0.85, signals: [...]}
    topic_interests JSONB,       -- {primary: ["tech", "legal"], secondary: ["math"]}
    interaction_stats JSONB,     -- {avg_turns: 4.2, avg_msg_length: 120, ...}
    primary_language VARCHAR(50),
    current_arc VARCHAR(100),    -- "growth", "stable", "declining", etc.
    profile_version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual behavioral signals extracted from conversations
CREATE TABLE behavioral_signals (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(user_id),
    conversation_id UUID,
    signal_type VARCHAR(50),     -- "temperament", "sentiment", "style", etc.
    signal_value JSONB,          -- Extracted signal data
    confidence FLOAT,
    extracted_at TIMESTAMPTZ DEFAULT NOW(),
    source_turn INTEGER,
    INDEX idx_signals_user_time (user_id, extracted_at DESC)
);

-- Dynamic fit scores with history
CREATE TABLE fit_scores (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(user_id),
    dimension VARCHAR(50),       -- "responsiveness", "escalation_risk", etc.
    score FLOAT,
    previous_score FLOAT,
    reasoning TEXT,              -- Human-readable explanation
    component_signals JSONB,     -- Signal IDs and weights used
    scored_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_scores_user_dim (user_id, dimension, scored_at DESC)
);

-- Profile snapshots for evolution tracking
CREATE TABLE profile_snapshots (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(user_id),
    snapshot JSONB,              -- Full profile state at this point
    arc_label VARCHAR(100),
    snapshot_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_snapshots_user (user_id, snapshot_at DESC)
);

-- Conversation log (processed)
CREATE TABLE conversations (
    conversation_id UUID PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(user_id),
    model VARCHAR(50),
    language VARCHAR(50),
    total_turns INTEGER,
    messages JSONB,              -- Full conversation messages
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Endpoints

### Profile Management

| Method | Path                                         | Description                               |
| ------ | -------------------------------------------- | ----------------------------------------- |
| GET    | `/api/profiles/{user_id}`                    | Get full profile with current scores      |
| GET    | `/api/profiles/{user_id}/timeline`           | Get profile evolution timeline            |
| GET    | `/api/profiles/{user_id}/scores`             | Get all current fit scores with reasoning |
| GET    | `/api/profiles/{user_id}/scores/{dimension}` | Get score history for a dimension         |

### Live Agent

| Method | Path                                | Description                                 |
| ------ | ----------------------------------- | ------------------------------------------- |
| POST   | `/api/agent/chat`                   | Send message, get profile-adapted response  |
| GET    | `/api/agent/chat/{conversation_id}` | Get conversation history                    |
| GET    | `/api/agent/adaptation/{user_id}`   | Preview how agent would adapt for this user |

### Batch Processing

| Method | Path                             | Description                                 |
| ------ | -------------------------------- | ------------------------------------------- |
| POST   | `/api/batch/ingest`              | Trigger ingestion of JSONL dataset          |
| GET    | `/api/batch/status`              | Check batch processing progress             |
| POST   | `/api/batch/recompute/{user_id}` | Recompute a user's profile from all signals |

### Request/Response Example — Chat

**Request:**

```json
// POST /api/agent/chat
{
  "user_id": "55798ace-d5ae-4797-a94f-3bc2f705d8c8",
  "message": "Can you explain how credit monitoring works?",
  "conversation_id": "optional-existing-conversation-id"
}
```

**Response:**

```json
{
  "response": "Credit monitoring tracks changes to your credit reports...",
  "conversation_id": "new-or-existing-id",
  "adaptations_applied": [
    "Matched user's concise communication style",
    "Used accessible language (expertise: 32/100)",
    "Warm tone — user shows cooperative temperament"
  ],
  "profile_summary": {
    "temperament": "patient",
    "style": "concise, casual",
    "escalation_risk": 12
  }
}
```

---

## Project Structure

```
v0-gail/
├── README.md
├── pyproject.toml                    # Python project config (dependencies, scripts)
├── alembic.ini                       # Database migration config
├── alembic/                          # Migration files
│   └── versions/
├── conversations_merged.json         # Source dataset (existing)
├── conversation.json                 # Sample record (existing)
├── src/
│   ├── __init__.py
│   ├── config.py                     # App configuration (env vars, constants)
│   ├── database.py                   # PostgreSQL + Redis connection setup
│   ├── models.py                     # SQLAlchemy ORM models
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entry point
│   │   ├── routes/
│   │   │   ├── profiles.py           # Profile CRUD endpoints
│   │   │   ├── scores.py             # Score query endpoints
│   │   │   ├── agent.py              # Live agent chat endpoints
│   │   │   └── batch.py              # Batch processing endpoints
│   │   └── schemas.py                # Pydantic request/response models
│   ├── profile_engine/
│   │   ├── __init__.py
│   │   ├── extractor.py              # LLM-based trait extraction
│   │   ├── aggregator.py             # Signal → profile aggregation
│   │   ├── batch_processor.py        # JSONL dataset processing
│   │   └── prompts.py                # Extraction prompt templates
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── calculator.py             # Score computation
│   │   ├── dimensions.py             # Dimension definitions
│   │   └── reasoning.py              # Score change explanations
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── live_agent.py             # Profile-aware conversation agent
│   │   ├── prompt_builder.py         # Dynamic system prompt construction
│   │   └── adaptation_rules.py       # Profile → behavior mappings
│   └── evolution/
│       ├── __init__.py
│       ├── arc_detector.py           # Behavioral arc detection
│       ├── conflict_resolver.py      # Contradictory signal handling
│       ├── snapshot.py               # Profile snapshots
│       └── temporal.py               # Time-based weighting
├── tests/
│   ├── conftest.py                   # Shared fixtures
│   ├── test_extractor.py
│   ├── test_aggregator.py
│   ├── test_scoring.py
│   ├── test_agent.py
│   ├── test_evolution.py
│   └── test_api.py
└── scripts/
    ├── seed_db.py                    # Load sample data for development
    └── run_batch.py                  # CLI script to run batch processing
```

---

## Implementation Order

### Phase 1: Foundation (database + data models + ingestion)

1. Set up `pyproject.toml` with dependencies
2. Create `src/config.py`, `src/database.py`, `src/models.py`
3. Set up Alembic migrations, create all tables
4. Build `src/profile_engine/batch_processor.py` to read JSONL and populate conversations table
5. Build basic FastAPI app with health check

### Phase 2: Profile Engine (trait extraction)

6. Build `src/profile_engine/prompts.py` with extraction templates
7. Build `src/profile_engine/extractor.py` — process one conversation → signals
8. Build `src/profile_engine/aggregator.py` — combine signals → profile
9. Wire batch processor to extract + aggregate for all users
10. Test with sample users from dataset

### Phase 3: Dynamic Fit Scoring

11. Build `src/scoring/dimensions.py` with dimension configs
12. Build `src/scoring/calculator.py` with recency-weighted scoring
13. Build `src/scoring/reasoning.py` for explainable score changes
14. Wire scoring into profile update pipeline

### Phase 4: Profile Evolution

15. Build `src/evolution/temporal.py` — decay functions
16. Build `src/evolution/conflict_resolver.py`
17. Build `src/evolution/arc_detector.py`
18. Build `src/evolution/snapshot.py` — weekly snapshots
19. Integrate evolution into profile update flow

### Phase 5: Live Agent

20. Build `src/agent/adaptation_rules.py` — profile → behavior mappings
21. Build `src/agent/prompt_builder.py` — dynamic system prompt
22. Build `src/agent/live_agent.py` — full conversation loop
23. Add async profile update after each conversation

### Phase 6: API + Integration

24. Build all API routes
25. Add Redis caching for profile lookups
26. End-to-end testing

---

## Verification & Testing

### Unit Tests

- **Extractor:** Feed known conversations, verify extracted traits match expected
- **Aggregator:** Feed known signals, verify profile state
- **Scorer:** Feed known signals + timestamps, verify score computation
- **Evolution:** Feed conflicting signals, verify arc detection and conflict resolution

### Integration Tests

- **Full pipeline:** Ingest sample conversation → extract → score → verify profile
- **Live agent:** Chat with two different profiles, verify response differences
- **Score update:** Add new conversation data, verify score shifts with reasoning

### End-to-End Verification

1. Run batch ingestion on a subset (100 users) from `conversations_merged.json`
2. Inspect generated profiles for known user IDs from the sample data (e.g., `55798ace` — identity protection user, `f2420c66` — detailed sanctions researcher)
3. Start live agent, chat as different users, confirm adapted responses
4. Compare agent responses for a high-expertise user vs low-expertise user with the same question
5. Verify that a user's profile evolution timeline shows meaningful arcs
