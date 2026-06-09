"""
WhatsApp Business API integration — AiSensy primary, Meta Cloud API fallback.

Provider priority:
  1. AiSensy (aisensy.com)    — Simpler API, no template pre-approval needed for
                                 utility/marketing messages.
                                 Env: AISENSY_API_KEY
                                 Secret: AISENSY_API_KEY

  2. Meta Cloud API (direct)  — Full feature set, requires template pre-approval
                                 in Meta Business Manager.
                                 Env: WHATSAPP_TOKEN + WHATSAPP_PHONE_ID

  3. Dry-run / log-only       — Falls through if neither is configured.

Usage:
    from content_generator.nurture.whatsapp import send_message

    result = send_message(
        contact="+919876543210",
        text="Hi Rajesh, following up on your Purity Beans inquiry!",
        lead_id="lead_001",
        segment="distributor",
        stage="inquiry",
    )

Template mode (Meta API only):
    result = send_message(
        contact="+919876543210",
        template_name="distributor_follow_up",
        params={"name": "Rajesh", "region": "South Mumbai"},
    )

Notes:
  - Indian numbers are auto-converted to E.164 (+91XXXXXXXXXX)
  - All sends are rate-limited (5 concurrent) and logged to nurture_log table
"""
from __future__ import annotations
import logging
import os
import time
import threading

logger = logging.getLogger(__name__)

_SEMAPHORE = threading.Semaphore(5)   # max 5 concurrent sends

_META_BASE_URL   = "https://graph.facebook.com/v18.0"
_AISENSY_API_URL = "https://backend.aisensy.com/campaign/t1/api/v2"


def is_configured() -> bool:
    """Return True if any WhatsApp provider is configured."""
    return bool(os.getenv("AISENSY_API_KEY")) or (
        bool(os.getenv("WHATSAPP_TOKEN")) and bool(os.getenv("WHATSAPP_PHONE_ID"))
    )


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

    Provider selection:
      - AISENSY_API_KEY set   → uses AiSensy (text messages work without template pre-approval)
      - WHATSAPP_TOKEN set    → uses Meta Cloud API (template_name required for cold messages)

    Returns:
        {"success": bool, "message_id": str, "error": str|None, "provider": str}
    """
    if not contact:
        return {"success": False, "message_id": "", "error": "no_contact", "provider": "none"}

    if not text and not template_name:
        return {"success": False, "message_id": "", "error": "no_content", "provider": "none"}

    phone = _normalise_phone(contact)

    with _SEMAPHORE:
        # 1. AiSensy
        if os.getenv("AISENSY_API_KEY"):
            result = _aisensy_send(phone, text or "", template_name, params or {})
            result["provider"] = "aisensy"
        # 2. Meta Cloud API
        elif os.getenv("WHATSAPP_TOKEN") and os.getenv("WHATSAPP_PHONE_ID"):
            if template_name:
                result = _meta_send_template(phone, template_name, params or {})
            else:
                result = _meta_send_text(phone, text or "")
            result["provider"] = "meta"
        else:
            logger.warning(
                "[whatsapp] Not configured — set AISENSY_API_KEY or "
                "WHATSAPP_TOKEN+WHATSAPP_PHONE_ID"
            )
            return {"success": False, "message_id": "", "error": "not_configured", "provider": "none"}

    _log_nurture(lead_id, segment, stage, "whatsapp", result)
    return result


# ── Provider 1: AiSensy ───────────────────────────────────────────────────────

def _aisensy_send(
    phone: str,
    text: str,
    template_name: str | None,
    params: dict,
) -> dict:
    """
    Send via AiSensy API.

    AiSensy supports both template and session messages through a single endpoint.
    For template messages: provide template_name and params.
    For text messages: provide text only (works within 24h session window).

    Docs: https://help.aisensy.com/api-documentation
    """
    try:
        import requests
    except ImportError:
        return {"success": False, "message_id": "", "error": "requests_not_installed"}

    api_key = os.getenv("AISENSY_API_KEY", "")

    if template_name:
        # Template message via AiSensy
        payload = {
            "apiKey":          api_key,
            "campaignName":    template_name,
            "destination":     phone,
            "userName":        "Purity Beans",
            "templateParams":  list(params.values()) if params else [],
            "source":          "purity-beans-engine",
            "media":           {},
        }
    else:
        # Session/text message via AiSensy
        payload = {
            "apiKey":      api_key,
            "campaignName": "purity_beans_nurture",
            "destination":  phone,
            "userName":    "Purity Beans",
            "templateParams": [text],
            "source":      "purity-beans-engine",
            "media":       {},
            "buttons":     [],
            "carouselCards": [],
        }

    try:
        resp = requests.post(_AISENSY_API_URL, json=payload, timeout=15)
        data = resp.json() if resp.content else {}

        if resp.status_code in (200, 201):
            msg_id = str(data.get("messageId", data.get("id", "")))
            logger.info("[whatsapp/aisensy] Sent to %s | id=%s | campaign=%s",
                        phone, msg_id, template_name or "session")
            return {"success": True, "message_id": msg_id, "error": None}
        else:
            err = data.get("message") or data.get("error") or f"HTTP {resp.status_code}"
            logger.warning("[whatsapp/aisensy] Send failed: %s", err)
            return {"success": False, "message_id": "", "error": err}

    except Exception as e:
        logger.error("[whatsapp/aisensy] Request error: %s", e)
        return {"success": False, "message_id": "", "error": str(e)}


# ── Provider 2: Meta Cloud API ────────────────────────────────────────────────

def _meta_send_template(phone: str, template_name: str, params: dict) -> dict:
    """Send a pre-approved WhatsApp template via Meta Cloud API."""
    try:
        import requests
    except ImportError:
        return {"success": False, "message_id": "", "error": "requests_not_installed"}

    token    = os.getenv("WHATSAPP_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
    url      = f"{_META_BASE_URL}/{phone_id}/messages"

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
            "name":       template_name,
            "language":   {"code": "en"},
            "components": components,
        },
    }

    try:
        resp = requests.post(
            url, json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=15,
        )
        data = resp.json()
        if resp.status_code == 200 and "messages" in data:
            msg_id = data["messages"][0].get("id", "")
            logger.info("[whatsapp/meta] Template '%s' sent to %s | id=%s",
                        template_name, phone, msg_id)
            return {"success": True, "message_id": msg_id, "error": None}
        else:
            err = data.get("error", {}).get("message", str(data))
            logger.warning("[whatsapp/meta] Template send failed: %s", err)
            return {"success": False, "message_id": "", "error": err}
    except Exception as e:
        logger.error("[whatsapp/meta] Request error: %s", e)
        return {"success": False, "message_id": "", "error": str(e)}


def _meta_send_text(phone: str, text: str) -> dict:
    """Send free-form text via Meta Cloud API (24h session window only)."""
    try:
        import requests
    except ImportError:
        return {"success": False, "message_id": "", "error": "requests_not_installed"}

    token    = os.getenv("WHATSAPP_TOKEN", "")
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
    url      = f"{_META_BASE_URL}/{phone_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type":    "individual",
        "to":                phone,
        "type":              "text",
        "text":              {"preview_url": False, "body": text},
    }

    try:
        resp = requests.post(
            url, json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=15,
        )
        data = resp.json()
        if resp.status_code == 200 and "messages" in data:
            msg_id = data["messages"][0].get("id", "")
            logger.info("[whatsapp/meta] Text sent to %s | id=%s", phone, msg_id)
            return {"success": True, "message_id": msg_id, "error": None}
        else:
            err = data.get("error", {}).get("message", str(data))
            logger.warning("[whatsapp/meta] Text send failed: %s", err)
            return {"success": False, "message_id": "", "error": err}
    except Exception as e:
        logger.error("[whatsapp/meta] Request error: %s", e)
        return {"success": False, "message_id": "", "error": str(e)}


# ── Shared helpers ────────────────────────────────────────────────────────────

def _normalise_phone(phone: str) -> str:
    """Convert Indian phone numbers to E.164 format (+91XXXXXXXXXX)."""
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
            channel=channel,
            template=f"{segment}/{stage}",
            status="sent" if result.get("success") else "failed",
            message_ref=result.get("message_id", ""),
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
