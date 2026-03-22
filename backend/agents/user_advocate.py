"""
User Advocate agent.

Scores an ad opportunity from the viewer's perspective.
Math scoring is PURE MATH (no LLM). Fast, used in GA fitness loop.
"""

from ..state import AdCandidate, AgentScore, Chromosome, ContentMood, SessionContext, UserProfile
from ..simulation.fatigue import get_effective_fatigue

MOOD_MODIFIER: dict[str, float] = {
    "calm": 0.10,
    "uplifting": 0.08,
    "playful": 0.05,
    "energetic": 0.00,
    "intense": -0.10,
    "dark": -0.15,
}


def score_user_advocate(
    user: UserProfile,
    ad: AdCandidate,
    session_context: SessionContext,
    chromosome: Chromosome,
) -> AgentScore:
    """
    Compute User Advocate score for an ad opportunity.

    Returns an AgentScore with math-derived score and factor breakdown.
    Reasoning field is initially a template; LLM enrichment happens in llm_reasoning.py.
    """
    c = chromosome
    cfg_ua_intensity = 0.7
    factors: dict[str, float] = {}

    base = 0.5
    factors["base"] = base

    # Relevance: does the ad match the user's interest categories?
    relevant = ad.category in user.interests
    relevance_bonus = (1.0 if relevant else 0.15) * c.relevance_weight * 0.8
    factors["relevance_bonus"] = round(relevance_bonus, 4)

    # Fatigue: use session accumulator if higher than base.
    fatigue = get_effective_fatigue(session_context, user)
    fatigue_penalty = fatigue * c.fatigue_weight * 1.5
    factors["fatigue_penalty"] = round(-fatigue_penalty, 4)

    # Timing: does the ad opportunity match the user's preferred watch time?
    time_matches = session_context.time_of_day.value == user.preferred_watch_time.value
    timing_bonus = (c.timing_weight * 0.3) if time_matches else 0.0
    factors["timing_bonus"] = round(timing_bonus, 4)

    # Session depth: penalize if many ads already shown.
    ads_shown = session_context.ads_shown_this_session
    if ads_shown > 2:
        session_penalty = 0.3 * c.session_depth_factor
    elif ads_shown > 1:
        session_penalty = 0.15 * c.session_depth_factor
    else:
        session_penalty = 0.0
    factors["session_penalty"] = round(-session_penalty, 4)

    # Content mood modifier.
    mood_mod = 0.0
    if session_context.content is not None:
        mood_mod = MOOD_MODIFIER.get(session_context.content.mood.value, 0.0)
    factors["mood_modifier"] = round(mood_mod, 4)

    # Intensity penalty: penalize ads at high-intensity content moments.
    intensity_penalty = 0.0
    if session_context.content is not None:
        minute = session_context.current_minute
        intensity = session_context.content.intensity_at(minute)
        if intensity > cfg_ua_intensity:
            intensity_penalty = 0.12
    factors["intensity_penalty"] = round(-intensity_penalty, 4)

    # Binge penalty.
    binge_penalty = 0.0
    if session_context.is_binging:
        binge_penalty = 0.08 * c.session_depth_factor
    factors["binge_penalty"] = round(-binge_penalty, 4)

    score = (
        base
        + relevance_bonus
        - fatigue_penalty
        + timing_bonus
        - session_penalty
        + mood_mod
        - intensity_penalty
        - binge_penalty
    )
    score = max(0.0, min(1.0, score))
    factors["final_score"] = round(score, 4)

    # Template reasoning (LLM may replace this later).
    top_factors = sorted(
        [(k, abs(v)) for k, v in factors.items() if k not in ("base", "final_score")],
        key=lambda x: x[1],
        reverse=True,
    )[:2]
    factor_str = ", ".join(f"{k}={v:+.3f}" for k, v in top_factors)
    reasoning = (
        f"Score: {score:.3f}. "
        f"Ad {'is' if relevant else 'is not'} relevant to user interests. "
        f"Key factors: {factor_str}."
    )

    return AgentScore(
        agent_name="User Advocate",
        score=round(score, 4),
        reasoning=reasoning,
        factors=factors,
    )
