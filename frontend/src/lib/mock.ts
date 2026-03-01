// UI constants & demo placeholders for features not yet wired to real-time
// backend streams (live transcript, agent thinking). Everything else comes
// from real API endpoints — see lib/api.ts.

// ---------------------------------------------------------------------------
// Action labels & override reasons (UI display helpers)
// ---------------------------------------------------------------------------

export const ACTION_LABELS: Record<string, string> = {
  send_email: 'Send Email',
  send_sms: 'Send SMS',
  escalate_to_call: 'Escalate to Call',
  escalate_to_human: 'Escalate to Human',
  schedule_followup: 'Schedule Follow-up',
  close_resolved: 'Close — Resolved',
  close_refused: 'Close — Refused',
}

export const OVERRIDE_REASONS = [
  'Contact requested different timing',
  'Internal agreement already in place',
  'Relationship sensitivity',
  'Regulatory constraint',
  'Other',
]

// ---------------------------------------------------------------------------
// Demo placeholder: uploaded context files (shown before real uploads)
// ---------------------------------------------------------------------------

export const MOCK_CONTEXT_FILES: {
  name: string
  url: string
  key: string | null
  size: number
}[] = [
  {
    name: 'payment-history.csv',
    url: 'https://utfs.io/f/example-payment-history',
    key: 'example-key-1',
    size: 12_400,
  },
  {
    name: 'contract-amendment.pdf',
    url: 'https://utfs.io/f/example-contract',
    key: 'example-key-2',
    size: 245_000,
  },
  {
    name: 'email-thread-2024.docx',
    url: 'https://utfs.io/f/example-email-thread',
    key: 'example-key-3',
    size: 38_200,
  },
]

// ---------------------------------------------------------------------------
// Demo placeholder: live transcript (no real-time websocket yet)
// ---------------------------------------------------------------------------

export const MOCK_LIVE_TRANSCRIPT: { speaker: string; text: string; ts: number }[] = [
  { speaker: 'Miroir', text: 'Good morning Mr. Kean. This is a call regarding your outstanding balance of €5,000 due today.', ts: 0 },
  { speaker: 'Kean', text: "I'm aware. I've been meaning to address this.", ts: 4000 },
  { speaker: 'Miroir', text: 'I appreciate that. Your deadline is today. Can we confirm a payment arrangement now?', ts: 8000 },
  { speaker: 'Kean', text: "I'll need to speak with my team first.", ts: 13000 },
  { speaker: 'Miroir', text: 'Understood. To avoid further escalation I need a commitment by 5pm today. Can you confirm a specific amount?', ts: 17000 },
  { speaker: 'Kean', text: 'Fine. I can arrange €2,500 by end of day.', ts: 23000 },
  { speaker: 'Miroir', text: "Confirmed. €2,500 by 5pm today. I'll send a payment link now. Thank you Mr. Kean.", ts: 27000 },
]

// ---------------------------------------------------------------------------
// Demo placeholder: agent thinking stream during call
// ---------------------------------------------------------------------------

export const MOCK_DECISION_LOG: { ts: number; event: string; type: string }[] = [
  { ts: 500, event: 'Profile loaded — risk 0.52, reply speed 0.3', type: 'info' },
  { ts: 4500, event: 'Contact engaging — monitoring tone', type: 'positive' },
  { ts: 9000, event: 'Soft stalling detected — applying deadline pressure', type: 'warning' },
  { ts: 14000, event: 'Deflection to team — holding firm position', type: 'warning' },
  { ts: 18000, event: 'Concrete deadline issued — confidence 0.79', type: 'action' },
  { ts: 24000, event: 'Partial commitment received — €2,500', type: 'positive' },
  { ts: 28000, event: 'Outcome: promise_to_pay — updating profile', type: 'action' },
]
