"""
Negotiator: combines User Advocate and Advertiser Advocate scores
to determine a final AdDecision.
"""

from datetime import datetime
from typing import Union

from ..state import AdCandidate, AdDecision, AgentScore, Chromosome, NegotiationResult, UserProfile
from ..config import config


def negotiate(
    user_advocate: Union[AgentScore, dict],
    advertiser_advocate: Union[AgentScore, dict],
    chromosome: Chromosome,
    user_id: int,
    ad_id: str,
    session_id: str,
) -> NegotiationResult:
    """
    Combine agent scores into a final decision.

    combined = user_score * 0.55 + advertiser_score * 0.45
    show_threshold = 0.45 + frequency_threshold_gene * 0.35
    soften_threshold = show_threshold - 0.15
    delay_threshold = soften_threshold - 0.15
    """
    if isinstance(user_advocate, dict):
        user_advocate = AgentScore.model_validate(user_advocate)
    if isinstance(advertiser_advocate, dict):
        advertiser_advocate = AgentScore.model_validate(advertiser_advocate)

    cfg = config.agents
    combined = (
        user_advocate.score * cfg.user_weight
        + advertiser_advocate.score * cfg.advertiser_weight
    )
    combined = max(0.0, min(1.0, combined))

    show_thresh = cfg.base_show_threshold + chromosome.frequency_threshold * cfg.show_threshold_scale
    soften_thresh = show_thresh - cfg.soften_offset
    delay_thresh = soften_thresh - cfg.delay_offset

    if combined >= show_thresh:
        decision = AdDecision.SHOW
    elif combined >= soften_thresh:
        decision = AdDecision.SOFTEN
    elif combined >= delay_thresh:
        decision = AdDecision.DELAY
    else:
        decision = AdDecision.SUPPRESS

    reasoning = (
        f"Combined score {combined:.3f} "
        f"(user={user_advocate.score:.3f} x 0.55, "
        f"advertiser={advertiser_advocate.score:.3f} x 0.45). "
        f"Thresholds: show={show_thresh:.3f}, soften={soften_thresh:.3f}, "
        f"delay={delay_thresh:.3f}. "
        f"Decision: {decision.value}."
    )

    return NegotiationResult(
        decision=decision,
        user_advocate=user_advocate,
        advertiser_advocate=advertiser_advocate,
        combined_score=round(combined, 4),
        reasoning=reasoning,
        timestamp=datetime.utcnow(),
        session_id=session_id,
        user_id=user_id,
        ad_id=ad_id,
    )
