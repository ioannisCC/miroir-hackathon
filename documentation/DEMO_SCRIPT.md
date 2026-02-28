# MIROIR — Demo Script
## 75 seconds. Every word planned.

---

### SETUP (before judges arrive)
Run `demo_setup.sql` in Supabase.
Have two browser tabs open:
- Tab 1: Miroir dashboard — contact page for Steven Kean
- Tab 2: Gmail inbox (ioanniscatargiu@gmail.com)
Have your phone charged and on the table.

---

### THE SCRIPT

**[0:00 — Open with the profile]**

Show the contact card on screen.

> "This is Steven Kean. Before any contact is made, Miroir has already
> built a behavioral profile from his communication history.
> Low follow-through. Selective engager. Consistent non-response pattern.
> The system knows this before picking up the phone."

**[0:12 — Show prior email in interaction history]**

> "Four days ago it sent an email — tone calibrated to his profile.
> No response. Exactly what the profile predicted."

**[0:20 — Run the SQL insert OR show follow_up already queued]**

Point to the follow_ups table on screen.

> "The system decided: escalate to a call.
> That instruction is sitting here. Watch what happens."

**[0:30 — Scheduler fires — call initiates]**

Phone rings on the table. Pick it up.

> "No button was pressed. The scheduler fired on its own."

**[0:38 — The call — act difficult]**

Be difficult. Use these lines:
- "I don't know what this is about."
- "I'm not paying anything."
- "Don't call me again."

Let the agent handle it for about 20 seconds.
The voice adapts. Stays professional. Does not threaten.

**[0:58 — End the call]**

Say "goodbye" — the end call phrase triggers.

**[1:05 — Show profile delta on screen]**

> "Call ended. Profile updated automatically.
> Outcome: refused engagement.
> Risk score moved up. New signal added."

**[1:12 — Show escalation to human]**

> "The system escalated to human — not because it failed,
> because it knew when to stop.
> Here is the briefing it generated for the human agent."

Show the briefing text on screen.

**[1:20 — Close]**

> "Every decision logged. Every reasoning chain auditable.
> This is not a collections tool.
> It is a behavioral intelligence layer.
> Swap the voice. Keep the brain.
> It works anywhere."

---

### IF SOMETHING BREAKS

**Call does not fire:**
→ Manually curl: `curl -X POST https://miroir-hackathon-production.up.railway.app/vapi/call/10406975-6057-4bf6-bce2-eb8f376ef1c6`
→ Say: "Let me trigger it directly via API" — still impressive

**Call fires but voice is bad:**
→ Keep going. The transcript is what matters. Point to it on screen.

**Profile does not update:**
→ Show the interaction log. "Transcript saved. Profile analysis runs async."
→ Refresh after 10 seconds.

**Total failure:**
→ Open the decisions table in Supabase.
→ Show the reasoning from the evaluation engine.
→ "This is the audit trail. Every decision, every confidence score, every reasoning chain. Permanently logged."
→ That alone is enough to win.

---

### THE ONE LINE THAT WINS

> "It knew when to stop. That is the intelligence."
