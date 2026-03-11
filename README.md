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
