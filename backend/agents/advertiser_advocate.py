"""
Advertiser Advocate agent.

Scores an ad opportunity from the advertiser's perspective.
Math scoring is PURE MATH (no LLM). Fast, used in GA fitness loop.
"""

from ..state import AdCandidate, AgentScore, Chromosome, Season, SessionContext, TimeOfDay, UserProfile
from ..data.grounding import get_primetime_boost


def score_advertiser_advocate(
    user: UserProfile,
    ad: AdCandidate,
    session_context: SessionContext,
    chromosome: Chromosome,
) -> AgentScore:
    """
    Compute Advertiser Advocate score for an ad opportunity.

    Returns an AgentScore with math-derived score and factor breakdown.
    """
    c = chromosome
    factors: dict[str, float] = {}

    base = 0.55
    factors["base"] = base

    # Relevance boost: does the ad category match user interests?
    relevant = ad.category in user.interests
    relevance_boost = (c.category_boost * 1.5) if relevant else 0.0
    factors["relevance_boost"] = round(relevance_boost, 4)

    # Engagement: higher engagement users are more valuable targets.
    engagement_boost = user.engagement_score * 0.3
    factors["engagement_boost"] = round(engagement_boost, 4)

    # Primetime boost: grounded in Avazu hourly CTR data.
    # get_primetime_boost() returns evening - morning delta from real data.
    # If Avazu unavailable, falls back to 0.15.
    _pt = get_primetime_boost()
    primetime_map: dict[str, float] = {
        "morning": 0.0,
        "afternoon": round(_pt * 0.33, 4),
        "evening": _pt if _pt > 0 else 0.15,
        "latenight": _pt if _pt > 0 else 0.15,
    }
    primetime_boost = primetime_map.get(session_context.time_of_day.value, 0.0)
    factors["primetime_boost"] = round(primetime_boost, 4)

    # Ad priority: higher-priority ads get a small score bump.
    priority_factor = (ad.priority - 0.5) * 0.2
    factors["priority_factor"] = round(priority_factor, 4)

    # Seasonal affinity: some ads perform better in certain seasons.
    seasonal_affinity = ad.seasonal_affinity.get(session_context.season.value, 0.0)
    factors["seasonal_affinity"] = round(seasonal_affinity, 4)

    # Demographic match: ad targets this age group explicitly.
    demographic_match = user.age_group in ad.target_demographics
    demo_bonus = 0.08 if demographic_match else 0.0
    factors["demographic_match"] = round(demo_bonus, 4)

    score = (
        base
        + relevance_boost
        + engagement_boost
        + primetime_boost
        + priority_factor
        + seasonal_affinity
        + demo_bonus
    )
    score = max(0.0, min(1.0, score))
    factors["final_score"] = round(score, 4)

    # Template reasoning.
    top_factors = sorted(
        [(k, abs(v)) for k, v in factors.items() if k not in ("base", "final_score")],
        key=lambda x: x[1],
        reverse=True,
    )[:2]
    factor_str = ", ".join(f"{k}={v:+.3f}" for k, v in top_factors)
    reasoning = (
        f"Score: {score:.3f}. "
        f"Ad {'targets' if demographic_match else 'does not target'} this age group. "
        f"Key factors: {factor_str}."
    )

    return AgentScore(
        agent_name="Advertiser Advocate",
        score=round(score, 4),
        reasoning=reasoning,
        factors=factors,
    )
