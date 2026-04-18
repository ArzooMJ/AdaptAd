"""
GA fitness evaluation — uses the real agent pipeline.

evaluate_chromosome_fitness() calls score_user_advocate() and
score_advertiser_advocate() directly, using the same code path as /api/decide.
This closes the train/inference gap: the chromosome the GA selects is the one
that actually produces the best decisions at runtime.
"""

import numpy as np

from ..state import (
    AdCandidate,
    AdDecision,
    Chromosome,
    ContentItem,
    Season,
    SessionContext,
    TimeOfDay,
    UserProfile,
)
from ..config import config
from ..agents.user_advocate import score_user_advocate
from ..agents.advertiser_advocate import score_advertiser_advocate

_TOD_OPTIONS = [TimeOfDay.morning, TimeOfDay.afternoon, TimeOfDay.evening, TimeOfDay.latenight]
_SEASON_OPTIONS = [Season.Spring, Season.Summer, Season.Fall, Season.Winter]


def _sat_rev(
    decision: AdDecision,
    relevant: bool,
    low_fatigue: bool,
    fatigue: float,
    ads_shown: int,
    tol_boost: float,
) -> tuple[float, float]:
    """Map (decision, context) to (satisfaction, revenue) scores."""
    if decision == AdDecision.SHOW:
        if relevant and low_fatigue:
            sat, rev = 0.68 + tol_boost, 1.00
        elif relevant:
            sat, rev = 0.42 + tol_boost, 0.85
        elif low_fatigue:
            sat, rev = 0.25 + tol_boost, 0.65
        else:
            sat, rev = 0.12 + tol_boost, 0.45
    elif decision == AdDecision.SWAP:
        # SWAP always plays a relevant ad.
        sat = (0.65 if low_fatigue else 0.45) + tol_boost
        rev = 0.75
    elif decision == AdDecision.DELAY:
        # Approximate combined value of deferral + guaranteed future SHOW.
        sat, rev = 0.62, 0.65
    else:  # SUPPRESS
        sat, rev = 0.72, 0.02

    if ads_shown >= 3:
        sat = max(0.0, sat - 0.15)
    elif ads_shown == 2:
        sat = max(0.0, sat - 0.08)
    if fatigue > 0.70:
        sat = max(0.0, sat - 0.10)

    return sat, rev


def evaluate_chromosome_fitness(
    chromosome: Chromosome,
    users: list[UserProfile],
    content_items: list[ContentItem],
    ad_pool: list[AdCandidate],
    scenarios_per_user: int = 5,
    rng_seed: int = 0,
) -> float:
    """
    Evaluate fitness of a single chromosome using the real agent pipeline.

    Samples `scenarios_per_user` random scenarios per user, runs each through
    score_user_advocate() -> score_advertiser_advocate() -> threshold decision,
    then computes weighted (satisfaction, revenue). The threshold formula here
    is identical to negotiator.py so the GA optimizes exactly what gets deployed.
    """
    rng = np.random.default_rng(rng_seed)
    cfg = config
    fa_cfg = cfg.fatigue
    ag_cfg = cfg.agents

    N = len(users) * scenarios_per_user
    if N == 0 or not ad_pool or not content_items:
        return 0.0

    # Sample all random state upfront to keep the loop body clean
    user_indices    = np.tile(np.arange(len(users)), scenarios_per_user)
    ad_indices      = rng.integers(0, len(ad_pool),       size=N)
    content_indices = rng.integers(0, len(content_items), size=N)
    ads_shown_arr   = rng.integers(0, 5,  size=N)
    minute_arr      = rng.integers(5, 45, size=N)
    fatigue_arr     = rng.uniform(0.0, 0.8, size=N)
    tod_indices     = rng.integers(0, 4, size=N)
    season_indices  = rng.integers(0, 4, size=N)

    # Precompute per-chromosome thresholds — mirrors negotiator.py score ladder.
    # DELAY is condition-based (intensity/timing), not a score band; approximated below.
    show_thresh = ag_cfg.base_show_threshold + chromosome.frequency_threshold * ag_cfg.show_threshold_scale
    swap_thresh = show_thresh - (0.08 + chromosome.swap_relevance_min * 0.14)
    # Intensity threshold that triggers DELAY (same formula as negotiator).
    delay_intensity_thresh = 0.50 + chromosome.delay_threshold * 0.25

    total_sat = 0.0
    total_rev = 0.0

    for i in range(N):
        fatigue   = float(fatigue_arr[i])
        ads_shown = int(ads_shown_arr[i])

        # Force suppress when fatigue is too high — mirrors simulation engine
        if fatigue > fa_cfg.force_suppress_threshold:
            total_sat += 0.72
            total_rev += 0.02
            continue

        user    = users[int(user_indices[i])]
        ad      = ad_pool[int(ad_indices[i])]
        content = content_items[int(content_indices[i])]

        ctx = SessionContext(
            time_of_day=_TOD_OPTIONS[int(tod_indices[i])],
            season=_SEASON_OPTIONS[int(season_indices[i])],
            ads_shown_this_session=ads_shown,
            content=content,
            current_minute=int(minute_arr[i]),
            is_binging=user.binge_tendency > cfg.simulation.binge_tendency_threshold,
            session_fatigue_accumulator=fatigue,
        )

        ua  = score_user_advocate(user, ad, ctx, chromosome)
        adv = score_advertiser_advocate(user, ad, ctx, chromosome)

        combined = max(0.0, min(1.0,
            ua.score * ag_cfg.user_weight + adv.score * ag_cfg.advertiser_weight
        ))

        # Approximate intensity from content at sampled minute (0.5 if no content).
        intensity = 0.5
        if content.intensity_curve:
            idx = min(int(minute_arr[i]), len(content.intensity_curve) - 1)
            intensity = content.intensity_curve[idx]

        # DELAY fires on intense scenes (mirrors negotiator condition-based logic).
        if intensity > delay_intensity_thresh and combined >= 0.25:
            decision = AdDecision.DELAY
        elif combined >= show_thresh:
            decision = AdDecision.SHOW
        elif combined >= swap_thresh:
            decision = AdDecision.SWAP
        else:
            decision = AdDecision.SUPPRESS

        relevant  = ad.category in user.interests
        tol_boost = max(0.0, min(0.15, user.ad_tolerance - 0.5))

        sat, rev = _sat_rev(decision, relevant, fatigue < 0.5, fatigue, ads_shown, tol_boost)
        total_sat += sat
        total_rev += rev

    fitness = (
        cfg.ga.fitness_user_weight    * (total_sat / N)
        + cfg.ga.fitness_revenue_weight * (total_rev / N)
    )
    return float(max(0.0, min(1.0, fitness)))


def evaluate_population_fitness(
    population: list[Chromosome],
    users: list[UserProfile],
    content_items: list[ContentItem],
    ad_pool: list[AdCandidate],
    scenarios_per_user: int = 5,
    rng_seed: int = 0,
) -> list[float]:
    """
    Evaluate fitness for every chromosome in the population.

    Returns a list of fitness scores in the same order as population.
    """
    return [
        evaluate_chromosome_fitness(
            chrom, users, content_items, ad_pool,
            scenarios_per_user=scenarios_per_user,
            rng_seed=rng_seed + i,
        )
        for i, chrom in enumerate(population)
    ]
