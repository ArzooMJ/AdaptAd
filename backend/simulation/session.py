"""
Session simulator.

Generates a full streaming session for a user, producing AdOpportunity objects
at each natural break point. Handles binge detection and fatigue accumulation.

Bug fix: ads_seen_so_far is now dynamically updated during session evaluation,
not pre-computed. The SessionContext.ads_shown_this_session is mutated as
decisions are applied via apply_decision().
"""

import random
import uuid
from typing import Optional

from ..state import (
    AdCandidate,
    AdDecision,
    AdOpportunity,
    ContentItem,
    SessionContext,
    TimeOfDay,
    Season,
    UserProfile,
)
from ..config import config
from ..data.constants import SEASONS, TIME_OF_DAY_VALUES
from .fatigue import update_fatigue, should_force_suppress


def _current_season() -> Season:
    """Return current real-world season (Northern Hemisphere)."""
    from datetime import date
    month = date.today().month
    if month in (3, 4, 5):
        return Season.Spring
    elif month in (6, 7, 8):
        return Season.Summer
    elif month in (9, 10, 11):
        return Season.Fall
    else:
        return Season.Winter


def _current_time_of_day() -> TimeOfDay:
    """Approximate time of day from current hour."""
    from datetime import datetime
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return TimeOfDay.morning
    elif 12 <= hour < 18:
        return TimeOfDay.afternoon
    elif 18 <= hour < 23:
        return TimeOfDay.evening
    else:
        return TimeOfDay.latenight


def build_session_context(
    content: ContentItem,
    content_queue: list[ContentItem],
    time_of_day: Optional[TimeOfDay] = None,
    season: Optional[Season] = None,
    user: Optional[UserProfile] = None,
    episodes_watched: int = 0,
) -> SessionContext:
    """
    Construct an initial SessionContext for a session.

    Binge detection: is_binging is True when content_queue has 2+ items AND
    the user has already watched 1+ episode this session.
    """
    cfg = config.simulation
    is_binging = (
        len(content_queue) >= cfg.binge_queue_threshold
        and episodes_watched >= cfg.binge_episode_threshold
        and (user is None or user.binge_tendency > cfg.binge_tendency_threshold)
    )
    return SessionContext(
        time_of_day=time_of_day or _current_time_of_day(),
        season=season or _current_season(),
        ads_shown_this_session=0,
        session_duration_minutes=0,
        content=content,
        current_minute=0,
        content_queue=content_queue,
        is_binging=is_binging,
        session_fatigue_accumulator=0.0,
    )


def apply_decision(
    session_context: SessionContext,
    user: UserProfile,
    decision: AdDecision,
    current_minute: int,
    minutes_since_last_ad: int = 5,
) -> SessionContext:
    """
    Apply a decision to the session context.

    Updates ads_shown_this_session and session_fatigue_accumulator.
    This is the fix for the pre-computed ads_seen_so_far bug:
    we mutate the context here rather than pre-computing.
    """
    # Increment shown count only for SHOW and SOFTEN.
    ads_shown = session_context.ads_shown_this_session
    if decision in (AdDecision.SHOW, AdDecision.SOFTEN):
        ads_shown += 1
    updated = session_context.model_copy(
        update={
            "ads_shown_this_session": ads_shown,
            "current_minute": current_minute,
            "session_duration_minutes": max(
                session_context.session_duration_minutes, current_minute
            ),
        }
    )
    updated = update_fatigue(updated, user, decision, minutes_since_last_ad)
    return updated


def simulate_session(
    user: UserProfile,
    content: ContentItem,
    ad_pool: list[AdCandidate],
    content_queue: Optional[list[ContentItem]] = None,
    time_of_day: Optional[TimeOfDay] = None,
    season: Optional[Season] = None,
    seed: Optional[int] = None,
    episodes_watched: int = 0,
) -> tuple[list[AdOpportunity], SessionContext]:
    """
    Simulate a single content item's worth of viewing, generating AdOpportunity
    objects at each natural break point.

    Returns:
        opportunities: List of AdOpportunity objects, one per break point.
        final_context: The session context after all opportunities are processed.

    NOTE: The returned AdOpportunity objects have session_context snapshots taken
    BEFORE the decision at that break point. The caller must call apply_decision()
    after each decision to advance the context.
    """
    if content_queue is None:
        content_queue = []
    rng = random.Random(seed)

    if not content.natural_break_points:
        # No break points: no ad opportunities. Log and return empty.
        print(
            f"Warning: content '{content.title}' has no natural break points. "
            "No ad opportunities generated."
        )
        ctx = build_session_context(content, content_queue, time_of_day, season, user, episodes_watched)
        return [], ctx

    ctx = build_session_context(content, content_queue, time_of_day, season, user, episodes_watched)
    opportunities: list[AdOpportunity] = []
    prev_break = 0

    for break_minute in content.natural_break_points:
        # Check if session should end due to fatigue.
        if ctx.session_fatigue_accumulator > config.simulation.session_end_fatigue:
            break

        # Snapshot context BEFORE decision (ads_shown reflects state before this break).
        ctx_snapshot = ctx.model_copy(update={"current_minute": break_minute})

        # Pick a random ad from the pool for this opportunity.
        if not ad_pool:
            break
        ad_candidate = rng.choice(ad_pool)

        opportunity = AdOpportunity(
            user=user,
            ad_candidate=ad_candidate,
            session_context=ctx_snapshot,
            opportunity_id=str(uuid.uuid4()),
        )
        opportunities.append(opportunity)

        # Advance minute pointer. Caller applies actual decision later.
        prev_break = break_minute

    # Set final session duration.
    ctx = ctx.model_copy(update={"session_duration_minutes": content.duration_minutes})
    return opportunities, ctx


def simulate_binge_session(
    user: UserProfile,
    episode_queue: list[ContentItem],
    ad_pool: list[AdCandidate],
    time_of_day: Optional[TimeOfDay] = None,
    season: Optional[Season] = None,
    seed: Optional[int] = None,
) -> tuple[list[AdOpportunity], SessionContext]:
    """
    Simulate a multi-episode binge session.

    Returns all AdOpportunity objects across all episodes, with
    is_binging correctly set once the binge threshold is reached.
    """
    if not episode_queue:
        raise ValueError("episode_queue must not be empty")
    rng = random.Random(seed)
    all_opportunities: list[AdOpportunity] = []
    episodes_watched = 0
    # Run the first episode outside the binge context.
    remaining_queue = episode_queue[1:]
    opps, ctx = simulate_session(
        user=user,
        content=episode_queue[0],
        ad_pool=ad_pool,
        content_queue=remaining_queue,
        time_of_day=time_of_day,
        season=season,
        seed=rng.randint(0, 2**31),
        episodes_watched=episodes_watched,
    )
    all_opportunities.extend(opps)
    episodes_watched += 1

    for i, episode in enumerate(remaining_queue):
        queue_ahead = remaining_queue[i + 1:]
        opps, ctx = simulate_session(
            user=user,
            content=episode,
            ad_pool=ad_pool,
            content_queue=queue_ahead,
            time_of_day=time_of_day,
            season=season,
            seed=rng.randint(0, 2**31),
            episodes_watched=episodes_watched,
        )
        # Carry forward fatigue from previous episode.
        for opp in opps:
            carried_ctx = opp.session_context.model_copy(
                update={"session_fatigue_accumulator": ctx.session_fatigue_accumulator}
            )
            all_opportunities.append(
                opp.model_copy(update={"session_context": carried_ctx})
            )
        episodes_watched += 1
        if ctx.session_fatigue_accumulator > config.simulation.session_end_fatigue:
            break

    return all_opportunities, ctx
