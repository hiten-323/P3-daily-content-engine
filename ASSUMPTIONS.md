# Assumptions

What this system takes as true. If one breaks, the linked component degrades —
each row lists the blast radius and the detection signal.

| # | Assumption | If it breaks | Detected by |
|---|---|---|---|
| 1 | Instagram Graph API token stays valid (renewed every ~59 days) | All IG publishing + insights stop | `[instagram] not_configured` / 401 in run logs; renewal reminder documented |
| 2 | Instagram ranks primarily by watch time + early engagement | Watch-time beat structure loses its edge | Follows-per-reach trend decays despite consistent output |
| 3 | Free-tier LLM quotas (Groq/Cerebras/OpenRouter) remain sufficient for ~6 calls/day | Generation falls to emergency content set | `any_provider_available()` false; fallback content in output |
| 4 | Shopify referring_site/landing_site reliably marks Instagram traffic | Revenue attribution undercounts IG | ig_orders stays 0 while IG traffic visibly grows |
| 5 | Day-level attribution is directionally correct over months | Learning optimizes for the wrong posts | Manual spot-check: winner posts vs order dates |
| 6 | GitHub Actions cron fires within ~15 min of schedule | Posts miss optimal windows | Actions run timestamps vs cron times |
| 7 | Repo-as-database stays manageable (learning JSON + 7-day image retention) | Repo bloat, slow checkouts | Repo size trend; tighten retention if >1GB |
| 8 | The founder produces reel videos from daily tool briefs | Evening slot posts thumbnails, not videos — reels underperform images | `output/ugc/tool_brief_*.json` untouched |
| 9 | Engagement-score weights (revenue 1/₹, order 25, follow 10) reflect real business value | Learning promotes wrong content | Revisit when ≥30 posts have revenue data |
| 10 | 105-follower account benefits most from 95% non-branded viral content | Growth stalls despite reach | IGNITION stage gate unmet after 8+ weeks |
| 11 | Meta doesn't materially change insights metric names (views/reach/saved…) | Insights fetch returns None, learning starves | `[insights] Graph API call failed` in logs; fallback metric set exists |
| 12 | One brand + growth reel per day is enough volume to learn from | Slow learning convergence | <12 samples after a month → optimizer never activates |

Review cadence: check this table monthly against run logs; move broken
assumptions to UNKNOWNS.md with a mitigation plan.
