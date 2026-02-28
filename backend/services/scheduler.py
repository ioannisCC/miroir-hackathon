"""
backend/services/scheduler.py

Autonomous action scheduler.
Runs every minute. Checks follow_ups table for due actions.
Dormant until a follow_up row exists — the table is the switch.
"""

import asyncio
from datetime import datetime, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.logging import get_logger

logger = get_logger(__name__)
scheduler = AsyncIOScheduler()


async def _execute_due_action(follow_up: dict) -> None:
    settings = get_settings()
    db = get_db()
    contact_id = follow_up["contact_id"]
    action_type = follow_up["action_type"]
    follow_up_id = follow_up["id"]

    logger.info(
        "Scheduler firing — contact: %s action: %s",
        contact_id,
        action_type,
    )

    # Mark as processing immediately — prevents double fire
    db.table("follow_ups").update({
        "status": "processing",
    }).eq("id", follow_up_id).execute()

    try:
        async with httpx.AsyncClient(timeout=30.0) as http:

            if action_type == "send_email":
                r = await http.post(
                    f"{settings.backend_url}/contacts/{contact_id}/execute-action",
                    json={"action": "send_email"},
                )
                r.raise_for_status()

            elif action_type == "escalate_to_call":
                r = await http.post(
                    f"{settings.backend_url}/vapi/call/{contact_id}",
                )
                r.raise_for_status()

            elif action_type == "evaluate":
                # Run evaluation — engine decides what to do next
                r = await http.post(
                    f"{settings.backend_url}/decisions/evaluate/{contact_id}",
                )
                r.raise_for_status()

        # Mark done
        db.table("follow_ups").update({
            "status": "completed",
        }).eq("id", follow_up_id).execute()

        logger.info(
            "Scheduler action completed — contact: %s action: %s",
            contact_id,
            action_type,
        )

    except Exception as e:
        logger.error(
            "Scheduler action failed — contact: %s action: %s error: %s",
            contact_id,
            action_type,
            e,
        )
        # Mark failed — visible in table
        db.table("follow_ups").update({
            "status": "failed",
        }).eq("id", follow_up_id).execute()

        # Dead letter queue
        try:
            db.table("failed_actions").insert({
                "contact_id": contact_id,
                "action_type": action_type,
                "payload": follow_up,
                "error_message": str(e),
                "retry_count": 0,
                "status": "pending",
            }).execute()
        except Exception:
            pass


@scheduler.scheduled_job("interval", minutes=1)
async def autonomous_cycle():
    """
    Runs every minute.
    Table empty = does nothing.
    Row present with scheduled_at <= now = fires action.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    try:
        due = (
            db.table("follow_ups")
            .select("*")
            .eq("status", "pending")
            .lte("scheduled_at", now)
            .execute()
            .data
        )
    except Exception as e:
        logger.error("Scheduler failed to query follow_ups: %s", e)
        return

    if not due:
        return  # Silent — nothing to do

    logger.info("Scheduler — %d actions due", len(due))

    for follow_up in due:
        await _execute_due_action(follow_up)