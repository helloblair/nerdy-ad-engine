# nerdy-ad-engine

Autonomous ad copy generation system for Varsity Tutors (Nerdy).
Generates, evaluates, and iterates Facebook/Instagram ad copy with minimal human intervention.

## Stack
- Frontend: Next.js 16 + Tailwind CSS → Vercel
- Backend: FastAPI + LangGraph → Fly.io
- Database: Supabase (Postgres)
- Agents: Gemini 2.5 Flash (generation) + Claude Sonnet (evaluation)

## Setup
See docs/ for decision log and architecture notes.
