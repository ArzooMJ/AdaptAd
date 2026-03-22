"""
SQLite database setup and helpers using aiosqlite.

Tables:
- decisions: Every NegotiationResult logged with timestamp.
- ab_sessions: A/B test sessions.
- ab_ratings: Per-participant ratings.
- evolution_runs: GA run metadata and results.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False

from ..config import config


_DB_PATH: Optional[str] = None


def get_db_path() -> str:
    return _DB_PATH or config.database.path


async def get_db():
    """FastAPI dependency that yields a database connection."""
    if not AIOSQLITE_AVAILABLE:
        raise RuntimeError("aiosqlite is not installed. Run: pip install aiosqlite")
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db(path: Optional[str] = None) -> None:
    """Create tables if they do not exist."""
    if not AIOSQLITE_AVAILABLE:
        print("Warning: aiosqlite not installed. Database functionality disabled.")
        return
    db_path = path or get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                ad_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                combined_score REAL,
                user_advocate_score REAL,
                advertiser_advocate_score REAL,
                reasoning TEXT,
                chromosome_genes TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ab_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                content_id INTEGER,
                adaptad_decisions TEXT,
                baseline_decisions TEXT,
                adaptad_label TEXT,
                baseline_label TEXT,
                created_at TEXT NOT NULL,
                completed BOOLEAN DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ab_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                session_label TEXT NOT NULL,
                annoyance INTEGER,
                relevance INTEGER,
                willingness INTEGER,
                participant_notes TEXT,
                rated_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS evolution_runs (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                status TEXT NOT NULL,
                current_generation INTEGER DEFAULT 0,
                max_generations INTEGER,
                best_fitness REAL,
                best_chromosome TEXT,
                history TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        await db.commit()


async def log_decision(db, result, chromosome_genes: Optional[list] = None) -> int:
    """Insert a NegotiationResult into the decisions table."""
    try:
        cursor = await db.execute(
            """
            INSERT INTO decisions
            (session_id, user_id, ad_id, decision, combined_score,
             user_advocate_score, advertiser_advocate_score, reasoning,
             chromosome_genes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.session_id,
                result.user_id,
                result.ad_id,
                result.decision.value,
                result.combined_score,
                result.user_advocate.score,
                result.advertiser_advocate.score,
                result.reasoning,
                json.dumps(chromosome_genes) if chromosome_genes else None,
                result.timestamp.isoformat(),
            ),
        )
        await db.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Warning: could not log decision to database: {e}")
        return -1
