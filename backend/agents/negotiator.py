"""
Negotiator: combines User Advocate and Advertiser Advocate scores
to determine a final AdDecision.

Decision flow:
  1. Intensity/timing conditions → DELAY (context-aware, not score-based)
  2. Score ladder             → SHOW / SWAP / SUPPRESS

DELAY fires when any of:
  - Scene intensity > threshold (controlled by delay_threshold gene)
  - Ads shown too close together (< 8 min since last shown ad)
  - Early in a binge session (first ad opportunity, < 10 min in)

DELAY only fires if combined_score >= 0.30 — if the ad has too little
merit it goes straight to SUPPRESS (no point deferring a bad ad).
"""

from datetime import datetime
from typing import Optional, Union

from ..state import AdCandidate, AdDecision, AgentScore, Chromosome, NegotiationResult, SessionContext
from ..config import config

_DELAY_MERIT_FLOOR = 0.25   # min combined score to justify deferring (not suppressing)
_BACK_TO_BACK_MINUTES = 8   # gap shorter than this = back-to-back
_EARLY_BINGE_MINUTES = 10   # first ad in a binge session before this minute


def negotiate(
    user_advocate: Union[AgentScore, dict],
    advertiser_advocate: Union[AgentScore, dict],
    chromosome: Chromosome,
    user_id: int,
    ad_id: str,
    session_id: str,
    session_context: Optional[SessionContext] = None,
    minutes_since_last_ad: int = 99,
) -> NegotiationResult:
    """
    Combine agent scores into a final decision.

    Pass session_context and minutes_since_last_ad to enable
    intensity-based DELAY and back-to-back detection.
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

    # ── Condition-based DELAY check ──────────────────────────────────────────
    if session_context is not None:
        intensity = 0.5
        if session_context.content is not None:
            intensity = session_context.content.intensity_at(session_context.current_minute)

        # Gene controls how sensitive DELAY is to scene intensity.
        intensity_threshold = 0.50 + chromosome.delay_threshold * 0.25

        back_to_back = (
            minutes_since_last_ad < _BACK_TO_BACK_MINUTES
            and session_context.ads_shown_this_session > 0
        )
        early_binge = (
            session_context.is_binging
            and session_context.ads_shown_this_session == 0
            and session_context.current_minute < _EARLY_BINGE_MINUTES
        )
        intense_scene = intensity > intensity_threshold

        if intense_scene or back_to_back or early_binge:
            if combined >= _DELAY_MERIT_FLOOR:
                decision = AdDecision.DELAY
                triggers = []
                if intense_scene:
                    triggers.append(f"scene intensity {intensity:.2f} > {intensity_threshold:.2f}")
                if back_to_back:
                    triggers.append(f"back-to-back ({minutes_since_last_ad}min gap)")
                if early_binge:
                    triggers.append("early binge session")
                reasoning = (
                    f"Combined score {combined:.3f}. DELAY: {'; '.join(triggers)}. "
                    f"Ad deferred to next break."
                )
            else:
                decision = AdDecision.SUPPRESS
                reasoning = (
                    f"Combined score {combined:.3f} below merit floor "
                    f"({_DELAY_MERIT_FLOOR}) — SUPPRESS rather than defer weak ad."
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

    # ── Score ladder: SHOW / SWAP / SUPPRESS ─────────────────────────────────
    show_thresh = cfg.base_show_threshold + chromosome.frequency_threshold * cfg.show_threshold_scale
    swap_thresh = show_thresh - (0.08 + chromosome.swap_relevance_min * 0.14)

    if combined >= show_thresh:
        decision = AdDecision.SHOW
    elif combined >= swap_thresh:
        decision = AdDecision.SWAP
    else:
        decision = AdDecision.SUPPRESS

    reasoning = (
        f"Combined score {combined:.3f} "
        f"(user={user_advocate.score:.3f} x 0.55, "
        f"advertiser={advertiser_advocate.score:.3f} x 0.45). "
        f"Thresholds: show={show_thresh:.3f}, swap={swap_thresh:.3f}. "
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