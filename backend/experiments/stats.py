"""
Statistical tests for AdaptAd hypotheses.

Tests used:
- One-sample Wilcoxon signed-rank test against threshold (H1, H2, H3).
- Paired Wilcoxon signed-rank test between evolved and each baseline (H1).
- Holm-Bonferroni correction for multiple comparisons.

scipy is an optional dependency. If not installed, returns approximate results
using a fallback sign test.
"""

import math
from typing import Optional


def _sign_test_p_value(values: list[float], threshold: float) -> float:
    """
    Fallback sign test: proportion of values above threshold, two-sided approximation.

    Not as powerful as Wilcoxon but works without scipy.
    Uses normal approximation to binomial for n > 10.
    """
    n = len(values)
    if n == 0:
        return 1.0
    k = sum(1 for v in values if v > threshold)
    # Normal approximation: z = (k - n/2) / sqrt(n/4)
    z = (k - n / 2) / math.sqrt(n / 4)
    # Two-sided p-value approximation using error function.
    p = 2 * (1 - _normal_cdf(abs(z)))
    return round(max(0.0, min(1.0, p)), 4)


def _normal_cdf(x: float) -> float:
    """Approximation of normal CDF using the error function."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _wilcoxon_one_sample(values: list[float], threshold: float) -> dict:
    """
    One-sample Wilcoxon signed-rank test.

    H0: median(values) <= threshold
    H1: median(values) > threshold (one-sided)
    """
    try:
        from scipy.stats import wilcoxon
        diffs = [v - threshold for v in values]
        # Remove zeros (values exactly equal to threshold).
        diffs = [d for d in diffs if d != 0]
        if len(diffs) < 4:
            return {"statistic": None, "p_value": 1.0, "method": "insufficient_data"}
        stat, p = wilcoxon(diffs, alternative="greater")
        return {"statistic": float(stat), "p_value": round(float(p), 4), "method": "wilcoxon"}
    except ImportError:
        p = _sign_test_p_value(values, threshold)
        return {"statistic": None, "p_value": p, "method": "sign_test_fallback"}
    except Exception as e:
        return {"statistic": None, "p_value": 1.0, "method": f"error: {str(e)}"}


def _wilcoxon_paired(a: list[float], b: list[float]) -> dict:
    """
    Paired Wilcoxon signed-rank test between two lists.

    H0: no difference in medians.
    H1: a > b (one-sided).
    """
    if len(a) != len(b):
        min_len = min(len(a), len(b))
        a, b = a[:min_len], b[:min_len]

    try:
        from scipy.stats import wilcoxon
        diffs = [x - y for x, y in zip(a, b)]
        diffs = [d for d in diffs if d != 0]
        if len(diffs) < 4:
            return {"statistic": None, "p_value": 1.0, "method": "insufficient_data"}
        stat, p = wilcoxon(diffs, alternative="greater")
        return {"statistic": float(stat), "p_value": round(float(p), 4), "method": "wilcoxon"}
    except ImportError:
        diffs = [x - y for x, y in zip(a, b)]
        p = _sign_test_p_value(diffs, 0.0)
        return {"statistic": None, "p_value": p, "method": "sign_test_fallback"}
    except Exception as e:
        return {"statistic": None, "p_value": 1.0, "method": f"error: {str(e)}"}


def _holm_bonferroni(p_values: list[float], alpha: float = 0.05) -> list[bool]:
    """
    Holm-Bonferroni correction for multiple comparisons.

    Returns a list of booleans: True = reject null hypothesis at adjusted alpha.
    """
    n = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    reject = [False] * n
    for rank, (orig_idx, p) in enumerate(indexed):
        adjusted_alpha = alpha / (n - rank)
        if p <= adjusted_alpha:
            reject[orig_idx] = True
        else:
            # Once we fail to reject, all subsequent are also not rejected.
            break
    return reject


def run_statistical_tests(
    evolved_fitnesses: list[float],
    baseline_fitnesses: dict[str, list[float]],
    h1_threshold: float = 0.65,
    alpha: float = 0.05,
) -> dict:
    """
    Run all statistical tests for the experiment.

    Args:
        evolved_fitnesses: List of fitness values from N independent runs.
        baseline_fitnesses: Dict of baseline_name -> list of fitness values
                           (can be repeated single values for non-random baselines).
        h1_threshold: Threshold for H1 one-sample test.
        alpha: Significance level.

    Returns:
        Dict with test results for H1 (one-sample + pairwise vs baselines).
    """
    results = {}

    # H1 one-sample test: evolved fitness > 0.65.
    h1_one_sample = _wilcoxon_one_sample(evolved_fitnesses, h1_threshold)
    results["h1_one_sample"] = h1_one_sample
    results["h1_pvalue"] = h1_one_sample["p_value"]
    results["h1_significant"] = h1_one_sample["p_value"] < alpha

    # Pairwise tests against each baseline.
    pairwise_p_values = []
    pairwise_results = {}
    for name, base_fits in baseline_fitnesses.items():
        test = _wilcoxon_paired(evolved_fitnesses, base_fits)
        pairwise_results[f"vs_{name}"] = test
        pairwise_p_values.append(test["p_value"])

    # Holm-Bonferroni correction.
    if pairwise_p_values:
        rejected = _holm_bonferroni(pairwise_p_values, alpha=alpha)
        baseline_names = list(baseline_fitnesses.keys())
        for i, name in enumerate(baseline_names):
            pairwise_results[f"vs_{name}"]["holm_bonferroni_reject"] = rejected[i]

    results["pairwise_vs_baselines"] = pairwise_results
    results["method_note"] = (
        "Wilcoxon signed-rank used when scipy available. "
        "Sign test fallback otherwise. "
        "Holm-Bonferroni applied to multiple comparisons."
    )

    return results


def run_sensitivity_analysis(
    users, content, ads,
    base_chromosome,
    perturbation_size: float = 0.2,
) -> dict:
    """
    Perturb each gene by +/- perturbation_size and measure fitness change.

    Returns a dict of gene_name -> mean_absolute_fitness_change.
    This identifies which genes the system is most sensitive to.
    """
    from ..simulation.engine import evaluate_policy
    from ..state import Chromosome
    from ..experiments.runner import _chromosome_to_policy

    base_policy = _chromosome_to_policy(base_chromosome)
    base_result = evaluate_policy(base_policy, users, content, ads)
    base_fitness = base_result["fitness"]

    gene_names = Chromosome.gene_names()
    sensitivities = {}

    for i, gene_name in enumerate(gene_names):
        vec = base_chromosome.to_vector()
        deltas = []
        for sign in [+1, -1]:
            perturbed_vec = vec[:]
            perturbed_vec[i] = max(0.0, min(1.0, vec[i] + sign * perturbation_size))
            perturbed_chrom = Chromosome.from_vector(perturbed_vec)
            policy = _chromosome_to_policy(perturbed_chrom)
            result = evaluate_policy(policy, users, content, ads)
            deltas.append(abs(result["fitness"] - base_fitness))
        sensitivities[gene_name] = round(sum(deltas) / len(deltas), 4)

    # Sort by sensitivity descending.
    return dict(sorted(sensitivities.items(), key=lambda x: x[1], reverse=True))
