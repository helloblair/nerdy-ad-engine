# nerdy-ad-engine

Autonomous ad generation and evaluation pipeline for Varsity Tutors (Nerdy). Generates ad copy + images, evaluates across 7 dimensions using an LLM-as-judge, and self-heals through targeted iteration — all with minimal human intervention.

## Key Features

- **5-Agent Pipeline** — Researcher → Writer (Gemini 2.5 Flash) → ImageAgent (Imagen 4) → Evaluator (Claude Sonnet 4.6) → Fixer, orchestrated by LangGraph
- **7-Dimension Evaluation** — 5 text dimensions + 2 visual dimensions (visual_brand_consistency, scroll_stopping_power) scored using Claude's vision capability
- **Self-Healing Loop** — Detects weakest dimension, applies targeted fix, detects regressions, adapts strategy. Up to 3 iterations per ad
- **Quality Ratchet** — Dynamic threshold that ratchets upward as more ads are approved (floor: 7.0, ceiling: 9.0)
- **Persona Targeting** — 15 parent personas with psychology profiles, emotional triggers, and proven hooks from real Nerdy sales data
- **A/B Variant Generation** — Same brief, 5 different hook strategies (pain_point, social_proof, urgency, aspirational, question)
- **Human Survey + Confusion Matrix** — 90+ human ratings collected, 43.3% precision identified as key calibration gap
- **Dual-Model Architecture** — Gemini writes, Claude judges. Cross-model tension prevents self-evaluation leniency
- **Full Observability** — Langfuse tracing, cost estimation, analytics dashboard with trend visualization

## Stack
- Frontend: Next.js 16 + Tailwind CSS → Vercel
- Backend: FastAPI + LangGraph → Fly.io
- Database: SQLite (local dev) or Supabase (deployed)
- Models: Gemini 2.5 Flash (writer) + Imagen 4 (images) + Claude Sonnet 4.6 (evaluator + fixer)

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys for [Google AI Studio](https://aistudio.google.com/apikey) and [Anthropic](https://console.anthropic.com/)

### Quick Start

```bash
# 1. Clone and install
git clone <repo-url> && cd nerdy-ad-engine
make install

# 2. Set up environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your GOOGLE_API_KEY and ANTHROPIC_API_KEY

# 3. Run both backend and frontend
make dev
```

Backend runs at `http://localhost:8080`, frontend at `http://localhost:3000`.

### Manual Setup (without Make)

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
uvicorn main:app --reload --port 8080

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Run the Ad Generation Pipeline

```bash
make run-pipeline
```

This creates a test campaign and runs the full generate → evaluate → fix loop using SQLite.

### Run Tests

```bash
make test
```

All tests use mocked LLM responses — no API keys or network access needed.

### Database

By default, the app uses SQLite (`backend/data/ads.db`) — no setup required.
To use Supabase instead, set in `backend/.env`:

```
DB_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

### Architecture

```
ResearcherAgent → WriterAgent → ImageAgent → EvaluatorAgent → Decision Gate
                       ↑                                           │
                       └──── FixerAgent ←──── (score < threshold) ─┘
                                                    │
                                              (3 iterations max)
                                                    │
                                              Flag for human review
```

See `docs/` for detailed documentation:
- `docs/technical_writeup.md` — Architecture, evaluation framework, key findings
- `docs/decision_log.md` — Every major technical decision with reasoning and tradeoffs
- `docs/self_healing.md` — How the fix loop, regression detection, and escalation work
- `docs/ai_tools_doc.md` — Models, prompts, and prompt engineering decisions
- `docs/limitations.md` — Known gaps and what a production version would need

## Deployment

### Environment Variables

**Local development (`.env` file in `backend/`):**

| Variable | Description | Required |
|---|---|---|
| ANTHROPIC_API_KEY | Claude API key for evaluator + fixer agents | Yes |
| GOOGLE_API_KEY | Gemini API key for writer + image agents | Yes |
| DB_BACKEND | `sqlite` (default) or `supabase` | No |
| SUPABASE_URL | Supabase project URL — leave unset to use SQLite | No |
| SUPABASE_KEY | Supabase anon/service key — leave unset to use SQLite | No |
| WRITER_SEED | Seed for reproducible generation (e.g. `42`) | No |
| LANGFUSE_PUBLIC_KEY | Langfuse observability public key | No |
| LANGFUSE_SECRET_KEY | Langfuse observability secret key | No |

**Production (Fly.io secrets):**

All of the above, plus `SUPABASE_URL` and `SUPABASE_KEY` must be set.

```bash
fly secrets set ANTHROPIC_API_KEY=sk-... GOOGLE_API_KEY=AI... \
  SUPABASE_URL=https://xxx.supabase.co SUPABASE_KEY=eyJ... \
  DB_BACKEND=supabase
```

**Frontend (Vercel environment variables):**

| Variable | Value |
|---|---|
| NEXT_PUBLIC_API_URL | `https://nerdy-ad-engine-api.fly.dev` |

### Live Demo

- **Frontend:** https://nerdy-ad-engine.vercel.app
- **API Health:** https://nerdy-ad-engine-api.fly.dev/health
- **API Status Page:** https://nerdy-ad-engine.vercel.app/api-status
