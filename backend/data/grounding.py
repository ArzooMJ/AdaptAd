"""
Data grounding module.

Merges real-data distributions (from pipeline.py) into synthetic user and
content generation. If datasets are missing, silently uses defaults.

Usage:
  from backend.data.grounding import get_grounded_genre_weights, get_primetime_boost
"""

import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

_distributions: Optional[dict] = None


def _get_distributions() -> dict:
    global _distributions
    if _distributions is None:
        try:
            from .pipeline import load_distributions
            _distributions = load_distributions()
        except Exception as e:
            logger.warning("Could not load distributions: %s. Using defaults.", e)
            _distributions = {}
    return _distributions


@lru_cache(maxsize=1)
def get_grounded_genre_weights() -> dict[str, float]:
    """
    Return genre weights grounded in MovieLens 25M data.

    Falls back to uniform weights if MovieLens is unavailable.
    """
    dist = _get_distributions()
    movielens = dist.get("movielens", {})
    weights = movielens.get("genre_weights")
    if weights:
        return weights
    # Fallback: uniform over the 10 genres in our system.
    from .constants import GENRES
    return {g: 1.0 / len(GENRES) for g in GENRES}


@lru_cache(maxsize=1)
def get_grounded_engagement_stats() -> tuple[float, float]:
    """
    Return (mean, std) for engagement score, grounded in MovieLens rating data.
    """
    dist = _get_distributions()
    movielens = dist.get("movielens", {})
    mean = movielens.get("engagement_mean", 0.62)
    std = movielens.get("engagement_std", 0.18)
    return float(mean), float(std)


@lru_cache(maxsize=1)
def get_grounded_ctr() -> float:
    """
    Return mean CTR grounded in Criteo data.
    Used to calibrate ad priority distributions.
    """
    dist = _get_distributions()
    criteo = dist.get("criteo", {})
    return float(criteo.get("mean_ctr", 0.031))


@lru_cache(maxsize=1)
def get_primetime_boost() -> float:
    """
    Return evening primetime CTR boost factor from Avazu data.
    Used in Advertiser Advocate primetime_boost parameter.
    """
    dist = _get_distributions()
    avazu = dist.get("avazu", {})
    return float(avazu.get("primetime_boost", 0.15))


@lru_cache(maxsize=1)
def get_hourly_ctr() -> dict[int, float]:
    """
    Return per-hour CTR values from Avazu data.
    """
    dist = _get_distributions()
    avazu = dist.get("avazu", {})
    hourly = avazu.get("hourly_ctr", {})
    if not hourly:
        from .pipeline import FALLBACK_HOURLY_CTR
        return FALLBACK_HOURLY_CTR
    return {int(k): float(v) for k, v in hourly.items()}


def get_content_preferences_from_movielens(rng, num_prefs: int = 3) -> list[str]:
    """
    Sample content genre preferences weighted by MovieLens distribution.

    Used in generate.py to replace uniform sampling.
    """
    from .constants import GENRES
    weights_dict = get_grounded_genre_weights()
    genres = GENRES
    weights = [weights_dict.get(g, 1.0 / len(genres)) for g in genres]
    total = sum(weights)
    weights = [w / total for w in weights]
    chosen = rng.choices(genres, weights=weights, k=num_prefs * 2)
    seen: set[str] = set()
    result: list[str] = []
    for g in chosen:
        if g not in seen:
            seen.add(g)
            result.append(g)
        if len(result) >= num_prefs:
            break
    return result


def grounding_summary() -> dict:
    """Return a summary of which data sources are active."""
    dist = _get_distributions()
    return {
        "movielens": dist.get("movielens", {}).get("source", "not loaded"),
        "criteo": dist.get("criteo", {}).get("source", "not loaded"),
        "avazu": dist.get("avazu", {}).get("source", "not loaded"),
        "engagement_mean": get_grounded_engagement_stats()[0],
        "mean_ctr": get_grounded_ctr(),
        "primetime_boost": get_primetime_boost(),
    }
