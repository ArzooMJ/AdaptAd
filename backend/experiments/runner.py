"""
Experiment runner.

Runs the full AdaptAd experiment pipeline:
1. Evolve chromosome for N independent runs.
2. Evaluate evolved policy against all baselines.
3. Run ablation conditions.
4. Compute H1/H2/H3 metrics.
5. Run statistical tests.
6. Save results to JSON.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..data.generate import generate_users
from ..data.content_library import generate_content_library
from ..data.ad_inventory import generate_ad_inventory
from ..ga.engine import GAEngine
from ..ga.storage import save_chromosome
from ..simulation.engine import (
    evaluate_policy,
    policy_always_show,
    policy_random,
    policy_frequency_cap,
)
from ..state import Chromosome
from .ablations import run_ablations
from .metrics import compute_h1, compute_h2, compute_h3, compute_diversity_index
from .stats import run_statistical_tests


def run_single_evolution(
    users, content, ads, seed: int, max_generations: int = 50
) -> tuple[Chromosome, list[dict]]:
    """
    Run one independent GA evolution.

    Returns (best_chromosome, generation_history).
    """
    engine = GAEngine(
        users=users,
        content_items=content,
        ad_pool=ads,
        seed=seed,
    )
    engine.initialize()
    history = []
    for stats in engine.run(max_generations=max_generations):
        history.append(stats)
    return engine.best_chromosome, history


def run_full_experiment(
    num_runs: int = 30,
    max_generations: int = 50,
    num_users: int = 200,
    output_dir: str = "results",
    seed_offset: int = 0,
    verbose: bool = True,
) -> dict:
    """
    Run the full experiment pipeline.

    Args:
        num_runs: Number of independent GA runs (30 for paper).
        max_generations: Max generations per run.
        num_users: Number of synthetic users.
        output_dir: Directory to save results JSON.
        seed_offset: Add to seed for reproducibility variants.
        verbose: Print progress.

    Returns:
        Full results dict with all metrics and statistical test results.
    """
    start_time = time.time()
    if verbose:
        print(f"Starting full experiment: {num_runs} runs x {max_generations} generations")

    # Generate shared data (same across all runs for fair comparison).
    users = generate_users(count=num_users, seed=42)
    content = generate_content_library(count=100, seed=42)
    ads = generate_ad_inventory(count=80, seed=42)

    # Run baseline policies once (deterministic).
    if verbose:
        print("Evaluating baselines...")
    baseline_results = {}
    for name, fn in [
        ("always_show", policy_always_show),
        ("random", lambda o: policy_random(o)),
        ("frequency_cap", policy_frequency_cap),
    ]:
        baseline_results[name] = evaluate_policy(fn, users, content, ads)
        if verbose:
            r = baseline_results[name]
            print(f"  {name}: fitness={r['fitness']:.4f} sat={r['satisfaction']:.4f} "
                  f"rev={r['revenue']:.4f} fatigue={r['fatigue']:.4f}")

    # Run N independent GA evolutions.
    evolved_fitnesses = []
    evolved_satisfactions = []
    evolved_revenues = []
    evolved_fatigues = []
    evolved_diversities = []
    best_overall_fitness = 0.0
    best_overall_chromosome = None
    all_histories = []

    for run_idx in range(num_runs):
        seed = run_idx + seed_offset + 100
        if verbose and (run_idx % 5 == 0 or run_idx == num_runs - 1):
            print(f"  Run {run_idx + 1}/{num_runs}...")

        best_chrom, history = run_single_evolution(users, content, ads, seed, max_generations)
        if best_chrom is None:
            continue

        # Evaluate the evolved policy.
        evolved_policy = _chromosome_to_policy(best_chrom)
        eval_result = evaluate_policy(evolved_policy, users, content, ads)

        evolved_fitnesses.append(eval_result["fitness"])
        evolved_satisfactions.append(eval_result["satisfaction"])
        evolved_revenues.append(eval_result["revenue"])
        evolved_fatigues.append(eval_result["fatigue"])
        evolved_diversities.append(
            compute_diversity_index(eval_result["decision_counts"])
        )
        all_histories.append({"run": run_idx, "history": history})

        if eval_result["fitness"] > best_overall_fitness:
            best_overall_fitness = eval_result["fitness"]
            best_overall_chromosome = best_chrom
            best_overall_chromosome.fitness = eval_result["fitness"]

    if verbose:
        print(f"Evolution complete. Best fitness: {best_overall_fitness:.4f}")
        print(f"Mean fitness across {len(evolved_fitnesses)} runs: "
              f"{sum(evolved_fitnesses)/len(evolved_fitnesses):.4f}")

    # Save best chromosome.
    if best_overall_chromosome:
        save_chromosome(best_overall_chromosome, label="experiment_best")

    # Run ablation conditions.
    if verbose:
        print("Running ablations...")
    ablation_results = run_ablations(users, content, ads)

    # Compute H1, H2, H3 metrics.
    h1 = compute_h1(evolved_fitnesses, baseline_results)
    h2 = compute_h2(evolved_satisfactions, evolved_fatigues)
    h3 = compute_h3(evolved_diversities)

    # Statistical tests.
    stat_results = run_statistical_tests(
        evolved_fitnesses=evolved_fitnesses,
        baseline_fitnesses={k: [v["fitness"]] * num_runs for k, v in baseline_results.items()},
        h1_threshold=0.65,
    )

    elapsed = time.time() - start_time
    if verbose:
        print(f"\nDone in {elapsed:.1f}s")
        print(f"H1 (fitness > 0.65): {'PASS' if h1['passes'] else 'FAIL'} "
              f"(mean={h1['mean']:.4f}, p={stat_results.get('h1_pvalue', 'N/A')})")
        print(f"H2 (fatigue < 0.40): {'PASS' if h2['fatigue_passes'] else 'FAIL'} "
              f"(mean={h2['mean_fatigue']:.4f})")
        print(f"H3 (diversity > 0.15): {'PASS' if h3['passes'] else 'FAIL'} "
              f"(mean={h3['mean']:.4f})")

    results = {
        "experiment_date": datetime.utcnow().isoformat(),
        "num_runs": num_runs,
        "max_generations": max_generations,
        "num_users": num_users,
        "elapsed_seconds": round(elapsed, 2),
        "baselines": baseline_results,
        "evolved": {
            "fitnesses": evolved_fitnesses,
            "mean_fitness": round(sum(evolved_fitnesses) / max(1, len(evolved_fitnesses)), 4),
            "mean_satisfaction": round(sum(evolved_satisfactions) / max(1, len(evolved_satisfactions)), 4),
            "mean_revenue": round(sum(evolved_revenues) / max(1, len(evolved_revenues)), 4),
            "mean_fatigue": round(sum(evolved_fatigues) / max(1, len(evolved_fatigues)), 4),
            "mean_diversity": round(sum(evolved_diversities) / max(1, len(evolved_diversities)), 4),
            "best_chromosome": best_overall_chromosome.to_vector() if best_overall_chromosome else None,
        },
        "ablations": ablation_results,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "statistical_tests": stat_results,
        "generation_histories": all_histories[:5],  # Save first 5 for plotting.
    }

    # Write results to disk.
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"experiment_{timestamp}.json"
    out_path.write_text(json.dumps(results, indent=2))
    if verbose:
        print(f"Results saved to {out_path}")

    return results


def _chromosome_to_policy(chromosome: Chromosome):
    """
    Convert a chromosome into a callable policy function for evaluate_policy().
    Uses the two-agent math scoring (no LLM).
    """
    from ..agents.user_advocate import score_user_advocate
    from ..agents.advertiser_advocate import score_advertiser_advocate
    from ..agents.negotiator import negotiate
    from ..simulation.fatigue import should_force_suppress
    from ..state import AdDecision

    def policy(opportunity):
        if should_force_suppress(opportunity.session_context):
            return AdDecision.SUPPRESS
        ua = score_user_advocate(
            opportunity.user, opportunity.ad_candidate,
            opportunity.session_context, chromosome
        )
        adv = score_advertiser_advocate(
            opportunity.user, opportunity.ad_candidate,
            opportunity.session_context, chromosome
        )
        result = negotiate(
            ua, adv, chromosome,
            opportunity.user.id,
            opportunity.ad_candidate.id,
            opportunity.opportunity_id,
        )
        return result.decision

    return policy


if __name__ == "__main__":
    results = run_full_experiment(num_runs=5, max_generations=10, verbose=True)
    print(json.dumps(results["evolved"], indent=2))
