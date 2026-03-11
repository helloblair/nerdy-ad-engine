# nerdy-ad-engine

Autonomous ad copy generation system for Varsity Tutors (Nerdy).
Generates, evaluates, and iterates Facebook/Instagram ad copy with minimal human intervention.

## Stack
- Frontend: Next.js 16 + Tailwind CSS → Vercel
- Backend: FastAPI + LangGraph → Fly.io
- Database: SQLite (local dev) or Supabase (deployed)
- Agents: Gemini 2.5 Flash (generation) + Claude Sonnet (evaluation)

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

See `docs/` for decision log and architecture notes.

## Deployment

### Environment Variables

**Local development (`.env` file in `backend/`):**

| Variable | Description | Required |
|---|---|---|
| ANTHROPIC_API_KEY | Claude API key for evaluator + fixer agents | Yes |
| GOOGLE_API_KEY | Gemini API key for writer agent | Yes |
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
