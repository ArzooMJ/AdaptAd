"""
Session simulation routes.

POST /api/simulate/session       Run a full streaming session simulation.
GET  /api/simulate/status/{id}   Get simulation status (for async runs).
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..agents.user_advocate import score_user_advocate
from ..agents.advertiser_advocate import score_advertiser_advocate
from ..agents.negotiator import negotiate
from ..simulation.session import simulate_session, apply_decision
from ..simulation.fatigue import should_force_suppress
from ..simulation.breaks import get_scored_break_points
from ..simulation.binge import get_binge_summary
from ..state import AdDecision, Chromosome, Season, TimeOfDay
from .routes_data import get_users, get_ads, get_content
from .routes_decide import get_chromosome

router = APIRouter(prefix="/api/simulate", tags=["simulate"])

_simulation_results: dict[str, dict] = {}


class SimulateRequest(BaseModel):
    user_id: int
    content_id: int
    time_of_day: TimeOfDay = TimeOfDay.evening
    season: Season = Season.Fall
    binge_queue_content_ids: list[int] = []
    use_llm: bool = False
    chromosome_genes: Optional[list[float]] = None
    seed: Optional[int] = None


@router.post("/session")
def simulate_session_route(req: SimulateRequest):
    users = get_users()
    content_items = get_content()
    ads = get_ads()

    user = next((u for u in users if u.id == req.user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {req.user_id} not found.")

    content = next((c for c in content_items if c.id == req.content_id), None)
    if not content:
        raise HTTPException(status_code=404, detail=f"Content {req.content_id} not found.")

    content_queue = [c for c in content_items if c.id in req.binge_queue_content_ids]

    if req.chromosome_genes and len(req.chromosome_genes) == 8:
        chromosome = Chromosome.from_vector(req.chromosome_genes)
    else:
        chromosome = get_chromosome()

    # Generate opportunities.
    opportunities, final_ctx = simulate_session(
        user=user,
        content=content,
        ad_pool=ads,
        content_queue=content_queue,
        time_of_day=req.time_of_day,
        season=req.season,
        seed=req.seed,
    )

    if not opportunities:
        return {
            "session_id": str(uuid.uuid4()),
            "user_id": req.user_id,
            "content_id": req.content_id,
            "break_points": [],
            "decisions": [],
            "summary": {
                "total_breaks": 0,
                "ads_shown": 0,
                "final_fatigue": user.fatigue_level,
                "decision_counts": {d.value: 0 for d in AdDecision},
            },
        }

    # Run decisions in sequence, threading live context forward.
    session_id = str(uuid.uuid4())
    running_ctx = opportunities[0].session_context.model_copy()
    decision_records = []
    decision_counts = {d.value: 0 for d in AdDecision}
    prev_minute = 0

    for opp in opportunities:
        live_ctx = running_ctx.model_copy(
            update={"current_minute": opp.session_context.current_minute}
        )
        live_opp = opp.model_copy(update={"session_context": live_ctx})

        if should_force_suppress(live_ctx):
            decision = AdDecision.SUPPRESS
            from datetime import datetime
            from ..state import AgentScore, NegotiationResult
            ua = AgentScore(
                agent_name="User Advocate", score=0.0,
                reasoning="Force suppressed: fatigue ceiling reached.", factors={}
            )
            adv = AgentScore(
                agent_name="Advertiser Advocate", score=0.0,
                reasoning="Force suppressed: fatigue ceiling reached.", factors={}
            )
            result = NegotiationResult(
                decision=decision, user_advocate=ua, advertiser_advocate=adv,
                combined_score=0.0, reasoning="Fatigue > 0.85. Forced suppress.",
                timestamp=datetime.utcnow(), session_id=session_id,
                user_id=user.id, ad_id=opp.ad_candidate.id,
            )
        else:
            ua = score_user_advocate(user, opp.ad_candidate, live_ctx, chromosome)
            adv = score_advertiser_advocate(user, opp.ad_candidate, live_ctx, chromosome)
            result = negotiate(ua, adv, chromosome, user.id, opp.ad_candidate.id, session_id)

        decision_counts[result.decision.value] += 1
        minutes_gap = max(0, opp.session_context.current_minute - prev_minute)
        running_ctx = apply_decision(running_ctx, user, result.decision, opp.session_context.current_minute, minutes_gap)
        prev_minute = opp.session_context.current_minute

        # Score quality of the break point.
        bp_scores = get_scored_break_points(content)
        bp_quality = next((s for m, s in bp_scores if m == opp.session_context.current_minute), None)

        decision_records.append({
            "break_minute": opp.session_context.current_minute,
            "break_point_quality": bp_quality,
            "ad_id": opp.ad_candidate.id,
            "ad_category": opp.ad_candidate.category,
            "ad_duration": opp.ad_candidate.duration_seconds,
            "decision": result.decision.value,
            "combined_score": result.combined_score,
            "user_advocate_score": result.user_advocate.score,
            "advertiser_advocate_score": result.advertiser_advocate.score,
            "reasoning": result.reasoning,
            "fatigue_at_break": round(running_ctx.session_fatigue_accumulator, 4),
            "ads_shown_before": live_ctx.ads_shown_this_session,
        })

    binge_info = get_binge_summary(user, episodes_watched=0, content_queue=content_queue)

    response = {
        "session_id": session_id,
        "user_id": req.user_id,
        "content_id": req.content_id,
        "content_title": content.title,
        "content_duration_minutes": content.duration_minutes,
        "break_points": sorted([r["break_minute"] for r in decision_records]),
        "decisions": decision_records,
        "binge_info": binge_info,
        "summary": {
            "total_breaks": len(decision_records),
            "ads_shown": decision_counts.get("SHOW", 0) + decision_counts.get("SOFTEN", 0),
            "final_fatigue": round(running_ctx.session_fatigue_accumulator, 4),
            "decision_counts": decision_counts,
        },
        "chromosome_genes": chromosome.to_vector(),
    }
    _simulation_results[session_id] = response
    return response


@router.get("/status/{session_id}")
def get_simulation_status(session_id: str):
    if session_id not in _simulation_results:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found.")
    return _simulation_results[session_id]
