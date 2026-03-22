"""
Simulation engine.

Provides evaluate_policy() for measuring a policy across users and sessions.
Also provides the three baseline policies used as comparison targets.
"""

import random
from typing import Callable, Optional

from ..state import (
    AdCandidate,
    AdDecision,
    AdOpportunity,
    Chromosome,
    ContentItem,
    SessionContext,
    UserProfile,
)
from ..config import config
from .session import simulate_session, apply_decision
from .fatigue import should_force_suppress

# Type alias: a policy takes an AdOpportunity and returns an AdDecision.
PolicyFn = Callable[[AdOpportunity], AdDecision]


# ---------------------------------------------------------------------------
# Baseline policies
# ---------------------------------------------------------------------------


def policy_always_show(opportunity: AdOpportunity) -> AdDecision:
    """Show every ad, every time. Upper bound on revenue, lower bound on satisfaction."""
    return AdDecision.SHOW


def policy_random(opportunity: AdOpportunity, seed: Optional[int] = None) -> AdDecision:
    """Coin flip: SHOW or SUPPRESS with equal probability."""
    rng = random.Random(seed)
    return rng.choice([AdDecision.SHOW, AdDecision.SUPPRESS])


def policy_frequency_cap(
    opportunity: AdOpportunity, cap: int = 3
) -> AdDecision:
    """
    Show up to `cap` ads per session, then SUPPRESS.

    The cap default of 3 per 30 minutes is a common industry heuristic.
    """
    if opportunity.session_context.ads_shown_this_session < cap:
        return AdDecision.SHOW
    return AdDecision.SUPPRESS


# ---------------------------------------------------------------------------
# Outcome scoring
# ---------------------------------------------------------------------------


def score_outcome(
    decision: AdDecision,
    opportunity: AdOpportunity,
) -> tuple[float, float]:
    """
    Return (satisfaction, revenue) for a decision given the opportunity context.

    This fast scoring function is used in GA fitness evaluation.
    It does not call any LLM.
    """
    user = opportunity.user
    ad = opportunity.ad_candidate
    ctx = opportunity.session_context

    # Is the ad relevant to this user?
    relevant = ad.category in user.interests
    fatigue = max(user.fatigue_level, ctx.session_fatigue_accumulator)
    ads_shown = ctx.ads_shown_this_session

    if decision == AdDecision.SHOW:
        if relevant and fatigue < 0.5:
            satisfaction = 0.75
            revenue = 1.0
        elif relevant and fatigue >= 0.5:
            satisfaction = 0.45
            revenue = 0.85
        elif not relevant and fatigue < 0.5:
            satisfaction = 0.30
            revenue = 0.70
        else:
            # Irrelevant ad to fatigued user. Bad outcome.
            satisfaction = 0.15
            revenue = 0.50
    elif decision == AdDecision.SOFTEN:
        satisfaction = 0.60 if relevant else 0.35
        revenue = 0.55
    elif decision == AdDecision.DELAY:
        satisfaction = 0.65
        revenue = 0.15
    else:  # SUPPRESS
        satisfaction = 0.70
        revenue = 0.02

    # Additional penalty for high-frequency ad exposure within session.
    if ads_shown >= 3:
        satisfaction = max(0.0, satisfaction - 0.15)
    elif ads_shown >= 2:
        satisfaction = max(0.0, satisfaction - 0.08)

    # Fatigue penalty on satisfaction.
    if fatigue > 0.70:
        satisfaction = max(0.0, satisfaction - 0.10)

    return round(satisfaction, 4), round(revenue, 4)


# ---------------------------------------------------------------------------
# Policy evaluation
# ---------------------------------------------------------------------------


def evaluate_policy(
    policy_fn: PolicyFn,
    users: list[UserProfile],
    content_items: list[ContentItem],
    ad_pool: list[AdCandidate],
    num_sessions_per_user: int = 1,
    seed: int = 42,
) -> dict[str, float]:
    """
    Evaluate a policy across all users over multiple simulated sessions.

    Returns:
        dict with keys:
            "satisfaction": mean satisfaction across all decisions
            "revenue": mean revenue across all decisions
            "fatigue": mean session-end fatigue across all sessions
            "fitness": weighted combined fitness (60% satisfaction + 40% revenue)
            "total_decisions": total number of ad opportunities evaluated
            "decision_counts": dict[str, int] with per-decision type counts
    """
    rng = random.Random(seed)
    all_satisfactions: list[float] = []
    all_revenues: list[float] = []
    all_end_fatigues: list[float] = []
    decision_counts: dict[str, int] = {d.value: 0 for d in AdDecision}

    for user in users:
        for _ in range(num_sessions_per_user):
            content = rng.choice(content_items)
            opportunities, final_ctx = simulate_session(
                user=user,
                content=content,
                ad_pool=ad_pool,
                seed=rng.randint(0, 2**31),
            )
            if not opportunities:
                all_end_fatigues.append(user.fatigue_level)
                continue

            # Running context carries ads_shown and fatigue across break points.
            # This is the fix for the pre-computed ads_seen_so_far bug:
            # each opportunity gets the LIVE running context before policy evaluation.
            running_ctx = opportunities[0].session_context.model_copy()
            prev_minute = 0

            for opp in opportunities:
                # Merge static opportunity context with running counters.
                live_opp = opp.model_copy(update={"session_context": running_ctx.model_copy(
                    update={"current_minute": opp.session_context.current_minute}
                )})

                # Force suppress if session fatigue is at the ceiling.
                if should_force_suppress(running_ctx):
                    decision = AdDecision.SUPPRESS
                else:
                    decision = policy_fn(live_opp)

                sat, rev = score_outcome(decision, live_opp)
                all_satisfactions.append(sat)
                all_revenues.append(rev)
                decision_counts[decision.value] += 1

                # Advance running context (updates ads_shown and fatigue).
                minutes_gap = max(0, opp.session_context.current_minute - prev_minute)
                running_ctx = apply_decision(
                    running_ctx, user, decision,
                    opp.session_context.current_minute,
                    minutes_gap,
                )
                prev_minute = opp.session_context.current_minute

            all_end_fatigues.append(running_ctx.session_fatigue_accumulator)

    if not all_satisfactions:
        return {
            "satisfaction": 0.0,
            "revenue": 0.0,
            "fatigue": 0.0,
            "fitness": 0.0,
            "total_decisions": 0,
            "decision_counts": decision_counts,
        }

    mean_sat = sum(all_satisfactions) / len(all_satisfactions)
    mean_rev = sum(all_revenues) / len(all_revenues)
    mean_fatigue = sum(all_end_fatigues) / len(all_end_fatigues)
    fitness = (
        config.ga.fitness_user_weight * mean_sat
        + config.ga.fitness_revenue_weight * mean_rev
    )

    return {
        "satisfaction": round(mean_sat, 4),
        "revenue": round(mean_rev, 4),
        "fatigue": round(mean_fatigue, 4),
        "fitness": round(fitness, 4),
        "total_decisions": len(all_satisfactions),
        "decision_counts": decision_counts,
    }


if __name__ == "__main__":
    from ..data.generate import generate_users
    from ..data.content_library import generate_content_library
    from ..data.ad_inventory import generate_ad_inventory

    users = generate_users(count=200, seed=42)
    content = generate_content_library(count=100, seed=42)
    ads = generate_ad_inventory(count=80, seed=42)

    for name, policy in [
        ("always_show", policy_always_show),
        ("random", lambda opp: policy_random(opp, seed=None)),
        ("frequency_cap", policy_frequency_cap),
    ]:
        results = evaluate_policy(policy, users, content, ads)
        print(
            f"{name:<16} | sat={results['satisfaction']:.2f} "
            f"rev={results['revenue']:.2f} fatigue={results['fatigue']:.2f} "
            f"fitness={results['fitness']:.2f} n={results['total_decisions']}"
        )
