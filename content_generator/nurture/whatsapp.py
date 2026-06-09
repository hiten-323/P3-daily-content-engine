"""
WhatsApp Business API integration — Meta Cloud API.

Sends template-based messages to leads via WhatsApp Business.

Requirements:
  pip install requests
  WHATSAPP_TOKEN=<Meta Cloud API token>
  WHATSAPP_PHONE_ID=<your WhatsApp Business phone number ID>

Usage:
    from content_generator.nurture.whatsapp import send_message

    result = send_message(
        contact="+919876543210",
        template_name="distributor_inquiry",
        params={"name": "Rajesh", "region": "South Mumbai"},
    )

Template-free mode (text):
    result = send_message(
        contact="+919876543210",
        text="Hi Rajesh, following up on your Purity Beans inquiry!",
    )

Notes:
  - Meta Cloud API requires E.164 format: +91XXXXXXXXXX
  - Template messages require pre-approved templates in Meta Business Manager
  - Text messages can only be sent within 24h of last user-initiated message
  - All calls are rate-limited and logged to nurture_log table
"""
from __future__ import annotations
import logging
import os
import time
import threading

logger = logging.getLogger(__name__)

# Rate limiter — WhatsApp Cloud API has per-minute limits
_SEMAPHORE = threading.Semaphore(5)   # max 5 concurrent sends

_BASE_URL = "https://graph.facebook.com/v18.0"


def is_configured() -> bool:
    """Return True if WhatsApp credentials are present."""
    return bool(os.getenv("WHATSAPP_TOKEN")) and bool(os.getenv("WHATSAPP_PHONE_ID"))


def send_message(
    contact: str,
    template_name: str | None = None,
    params: dict | None       = None,
    text: str | None          = None,
    lead_id: str              = "",
    segment: str              = "",
    stage: str                = "",
) -> dict:
    """
    Send a WhatsApp message to a contact.

    Priority: if template_name is given, sends a template message.
    Otherwise sends a free-form text message (requires 24h window).

    Returns:
        {"success": bool, "message_id": str, "error": str|None}
    """
    if not is_configured():
        logger.warning("[whatsapp] Not configured — WHATSAPP_TOKEN / WHATSAPP_PHONE_ID missing")
        return {"success": False, "message_id": "", "error": "not_configured"}

    if not contact:
        return {"success": False, "message_id": "", "error": "no_contact"}

    # Normalise to E.164
    phone = _normalise_phone(contact)

    with _SEMAPHORE:
        if template_name:
            result = _send_template(phone, template_name, params or {})
        elif text:
            result = _send_text(phone, text)
        else:
            return {"success": False, "message_id": "", "error": "no_content"}

    # Log to nurture_log regardless of outcome
    _log_nurture(lead_id, segment, stage, "whatsapp", result)

    return result


def _send_template(phone: str, template_name: str, params: dict) -> dict:
    """Send a pre-approved WhatsApp template message."""
    try:
        import requests
    except ImportError:
        logger.error("[whatsapp] requests not installed — pip install requests")
        return {"success": False, "message_id": "", "error": "requests_not_installed"}

    token    = os.getenv("WHATSAPP_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
    url      = f"{_BASE_URL}/{phone_id}/messages"

    # Build component parameters from params dict
    components = []
    if params:
        body_params = [{"type": "text", "text": str(v)} for v in params.values()]
        components  = [{"type": "body", "parameters": body_params}]

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                phone,
        "type":              "template",
        "template": {
            "name":     template_name,
            "language": {"code": "en"},
            "components": components,
        },
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        data = resp.json()

        if resp.status_code == 200 and "messages" in data:
            msg_id = data["messages"][0].get("id", "")
            logger.info("[whatsapp] Template '%s' sent to %s | id=%s", template_name, phone, msg_id)
            return {"success": True, "message_id": msg_id, "error": None}
        else:
            err = data.get("error", {}).get("message", str(data))
            logger.warning("[whatsapp] Template send failed: %s", err)
            return {"success": False, "message_id": "", "error": err}

    except Exception as e:
        logger.error("[whatsapp] Request error: %s", e)
        return {"success": False, "message_id": "", "error": str(e)}


def _send_text(phone: str, text: str) -> dict:
    """Send a free-form text message (only within 24h customer service window)."""
    try:
        import requests
    except ImportError:
        return {"success": False, "message_id": "", "error": "requests_not_installed"}

    token    = os.getenv("WHATSAPP_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
    url      = f"{_BASE_URL}/{phone_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                phone,
        "type":              "text",
        "text":              {"preview_url": False, "body": text},
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        data = resp.json()

        if resp.status_code == 200 and "messages" in data:
            msg_id = data["messages"][0].get("id", "")
            logger.info("[whatsapp] Text sent to %s | id=%s", phone, msg_id)
            return {"success": True, "message_id": msg_id, "error": None}
        else:
            err = data.get("error", {}).get("message", str(data))
            logger.warning("[whatsapp] Text send failed: %s", err)
            return {"success": False, "message_id": "", "error": err}

    except Exception as e:
        logger.error("[whatsapp] Request error: %s", e)
        return {"success": False, "message_id": "", "error": str(e)}


def _normalise_phone(phone: str) -> str:
    """Convert Indian phone numbers to E.164 format."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("0"):
        phone = "+91" + phone[1:]
    elif not phone.startswith("+"):
        phone = "+91" + phone
    return phone


def _log_nurture(
    lead_id: str, segment: str, stage: str,
    channel: str, result: dict,
) -> None:
    """Persist nurture send event to DB."""
    if not lead_id:
        return
    try:
        from content_generator.analytics.metrics_store import record_nurture_sent
        record_nurture_sent(
            lead_id=lead_id,
            segment=segment,
            stage=stage,
            channel=channel,
            success=result.get("success", False),
            message_id=result.get("message_id", ""),
        )
    except Exception as e:
        logger.debug("[whatsapp] Nurture log failed: %s", e)


# ── Batch dispatch ────────────────────────────────────────────────────────────

def dispatch_nurture_batch(
    leads: list[dict],
    dry_run: bool = False,
) -> list[dict]:
    """
    Dispatch WhatsApp nurture messages to a list of leads.

    Each lead dict must have: lead_id, segment, stage, contact, name.
    Uses the nurture template for (segment, stage).

    dry_run=True logs what would be sent without making API calls.

    Returns list of results per lead.
    """
    from content_generator.nurture.templates import render_template

    results = []
    for lead in leads:
        seg     = lead.get("segment", "consumer")
        stage   = lead.get("stage", "inquiry")
        contact = lead.get("contact", "")
        name    = lead.get("name", "")
        lead_id = lead.get("lead_id", "")

        tmpl = render_template(seg, stage, name=name)
        if not tmpl:
            logger.debug("[whatsapp] No template for (%s, %s) — skipping %s", seg, stage, lead_id)
            continue

        # Only dispatch WhatsApp if channel supports it
        if tmpl["channel"] not in ("whatsapp", "both"):
            continue

        if dry_run:
            logger.info(
                "[whatsapp] DRY RUN — would send to %s (%s) | template=(%s, %s)",
                contact, lead_id, seg, stage,
            )
            results.append({"lead_id": lead_id, "success": True, "dry_run": True})
            continue

        if not contact:
            logger.warning("[whatsapp] No contact for lead %s — skipping", lead_id)
            continue

        result = send_message(
            contact=contact,
            text=tmpl["body"],
            lead_id=lead_id,
            segment=seg,
            stage=stage,
        )
        results.append({"lead_id": lead_id, **result})

        # Polite rate limiting — 200ms between sends
        time.sleep(0.2)

    return results
