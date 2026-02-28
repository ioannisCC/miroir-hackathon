// Mock data — no backend integration. Types inferred from usage.

export type Interaction = {
  id: string
  type: string
  summary: string
  timestamp: string
  outcome: string | null
}

export type Decision = {
  approach_chosen: string
  reasoning: string
  confidence_score: number
  confidence_notes: string
  escalate: boolean
  pass1_reasoning: string
  pass2_reasoning: string
}

export type TranscriptEntry = {
  speaker: string
  text: string
  ts: number
}

export type DecisionLogEntry = {
  ts: number
  event: string
  type: string
}

export type AuditCheck = { rule: string; pass: boolean }

export type Audit = {
  duration: string
  outcome: string
  checks: AuditCheck[]
}

export type MockContextFile = {
  name: string
  url: string
  key: string | null
  size: number
}

/** Mock uploaded context files for display (e.g. on contact detail page). */
export const MOCK_CONTEXT_FILES: MockContextFile[] = [
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
// Contacts (id for routes; email for interactions/decisions)
// ---------------------------------------------------------------------------

export type MockContact = {
  id: string
  name: string
  email: string
  behavior_profile: Record<string, unknown>
  risk_score?: number
  trust_score?: number
}

export const MOCK_CONTACTS: MockContact[] = [
  { id: 'steven-kean', name: 'Steven Kean', email: 'steven.kean@enron.com', behavior_profile: { summary: 'Selective non-responder. Reply speed 0.3. Two emails sent, zero response.', psychological_profile: 'Selective non-responder with low reply speed (0.3). Two emails sent, zero response so far. Tends to avoid direct engagement and may need repeated, clear prompts. Best approached with concise, factual messaging and explicit deadlines. Follow-through score suggests moderate reliability once committed.', reply_speed_score: 0.3, follow_through_score: 0.4 }, risk_score: 0.52, trust_score: 0.45 },
  { id: 'jeff-dasovich', name: 'Jeff Dasovich', email: 'jeff.dasovich@enron.com', behavior_profile: { summary: 'Cooperative. Promise to pay received. Warm, relationship-driven.', psychological_profile: 'Cooperative and relationship-driven. Has already signalled willingness to pay; responds well to warmth and acknowledgment of his situation. Trust score is high (0.70). Communication should be supportive and clear, reinforcing the agreed plan rather than applying pressure.', trust_score: 0.70 }, risk_score: 0.2, trust_score: 0.70 },
  { id: 'vince-kaminski', name: 'Vince Kaminski', email: 'vince.kaminski@enron.com', behavior_profile: { summary: 'Hierarchical communicator. Responds to authority. Formal tone preferred.', psychological_profile: 'Hierarchical communicator who responds to authority and structure. Prefers formal tone and clear chain of command. References to policy, contracts, or official terms tend to land well. Avoid casual or overly friendly tone; keep messages professional and fact-based.', trust_score: 0.60 }, risk_score: 0.45, trust_score: 0.60 },
  { id: 'jeff-skilling', name: 'Jeff Skilling', email: 'jeff.skilling@enron.com', behavior_profile: { summary: 'Operates through assistant. High-status. Human judgment required.', psychological_profile: 'High-status contact who typically operates through an assistant. Direct outreach may be filtered; human judgment and discretion are required. Messaging should be suitable for delegation and avoid anything that could be perceived as pushy or informal. Escalation paths should be clear.', trust_score: 0.35 }, risk_score: 0.65, trust_score: 0.38 },
  { id: 'john-arnold', name: 'John Arnold', email: 'john.arnold@enron.com', behavior_profile: { summary: 'Direct, transactional. Brief, specific messages. No pleasantries.', psychological_profile: 'Direct and transactional. Prefers brief, specific messages with no unnecessary pleasantries. Reply speed is high (0.8); he engages when the ask is clear. Keep language tight, numbers and dates explicit, and avoid long explanations or relationship-building filler.', reply_speed_score: 0.8 }, risk_score: 0.35, trust_score: 0.70 },
]

export function getMockContactById(id: string): MockContact | undefined {
  return MOCK_CONTACTS.find((c) => c.id === id)
}

export function getMockContacts(): MockContact[] {
  return MOCK_CONTACTS
}

// ---------------------------------------------------------------------------
// Interactions (by contact email)
// ---------------------------------------------------------------------------

export const MOCK_INTERACTIONS: Record<string, Interaction[]> = {
  'steven.kean@enron.com': [
    { id: '1', type: 'email', summary: 'Initial payment reminder — formal tone', timestamp: '2026-02-20T09:00:00Z', outcome: null },
    { id: '2', type: 'email', summary: 'Second notice — deadline Feb 28 explicit', timestamp: '2026-02-24T09:00:00Z', outcome: null },
  ],
  'jeff.dasovich@enron.com': [
    { id: '3', type: 'email', summary: 'Soft reminder sent with payment link', timestamp: '2026-02-25T10:00:00Z', outcome: 'promise_to_pay' },
  ],
  'vince.kaminski@enron.com': [],
  'jeff.skilling@enron.com': [
    { id: '4', type: 'email', summary: 'Formal notice sent to Sherri Sera (assistant)', timestamp: '2026-02-22T11:00:00Z', outcome: null },
  ],
  'john.arnold@enron.com': [],
}

export function getMockInteractions(contactEmail: string): Interaction[] {
  return MOCK_INTERACTIONS[contactEmail] ?? []
}

// ---------------------------------------------------------------------------
// Decisions (by contact email)
// ---------------------------------------------------------------------------

export const MOCK_DECISIONS: Record<string, Decision> = {
  'steven.kean@enron.com': {
    approach_chosen: 'escalate_to_call',
    reasoning: 'Two emails sent. Zero response. Reply speed score 0.3 — consistent non-response pattern confirmed across 6 risk indicators. Hard rule satisfied: two emails completed. Final day of deadline. Recommend voice escalation with firm deadline framing.',
    confidence_score: 0.82,
    confidence_notes: 'High confidence. Pattern consistent. Contact has documented non-response history.',
    escalate: true,
    pass1_reasoning: 'Behavioral data alone suggests this contact selectively ignores written communication. Voice escalation is the only channel likely to generate response.',
    pass2_reasoning: 'Company guidelines confirm: two emails sent, deadline reached, confidence above 0.7 threshold. Escalate to call approved.',
  },
  'jeff.dasovich@enron.com': {
    approach_chosen: 'schedule_followup',
    reasoning: 'Contact responded positively. Trust score 0.70, zero risk indicators. Promise to pay received. Schedule follow-up in 48h to confirm payment received.',
    confidence_score: 0.91,
    confidence_notes: 'High confidence. Cooperative contact. Clear verbal commitment made.',
    escalate: false,
    pass1_reasoning: 'Warm, relationship-driven contact. Promise received. Follow-up is correct next step.',
    pass2_reasoning: 'Consistent with company workflow. No escalation needed. Follow-up scheduled.',
  },
  'vince.kaminski@enron.com': {
    approach_chosen: 'send_email',
    reasoning: 'First contact. Trust 0.60, moderate risk. Profile shows hierarchical communication pattern — responds to authority. Email must be formal, reference contractual obligation directly, avoid casual tone.',
    confidence_score: 0.74,
    confidence_notes: 'Medium-high confidence. First interaction — limited outcome data available.',
    escalate: false,
    pass1_reasoning: 'Hierarchical responder. Formal authority framing will be most effective.',
    pass2_reasoning: 'First contact. Company rules: email first. Confidence above 0.5 threshold. Proceed.',
  },
  'jeff.skilling@enron.com': {
    approach_chosen: 'escalate_to_human',
    reasoning: 'Contact operates exclusively through assistant. Direct email unlikely to reach decision maker. Failed to sign required documents previously. Confidence below 0.4 threshold — autonomous action not appropriate.',
    confidence_score: 0.38,
    confidence_notes: 'Low confidence. Assistant-mediated contact. Human operator judgment required.',
    escalate: true,
    pass1_reasoning: 'No direct communication channel. High-status contact requiring relationship management beyond algorithmic approach.',
    pass2_reasoning: 'Hard rule triggered: confidence below 0.4. Escalate to human mandatory.',
  },
  'john.arnold@enron.com': {
    approach_chosen: 'send_email',
    reasoning: 'First contact. Trust 0.70. Direct communication style — responds best to brief, specific, transactional messages. No pleasantries. State the amount, state the deadline, provide payment link.',
    confidence_score: 0.77,
    confidence_notes: 'Medium-high confidence. Profile strongly suggests direct approach effective.',
    escalate: false,
    pass1_reasoning: 'Trader profile. Concise, direct communication. Email should mirror his own style.',
    pass2_reasoning: 'First contact. Email appropriate. Confidence above threshold. Proceed.',
  },
}

export function getMockDecision(contactEmail: string): Decision | undefined {
  return MOCK_DECISIONS[contactEmail]
}

// ---------------------------------------------------------------------------
// Live transcript (e.g. during/listening to call)
// ---------------------------------------------------------------------------

export const MOCK_LIVE_TRANSCRIPT: TranscriptEntry[] = [
  { speaker: 'Miroir', text: 'Good morning Mr. Kean. This is a call regarding your outstanding balance of €5,000 due today.', ts: 0 },
  { speaker: 'Kean', text: "I'm aware. I've been meaning to address this.", ts: 4000 },
  { speaker: 'Miroir', text: 'I appreciate that. Your deadline is today. Can we confirm a payment arrangement now?', ts: 8000 },
  { speaker: 'Kean', text: "I'll need to speak with my team first.", ts: 13000 },
  { speaker: 'Miroir', text: 'Understood. To avoid further escalation I need a commitment by 5pm today. Can you confirm a specific amount?', ts: 17000 },
  { speaker: 'Kean', text: 'Fine. I can arrange €2,500 by end of day.', ts: 23000 },
  { speaker: 'Miroir', text: "Confirmed. €2,500 by 5pm today. I'll send a payment link now. Thank you Mr. Kean.", ts: 27000 },
]

// ---------------------------------------------------------------------------
// Decision log (during call — agent reasoning stream)
// ---------------------------------------------------------------------------

export const MOCK_DECISION_LOG: DecisionLogEntry[] = [
  { ts: 500, event: 'Profile loaded — risk 0.52, reply speed 0.3', type: 'info' },
  { ts: 4500, event: 'Contact engaging — monitoring tone', type: 'positive' },
  { ts: 9000, event: 'Soft stalling detected — applying deadline pressure', type: 'warning' },
  { ts: 14000, event: 'Deflection to team — holding firm position', type: 'warning' },
  { ts: 18000, event: 'Concrete deadline issued — confidence 0.79', type: 'action' },
  { ts: 24000, event: 'Partial commitment received — €2,500', type: 'positive' },
  { ts: 28000, event: 'Outcome: promise_to_pay — updating profile', type: 'action' },
]

// ---------------------------------------------------------------------------
// Post-call audit
// ---------------------------------------------------------------------------

export const MOCK_AUDIT: Audit = {
  duration: '4m 32s',
  outcome: 'promise_to_pay',
  checks: [
    { rule: 'Concrete next step proposed', pass: true },
    { rule: 'Profile updated after call', pass: true },
    { rule: 'No forbidden language detected', pass: true },
  ],
}

// ---------------------------------------------------------------------------
// Override reasons & action labels
// ---------------------------------------------------------------------------

export const OVERRIDE_REASONS = [
  'Contact requested different timing',
  'Internal agreement already in place',
  'Relationship sensitivity',
  'Regulatory constraint',
  'Other',
]

export const ACTION_LABELS: Record<string, string> = {
  send_email: 'Send Email',
  send_sms: 'Send SMS',
  escalate_to_call: 'Escalate to Call',
  escalate_to_human: 'Escalate to Human',
  schedule_followup: 'Schedule Follow-up',
  close_resolved: 'Close — Resolved',
  close_refused: 'Close — Refused',
}
