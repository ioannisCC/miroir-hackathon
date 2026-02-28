-- Run this in Supabase SQL Editor (https://supabase.com/dashboard → SQL Editor)

CREATE TABLE IF NOT EXISTS company_guidelines (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    call_rules text NOT NULL DEFAULT '',
    email_rules text NOT NULL DEFAULT '',
    evaluation_rules text NOT NULL DEFAULT '',
    hard_rules jsonb NOT NULL DEFAULT '[]'::jsonb,
    general_context text NOT NULL DEFAULT '',
    updated_at timestamptz DEFAULT now()
);

-- Seed with demo data
INSERT INTO company_guidelines (call_rules, email_rules, evaluation_rules, hard_rules, general_context)
VALUES (
    E'Never threaten legal action.\nNever be aggressive or demeaning.\nKeep responses under 3 sentences — this is a voice call.\nDrive toward one specific outcome: a payment commitment with a date.\nIf the contact indicates financial hardship (not just refusal to pay), proactively offer installment payment plans.\nIf contact stalls, introduce a specific deadline calmly.\nAlways say amounts as natural spoken words — say "five thousand euros" not "5,000".\nIf contact is cooperative, reward with flexibility — offer extended timelines.',

    E'Adapt tone entirely to the contact''s behavioral profile.\nNever threaten legal action.\nNever use aggressive or demeaning language.\nNever create false urgency or fabricate deadlines.\nNever imply consequences you cannot deliver.\nBe specific — reference the debt amount and any prior contact.\nKeep it under 200 words.\nEnd with a clear single call to action.\nSign as [Agent Name] — never impersonate a specific person.\nIf prior interactions suggest financial hardship, mention installment options in the email.',

    E'Always escalate to human if confidence is below 0.4.\nCannot escalate to call until at least 2 emails have been sent.\nNo outbound contact before 09:00 or after 18:00 contact local time.\nOn the final day of a payment deadline, escalate to call regardless of email count.\nLegal threats require human approval before sending.\nIf debtor shows signs of financial hardship (not mere refusal), recommend offering installment plans before escalating.',

    '[
      {"id": "never_call_before_two_emails", "description": "Cannot escalate to call until at least 2 emails have been sent", "enabled": true},
      {"id": "never_threaten_legal_action_without_approval", "description": "Legal threats require human approval before sending", "enabled": true},
      {"id": "never_contact_outside_business_hours", "description": "No outbound contact before 09:00 or after 18:00 local time", "enabled": true},
      {"id": "always_escalate_to_human_if_low_confidence", "description": "If confidence score is below 0.4, always escalate to human", "enabled": true},
      {"id": "always_call_on_final_deadline_day", "description": "On the final day of a payment deadline, escalate to call regardless of email count", "enabled": true},
      {"id": "offer_installments_on_hardship", "description": "If debtor indicates financial hardship, offer installment payment plans before further escalation", "enabled": true}
    ]'::jsonb,

    E'We are Miroir, a professional debt collection service. We use behavioral intelligence to adapt our approach to each debtor. Our goal is resolution, not confrontation. We prefer payment plans over escalation. We treat every contact with dignity and respect.'
);
