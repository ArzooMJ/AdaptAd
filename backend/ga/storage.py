"""
Chromosome save/load utilities.

Chromosomes are stored as JSON files in the chromosomes/ directory.
Filename format: chromosome_{timestamp}_{fitness:.4f}.json
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..state import Chromosome
from ..config import config


def _chromosomes_dir() -> Path:
    d = Path(config.chromosomes_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_chromosome(chromosome: Chromosome, label: Optional[str] = None) -> str:
    """
    Save a chromosome to disk.

    Returns the file path of the saved file.
    Fitness defaults to 0.0 if not set.
    """
    fitness = chromosome.fitness if chromosome.fitness is not None else 0.0
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{label}" if label else ""
    filename = f"chromosome_{timestamp}{suffix}_{fitness:.4f}.json"
    path = _chromosomes_dir() / filename
    data = {
        "genes": chromosome.to_vector(),
        "fitness": fitness,
        "gene_names": Chromosome.gene_names(),
        "saved_at": datetime.utcnow().isoformat(),
        "label": label,
    }
    path.write_text(json.dumps(data, indent=2))
    return str(path)


def load_chromosome(path: str) -> Chromosome:
    """
    Load a chromosome from a JSON file.

    Raises FileNotFoundError if the file does not exist.
    Raises ValueError if the file is malformed.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Chromosome file not found: {path}")
    try:
        data = json.loads(p.read_text())
        genes = data["genes"]
        chrom = Chromosome.from_vector(genes)
        chrom.fitness = data.get("fitness")
        return chrom
    except (KeyError, ValueError) as e:
        raise ValueError(f"Malformed chromosome file {path}: {e}") from e


def list_chromosomes(directory: Optional[str] = None) -> list[dict]:
    """
    List all saved chromosomes sorted by fitness descending.

    Returns a list of dicts with keys: path, fitness, saved_at, label.
    """
    d = Path(directory) if directory else _chromosomes_dir()
    if not d.exists():
        return []
    results = []
    for p in sorted(d.glob("chromosome_*.json")):
        try:
            data = json.loads(p.read_text())
            results.append({
                "path": str(p),
                "filename": p.name,
                "fitness": data.get("fitness", 0.0),
                "saved_at": data.get("saved_at", ""),
                "label": data.get("label"),
                "genes": data.get("genes", []),
            })
        except Exception:
            # Skip malformed files.
            continue
    results.sort(key=lambda x: x["fitness"], reverse=True)
    return results


def load_best_chromosome(directory: Optional[str] = None) -> Optional[Chromosome]:
    """
    Load the chromosome with the highest fitness from the chromosomes directory.

    Returns None if no saved chromosomes exist.
    """
    saved = list_chromosomes(directory)
    if not saved:
        return None
    best = saved[0]
    return load_chromosome(best["path"])


def delete_chromosome(path: str) -> bool:
    """
    Delete a saved chromosome file.

    Returns True if deleted, False if file not found.
    """
    p = Path(path)
    if p.exists():
        p.unlink()
        return True
    return False
