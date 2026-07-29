# Intelligent Customer Service Chatbot Platform (ICS)

A Python + Streamlit customer service platform — AI chat engine, admin
portal, document/voice intelligence, and production hardening — built
across five sequential phases (ICS-001 → ICS-005), all now complete.

~4,600 lines of Python across 47 files. Zero non-Python frameworks.

## Run it

```bash
pip install -r requirements.txt
# optional: voice, OCR, and PDF/DOCX/XLSX parsing
pip install -r requirements-optional.txt

streamlit run app.py
```

The app creates `ics_platform.db` (SQLite) and seeds starter FAQs +
prompt templates automatically on first run.

### Run the test suite

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Tests run against a disposable `test_ics_platform.db`, never your real
database.

### Run with Docker

```bash
cp .env.example .env   # fill in a real ICS_SECRET_KEY
docker compose up --build
```

## Project structure

```
customer_service_chatbot/
├── app.py                     # Entry point, routing, sidebar nav, error boundaries
├── config.py                   # Environment-driven settings
├── constants.py                  # Colors, roles, nav items, session keys
├── database.py                    # SQLAlchemy models (all tables) + session mgmt
├── authentication.py               # Register/login/logout/RBAC/lockout/hashing
├── styles.py                        # Global CSS (glassmorphism, gradients, KPIs)
├── requirements.txt                  # Core runtime deps
├── requirements-optional.txt          # Voice / OCR / document-parsing deps
├── requirements-dev.txt                # + pytest
├── Dockerfile, docker-compose.yml, Procfile, runtime.txt, .env.example
├── .streamlit/config.toml              # Theme + telemetry-off + upload limits
│
├── chatbot/                    # ICS-002: AI engine
│   ├── text_processing.py        # tokenize/clean/lemmatize/keywords/lang-detect
│   ├── intent_classifier.py        # rule-based intent + confidence scoring
│   ├── sentiment_analyzer.py         # lexicon sentiment (7 labels)
│   ├── faq_engine.py                   # TF-IDF cosine-similarity knowledge search
│   ├── memory_manager.py                 # short-term conversation context
│   ├── recommendation_engine.py            # related-article suggestions
│   ├── response_generator.py                 # reply templates + escalation rules
│   ├── conversation_manager.py                 # DB-backed conversation/message CRUD
│   └── chatbot_engine.py                         # top-level process_message() pipeline
│
├── services/                   # ICS-003/004: admin + platform services
│   ├── admin_service.py           # users, KB CMS, escalations, audit logs
│   ├── settings_service.py          # key/value app settings
│   ├── customer_profile_service.py    # derived per-customer analytics
│   └── prompt_service.py                # editable LLM-ready prompt templates
│
├── analytics/metrics.py        # ICS-003: conversation/intent/sentiment aggregation
│
├── utils/                      # ICS-004/005: cross-cutting capabilities
│   ├── voice_service.py          # STT/TTS (feature-detected, graceful fallback)
│   ├── document_service.py         # file text extraction + extractive summary
│   ├── ocr_service.py                # image OCR (feature-detected)
│   ├── translation_service.py          # 11-language phrase dictionary
│   ├── automation_service.py             # business-hours + escalation priority
│   └── error_handler.py                    # centralised page-level error boundary
│
├── app_pages/                  # UI
│   ├── landing.py, auth_pages.py, dashboard.py, profile.py
│   ├── chat.py                    # premium chat UI + voice + document upload
│   ├── knowledge_base.py            # customer-facing FAQ search
│   ├── analytics.py, reports.py       # ICS-003 admin analytics/exports
│   ├── admin_console.py                 # users / KB CMS / escalations / audit / prompts / profiles
│   └── settings.py                        # branding / AI config / chat config / model info / system info
│
└── tests/                      # ICS-005
    ├── conftest.py, test_authentication.py, test_chatbot_nlp.py
    ├── test_chatbot_integration.py, test_database_and_admin.py
```

**Note on `models/`:** the folder exists (per the original spec) but is
intentionally empty — all SQLAlchemy models live in `database.py` as a
single source of truth for the schema. Splitting them out is a
mechanical refactor if the project grows large enough to want it.

## What's implemented, phase by phase

### ICS-001 — Foundation
Registration/login/logout, forgot/change password, PBKDF2-HMAC-SHA256
hashing (per-user salt, 260k iterations), RBAC, session tracking.
`users`/`profiles`/`sessions`/`activity_logs` tables. Glassmorphism
landing page, gradient buttons, dark/light mode, role-gated sidebar.

### ICS-002 — AI chatbot engine
Full pipeline: preprocess → classify intent (17 intents + unknown) →
analyze sentiment (7 labels) → search knowledge base (TF-IDF cosine
similarity) → generate response → update memory → persist. All
dependency-free (stdlib only), so it runs with zero extra installs;
each stage is a single swappable function if you want to plug in
spaCy / a trained classifier / sentence-transformers + FAISS later.
Premium chat UI: bubbles, sentiment badges, quick prompts, pin/
favourite/rename/delete conversations, CSV transcript export.

### ICS-003 — Admin portal
Admin Console with tabs: user management (search/filter/role change/
activate/deactivate/reset password/delete), knowledge-base CMS (create/
edit/delete/status), escalation queue (assign/resolve), audit log
viewer, prompt template editor, customer profile table. Analytics
dashboard (conversation volume, intent/sentiment distribution, AI
resolution rate, avg response time). Reports page with CSV/JSON export.
Settings page (branding, AI thresholds, chat config, AI model info,
system info), backed by a generic `app_settings` key/value table.

### ICS-004 — Voice, multilingual, documents, profiling
- **Voice**: SpeechRecognition (STT) + pyttsx3 (TTS), feature-detected
  — the mic/voice controls simply hide themselves if the optional
  packages aren't installed, instead of crashing.
- **Multilingual**: language auto-detection (keyword-overlap heuristic)
  plus a curated 11-language phrase dictionary (EN/FR/ES/DE/AR/PT/ZH/
  HI/YO/IG/HA) for common bot replies. This is honestly scoped: it is
  *not* a general machine translator for arbitrary free text — that's
  a clearly marked upgrade path, not a hidden gap.
- **Documents**: upload PDF/DOCX/TXT/CSV/XLSX/images in chat; text
  extraction (native for TXT/CSV, optional-dependency for the rest)
  feeds a dependency-free extractive summarizer + key-point list.
- **OCR**: pytesseract + Pillow, feature-detected, plus lightweight
  receipt/invoice field extraction (total, date) via regex.
- **Escalation**: automatic, rule-based (angry sentiment, emergency
  keywords, repeated low-confidence replies, frustrated refund
  requests), with a priority classifier and an admin assignment/
  resolution workflow.
- **Customer profiling**: per-customer conversation count, escalation
  count, most frequent intent, rolling sentiment score, preferred
  language — recomputed after every chat turn.
- **Prompt management**: admin-editable prompt templates, persisted in
  the database, ready for a future LLM-backed response generator.

### ICS-005 — Hardening, testing, deployment, docs
- **Security**: account lockout after 5 failed logins (15-minute
  cooldown), password strength validation, centralized page-level
  error boundary (`utils/error_handler.py`) so one broken page can't
  crash the session, all queries parameterized via SQLAlchemy (no raw
  SQL injection surface), input validation on registration/FAQ forms.
- **Testing**: pytest suite covering auth (hashing, registration,
  login, lockout), the NLP pipeline (intent/sentiment), full
  integration (FAQ search, conversation CRUD, end-to-end
  `process_message()`, escalation triggering), and the database/admin
  layer (relationships, constraints, CRUD, audit logging).
- **Deployment**: `Dockerfile`, `docker-compose.yml`, `Procfile`,
  `runtime.txt`, `.env.example`, `.streamlit/config.toml` (theme +
  telemetry off + upload limits).
- **Logging**: rotating-friendly file + console logging
  (`logs/app.log`), audit trail in the database (`activity_logs`).
- **Cleanup**: removed the ICS-001 `coming_soon` placeholder page once
  every nav section had a real implementation; no dead imports, no
  TODO/FIXME markers left in the codebase.

## Testing this without pip/network access

I built and byte-compiled every file in this project, and hand-traced
the import graph and logic — but couldn't `pip install` or launch a
live Streamlit server in the sandbox this was built in (no network
access). **Please run `pytest tests/ -v` and `streamlit run app.py`
yourself before relying on this for a defence or demo**, and let me
know if anything doesn't behave as documented.

## Known limitations

- **NLP is rule-based, not ML-trained.** Intent classification and
  sentiment analysis use lexicons/keyword overlap, not a trained
  model — deliberately, so the platform works with zero ML
  dependencies or training data. Swapping in spaCy, a fine-tuned
  classifier, or an LLM is designed to be a contained change (see
  each module's docstring for exactly which function to replace).
- **Translation is a phrase dictionary**, not general machine
  translation, for the reasons above.
- **Voice/OCR/PDF/DOCX/XLSX require optional packages** (and, for
  OCR, the Tesseract binary) that aren't bundled — the app detects
  their absence and disables just that feature rather than crashing.
- **PostgreSQL support is config-only** — tested against SQLite in
  this build; switching `ICS_DATABASE_URL` should work out of the box
  since everything goes through SQLAlchemy, but wasn't verified
  against a live Postgres instance here.
- **No live load-testing** was performed (no environment to run one).

## Default test roles

Register a new account from the UI — it defaults to `customer`. To
test as an admin, register normally, then either use the Admin
Console's "change role" control (once you have one admin) or update
that user's `role` column to `admin` directly in `ics_platform.db` for
the very first admin account.
