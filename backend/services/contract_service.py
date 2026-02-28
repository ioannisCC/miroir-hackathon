"""
backend/services/contract_service.py

ContractService: analyzes contract PDFs via Claude vision.
Extracts structured data and maps signals to behavioral profile fields.
"""

import base64
import json
import re

import anthropic

from backend.core.config import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are a contract intelligence analyst. Extract structured data from contracts.

RULES:
- Only extract what is explicitly present in the document
- If a field is not found, use null
- Dates must be in ISO format (YYYY-MM-DD) where possible
- Amounts must be numeric (no currency symbols in the number field)
- Be precise about signatures and stamps — look carefully

Return JSON only. No markdown. No preamble.
""".strip()


class ContractService:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model

    def analyze(self, pdf_bytes: bytes, filename: str = "contract.pdf") -> dict:
        """
        Analyze a contract PDF. Returns structured extraction + behavioral signals.
        """
        logger.info("Analyzing contract: %s (%d bytes)", filename, len(pdf_bytes))

        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode()

        prompt = """
Analyze this contract document and extract all available information.

Return this exact JSON structure:
{
  "parties": [
    {"name": "<party name>", "role": "<buyer/seller/lender/borrower/other>"}
  ],
  "dates": {
    "contract_date": "<ISO date or null>",
    "effective_date": "<ISO date or null>",
    "expiry_date": "<ISO date or null>",
    "payment_due_date": "<ISO date or null>"
  },
  "amounts": [
    {"description": "<what this amount is for>", "value": <number>, "currency": "<currency code>"}
  ],
  "language": "<detected language>",
  "signed": <true/false/null>,
  "stamped": <true/false/null>,
  "signature_count": <number or null>,
  "red_flags": [
    {"flag": "<description of concern>", "severity": <0.0-1.0>}
  ],
  "summary": "<2-3 sentences: what this contract is about and key obligations>",
  "behavioral_signals": {
    "late_signature_risk": <0.0-1.0 or null>,
    "follow_through_signal": "<what contract terms suggest about follow-through>",
    "risk_notes": "<any patterns suggesting payment risk>"
  }
}

Red flags include: missing signatures, missing stamps, expired dates, unusual clauses,
inconsistent party information, missing payment terms.
""".strip()

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }],
            )
        except anthropic.APIError as e:
            logger.error("Claude API error analyzing contract %s: %s", filename, e)
            raise

        if not response.content:
            raise ValueError(f"Claude returned empty response for contract {filename}")

        logger.info(
            "Contract analyzed: %s — input: %d output: %d tokens",
            filename,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        raw = response.content[0].text
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse contract JSON: %s\nRaw: %s", e, raw[:300])
            raise ValueError(f"Invalid JSON from contract analysis: {e}") from e

    def map_to_profile_signals(self, analysis: dict) -> dict:
        """
        Map contract analysis to behavioral profile signal updates.
        Used to enrich a contact's behavior_profile in Supabase.
        """
        signals = analysis.get("behavioral_signals", {})
        red_flags = analysis.get("red_flags", [])

        risk_indicators = []
        for flag in red_flags:
            risk_indicators.append({
                "signal": flag.get("flag"),
                "severity": flag.get("severity", 0.5),
                "source": "contract_analysis",
            })

        # Missing signature is a strong follow-through signal
        if analysis.get("signed") is False:
            risk_indicators.append({
                "signal": "Contract unsigned — pattern of incomplete commitments",
                "severity": 0.8,
                "source": "contract_analysis",
            })

        if analysis.get("stamped") is False:
            risk_indicators.append({
                "signal": "Contract unstamped — may indicate informal agreement handling",
                "severity": 0.5,
                "source": "contract_analysis",
            })

        return {
            "contract_risk_indicators": risk_indicators,
            "follow_through_signal": signals.get("follow_through_signal", ""),
            "contract_risk_notes": signals.get("risk_notes", ""),
            "late_signature_risk": signals.get("late_signature_risk"),
        }