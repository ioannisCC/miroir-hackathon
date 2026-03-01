# MIROIR

**Autonomous behavioral intelligence agent** that profiles contacts from communication history, decides how to engage them, and executes actions — calls, emails, escalations — with full audit logging.

> Built at **Build a Zero Human Company Hackathon 2026** · Athens

---

## 🌐 Live Demo

| Service | URL |
|---------|-----|
| **Frontend** | [lively-solace-production-3e55.up.railway.app](https://lively-solace-production-3e55.up.railway.app) |
| **Backend API** | [miroir-backend.up.railway.app](https://miroir-backend.up.railway.app) |
| **API Docs** (Swagger) | [miroir-backend.up.railway.app/docs](https://miroir-backend.up.railway.app/docs) |
| **Health Check** | [miroir-backend.up.railway.app/health](https://miroir-backend.up.railway.app/health) |

---

## What it does

MIROIR analyzes **all communications between the steerer and the steerie**:

- **Steerer** — The agent leading the conversation (debt collector, recruiter, sales rep).
- **Steerie** — The contact on the other side.

From communication history we build a **behavioral profile** — reply speed, tone, follow-through, pressure response, risk indicators. The agent uses this profile to decide **how to talk to each contact** to maximize the chance of achieving the steerer's objective.

### Two presets, one system

| Preset | Objective | Example |
|--------|-----------|---------|
| 💰 **Debt Collection** | Get the contact to commit to a payment plan | 5 Enron contacts with full behavioral profiles |
| 🎯 **Recruitment** | Get the candidate to schedule an interview | 3 contacts across cold → warm spectrum |

Switch presets with one click in the dashboard — the entire system adapts: guidelines, prompts, call rules, email rules.

### Autonomous scheduling

MIROIR doesn't wait for a human to press buttons. An **autonomous scheduler** runs every 60 seconds, checking the `follow_ups` table for due actions:

```
┌─────────────────────────────────────────────────────────┐
│                   AUTONOMOUS LOOP (60s)                  │
│                                                          │
│  1. Query follow_ups WHERE status=pending AND due ≤ now  │
│  2. For each due action:                                 │
│     • Business hours gate (09:00–18:00 contact local)    │
│     • If outside hours → reschedule to next 09:00        │
│     • If inside hours → execute action:                  │
│       - send_email    → drafts + sends via Resend        │
│       - escalate_to_call → triggers ElevenLabs call      │
│       - escalate_to_human → flags for human review       │
│       - evaluate      → runs full LLM evaluation cycle   │
│  3. Mark completed / failed → dead letter queue on error │
│                                                          │
│  Empty table = completely silent. No polling noise.      │
└─────────────────────────────────────────────────────────┘
```

Follow-ups are created automatically after calls (post-call analysis) and evaluations. The system chains actions: **evaluate → decide → schedule follow-up → execute → re-evaluate** — a fully autonomous loop that only stops when the goal is met or a human intervenes.

To trigger a demo follow-up manually:
```sql
INSERT INTO follow_ups (contact_id, scheduled_at, action_type, status)
VALUES ('<contact_id>', now() + interval '2 minutes', 'send_email', 'pending');
```

---

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Frontend   │────▶│   FastAPI Backend │────▶│   Supabase   │
│  React + TSR │     │   + Claude LLM   │     │  PostgreSQL  │
└─────────────┘     └──────┬───────────┘     └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ElevenLabs     Anthropic     Resend
        (voice calls)  (Claude AI)   (emails)
```

---

## 🚀 Local Installation

### Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** (Python package manager)
- **Node.js 20+** and **pnpm** (for frontend)
- A **Supabase** project with the required tables
- An **Anthropic** API key (Claude)

### 1. Clone & install backend

```bash
git clone https://github.com/ioannisCC/miroir-hackathon.git
cd miroir-hackathon
uv sync
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Voice calls (optional — pick one)
VOICE_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=...
ELEVENLABS_AGENT_ID=...

# Email sending (optional)
RESEND_API_KEY=re_...
DEMO_EMAIL=your@email.com

# App
ENVIRONMENT=development
BACKEND_URL=http://localhost:8000
```

### 3. Start backend

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Verify: [http://localhost:8000/health](http://localhost:8000/health)  
API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Seed demo data

```bash
# Debt collection contacts (5 Enron profiles)
uv run python scripts/push_profiles_to_supabase.py

# Recruitment contacts (3 candidates)
uv run python scripts/seed_recruitment_contacts.py
```

### 5. Start frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000)

> **Note:** Set `VITE_API_URL=http://localhost:8000` in `frontend/.env` or it defaults to `http://localhost:8000`.

---

## 📋 Testing the Features

### Via the Dashboard (Frontend)

1. **Switch presets** — Click 💰 or 🎯 at the top. Contacts list and guidelines update instantly.
2. **Evaluate a contact** — Open a contact → click **Evaluate**. Claude analyzes the profile and recommends the next action.
3. **Send an email** — Click **Send Email**. Claude drafts a profile-adapted email and sends it via Resend.
4. **Start a call** — Click **Call**. ElevenLabs initiates an outbound voice call using the behavioral profile.
5. **Override a decision** — After evaluation, click **Override** to change the recommended action with a reason.
6. **Upload a document** — Drag a PDF into the "Client context" section. Claude analyzes it and merges signals into the profile.
7. **Edit guidelines** — Edit the general context or call rules directly in the dashboard. Changes take effect immediately.

### Via curl (API)

All endpoints below work against the live deployment. Replace `localhost:8000` with `miroir-backend.up.railway.app` for production.

**List contacts (recruitment preset):**
```bash
curl "http://localhost:8000/contacts?use_case=recruitment"
```

**Get a single contact:**
```bash
curl http://localhost:8000/contacts/{contact_id}
```

**Evaluate a contact (Claude decides next action):**
```bash
curl -X POST http://localhost:8000/decisions/{contact_id}/evaluate
```

**Send a behavioral-profile-adapted email:**
```bash
curl -X POST http://localhost:8000/contacts/{contact_id}/execute-action \
  -H "Content-Type: application/json" \
  -d '{"action": "send_email"}'
```

**Start a voice call:**
```bash
curl -X POST http://localhost:8000/vapi/call/{contact_id}
```

**Draft an email (without sending):**
```bash
curl -X POST http://localhost:8000/contacts/{contact_id}/draft-email
```

**Override a decision:**
```bash
curl -X POST http://localhost:8000/decisions/{decision_id}/override \
  -H "Content-Type: application/json" \
  -d '{"action": "send_email", "reason": "Candidate responded positively on LinkedIn"}'
```

**Switch to recruitment preset:**
```bash
curl -X POST http://localhost:8000/guidelines/preset/recruitment
```

**Switch to debt collection preset:**
```bash
curl -X POST http://localhost:8000/guidelines/preset/debt_collection
```

**Analyze a contract PDF:**
```bash
curl -X POST http://localhost:8000/contracts/analyze/{contact_id} \
  -F "file=@contract.pdf"
```

**Get the voice prompt for a contact:**
```bash
curl http://localhost:8000/vapi/prompt/{contact_id}
```

**View guidelines:**
```bash
curl http://localhost:8000/guidelines
```

**Update guidelines:**
```bash
curl -X PUT http://localhost:8000/guidelines \
  -H "Content-Type: application/json" \
  -d '{"general_context": "We are a friendly team that values respect."}'
```

---

## 🗂️ API Reference

### Contacts — `/contacts`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/contacts` | List contacts (auto-filtered by active preset) |
| `GET` | `/contacts/{id}` | Get contact with full behavioral profile |
| `GET` | `/contacts/{id}/interactions` | Interaction history (calls, emails) |
| `GET` | `/contacts/{id}/decisions` | Decision history with reasoning |
| `POST` | `/contacts/{id}/draft-email` | Draft a profile-adapted email |
| `POST` | `/contacts/{id}/execute-action` | Execute action (send_email, escalate_to_call, escalate_to_human) |
| `POST` | `/contacts/{id}/post-call` | Post-call analysis — update profile from transcript |

### Decisions — `/decisions`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/decisions/{contact_id}/evaluate` | Two-pass LLM evaluation → recommended action |
| `POST` | `/decisions/{id}/override` | Operator override with audit reason |

### Contracts — `/contracts`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/contracts/analyze` | Analyze PDF/image — return structured data |
| `POST` | `/contracts/analyze/{contact_id}` | Analyze and merge signals into contact profile |

### Voice — `/vapi`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/vapi/call/{contact_id}` | Initiate outbound call (ElevenLabs or Vapi) |
| `POST` | `/vapi/webhook` | Call lifecycle webhook (saves transcript, triggers analysis) |
| `GET` | `/vapi/prompt/{contact_id}` | Get system prompt + first message for browser calls |

### Guidelines — `/guidelines`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/guidelines` | Read current guidelines |
| `PUT` | `/guidelines` | Update guidelines (partial) |
| `POST` | `/guidelines/preset/{name}` | Activate a preset (debt_collection / recruitment) |
| `GET` | `/guidelines/active` | Get active preset metadata |
| `GET` | `/guidelines/presets` | List available preset names |

---

## 🧪 Demo Contacts

### Debt Collection (5 contacts)

| Name | Trust | Risk | Profile |
|------|-------|------|---------|
| Jeff Dasovich | 0.70 | 0.20 | Highly responsive, relationship-focused |
| John Arnold | 0.70 | 0.46 | Direct, technically precise trader |
| Vince Kaminski | 0.60 | 0.36 | Hierarchical, analytical risk officer |
| Steven Kean | 0.45 | 1.00 | Selective, high-level engagement only |
| Jeff Skilling | 0.45 | 0.40 | Delegates everything, hard to reach |

### Recruitment (3 contacts)

| Name | Trust | Risk | Scenario |
|------|-------|------|----------|
| Maria Konstantinou | 0.45 | 0.65 | ⚡ **Cold call** — zero prior contact, found on LinkedIn |
| Nikos Andreou | 0.58 | 0.48 | 🔄 **Intermediate** — replied once, then went silent 12 days |
| Alex Papadopoulos | 0.78 | 0.55 | 🎯 **Warm** — deep profile, known preferences |

---

## 📁 Project Structure

```
miroir-hackathon/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── core/
│   │   ├── config.py           # All env vars loaded here
│   │   ├── database.py         # Supabase client
│   │   └── logging.py          # Structured logging
│   ├── models/
│   │   └── schemas.py          # Pydantic models (BehaviorProfile, Contact, etc.)
│   ├── routers/
│   │   ├── contacts.py         # Contact CRUD + actions
│   │   ├── decisions.py        # Evaluation + override
│   │   ├── contracts.py        # PDF analysis
│   │   ├── vapi.py             # Voice call management
│   │   └── guidelines.py       # Preset switching + guideline editing
│   ├── services/
│   │   ├── email_service.py    # Claude-drafted emails
│   │   ├── email_sender.py     # Resend integration
│   │   ├── evaluation.py       # Two-pass LLM evaluation
│   │   ├── pipeline.py         # Full pipeline orchestration
│   │   ├── profiler.py         # Map-reduce profile extraction
│   │   ├── contract_service.py # PDF → Claude vision analysis
│   │   ├── guidelines.py       # Preset definitions + Supabase sync
│   │   ├── scheduler.py        # APScheduler for autonomous follow-ups
│   │   ├── human_escalation.py # Human agent briefing generator
│   │   └── enron.py            # Enron dataset loader
│   └── prompts/
│       └── profile_extraction.py
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── index.tsx       # Dashboard — presets, guidelines, contacts list
│   │   │   └── contacts.$contactId.tsx  # Contact detail — full UI
│   │   ├── lib/
│   │   │   ├── api.ts          # 18 API endpoint helpers
│   │   │   ├── mock.ts         # UI constants (action labels, reasons)
│   │   │   └── utils.ts        # cn() + prettyPrintJson()
│   │   └── components/
│   │       └── JsonHighlight.tsx
│   └── package.json
├── scripts/
│   ├── push_profiles_to_supabase.py   # Seed debt collection contacts
│   ├── seed_recruitment_contacts.py   # Seed recruitment contacts
│   ├── run_profiling.py               # Extract profiles from Enron emails
│   └── download_enron.py              # Download Enron dataset
└── pyproject.toml
```

---

## Stack

**Backend:** Python · FastAPI · Claude Sonnet · Supabase · APScheduler  
**Frontend:** React 19 · TanStack Router/Start · Tailwind CSS 4 · Vite 7  
**Voice:** ElevenLabs Conversational AI  
**Email:** Resend  
**Deploy:** Railway

---

## License

Built for the hackathon. Do whatever you want with it.
