"""
Add use_case column to contacts + insert recruitment demo contact.
Run: cd /Users/ioannis/Downloads/miroir-hackathon && .venv/bin/python scripts/add_recruitment_contact.py
"""
import sys
sys.path.insert(0, ".")

from backend.core.database import get_db

db = get_db()

# --- Step 1: Check if use_case column exists ---
row = db.table("contacts").select("*").limit(1).execute().data
if row and "use_case" in row[0]:
    print("use_case column already exists")
else:
    print("use_case column NOT found — you need to run this SQL in Supabase SQL Editor:")
    print("""
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS use_case TEXT DEFAULT 'debt_collection';
UPDATE contacts SET use_case = 'debt_collection' WHERE use_case IS NULL;
""")
    print("Run that SQL first, then re-run this script.")
    sys.exit(1)

# --- Step 2: Tag existing contacts as debt_collection ---
db.table("contacts").update({"use_case": "debt_collection"}).is_("use_case", "null").execute()
print("Tagged existing contacts as debt_collection")

# --- Step 3: Insert recruitment demo contact ---
RECRUITMENT_PROFILE = {
    "summary": (
        "Alex Papadopoulos is a senior software engineer with 8 years of experience "
        "in distributed systems and cloud infrastructure. Communication analysis reveals "
        "a highly analytical personality who values technical depth over corporate pleasantries. "
        "Responds quickly to technically substantive messages but ignores generic outreach. "
        "Shows strong follow-through on commitments he finds intellectually interesting. "
        "Prefers direct, no-nonsense communication. Past interactions suggest he's open to "
        "new opportunities but only if they offer genuine technical challenges."
    ),
    "communication_tone": "Direct and analytical — values substance over formality. Responds well to technically specific outreach.",
    "communication_tone_score": 0.85,
    "follow_through_score": 0.75,
    "reply_speed_score": 0.6,
    "pressure_score": 0.7,
    "channel_preference": "Email preferred for initial contact, transitions to video calls for deeper discussions.",
    "pressure_response": "Responds well to genuine urgency (team deadlines, project launches) but dismisses artificial pressure tactics.",
    "trust_indicators": [
        {"signal": "Engages deeply when technical specifics are discussed", "severity": 0.8, "source": "email_analysis"},
        {"signal": "Follows through on scheduled calls consistently", "severity": 0.7, "source": "calendar_data"},
        {"signal": "Provides honest feedback even when negative", "severity": 0.6, "source": "email_analysis"},
        {"signal": "Shares relevant articles and resources proactively", "severity": 0.5, "source": "email_analysis"},
    ],
    "risk_indicators": [
        {"signal": "Ignores generic recruiter messages — 3 unanswered outreach attempts from other firms", "severity": 0.7, "source": "email_analysis"},
        {"signal": "Currently employed and not actively job searching", "severity": 0.5, "source": "linkedin_profile"},
        {"signal": "Has counter-offered at previous company twice — may use offers as leverage", "severity": 0.4, "source": "market_intel"},
    ],
    "debt_amount": 0,
    "phone": "+306986903946",
    "timezone": "Europe/Athens",
}

contact_data = {
    "name": "Alex Papadopoulos",
    "email": "alex.papadopoulos@techmail.dev",
    "behavior_profile": RECRUITMENT_PROFILE,
    "trust_score": 0.78,
    "risk_score": 0.55,
    "use_case": "recruitment",
}

# Upsert — safe to run multiple times
existing = db.table("contacts").select("id").eq("email", contact_data["email"]).execute()
if existing.data:
    contact_id = existing.data[0]["id"]
    db.table("contacts").update(contact_data).eq("id", contact_id).execute()
    print(f"Updated recruitment contact: {contact_data['name']} (id: {contact_id})")
else:
    result = db.table("contacts").insert(contact_data).execute()
    contact_id = result.data[0]["id"]
    print(f"Inserted recruitment contact: {contact_data['name']} (id: {contact_id})")

print("\nDone! Recruitment contact ready.")
