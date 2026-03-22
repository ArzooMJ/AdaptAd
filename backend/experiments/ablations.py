"""
Ablation study conditions.

Four conditions:
1. Full system: GA + two-agent negotiation (User Advocate + Advertiser Advocate).
2. GA only: use GA fitness score directly as decision signal, no agent split.
3. Agents without GA: default chromosome (all 0.5 genes).
4. Single agent: User Advocate only, or Advertiser Advocate only.
"""

from ..state import AdDecision, AdOpportunity, Chromosome
from ..simulation.engine import evaluate_policy
from ..simulation.fatigue import should_force_suppress


def _full_system_policy(chromosome: Chromosome):
    """Full two-agent system with evolved chromosome."""
    from ..agents.user_advocate import score_user_advocate
    from ..agents.advertiser_advocate import score_advertiser_advocate
    from ..agents.negotiator import negotiate

    def policy(opp: AdOpportunity) -> AdDecision:
        if should_force_suppress(opp.session_context):
            return AdDecision.SUPPRESS
        ua = score_user_advocate(opp.user, opp.ad_candidate, opp.session_context, chromosome)
        adv = score_advertiser_advocate(opp.user, opp.ad_candidate, opp.session_context, chromosome)
        result = negotiate(ua, adv, chromosome, opp.user.id, opp.ad_candidate.id, opp.opportunity_id)
        return result.decision

    return policy


def _ga_only_policy(chromosome: Chromosome):
    """
    GA only: use raw fitness-derived score without agent split.

    Combines user and advertiser scoring into a single score using equal
    weighting (0.5/0.5) and maps directly to decision thresholds.
    """
    from ..agents.user_advocate import score_user_advocate
    from ..agents.advertiser_advocate import score_advertiser_advocate
    from ..config import config

    def policy(opp: AdOpportunity) -> AdDecision:
        if should_force_suppress(opp.session_context):
            return AdDecision.SUPPRESS
        ua = score_user_advocate(opp.user, opp.ad_candidate, opp.session_context, chromosome)
        adv = score_advertiser_advocate(opp.user, opp.ad_candidate, opp.session_context, chromosome)
        # Equal weighting instead of the tuned 0.55/0.45 split.
        combined = (ua.score + adv.score) / 2.0
        show_thresh = 0.45 + chromosome.frequency_threshold * 0.35
        soften_thresh = show_thresh - 0.15
        delay_thresh = soften_thresh - 0.15
        if combined >= show_thresh:
            return AdDecision.SHOW
        elif combined >= soften_thresh:
            return AdDecision.SOFTEN
        elif combined >= delay_thresh:
            return AdDecision.DELAY
        return AdDecision.SUPPRESS

    return policy


def _agents_no_ga_policy():
    """Agents without GA: use default chromosome (all genes = 0.5)."""
    default_chrom = Chromosome()
    return _full_system_policy(default_chrom)


def _user_advocate_only_policy(chromosome: Chromosome):
    """Single agent: User Advocate only. Advertiser score is fixed at neutral 0.5."""
    from ..agents.user_advocate import score_user_advocate
    from ..state import AgentScore
    from ..agents.negotiator import negotiate

    dummy_adv = AgentScore(
        agent_name="Advertiser Advocate",
        score=0.5,
        reasoning="Fixed neutral score (ablation: user advocate only).",
        factors={},
    )

    def policy(opp: AdOpportunity) -> AdDecision:
        if should_force_suppress(opp.session_context):
            return AdDecision.SUPPRESS
        ua = score_user_advocate(opp.user, opp.ad_candidate, opp.session_context, chromosome)
        result = negotiate(ua, dummy_adv, chromosome, opp.user.id, opp.ad_candidate.id, opp.opportunity_id)
        return result.decision

    return policy


def _advertiser_advocate_only_policy(chromosome: Chromosome):
    """Single agent: Advertiser Advocate only. User score is fixed at neutral 0.5."""
    from ..agents.advertiser_advocate import score_advertiser_advocate
    from ..state import AgentScore
    from ..agents.negotiator import negotiate

    dummy_ua = AgentScore(
        agent_name="User Advocate",
        score=0.5,
        reasoning="Fixed neutral score (ablation: advertiser advocate only).",
        factors={},
    )

    def policy(opp: AdOpportunity) -> AdDecision:
        if should_force_suppress(opp.session_context):
            return AdDecision.SUPPRESS
        adv = score_advertiser_advocate(opp.user, opp.ad_candidate, opp.session_context, chromosome)
        result = negotiate(dummy_ua, adv, chromosome, opp.user.id, opp.ad_candidate.id, opp.opportunity_id)
        return result.decision

    return policy


def run_ablations(users, content, ads, evolved_chromosome: Chromosome = None) -> dict:
    """
    Run all four ablation conditions and return results.

    If evolved_chromosome is None, use a default chromosome for conditions
    that require one. In practice the runner passes the best evolved chromosome.
    """
    chrom = evolved_chromosome or Chromosome()

    conditions = {
        "full_system": _full_system_policy(chrom),
        "ga_only": _ga_only_policy(chrom),
        "agents_no_ga": _agents_no_ga_policy(),
        "user_advocate_only": _user_advocate_only_policy(chrom),
        "advertiser_advocate_only": _advertiser_advocate_only_policy(chrom),
    }

    results = {}
    for name, policy_fn in conditions.items():
        r = evaluate_policy(policy_fn, users, content, ads)
        results[name] = r

    return results
