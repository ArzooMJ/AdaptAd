"""
Binge detection and binge-session management.

Binge state is active when:
- The content queue has 2+ upcoming episodes.
- The user has already watched 1+ episode this session.
- The user's binge_tendency > 0.5.

During a binge, ad frequency is reduced and fatigue sensitivity increases.
After 3+ consecutive episodes, is_binging=True and penalties are applied.
"""

from ..state import ContentItem, SessionContext, UserProfile
from ..config import config


def should_autoplay(
    user: UserProfile,
    content_queue: list[ContentItem],
    episodes_watched: int,
) -> bool:
    """
    Return True if the next episode should auto-play.

    Autoplay triggers when the user has binge tendency > threshold
    and there is content in the queue.
    """
    cfg = config.simulation
    return (
        len(content_queue) >= 1
        and episodes_watched >= 1
        and user.binge_tendency > cfg.binge_tendency_threshold
    )


def is_binge_active(
    user: UserProfile,
    content_queue: list[ContentItem],
    episodes_watched: int,
) -> bool:
    """
    Return True if binge mode is currently active.

    Binge mode requires the queue threshold AND episode threshold.
    """
    cfg = config.simulation
    return (
        len(content_queue) >= cfg.binge_queue_threshold
        and episodes_watched >= cfg.binge_episode_threshold
        and user.binge_tendency > cfg.binge_tendency_threshold
    )


def binge_ad_frequency_multiplier(episodes_watched: int) -> float:
    """
    Return a multiplier on the show_threshold during binge sessions.

    More episodes watched = higher bar for showing ads.
    After 3 episodes, threshold rises by 20%.
    After 5 episodes, threshold rises by 35%.
    """
    if episodes_watched >= 5:
        return 1.35
    if episodes_watched >= 3:
        return 1.20
    return 1.0


def binge_fatigue_sensitivity_multiplier(episodes_watched: int) -> float:
    """
    Return a multiplier on fatigue penalties during binge.

    More episodes watched = fatigue accumulates faster.
    """
    if episodes_watched >= 5:
        return 1.30
    if episodes_watched >= 3:
        return 1.15
    return 1.0


def update_binge_state(
    session_context: SessionContext,
    user: UserProfile,
    episodes_watched: int,
    content_queue: list[ContentItem],
) -> SessionContext:
    """
    Return an updated SessionContext with the current binge state applied.
    """
    binging = is_binge_active(user, content_queue, episodes_watched)
    return session_context.model_copy(update={"is_binging": binging})


def get_binge_summary(
    user: UserProfile,
    episodes_watched: int,
    content_queue: list[ContentItem],
) -> dict:
    """Return a summary of current binge state for logging and API responses."""
    active = is_binge_active(user, content_queue, episodes_watched)
    return {
        "is_binging": active,
        "episodes_watched": episodes_watched,
        "queue_remaining": len(content_queue),
        "ad_frequency_multiplier": binge_ad_frequency_multiplier(episodes_watched) if active else 1.0,
        "fatigue_sensitivity_multiplier": binge_fatigue_sensitivity_multiplier(episodes_watched) if active else 1.0,
    }
