"""
Natural break point detection and scoring.

Break points are minutes in a content item where an ad can be inserted.
Rules:
- Never in the first or last 5 minutes.
- Prefer low-intensity minutes (scene transitions).
- High-intensity break points are penalized but not removed.
- Episodes get 2-4 break points. Movies get 4-7.
"""

from ..state import ContentItem
from ..config import config


def score_break_point(content: ContentItem, minute: int) -> float:
    """
    Return a quality score for placing an ad at `minute`.

    Higher score = better moment to insert an ad.
    Score is 0 if the minute violates the buffer rule.
    """
    buffer = config.simulation.break_point_buffer_minutes
    if minute < buffer or minute > content.duration_minutes - buffer:
        return 0.0

    intensity = content.intensity_at(minute)
    # Low intensity = good time for an ad. Invert and scale.
    base_score = 1.0 - intensity

    # Extra penalty for very high intensity moments.
    if intensity > 0.7:
        base_score -= 0.2

    # Slight preference for earlier break points (viewers less fatigued).
    position_factor = 1.0 - (minute / content.duration_minutes) * 0.15
    return max(0.0, base_score * position_factor)


def get_scored_break_points(content: ContentItem) -> list[tuple[int, float]]:
    """
    Return all valid break points with their quality scores, sorted by score descending.

    Each tuple is (minute, score).
    """
    buffer = config.simulation.break_point_buffer_minutes
    scored = []
    for bp in content.natural_break_points:
        s = score_break_point(content, bp)
        if s > 0.0:
            scored.append((bp, round(s, 4)))
    return sorted(scored, key=lambda x: x[1], reverse=True)


def select_best_break_points(
    content: ContentItem,
    max_breaks: int,
    min_gap_minutes: int = 8,
) -> list[int]:
    """
    Select up to `max_breaks` break points from a content item.

    Enforces a minimum gap between selected break points to avoid
    placing ads too close together.

    Returns a sorted list of minute values.
    """
    scored = get_scored_break_points(content)
    if not scored:
        return []

    selected: list[int] = []
    for minute, score in scored:
        if len(selected) >= max_breaks:
            break
        # Enforce minimum gap.
        too_close = any(abs(minute - prev) < min_gap_minutes for prev in selected)
        if not too_close:
            selected.append(minute)

    return sorted(selected)


def get_next_break_point(
    content: ContentItem,
    current_minute: int,
    min_gap_minutes: int = 3,
) -> int | None:
    """
    Return the next valid break point after `current_minute`.

    Returns None if no break points remain.
    """
    buffer = config.simulation.break_point_buffer_minutes
    for bp in sorted(content.natural_break_points):
        if bp > current_minute + min_gap_minutes and score_break_point(content, bp) > 0:
            return bp
    return None


def has_break_points(content: ContentItem) -> bool:
    """Return True if the content has at least one valid break point."""
    buffer = config.simulation.break_point_buffer_minutes
    return any(
        buffer <= bp <= content.duration_minutes - buffer
        for bp in content.natural_break_points
    )
