"""
Metric computation for H1, H2, H3 hypotheses.

H1: Evolved fitness > 0.65 (mean across runs).
H2: Post-session fatigue < 0.40 AND ad relevance > 70%.
H3: Strategy diversity index (normalized Shannon entropy) > 0.15.
"""

import math
from ..state import AdDecision


def compute_diversity_index(decision_counts: dict[str, int]) -> float:
    """
    Compute normalized Shannon entropy over decision type distribution.

    Range: [0, 1]. 0 = all decisions identical. 1 = perfectly uniform.
    The max entropy for 4 categories is log2(4) = 2.0.
    """
    total = sum(decision_counts.values())
    if total == 0:
        return 0.0
    max_entropy = math.log2(4)  # 4 decision types.
    entropy = 0.0
    for count in decision_counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return round(entropy / max_entropy, 4)


def compute_h1(evolved_fitnesses: list[float], baseline_results: dict) -> dict:
    """
    H1: Mean evolved fitness > 0.65, significantly higher than all baselines.

    Returns pass/fail and supporting statistics.
    """
    if not evolved_fitnesses:
        return {"passes": False, "mean": 0.0, "std": 0.0, "threshold": 0.65}

    mean = sum(evolved_fitnesses) / len(evolved_fitnesses)
    variance = sum((f - mean) ** 2 for f in evolved_fitnesses) / max(1, len(evolved_fitnesses) - 1)
    std = math.sqrt(variance)

    baseline_comparisons = {}
    for name, result in baseline_results.items():
        baseline_fitness = result["fitness"]
        # Proportion of runs where evolved outperformed this baseline.
        prop_better = sum(1 for f in evolved_fitnesses if f > baseline_fitness) / len(evolved_fitnesses)
        baseline_comparisons[name] = {
            "baseline_fitness": round(baseline_fitness, 4),
            "prop_runs_better": round(prop_better, 4),
            "mean_delta": round(mean - baseline_fitness, 4),
        }

    return {
        "passes": mean > 0.65,
        "threshold": 0.65,
        "mean": round(mean, 4),
        "std": round(std, 4),
        "n_runs": len(evolved_fitnesses),
        "baseline_comparisons": baseline_comparisons,
    }


def compute_h2(
    evolved_satisfactions: list[float],
    evolved_fatigues: list[float],
    fatigue_threshold: float = 0.40,
    relevance_threshold: float = 0.70,
) -> dict:
    """
    H2: Mean fatigue < 0.40 AND mean satisfaction (as proxy for relevance) > 0.70.

    We use satisfaction as a proxy for relevance because the simulation
    satisfaction score is primarily driven by ad-user relevance match.
    """
    if not evolved_fatigues:
        return {
            "fatigue_passes": False, "relevance_passes": False,
            "mean_fatigue": 0.0, "mean_satisfaction": 0.0
        }

    mean_fatigue = sum(evolved_fatigues) / len(evolved_fatigues)
    mean_sat = sum(evolved_satisfactions) / len(evolved_satisfactions) if evolved_satisfactions else 0.0

    # Proportion of runs passing each threshold.
    prop_fatigue = sum(1 for f in evolved_fatigues if f < fatigue_threshold) / len(evolved_fatigues)
    prop_relevance = sum(1 for s in evolved_satisfactions if s > relevance_threshold) / max(1, len(evolved_satisfactions))

    return {
        "fatigue_passes": mean_fatigue < fatigue_threshold,
        "relevance_passes": mean_sat > relevance_threshold,
        "fatigue_threshold": fatigue_threshold,
        "relevance_threshold": relevance_threshold,
        "mean_fatigue": round(mean_fatigue, 4),
        "mean_satisfaction": round(mean_sat, 4),
        "prop_runs_fatigue_pass": round(prop_fatigue, 4),
        "prop_runs_relevance_pass": round(prop_relevance, 4),
    }


def compute_h3(evolved_diversities: list[float], diversity_threshold: float = 0.15) -> dict:
    """
    H3: Mean strategy diversity index > 0.15.

    Diversity index is normalized Shannon entropy over SHOW/SOFTEN/DELAY/SUPPRESS.
    """
    if not evolved_diversities:
        return {"passes": False, "mean": 0.0, "threshold": diversity_threshold}

    mean = sum(evolved_diversities) / len(evolved_diversities)
    variance = sum((d - mean) ** 2 for d in evolved_diversities) / max(1, len(evolved_diversities) - 1)
    std = math.sqrt(variance)
    prop_pass = sum(1 for d in evolved_diversities if d > diversity_threshold) / len(evolved_diversities)

    return {
        "passes": mean > diversity_threshold,
        "threshold": diversity_threshold,
        "mean": round(mean, 4),
        "std": round(std, 4),
        "prop_runs_pass": round(prop_pass, 4),
        "n_runs": len(evolved_diversities),
    }


def compute_sensitivity_analysis(
    base_results: dict,
    perturbed_results: dict[str, dict],
) -> dict:
    """
    Compute how sensitive the fitness metric is to parameter perturbations.

    Args:
        base_results: Results from the baseline evolved policy.
        perturbed_results: dict of parameter_name -> results with that param changed.

    Returns:
        dict of parameter_name -> sensitivity (absolute change in fitness).
    """
    base_fitness = base_results.get("fitness", 0.0)
    sensitivity = {}
    for param, results in perturbed_results.items():
        delta = abs(results.get("fitness", 0.0) - base_fitness)
        sensitivity[param] = round(delta, 4)
    # Sort by sensitivity descending.
    return dict(sorted(sensitivity.items(), key=lambda x: x[1], reverse=True))
