# MIROIR

Behavioral intelligence layer for collections operations. Profiles contacts from communication history, decides how to engage, logs every decision.

> Built at Build a Zero Human Company Hackathon 2026 · Athens

---

## Run locally

**Requirements:** Python 3.12+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/YOUR_USERNAME/miroir-hackathon.git
cd miroir-hackathon
uv sync
cp backend/.env.example backend/.env
# fill in backend/.env — see below
uv run uvicorn backend.main:app --reload --port 8000
```

Health check: `http://localhost:8000/health`  
API docs: `http://localhost:8000/docs`

---

## Environment variables

```env
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
VAPI_API_KEY=
VAPI_ASSISTANT_ID=
BACKEND_URL=http://localhost:8000
ENVIRONMENT=development
```

---

## Load demo contacts

5 pre-built behavioral profiles from the Enron dataset:

```bash
uv run python scripts/push_profiles_to_supabase.py
```

---

## Stack

Python · FastAPI · Claude Sonnet · Supabase · Vapi · ElevenLabs · React 19 · Railway · Vercel