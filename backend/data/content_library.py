"""
Synthetic content library.

Generates 100 content items with genre, mood, duration, and intensity metadata.
"""

import random
from pathlib import Path
from typing import Optional

from ..state import ContentItem, ContentMood
from .constants import GENRES

DEFAULT_SEED = 42

# Mood per genre. Multiple moods listed with relative weights.
GENRE_MOODS: dict[str, list[tuple[str, float]]] = {
    "Action":      [("energetic", 0.50), ("intense", 0.35), ("uplifting", 0.15)],
    "Comedy":      [("playful", 0.55), ("uplifting", 0.35), ("calm", 0.10)],
    "Drama":       [("intense", 0.35), ("dark", 0.30), ("calm", 0.25), ("uplifting", 0.10)],
    "Sci-Fi":      [("energetic", 0.35), ("intense", 0.35), ("calm", 0.20), ("dark", 0.10)],
    "Horror":      [("dark", 0.60), ("intense", 0.35), ("calm", 0.05)],
    "Documentary": [("calm", 0.55), ("uplifting", 0.25), ("energetic", 0.20)],
    "Romance":     [("uplifting", 0.45), ("calm", 0.35), ("playful", 0.20)],
    "Thriller":    [("intense", 0.45), ("dark", 0.35), ("energetic", 0.20)],
    "Animation":   [("playful", 0.45), ("uplifting", 0.35), ("energetic", 0.20)],
    "Fantasy":     [("uplifting", 0.35), ("energetic", 0.30), ("intense", 0.20), ("dark", 0.15)],
}

# Typical duration ranges by content type.
MOVIE_DURATION_RANGE = (80, 150)
EPISODE_DURATION_RANGE = (22, 60)

# Series titles. 10 series x up to 3 episodes each = 30 series content items.
# The remaining 70 are movies.
SERIES_TITLES = [
    "Darkwave Chronicles",
    "The Signal",
    "Offworld",
    "Pulse City",
    "Ironhaven",
    "Velvet Underground",
    "The Reckoning",
    "Starfall",
    "Night Protocol",
    "Hollow Earth",
]

MOVIE_TITLES = [
    "Edge of Tomorrow", "Lantern Light", "The Forgotten Shore", "Cascade",
    "Iron Meridian", "The Blue Divide", "Shadow Protocol", "Earthbound",
    "Lone Circuit", "The Pale Hour", "Fracture Point", "Neon Descent",
    "The Crossing", "Amber Dawn", "Gravity Wells", "Mirror Stage",
    "Quantum Breach", "The Long Winter", "Ember Falls", "Hollow Signal",
    "Deep Fracture", "The Outer Rim", "Shoreline", "Beneath the Static",
    "Fault Lines", "The Quiet Storm", "Override", "Solar Drift",
    "Threshold", "The Vanishing Point", "Blind Orbit", "Cold Harbor",
    "The Final Relay", "Drift Code", "Sunken Archive", "The Last Signal",
    "Terminal Bloom", "Static Fields", "Warped Horizon", "Night Current",
    "Parallel Rift", "Void Transit", "The Open Circuit", "Signal Lost",
    "Crossfire Protocol", "Dead Orbit", "Fractured Light", "Midnight Axis",
    "Residual Echo", "The Burning Grid", "Shallow Grave", "Ironclad",
    "Pattern Break", "The End Sequence", "Zero Hour", "Rogue Frequency",
    "Final Approach", "The Last Descent", "Blackout Protocol", "Static Bloom",
    "Cold Wire", "The Drift", "Phantom Layer", "Deep Signal",
    "Breach Point", "Lost Frequency", "The Iron Shore", "Sunfall",
    "Dark Meridian", "Horizon Shift",
]


def _generate_intensity_curve(
    duration: int, mood: ContentMood, rng: random.Random
) -> list[float]:
    """
    Generate a per-minute intensity curve.

    Base intensity is shaped by mood. High-intensity genres have more peaks.
    """
    mood_baseline: dict[str, float] = {
        "calm": 0.30,
        "uplifting": 0.45,
        "playful": 0.40,
        "energetic": 0.55,
        "intense": 0.65,
        "dark": 0.60,
    }
    baseline = mood_baseline.get(mood.value, 0.5)
    curve = []
    current = baseline
    for minute in range(duration):
        # Random walk around baseline with momentum.
        delta = rng.gauss(0, 0.08)
        current = max(0.05, min(0.95, current + delta))
        # Pull toward baseline slowly.
        current = current * 0.85 + baseline * 0.15
        # Climax tendency: intensity peaks near the last 15% of content.
        if minute > duration * 0.80:
            current = min(0.95, current + 0.04)
        curve.append(round(current, 3))
    return curve


def _natural_break_points(
    duration: int, is_series: bool, intensity_curve: list[float], rng: random.Random
) -> list[int]:
    """
    Place break points at low-intensity minutes, avoiding first/last 5 min.

    Episodes (22-60 min) get 2-4 breaks.
    Movies (80+ min) get 4-7 breaks.
    """
    buffer = 5
    start = buffer
    end = duration - buffer
    if end <= start:
        return []
    eligible = list(range(start, end + 1))
    if not eligible:
        return []
    # Prefer minutes where intensity is low (scene transitions).
    weighted = [(m, 1.0 / (intensity_curve[m] + 0.1)) for m in eligible]
    weights = [w for _, w in weighted]
    minutes = [m for m, _ in weighted]
    if is_series:
        num_breaks = rng.randint(2, min(4, len(eligible)))
    else:
        num_breaks = rng.randint(4, min(7, len(eligible)))
    num_breaks = min(num_breaks, len(eligible))
    chosen = rng.choices(minutes, weights=weights, k=num_breaks * 3)
    # Deduplicate and sort.
    seen: set[int] = set()
    result: list[int] = []
    for m in sorted(chosen):
        if m not in seen:
            seen.add(m)
            result.append(m)
        if len(result) >= num_breaks:
            break
    return sorted(result)


def generate_content_library(
    count: int = 100, seed: Optional[int] = DEFAULT_SEED
) -> list[ContentItem]:
    rng = random.Random(seed)
    items: list[ContentItem] = []

    # First 30 items are series episodes (10 series, 3 episodes each).
    item_id = 1
    for series_idx, series_title in enumerate(SERIES_TITLES):
        genre = rng.choice(list(GENRE_MOODS.keys()))
        mood_choices = GENRE_MOODS[genre]
        moods, mood_weights = zip(*mood_choices)
        series_season = 1
        for ep_num in range(1, 4):
            mood = ContentMood(rng.choices(moods, weights=mood_weights, k=1)[0])
            duration = rng.randint(*EPISODE_DURATION_RANGE)
            intensity = _generate_intensity_curve(duration, mood, rng)
            breaks = _natural_break_points(duration, True, intensity, rng)
            items.append(
                ContentItem(
                    id=item_id,
                    title=f"{series_title} S{series_season}E{ep_num}",
                    genre=genre,
                    duration_minutes=duration,
                    mood=mood,
                    episode_number=ep_num,
                    season_number=series_season,
                    is_series=True,
                    natural_break_points=breaks,
                    intensity_curve=intensity,
                )
            )
            item_id += 1

    # Remaining items are movies.
    movie_titles_shuffled = MOVIE_TITLES[:]
    rng.shuffle(movie_titles_shuffled)
    for i in range(count - 30):
        title = movie_titles_shuffled[i % len(movie_titles_shuffled)]
        if i >= len(movie_titles_shuffled):
            title = f"{title} ({i // len(movie_titles_shuffled) + 1})"
        genre = rng.choice(list(GENRE_MOODS.keys()))
        mood_choices = GENRE_MOODS[genre]
        moods, mood_weights = zip(*mood_choices)
        mood = ContentMood(rng.choices(moods, weights=mood_weights, k=1)[0])
        duration = rng.randint(*MOVIE_DURATION_RANGE)
        intensity = _generate_intensity_curve(duration, mood, rng)
        breaks = _natural_break_points(duration, False, intensity, rng)
        items.append(
            ContentItem(
                id=item_id,
                title=title,
                genre=genre,
                duration_minutes=duration,
                mood=mood,
                episode_number=None,
                season_number=None,
                is_series=False,
                natural_break_points=breaks,
                intensity_curve=intensity,
            )
        )
        item_id += 1

    return items[:count]


def load_or_generate_content(
    cache_path: Optional[str] = None,
    count: int = 100,
    seed: Optional[int] = DEFAULT_SEED,
) -> list[ContentItem]:
    import json

    if cache_path is not None:
        p = Path(cache_path)
        if p.exists():
            try:
                raw = json.loads(p.read_text())
                return [ContentItem.model_validate(item) for item in raw]
            except Exception as e:
                print(f"Warning: could not load content cache from {cache_path}: {e}. Regenerating.")

    items = generate_content_library(count=count, seed=seed)

    if cache_path is not None:
        try:
            p = Path(cache_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps([item.model_dump() for item in items], indent=2))
        except Exception as e:
            print(f"Warning: could not save content cache to {cache_path}: {e}")

    return items


if __name__ == "__main__":
    library = generate_content_library(count=10, seed=42)
    for item in library:
        print(
            f"  {item.id:3d} | {item.title:<40} | {item.genre:<12} | "
            f"{item.mood.value:<10} | {item.duration_minutes}min | "
            f"breaks={item.natural_break_points}"
        )
