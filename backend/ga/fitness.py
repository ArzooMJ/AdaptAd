"""
GA fitness evaluation.

PURE MATH. No LLM calls. No I/O. NumPy only.
This inner loop runs millions of times during evolution.

Fitness = 60% mean user satisfaction + 40% mean advertiser revenue,
averaged across all users and sampled scenarios.
"""

import numpy as np

from ..state import (
    AdDecision,
    Chromosome,
    ContentMood,
    TimeOfDay,
    UserProfile,
    AdCandidate,
    ContentItem,
)
from ..config import config


# Pre-compute mood modifier lookup as a constant array.
# Order matches ContentMood enum order for fast indexing.
MOOD_VALUES = ["calm", "uplifting", "playful", "energetic", "intense", "dark"]
MOOD_MODIFIER = {
    "calm": 0.10,
    "uplifting": 0.08,
    "playful": 0.05,
    "energetic": 0.00,
    "intense": -0.10,
    "dark": -0.15,
}

# Decision indices for output array
SHOW_IDX = 0
SOFTEN_IDX = 1
DELAY_IDX = 2
SUPPRESS_IDX = 3


def _user_advocate_score_vectorized(
    chromosome: Chromosome,
    fatigue: np.ndarray,       # shape (N,)
    relevant: np.ndarray,      # shape (N,) bool
    time_matches: np.ndarray,  # shape (N,) bool
    ads_shown: np.ndarray,     # shape (N,) int
    mood_modifier: np.ndarray, # shape (N,)
    intensity_high: np.ndarray,# shape (N,) bool
    is_binging: np.ndarray,    # shape (N,) bool
) -> np.ndarray:
    """
    Vectorized User Advocate scoring.

    All inputs are 1-D arrays of length N (one entry per scenario).
    Returns scores clamped to [0, 1].
    """
    c = chromosome
    base = 0.5

    relevance_bonus = np.where(
        relevant,
        1.0 * c.relevance_weight * 0.8,
        0.15 * c.relevance_weight * 0.8,
    )
    fatigue_penalty = fatigue * c.fatigue_weight * 1.5

    timing_bonus = np.where(time_matches, c.timing_weight * 0.3, 0.0)

    session_penalty = np.where(
        ads_shown > 2,
        0.3 * c.session_depth_factor,
        np.where(ads_shown > 1, 0.15 * c.session_depth_factor, 0.0),
    )

    intensity_penalty = np.where(intensity_high, 0.12, 0.0)
    binge_penalty = np.where(is_binging, 0.08 * c.session_depth_factor, 0.0)

    score = (
        base
        + relevance_bonus
        - fatigue_penalty
        + timing_bonus
        - session_penalty
        + mood_modifier
        - intensity_penalty
        - binge_penalty
    )
    return np.clip(score, 0.0, 1.0)


def _advertiser_advocate_score_vectorized(
    chromosome: Chromosome,
    relevant: np.ndarray,       # shape (N,)
    engagement: np.ndarray,     # shape (N,)
    is_primetime: np.ndarray,   # shape (N,) 0.0/0.05/0.15
    priority: np.ndarray,       # shape (N,)
    seasonal_affinity: np.ndarray, # shape (N,)
    demographic_match: np.ndarray, # shape (N,) bool
) -> np.ndarray:
    """Vectorized Advertiser Advocate scoring."""
    c = chromosome
    base = 0.55

    relevance_boost = np.where(relevant, c.category_boost * 1.5, 0.0)
    engagement_boost = engagement * 0.3
    priority_factor = (priority - 0.5) * 0.2
    demo_bonus = np.where(demographic_match, 0.08, 0.0)

    score = (
        base
        + relevance_boost
        + engagement_boost
        + is_primetime
        + priority_factor
        + seasonal_affinity
        + demo_bonus
    )
    return np.clip(score, 0.0, 1.0)


def _determine_decision_vectorized(
    chromosome: Chromosome,
    combined: np.ndarray,  # shape (N,)
) -> np.ndarray:
    """
    Vectorized decision mapping from combined score.

    Returns integer array: 0=SHOW, 1=SOFTEN, 2=DELAY, 3=SUPPRESS
    """
    show_thresh = 0.45 + chromosome.frequency_threshold * 0.35
    soften_thresh = show_thresh - 0.15
    delay_thresh = soften_thresh - 0.15

    decision = np.full(combined.shape, SUPPRESS_IDX, dtype=np.int8)
    decision = np.where(combined >= delay_thresh, DELAY_IDX, decision)
    decision = np.where(combined >= soften_thresh, SOFTEN_IDX, decision)
    decision = np.where(combined >= show_thresh, SHOW_IDX, decision)
    return decision


def _score_outcomes_vectorized(
    decisions: np.ndarray,  # shape (N,) int
    relevant: np.ndarray,   # shape (N,) bool
    fatigue: np.ndarray,    # shape (N,)
    ads_shown: np.ndarray,  # shape (N,) int
) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert (decision, context) pairs to (satisfaction, revenue) arrays.

    Mirrors the logic in simulation/engine.py score_outcome() but vectorized.
    """
    sat = np.zeros(len(decisions), dtype=np.float32)
    rev = np.zeros(len(decisions), dtype=np.float32)

    show = decisions == SHOW_IDX
    soften = decisions == SOFTEN_IDX
    delay = decisions == DELAY_IDX
    supp = decisions == SUPPRESS_IDX
    low_fat = fatigue < 0.5

    # SHOW outcomes
    sat = np.where(show & relevant & low_fat, 0.75, sat)
    rev = np.where(show & relevant & low_fat, 1.00, rev)
    sat = np.where(show & relevant & ~low_fat, 0.45, sat)
    rev = np.where(show & relevant & ~low_fat, 0.85, rev)
    sat = np.where(show & ~relevant & low_fat, 0.30, sat)
    rev = np.where(show & ~relevant & low_fat, 0.70, rev)
    sat = np.where(show & ~relevant & ~low_fat, 0.15, sat)
    rev = np.where(show & ~relevant & ~low_fat, 0.50, rev)

    # SOFTEN
    sat = np.where(soften & relevant, 0.60, sat)
    sat = np.where(soften & ~relevant, 0.35, sat)
    rev = np.where(soften, 0.55, rev)

    # DELAY
    sat = np.where(delay, 0.65, sat)
    rev = np.where(delay, 0.15, rev)

    # SUPPRESS
    sat = np.where(supp, 0.70, sat)
    rev = np.where(supp, 0.02, rev)

    # Session frequency penalty on satisfaction.
    sat = np.where(ads_shown >= 3, np.maximum(0.0, sat - 0.15), sat)
    sat = np.where((ads_shown == 2), np.maximum(0.0, sat - 0.08), sat)

    # Fatigue penalty.
    sat = np.where(fatigue > 0.70, np.maximum(0.0, sat - 0.10), sat)

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
    Evaluate fitness of a single chromosome.

    Samples `scenarios_per_user` random scenarios per user and computes the
    weighted average of satisfaction and revenue.

    PURE MATH. Called millions of times by the GA inner loop.
    """
    rng = np.random.default_rng(rng_seed)
    cfg = config
    fa_cfg = cfg.fatigue

    N = len(users) * scenarios_per_user
    if N == 0 or not ad_pool or not content_items:
        return 0.0

    # Build scenario arrays.
    user_indices = np.tile(np.arange(len(users)), scenarios_per_user)

    # Sample random ads and content.
    ad_indices = rng.integers(0, len(ad_pool), size=N)
    content_indices = rng.integers(0, len(content_items), size=N)
    ads_shown = rng.integers(0, 5, size=N).astype(np.float32)

    # Extract user features.
    fatigue_arr = np.array([users[i].fatigue_level for i in user_indices], dtype=np.float32)
    engagement_arr = np.array([users[i].engagement_score for i in user_indices], dtype=np.float32)
    preferred_tod = [users[i].preferred_watch_time.value for i in user_indices]
    interests_list = [users[i].interests for i in user_indices]
    age_groups = [users[i].age_group for i in user_indices]
    binge_tendency = np.array([users[i].binge_tendency for i in user_indices], dtype=np.float32)

    # Sample time of day for each scenario.
    tod_options = ["morning", "afternoon", "evening", "latenight"]
    tod_indices = rng.integers(0, 4, size=N)
    sampled_tod = [tod_options[i] for i in tod_indices]

    # Extract ad features.
    ad_categories = [ad_pool[i].category for i in ad_indices]
    ad_priorities = np.array([ad_pool[i].priority for i in ad_indices], dtype=np.float32)
    ad_target_demos = [ad_pool[i].target_demographics for i in ad_indices]

    # Season for seasonal affinity lookup.
    season_options = ["Spring", "Summer", "Fall", "Winter"]
    season_indices = rng.integers(0, 4, size=N)
    sampled_seasons = [season_options[i] for i in season_indices]
    seasonal_affinity = np.array(
        [ad_pool[ad_indices[i]].seasonal_affinity.get(sampled_seasons[i], 0.0) for i in range(N)],
        dtype=np.float32,
    )

    # Relevant = ad category in user interests.
    relevant = np.array(
        [ad_categories[i] in interests_list[i] for i in range(N)], dtype=bool
    )

    # Time match = sampled time of day matches user preferred watch time.
    time_matches = np.array(
        [sampled_tod[i] == preferred_tod[i] for i in range(N)], dtype=bool
    )

    # Primetime boost.
    primetime_map = {"morning": 0.0, "afternoon": 0.05, "evening": 0.15, "latenight": 0.15}
    is_primetime = np.array([primetime_map[t] for t in sampled_tod], dtype=np.float32)

    # Demographic match.
    demographic_match = np.array(
        [age_groups[i] in ad_target_demos[i] for i in range(N)], dtype=bool
    )

    # Mood modifier: sample a random content mood for each scenario.
    mood_values_list = list(MOOD_MODIFIER.keys())
    mood_sample_indices = rng.integers(0, len(mood_values_list), size=N)
    mood_modifier = np.array(
        [MOOD_MODIFIER[mood_values_list[j]] for j in mood_sample_indices], dtype=np.float32
    )

    # Intensity: random chance that current minute is high intensity.
    intensity_high = rng.random(N) > 0.7  # ~30% of break points are high-intensity.

    # Binge state: based on binge tendency threshold.
    is_binging = binge_tendency > cfg.simulation.binge_tendency_threshold

    # Session fatigue accumulator: approximate with base fatigue + ads_shown impact.
    session_fatigue = np.clip(
        fatigue_arr + ads_shown * fa_cfg.show_increment,
        0.0, 1.0
    ).astype(np.float32)

    # Force suppress where session fatigue exceeds ceiling.
    force_suppress = session_fatigue > fa_cfg.force_suppress_threshold

    ua_scores = _user_advocate_score_vectorized(
        chromosome=chromosome,
        fatigue=session_fatigue,
        relevant=relevant,
        time_matches=time_matches,
        ads_shown=ads_shown.astype(int),
        mood_modifier=mood_modifier,
        intensity_high=intensity_high,
        is_binging=is_binging,
    )

    adv_scores = _advertiser_advocate_score_vectorized(
        chromosome=chromosome,
        relevant=relevant,
        engagement=engagement_arr,
        is_primetime=is_primetime,
        priority=ad_priorities,
        seasonal_affinity=seasonal_affinity,
        demographic_match=demographic_match,
    )

    combined = ua_scores * cfg.agents.user_weight + adv_scores * cfg.agents.advertiser_weight
    combined = np.clip(combined, 0.0, 1.0)

    decisions = _determine_decision_vectorized(chromosome, combined)

    # Force suppress where fatigue ceiling reached.
    decisions = np.where(force_suppress, SUPPRESS_IDX, decisions)

    sat, rev = _score_outcomes_vectorized(decisions, relevant, session_fatigue, ads_shown.astype(int))

    fitness = (
        cfg.ga.fitness_user_weight * float(np.mean(sat))
        + cfg.ga.fitness_revenue_weight * float(np.mean(rev))
    )
    return float(np.clip(fitness, 0.0, 1.0))


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
