"""
Decision routes.

POST /api/decide          Single ad decision for one user + ad + context.
POST /api/decide/batch    Batch decisions for all users against one ad.
GET  /api/decide/{id}     Retrieve a specific decision result by log ID.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..agents.user_advocate import score_user_advocate
from ..agents.advertiser_advocate import score_advertiser_advocate
from ..agents.negotiator import negotiate
from ..agents.llm_reasoning import enrich_with_llm_reasoning
from ..ga.storage import load_best_chromosome
from ..simulation.fatigue import should_force_suppress
from ..state import (
    AdDecision,
    Chromosome,
    ContentItem,
    NegotiationResult,
    Season,
    SessionContext,
    TimeOfDay,
    UserProfile,
)
from .routes_data import get_users, get_ads, get_content

router = APIRouter(prefix="/api", tags=["decide"])

# In-memory decision log (fallback when DB unavailable).
_decision_log: dict[str, dict] = {}
_current_chromosome: Optional[Chromosome] = None


def get_chromosome() -> Chromosome:
    """Return the current best chromosome, loading from disk if needed."""
    global _current_chromosome
    if _current_chromosome is None:
        _current_chromosome = load_best_chromosome() or Chromosome()
    return _current_chromosome


class DecideRequest(BaseModel):
    user_id: int
    ad_id: str
    time_of_day: TimeOfDay = TimeOfDay.evening
    season: Season = Season.Fall
    ads_shown_this_session: int = 0
    session_fatigue: float = 0.0
    content_id: Optional[int] = None
    current_minute: int = 0
    is_binging: bool = False
    use_llm: bool = False
    chromosome_genes: Optional[list[float]] = None


class BatchDecideRequest(BaseModel):
    ad_id: str
    time_of_day: TimeOfDay = TimeOfDay.evening
    season: Season = Season.Fall
    ads_shown_this_session: int = 0
    session_fatigue: float = 0.0
    use_llm: bool = False


def _make_decision(
    user: UserProfile,
    ad,
    ctx: SessionContext,
    chromosome: Chromosome,
    use_llm: bool = False,
    session_id: str = "api",
) -> NegotiationResult:
    if should_force_suppress(ctx):
        from datetime import datetime
        from ..state import AgentScore
        dummy_ua = AgentScore(
            agent_name="User Advocate", score=0.0,
            reasoning="Force suppressed due to high fatigue.", factors={}
        )
        dummy_adv = AgentScore(
            agent_name="Advertiser Advocate", score=0.0,
            reasoning="Force suppressed due to high fatigue.", factors={}
        )
        return NegotiationResult(
            decision=AdDecision.SUPPRESS,
            user_advocate=dummy_ua,
            advertiser_advocate=dummy_adv,
            combined_score=0.0,
            reasoning="Session fatigue exceeds 0.85. Ad suppressed to protect viewer.",
            timestamp=datetime.utcnow(),
            session_id=session_id,
            user_id=user.id,
            ad_id=ad.id,
        )

    ua = score_user_advocate(user, ad, ctx, chromosome)
    adv = score_advertiser_advocate(user, ad, ctx, chromosome)
    result = negotiate(ua, adv, chromosome, user.id, ad.id, session_id)

    if use_llm:
        result = enrich_with_llm_reasoning(result, user, ad)

    return result


@router.post("/decide")
def decide(req: DecideRequest):
    users = get_users()
    ads = get_ads()
    content_items = get_content()

    user = next((u for u in users if u.id == req.user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {req.user_id} not found.")
    ad = next((a for a in ads if a.id == req.ad_id), None)
    if not ad:
        raise HTTPException(status_code=404, detail=f"Ad {req.ad_id} not found.")

    content_item = None
    if req.content_id is not None:
        content_item = next((c for c in content_items if c.id == req.content_id), None)

    ctx = SessionContext(
        time_of_day=req.time_of_day,
        season=req.season,
        ads_shown_this_session=req.ads_shown_this_session,
        current_minute=req.current_minute,
        content=content_item,
        is_binging=req.is_binging,
        session_fatigue_accumulator=req.session_fatigue,
    )

    if req.chromosome_genes and len(req.chromosome_genes) == 8:
        chromosome = Chromosome.from_vector(req.chromosome_genes)
    else:
        chromosome = get_chromosome()

    session_id = str(uuid.uuid4())
    result = _make_decision(user, ad, ctx, chromosome, use_llm=req.use_llm, session_id=session_id)

    result_dict = result.model_dump()
    result_dict["timestamp"] = result.timestamp.isoformat()
    _decision_log[session_id] = result_dict

    return result_dict


@router.post("/decide/batch")
def batch_decide(req: BatchDecideRequest):
    users = get_users()
    ads = get_ads()

    ad = next((a for a in ads if a.id == req.ad_id), None)
    if not ad:
        raise HTTPException(status_code=404, detail=f"Ad {req.ad_id} not found.")

    chromosome = get_chromosome()
    ctx_base = SessionContext(
        time_of_day=req.time_of_day,
        season=req.season,
        ads_shown_this_session=req.ads_shown_this_session,
        session_fatigue_accumulator=req.session_fatigue,
    )

    results = []
    decision_counts = {d.value: 0 for d in AdDecision}

    for user in users:
        session_id = f"batch_{user.id}"
        result = _make_decision(user, ad, ctx_base, chromosome, use_llm=False, session_id=session_id)
        decision_counts[result.decision.value] += 1
        results.append({
            "user_id": user.id,
            "user_name": user.name,
            "age_group": user.age_group,
            "decision": result.decision.value,
            "combined_score": result.combined_score,
            "user_advocate_score": result.user_advocate.score,
            "advertiser_advocate_score": result.advertiser_advocate.score,
        })

    return {
        "ad_id": req.ad_id,
        "total_users": len(results),
        "decision_counts": decision_counts,
        "results": results,
    }


@router.get("/decide/{decision_id}")
def get_decision(decision_id: str):
    if decision_id not in _decision_log:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found.")
    return _decision_log[decision_id]


@router.post("/chromosome/set")
def set_active_chromosome(genes: list[float]):
    """Set the active chromosome used for decisions (useful after loading a saved one)."""
    global _current_chromosome
    if len(genes) != 8:
        raise HTTPException(status_code=400, detail="Chromosome must have exactly 8 genes.")
    _current_chromosome = Chromosome.from_vector(genes)
    return {"genes": genes, "status": "active"}
