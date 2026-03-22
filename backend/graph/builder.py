"""
LangGraph graph definitions for AdaptAd.

Evolution graph: START -> init_ga -> evolve (loop) -> END
Decision graph: START -> [user_advocate || advertiser_advocate] -> negotiate -> llm_explain -> END

Both graphs operate on GraphState.
"""

from typing import Any, Literal

try:
    from langgraph.graph import StateGraph, START, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    # Provide stub so the rest of the codebase can import without crashing.
    StateGraph = None
    START = "START"
    END = "END"

from ..state import GraphState, Chromosome
from ..config import config
from ..ga.engine import GAEngine, init_population
from ..ga.fitness import evaluate_population_fitness
from ..ga.storage import save_chromosome


# ---------------------------------------------------------------------------
# Evolution graph nodes
# ---------------------------------------------------------------------------


def node_init_ga(state: dict) -> dict:
    """
    Initialize the GA population.

    Sets up population, resets generation counter and history.
    """
    gs = GraphState.model_validate(state)
    pop_size = config.ga.population_size
    population = init_population(pop_size, seed=42)
    return {
        **state,
        "population": [c.model_dump() for c in population],
        "current_generation": 0,
        "ga_history": [],
        "best_chromosome": None,
        "ga_converged": False,
        "phase": "evolving",
        "error": None,
    }


def _build_engine_from_state(state: dict) -> tuple[GAEngine, dict]:
    """Helper: reconstruct a GAEngine from GraphState dict."""
    gs = GraphState.model_validate(state)
    engine = GAEngine(
        users=gs.user_pool,
        content_items=[],  # Loaded lazily by routes.
        ad_pool=gs.ad_pool,
    )
    # Restore population.
    engine.population = [
        Chromosome.model_validate(c) for c in (state.get("population") or [])
    ]
    engine.current_generation = state.get("current_generation", 0)
    engine.fitness_history = [
        entry.get("best_fitness", 0.0) for entry in (state.get("ga_history") or [])
    ]
    best_raw = state.get("best_chromosome")
    if best_raw:
        engine.best_chromosome = Chromosome.model_validate(best_raw)
        engine.best_fitness = engine.best_chromosome.fitness or 0.0
    return engine, state


def node_evolve(state: dict) -> dict:
    """
    Run one generation of the GA.

    The graph loops back here until convergence or max_generations.
    """
    from ..data.generate import generate_users
    from ..data.content_library import generate_content_library
    from ..data.ad_inventory import generate_ad_inventory

    gs = GraphState.model_validate(state)

    # Rebuild engine state.
    users = gs.user_pool or generate_users(count=200, seed=42)
    content_items = generate_content_library(count=100, seed=42)
    ad_pool = gs.ad_pool or generate_ad_inventory(count=80, seed=42)

    engine = GAEngine(users=users, content_items=content_items, ad_pool=ad_pool)
    engine.population = [Chromosome.model_validate(c) for c in (state.get("population") or [])]
    engine.current_generation = state.get("current_generation", 0)
    engine.fitness_history = [
        entry.get("best_fitness", 0.0) for entry in (state.get("ga_history") or [])
    ]
    best_raw = state.get("best_chromosome")
    if best_raw:
        engine.best_chromosome = Chromosome.model_validate(best_raw)
        engine.best_fitness = engine.best_chromosome.fitness or 0.0
    engine.generations_since_improvement = state.get("generations_since_improvement", 0)

    # Evaluate current population if fitnesses not yet set.
    if not engine.fitnesses:
        engine._evaluate()

    # Run one step.
    stats = engine.step()

    history = list(state.get("ga_history") or [])
    history.append(stats)

    best_dict = engine.best_chromosome.model_dump() if engine.best_chromosome else None

    return {
        **state,
        "population": [c.model_dump() for c in engine.population],
        "current_generation": engine.current_generation,
        "ga_history": history,
        "best_chromosome": best_dict,
        "ga_converged": engine.converged,
        "generations_since_improvement": engine.generations_since_improvement,
        "phase": "converged" if engine.converged else "evolving",
    }


def should_continue_evolving(state: dict) -> Literal["evolve", "done"]:
    """Conditional edge: continue evolving or finish."""
    converged = state.get("ga_converged", False)
    current_gen = state.get("current_generation", 0)
    max_gen = state.get("max_generations", config.ga.max_generations)
    if converged or current_gen >= max_gen:
        return "done"
    return "evolve"


# ---------------------------------------------------------------------------
# Decision graph nodes
# ---------------------------------------------------------------------------


def node_user_advocate(state: dict) -> dict:
    """Compute User Advocate math score."""
    from ..agents.user_advocate import score_user_advocate

    gs = GraphState.model_validate(state)
    if gs.user is None or gs.ad_candidate is None or gs.session_context is None:
        return {**state, "error": "Missing user, ad_candidate, or session_context for decision."}

    chromosome = (
        gs.best_chromosome
        or Chromosome()  # Default chromosome if none evolved yet.
    )
    agent_score = score_user_advocate(
        user=gs.user,
        ad=gs.ad_candidate,
        session_context=gs.session_context,
        chromosome=chromosome,
    )
    return {**state, "user_advocate_score": agent_score.model_dump()}


def node_advertiser_advocate(state: dict) -> dict:
    """Compute Advertiser Advocate math score."""
    from ..agents.advertiser_advocate import score_advertiser_advocate

    gs = GraphState.model_validate(state)
    if gs.user is None or gs.ad_candidate is None or gs.session_context is None:
        return {**state, "error": "Missing user, ad_candidate, or session_context for decision."}

    chromosome = gs.best_chromosome or Chromosome()
    agent_score = score_advertiser_advocate(
        user=gs.user,
        ad=gs.ad_candidate,
        session_context=gs.session_context,
        chromosome=chromosome,
    )
    return {**state, "advertiser_advocate_score": agent_score.model_dump()}


def node_negotiate(state: dict) -> dict:
    """Combine agent scores and determine final decision."""
    from ..agents.negotiator import negotiate

    gs = GraphState.model_validate(state)
    if gs.user_advocate_score is None or gs.advertiser_advocate_score is None:
        return {**state, "error": "Missing agent scores for negotiation."}

    chromosome = gs.best_chromosome or Chromosome()
    result = negotiate(
        user_advocate=gs.user_advocate_score,
        advertiser_advocate=gs.advertiser_advocate_score,
        chromosome=chromosome,
        user_id=gs.user.id if gs.user else 0,
        ad_id=gs.ad_candidate.id if gs.ad_candidate else "unknown",
        session_id=state.get("job_id") or "session_0",
    )
    return {**state, "negotiation_result": result.model_dump()}


def node_llm_explain(state: dict) -> dict:
    """
    Generate LLM-based reasoning for both agents (optional).

    Falls back to template reasoning if LLM is unavailable or disabled.
    This node runs AFTER the decision is already made.
    """
    from ..agents.llm_reasoning import enrich_with_llm_reasoning

    gs = GraphState.model_validate(state)
    if gs.negotiation_result is None:
        return state  # Nothing to explain.

    result = enrich_with_llm_reasoning(gs.negotiation_result, gs.user, gs.ad_candidate)
    return {**state, "negotiation_result": result.model_dump()}


# ---------------------------------------------------------------------------
# Graph builders
# ---------------------------------------------------------------------------


def build_evolution_graph():
    """
    Build and compile the LangGraph evolution graph.

    START -> init_ga -> evolve -> (loop via conditional edge) -> END
    """
    if not LANGGRAPH_AVAILABLE:
        raise ImportError(
            "langgraph is not installed. Run: pip install langgraph"
        )

    builder = StateGraph(dict)
    builder.add_node("init_ga", node_init_ga)
    builder.add_node("evolve", node_evolve)
    builder.add_edge(START, "init_ga")
    builder.add_edge("init_ga", "evolve")
    builder.add_conditional_edges(
        "evolve",
        should_continue_evolving,
        {"evolve": "evolve", "done": END},
    )
    return builder.compile()


def build_decision_graph():
    """
    Build and compile the LangGraph decision graph.

    START -> [user_advocate + advertiser_advocate in parallel] -> negotiate -> llm_explain -> END
    """
    if not LANGGRAPH_AVAILABLE:
        raise ImportError(
            "langgraph is not installed. Run: pip install langgraph"
        )

    builder = StateGraph(dict)
    builder.add_node("user_advocate", node_user_advocate)
    builder.add_node("advertiser_advocate", node_advertiser_advocate)
    builder.add_node("negotiate", node_negotiate)
    builder.add_node("llm_explain", node_llm_explain)

    # Parallel fan-out from START.
    builder.add_edge(START, "user_advocate")
    builder.add_edge(START, "advertiser_advocate")
    # Fan-in: both must complete before negotiation.
    builder.add_edge("user_advocate", "negotiate")
    builder.add_edge("advertiser_advocate", "negotiate")
    builder.add_edge("negotiate", "llm_explain")
    builder.add_edge("llm_explain", END)

    return builder.compile()
