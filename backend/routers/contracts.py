"""
backend/routers/contracts.py

Contract intelligence endpoints.
POST /contracts/analyze — analyze a contract PDF, return structured data.
POST /contracts/analyze/{contact_id} — analyze and link signals to a contact profile.
"""

from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.core.database import get_db
from backend.core.logging import get_logger
from backend.services.contract_service import ContractService

logger = get_logger(__name__)
router = APIRouter()


@router.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    """
    Analyze a contract PDF. Returns structured extraction.
    No contact linkage — standalone analysis.
    """
    if not file.filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Only PDF and image files supported")

    try:
        pdf_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    try:
        service = ContractService()
        result = service.analyze(pdf_bytes, file.filename)
        return result
    except Exception as e:
        logger.error("Contract analysis failed for %s: %s", file.filename, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{contact_id}")
async def analyze_and_link(contact_id: UUID, file: UploadFile = File(...)):
    """
    Analyze a contract and update the linked contact's behavioral profile
    with extracted risk signals.
    """
    if not file.filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Only PDF and image files supported")

    db = get_db()

    # Load contact
    try:
        contact = (
            db.table("contacts")
            .select("*")
            .eq("id", str(contact_id))
            .single()
            .execute()
            .data
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Contact not found: {e}")

    try:
        pdf_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    try:
        service = ContractService()
        analysis = service.analyze(pdf_bytes, file.filename)
        profile_signals = service.map_to_profile_signals(analysis)
    except Exception as e:
        logger.error("Contract analysis failed for %s: %s", file.filename, e)
        raise HTTPException(status_code=500, detail=str(e))

    # Merge contract signals into existing behavior_profile
    try:
        existing_profile = contact.get("behavior_profile", {})
        existing_risk = existing_profile.get("risk_indicators", [])
        contract_risks = profile_signals.get("contract_risk_indicators", [])

        # Merge — avoid duplicates by source
        existing_non_contract = [
            r for r in existing_risk
            if (r.get("source") if isinstance(r, dict) else "") != "contract_analysis"
        ]
        merged_risk = existing_non_contract + contract_risks

        updated_profile = {
            **existing_profile,
            "risk_indicators": merged_risk,
            "contract_follow_through_signal": profile_signals.get("follow_through_signal"),
            "contract_risk_notes": profile_signals.get("contract_risk_notes"),
        }

        # Recompute risk score
        if merged_risk:
            total_severity = sum(
                r.get("severity", 0.5) if isinstance(r, dict) else 0.5
                for r in merged_risk
            )
            new_risk_score = round(min(total_severity / 5.0, 1.0), 2)
        else:
            new_risk_score = contact.get("risk_score", 0.2)

        db.table("contacts").update({
            "behavior_profile": updated_profile,
            "risk_score": new_risk_score,
        }).eq("id", str(contact_id)).execute()

        logger.info(
            "Contract signals merged for %s — new risk_score: %.2f",
            contact.get("email"),
            new_risk_score,
        )
    except Exception as e:
        logger.error("Failed to update contact profile: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "analysis": analysis,
        "profile_signals": profile_signals,
        "contact_id": str(contact_id),
        "updated_risk_score": new_risk_score,
    }