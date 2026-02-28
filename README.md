# MIROIR

Behavioral intelligence layer for collections operations. Profiles contacts from communication history, decides how to engage, logs every decision.

> Built at Build a Zero Human Company Hackathon 2026 · Athens

---

## What it does

MIROIR analyzes **all communications between the steerer and the steerie**:

- **Steerer** — The person leading the conversation (e.g. sales rep, debt collector, account manager).
- **Steerie** — The customer or contact on the other side of the conversation.

From that history we build a **behavioural profile** of the steerie. The agent uses this profile to know **how to steer the conversation** so the steerer’s goal is met — for example:

- **Sales:** steer the conversation toward a successful sale.
- **Debt collection:** steer the conversation so the steerie is convinced to pay or commit to a plan.

So the system learns *how* to talk to each contact to maximise the chance of achieving the steerer’s objective.

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

## Run the frontend

From the project root:

```bash
cd frontend
nvm use
pnpm install
pnpm dev
```

The app will be available at `http://localhost:3000` (or the port shown in the terminal).

---

## Frontend (file uploads)

The frontend uses [UploadThing](https://uploadthing.com) for client-context file uploads (PDF, CSV, Word). To enable uploads:

1. Sign up at [uploadthing.com](https://uploadthing.com) and create an app.
2. Copy your token from the dashboard.
3. In the `frontend/` directory, copy `.env.example` to `.env` and set:
   ```env
   UPLOADTHING_TOKEN=your_token_here
   ```
4. Restart the dev server. Uploads will work from the contact detail page (Client context section).

---

## Stack

Python · FastAPI · Claude Sonnet · Supabase · Vapi · ElevenLabs · React 19 · Railway · Vercel