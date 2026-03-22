"""
Fatigue dynamics state machine.

Tracks dynamic session fatigue, which is separate from a user's base fatigue_level.
The session fatigue accumulator starts at 0 and is clamped to [base_fatigue, 1.0].
"""

from ..config import config
from ..state import AdDecision, SessionContext, UserProfile


def update_fatigue(
    session_context: SessionContext,
    user: UserProfile,
    decision: AdDecision,
    minutes_since_last_ad: int = 0,
) -> SessionContext:
    """
    Apply fatigue increment for a decision and decay for ad-free viewing.

    Returns a new SessionContext with updated session_fatigue_accumulator.
    The accumulator never falls below the user's base fatigue_level.
    """
    cfg = config.fatigue
    increment_map = {
        AdDecision.SHOW: cfg.show_increment,
        AdDecision.SOFTEN: cfg.soften_increment,
        AdDecision.DELAY: cfg.delay_increment,
        AdDecision.SUPPRESS: cfg.suppress_increment,
    }
    increment = increment_map.get(decision, 0.0)
    # Decay: reward ad-free viewing time since last ad opportunity.
    decay = cfg.decay_per_minute * max(0, minutes_since_last_ad)
    new_fatigue = session_context.session_fatigue_accumulator + increment - decay
    # Floor is the user's base fatigue (never fully recovered below their baseline).
    new_fatigue = max(user.fatigue_level, min(1.0, new_fatigue))
    return session_context.model_copy(update={"session_fatigue_accumulator": new_fatigue})


def should_force_suppress(session_context: SessionContext) -> bool:
    """Returns True if fatigue is high enough to force SUPPRESS regardless of scoring."""
    return session_context.session_fatigue_accumulator > config.fatigue.force_suppress_threshold


def fatigue_penalty(session_context: SessionContext) -> float:
    """
    Returns an additional score penalty when fatigue is elevated but below force-suppress.
    Applied by agents before their final score is output.
    """
    if session_context.session_fatigue_accumulator > config.fatigue.penalty_threshold:
        return config.fatigue.penalty_amount
    return 0.0


def get_effective_fatigue(session_context: SessionContext, user: UserProfile) -> float:
    """
    Returns the effective fatigue for scoring.

    Uses session accumulator when it is higher than the user's base level,
    otherwise uses the base level.
    """
    return max(user.fatigue_level, session_context.session_fatigue_accumulator)
