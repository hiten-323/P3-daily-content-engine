"""
Pipeline tracker — manages lead stage progression and computes velocity metrics.

Core operations:
  advance_stage()       — move a lead to the next stage (with event log)
  churn_lead()          — mark a lead as churned (with reason)
  close_deal()          — record a closed deal with revenue
  get_pipeline_report() — full pipeline health snapshot
  get_velocity()        — how fast are leads moving through the pipeline?

The pipeline report feeds directly into the dashboard and weekly summary,
and closes the content attribution loop by surfacing:
  "reel_1_day42 generated 3 distributor leads — 2 are now at trial_order stage
   — combined expected value: Rs 12,60,000"
"""
import datetime
import logging

logger = logging.getLogger(__name__)


def advance_stage(
    lead_id: str,
    notes: str     = "",
    revenue: float = 0.0,
) -> dict:
    """
    Move a lead to the next stage in its pipeline.

    Returns updated lead dict or raises ValueError if already terminal.

    Example:
        advance_stage("dist_20260609_001", notes="Sample dispatched to Nagpur")
        # dist_... moves from 'qualified' -> 'sample_sent'
    """
    from content_generator.analytics.metrics_store import get_leads, record_pipeline_event, upsert_lead
    from content_generator.leads.pipeline import get_next_stage

    leads = get_leads()
    lead  = next((l for l in leads if l["lead_id"] == lead_id), None)
    if not lead:
        raise ValueError(f"Lead not found: {lead_id}")

    segment       = lead["segment"]
    current_stage = lead["stage"]
    next_s        = get_next_stage(segment, current_stage)

    if next_s is None:
        raise ValueError(f"Lead {lead_id} is already at terminal stage '{current_stage}'")

    record_pipeline_event(
        lead_id=lead_id,
        from_stage=current_stage,
        to_stage=next_s,
        notes=notes,
        revenue=revenue,
    )

    logger.info(
        "[crm] %s advanced: %s -> %s (revenue=Rs%.0f)",
        lead_id, current_stage, next_s, revenue,
    )

    # If revenue provided, record against source content
    if revenue > 0 and lead.get("source_content"):
        try:
            from content_generator.analytics.metrics_store import record_revenue
            record_revenue(
                content_id=lead["source_content"],
                revenue=revenue,
                platform=lead.get("source_platform", "unknown"),
                audience=segment,
                event_type="pipeline_revenue",
            )
        except Exception as e:
            logger.warning("[crm] Revenue attribution failed: %s", e)

    return {**lead, "stage": next_s}


def churn_lead(lead_id: str, reason: str = "") -> None:
    """Mark a lead as churned with reason."""
    from content_generator.analytics.metrics_store import record_pipeline_event
    record_pipeline_event(
        lead_id=lead_id, to_stage="churned",
        notes=f"CHURNED: {reason}",
    )
    logger.info("[crm] %s churned: %s", lead_id, reason)


def close_deal(
    lead_id: str,
    revenue: float,
    notes: str = "",
) -> dict:
    """
    Record a closed deal — final revenue realised from this lead.

    Advances lead to 'active'/'reordering'/'loyal' and records full revenue.
    Attribution flows back to source content automatically.
    """
    from content_generator.analytics.metrics_store import get_leads
    from content_generator.leads.pipeline import PIPELINE_STAGES

    leads = get_leads()
    lead  = next((l for l in leads if l["lead_id"] == lead_id), None)
    if not lead:
        raise ValueError(f"Lead not found: {lead_id}")

    segment    = lead["segment"]
    # Find the "active" terminal stage for this segment
    stages     = PIPELINE_STAGES.get(segment, [])
    terminal_map = {
        "distributor":  "active",
        "modern_trade": "chain_listed",
        "retailer":     "reordering",
        "consumer":     "loyal",
    }
    terminal = terminal_map.get(segment, stages[-2] if len(stages) > 1 else stages[-1])

    from content_generator.analytics.metrics_store import record_pipeline_event, record_revenue
    record_pipeline_event(
        lead_id=lead_id,
        from_stage=lead["stage"],
        to_stage=terminal,
        notes=f"DEAL CLOSED — Rs {revenue:,.0f}. {notes}",
        revenue=revenue,
    )

    if lead.get("source_content"):
        record_revenue(
            content_id=lead["source_content"],
            revenue=revenue,
            platform=lead.get("source_platform", "unknown"),
            audience=segment,
            event_type="deal_closed",
        )

    logger.info(
        "[crm] DEAL CLOSED — %s | Rs %.0f | source=%s",
        lead_id, revenue, lead.get("source_content", "direct"),
    )

    return {
        "lead_id":        lead_id,
        "segment":        segment,
        "revenue_closed": revenue,
        "source_content": lead.get("source_content", ""),
        "final_stage":    terminal,
    }


def get_pipeline_report() -> dict:
    """
    Return a complete pipeline health snapshot.

    Output:
    {
        "total_leads":           52,
        "total_pipeline_ev":     Rs 47,32,000,
        "by_segment": {
            "distributor": { "inquiry": {count, ev}, "qualified": {...}, ... },
            ...
        },
        "hot_leads":             [...],
        "stalling_leads":        [...],
        "content_attribution":   [...top content pieces by leads generated],
    }
    """
    from content_generator.analytics.metrics_store import get_leads, get_pipeline_summary
    from content_generator.crm.value_calculator import get_pipeline_value, estimate_expected_value
    from content_generator.leads.lead_capture import get_hot_leads, get_stalling_leads

    all_leads = get_leads()
    summary   = get_pipeline_summary()
    pv        = get_pipeline_value(all_leads)

    # Enrich summary with EV per stage
    for seg, stages in summary.items():
        for stage, data in stages.items():
            ev_each = estimate_expected_value(seg, stage)
            data["ev_per_lead"] = ev_each
            data["total_ev"]    = round(ev_each * data["count"], 2)

    # Content attribution — which content generated most leads?
    content_leads: dict[str, dict] = {}
    for lead in all_leads:
        src = lead.get("source_content") or "direct"
        if src not in content_leads:
            content_leads[src] = {"content_id": src, "leads": 0, "total_ev": 0.0}
        content_leads[src]["leads"]    += 1
        content_leads[src]["total_ev"] += estimate_expected_value(
            lead["segment"], lead["stage"]
        )
    top_content = sorted(content_leads.values(), key=lambda x: x["total_ev"], reverse=True)[:10]

    return {
        "total_leads":        len(all_leads),
        "total_pipeline_ev":  pv["total_ev"],
        "by_segment":         summary,
        "pipeline_by_segment": pv["by_segment"],
        "hot_leads":          get_hot_leads(limit=5),
        "stalling_leads":     get_stalling_leads()[:5],
        "content_attribution": top_content,
    }


def get_velocity(segment: str = None, days: int = 30) -> list[dict]:
    """
    Return stage velocity — average days spent in each stage.
    Helps identify where the pipeline is blocking.
    """
    from content_generator.analytics.metrics_store import _ensure_init, _conn
    import sqlite3

    _ensure_init()
    clause = "AND l.segment=?" if segment else ""
    params = [segment] if segment else []

    with _conn() as con:
        rows = con.execute(f"""
            SELECT
                l.segment,
                pe.from_stage,
                pe.to_stage,
                COUNT(*) AS transitions,
                AVG(
                    CAST(
                        (julianday(pe.created_at) -
                         julianday(lag_event.created_at)) AS REAL
                    )
                ) AS avg_days_in_stage
            FROM pipeline_events pe
            JOIN leads l ON pe.lead_id = l.lead_id
            LEFT JOIN pipeline_events lag_event
                ON lag_event.lead_id = pe.lead_id
                AND lag_event.to_stage = pe.from_stage
            WHERE pe.from_stage != '' {clause}
            GROUP BY l.segment, pe.from_stage
            ORDER BY l.segment, pe.from_stage
        """, params).fetchall()
    return [dict(r) for r in rows]
