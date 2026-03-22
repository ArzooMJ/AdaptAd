"""
Experiment routes.

POST /api/experiments/run          Run full experiment (background task).
GET  /api/experiments/{job_id}     Get experiment status and results.
POST /api/experiments/sensitivity  Run sensitivity analysis on best chromosome.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/experiments", tags=["experiments"])

_experiment_jobs: dict[str, dict] = {}


class ExperimentRequest(BaseModel):
    num_runs: int = 30
    max_generations: int = 50
    num_users: int = 200
    seed_offset: int = 0


class SensitivityRequest(BaseModel):
    chromosome_genes: Optional[list[float]] = None
    perturbation_size: float = 0.2


def _run_experiment_task(job_id: str, req: ExperimentRequest):
    job = _experiment_jobs[job_id]
    job["status"] = "running"
    try:
        from ..experiments.runner import run_full_experiment
        results = run_full_experiment(
            num_runs=req.num_runs,
            max_generations=req.max_generations,
            num_users=req.num_users,
            output_dir="results",
            seed_offset=req.seed_offset,
            verbose=False,
        )
        job["status"] = "completed"
        job["results"] = results
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


@router.post("/run")
def run_experiment(req: ExperimentRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _experiment_jobs[job_id] = {"job_id": job_id, "status": "queued", "results": None, "error": None}
    background_tasks.add_task(_run_experiment_task, job_id, req)
    return {"job_id": job_id, "status": "queued"}


@router.get("/{job_id}")
def get_experiment_status(job_id: str):
    if job_id not in _experiment_jobs:
        raise HTTPException(status_code=404, detail=f"Experiment job {job_id} not found.")
    return _experiment_jobs[job_id]


@router.post("/sensitivity")
def run_sensitivity(req: SensitivityRequest):
    from ..data.generate import generate_users
    from ..data.content_library import generate_content_library
    from ..data.ad_inventory import generate_ad_inventory
    from ..experiments.stats import run_sensitivity_analysis
    from ..state import Chromosome
    from .routes_decide import get_chromosome

    users = generate_users(count=100, seed=42)
    content = generate_content_library(count=50, seed=42)
    ads = generate_ad_inventory(count=40, seed=42)

    if req.chromosome_genes and len(req.chromosome_genes) == 8:
        chromosome = Chromosome.from_vector(req.chromosome_genes)
    else:
        chromosome = get_chromosome()

    sensitivities = run_sensitivity_analysis(
        users, content, ads, chromosome, req.perturbation_size
    )
    return {
        "chromosome_genes": chromosome.to_vector(),
        "perturbation_size": req.perturbation_size,
        "gene_sensitivities": sensitivities,
    }
