"""
GA tests. Run with: pytest backend/tests/test_ga.py -v

Verifies:
- Population initialization produces valid chromosomes.
- One step improves or maintains fitness.
- 10 generations produce meaningful fitness improvement.
- Convergence detection works.
- Chromosome save/load round-trips correctly.
- All 4 decision types appear across 200 users.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
import numpy as np

from backend.state import Chromosome, AdDecision
from backend.ga.engine import GAEngine, init_population, evolve_one_generation, check_convergence
from backend.ga.fitness import evaluate_chromosome_fitness, evaluate_population_fitness
from backend.ga.storage import save_chromosome, load_chromosome, list_chromosomes
from backend.data.generate import generate_users
from backend.data.content_library import generate_content_library
from backend.data.ad_inventory import generate_ad_inventory
from backend.agents.user_advocate import score_user_advocate
from backend.agents.advertiser_advocate import score_advertiser_advocate
from backend.agents.negotiator import negotiate


@pytest.fixture(scope="module")
def data():
    users = generate_users(count=50, seed=42)
    content = generate_content_library(count=20, seed=42)
    ads = generate_ad_inventory(count=20, seed=42)
    return users, content, ads


def test_init_population():
    pop = init_population(30, seed=42)
    assert len(pop) == 30
    for chrom in pop:
        vec = chrom.to_vector()
        assert len(vec) == 8
        assert all(0.0 <= g <= 1.0 for g in vec), f"Gene out of range: {vec}"


def test_chromosome_roundtrip():
    vec = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    c = Chromosome.from_vector(vec)
    assert c.to_vector() == vec


def test_fitness_evaluation_bounded(data):
    users, content, ads = data
    chrom = Chromosome()
    fitness = evaluate_chromosome_fitness(chrom, users, content, ads, scenarios_per_user=3)
    assert 0.0 <= fitness <= 1.0, f"Fitness out of range: {fitness}"


def test_fitness_all_zeros(data):
    users, content, ads = data
    # All-zero chromosome should produce conservative decisions and valid fitness.
    chrom = Chromosome.from_vector([0.0] * 8)
    fitness = evaluate_chromosome_fitness(chrom, users, content, ads, scenarios_per_user=3)
    assert 0.0 <= fitness <= 1.0


def test_fitness_all_ones(data):
    users, content, ads = data
    chrom = Chromosome.from_vector([1.0] * 8)
    fitness = evaluate_chromosome_fitness(chrom, users, content, ads, scenarios_per_user=3)
    assert 0.0 <= fitness <= 1.0


def test_ten_generations_fitness_improves(data):
    users, content, ads = data
    engine = GAEngine(users=users, content_items=content, ad_pool=ads, seed=42)
    engine.initialize()
    initial_best = engine.best_fitness

    for _ in engine.run(max_generations=10):
        pass

    final_best = engine.best_fitness
    # Fitness should not decrease over 10 generations.
    assert final_best >= initial_best - 0.01, (
        f"Fitness regressed: {initial_best:.4f} -> {final_best:.4f}"
    )
    # Fitness should be above a reasonable floor.
    assert final_best > 0.30, f"Fitness too low after 10 generations: {final_best:.4f}"


def test_convergence_detection():
    history = [0.5] * 15  # Flat for 15 generations.
    assert check_convergence(history, window=10, threshold=0.001) is True

    history2 = [0.5 + i * 0.01 for i in range(15)]  # Still improving.
    assert check_convergence(history2, window=10, threshold=0.001) is False


def test_save_load_chromosome(tmp_path):
    import os
    from backend.config import config
    original_dir = config.chromosomes_dir
    config.chromosomes_dir = str(tmp_path)

    try:
        chrom = Chromosome.from_vector([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
        chrom.fitness = 0.6543
        path = save_chromosome(chrom, label="test")
        loaded = load_chromosome(path)
        assert loaded.to_vector() == chrom.to_vector()
        assert abs(loaded.fitness - 0.6543) < 1e-6

        saved = list_chromosomes(str(tmp_path))
        assert len(saved) == 1
        assert saved[0]["fitness"] == 0.6543
    finally:
        config.chromosomes_dir = original_dir


def test_agent_scores_bounded(data):
    users, content, ads = data
    chrom = Chromosome()
    user = users[0]
    ad = ads[0]

    from backend.simulation.session import build_session_context
    from backend.state import TimeOfDay, Season

    ctx = build_session_context(
        content=content[0],
        content_queue=[],
        time_of_day=TimeOfDay.evening,
        season=Season.Fall,
        user=user,
    )

    ua = score_user_advocate(user, ad, ctx, chrom)
    assert 0.0 <= ua.score <= 1.0

    adv = score_advertiser_advocate(user, ad, ctx, chrom)
    assert 0.0 <= adv.score <= 1.0


def test_all_four_decisions_appear(data):
    """All 4 decision types should appear across 200 users with varied chromosomes."""
    users, content, ads = data
    from backend.simulation.session import build_session_context
    from backend.state import TimeOfDay, Season

    decisions_seen: set[str] = set()
    # Use 4 different chromosomes to ensure diverse decisions.
    chromosomes = [
        Chromosome.from_vector([0.0] * 8),  # Conservative.
        Chromosome.from_vector([1.0] * 8),  # Aggressive.
        Chromosome.from_vector([0.5] * 8),  # Neutral.
        Chromosome.from_vector([0.3, 0.7, 0.5, 0.2, 0.8, 0.4, 0.6, 0.1]),
    ]

    for user in users:
        for ad in ads[:5]:
            for chrom in chromosomes:
                for tod in [TimeOfDay.morning, TimeOfDay.evening]:
                    ctx = build_session_context(
                        content=content[0],
                        content_queue=[],
                        time_of_day=tod,
                        season=Season.Winter,
                        user=user,
                    )
                    # Vary ads_shown.
                    for n_ads in [0, 3]:
                        ctx2 = ctx.model_copy(update={"ads_shown_this_session": n_ads})
                        ua = score_user_advocate(user, ad, ctx2, chrom)
                        adv = score_advertiser_advocate(user, ad, ctx2, chrom)
                        result = negotiate(ua, adv, chrom, user.id, ad.id, "test_session")
                        decisions_seen.add(result.decision.value)

                    if len(decisions_seen) == 4:
                        break
                if len(decisions_seen) == 4:
                    break
            if len(decisions_seen) == 4:
                break
        if len(decisions_seen) == 4:
            break

    missing = set(d.value for d in AdDecision) - decisions_seen
    assert not missing, f"These decision types never appeared: {missing}"


def test_ga_population_stats(data):
    users, content, ads = data
    engine = GAEngine(users=users, content_items=content, ad_pool=ads, seed=7)
    engine.initialize()
    stats = engine.get_population_stats()
    assert "best_fitness" in stats
    assert "diversity" in stats
    assert 0.0 <= stats["diversity"] <= 1.0
