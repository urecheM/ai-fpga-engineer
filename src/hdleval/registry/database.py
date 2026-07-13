"""SQLite-backed experiment database supporting historical comparison.

Stores one row per (experiment, run, benchmark) with the full record JSON plus
indexed columns for common queries. Enables cross-release comparison and feeds
the leaderboard/report generators.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import uuid
from collections.abc import Iterable
from contextlib import closing, suppress
from pathlib import Path
from typing import Any

from .experiment import ExperimentRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT,
    experiment TEXT,
    benchmark TEXT,
    benchmark_version TEXT,
    model TEXT,
    prompt TEXT,
    seed INTEGER,
    trial INTEGER,
    passed INTEGER,
    failure_class TEXT,
    duration_s REAL,
    git_commit TEXT,
    started_at REAL,
    record_json TEXT,
    PRIMARY KEY (run_id, benchmark, trial)
);
CREATE INDEX IF NOT EXISTS idx_runs_experiment ON runs(experiment);
CREATE INDEX IF NOT EXISTS idx_runs_model ON runs(model);
CREATE INDEX IF NOT EXISTS idx_runs_category ON runs(benchmark);
"""


class ExperimentDB:
    def __init__(self, path: str | Path = "experiments/registry.sqlite") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # SQLite requires POSIX locking that some networked/fuse filesystems do
        # not provide. We therefore operate on a local working copy and mirror
        # it to the destination on commit/close, keeping the registry portable.
        self._work = Path(tempfile.gettempdir()) / f"hdleval-{uuid.uuid4().hex}.sqlite"
        if self.path.exists():
            with suppress(OSError):
                shutil.copy2(self.path, self._work)
        self._conn = sqlite3.connect(str(self._work))
        self._conn.row_factory = sqlite3.Row
        with closing(self._conn.cursor()) as cur:
            cur.executescript(_SCHEMA)
        self._conn.commit()
        self._mirror()

    def _mirror(self) -> None:
        """Copy the local working DB to the (possibly fuse-mounted) destination."""
        with suppress(OSError):
            shutil.copy2(self._work, self.path)

    def insert(self, rec: ExperimentRecord) -> None:
        with closing(self._conn.cursor()) as cur:
            cur.execute(
                """INSERT OR REPLACE INTO runs
                (run_id, experiment, benchmark, benchmark_version, model, prompt,
                 seed, trial, passed, failure_class, duration_s, git_commit,
                 started_at, record_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rec.run_id,
                    rec.experiment,
                    rec.benchmark,
                    rec.benchmark_version,
                    rec.model,
                    rec.prompt,
                    rec.seed,
                    rec.trial,
                    int(rec.passed),
                    rec.failure_class,
                    rec.duration_s,
                    rec.environment.get("git_commit", "unknown"),
                    rec.started_at,
                    json.dumps(rec.to_dict(), sort_keys=True),
                ),
            )
        self._conn.commit()
        self._mirror()

    def insert_many(self, recs: Iterable[ExperimentRecord]) -> None:
        for r in recs:
            self.insert(r)

    def all_records(self, experiment: str | None = None) -> list[dict[str, Any]]:
        q = "SELECT record_json FROM runs"
        args: tuple[Any, ...] = ()
        if experiment:
            q += " WHERE experiment = ?"
            args = (experiment,)
        with closing(self._conn.cursor()) as cur:
            cur.execute(q, args)
            return [json.loads(row["record_json"]) for row in cur.fetchall()]

    def experiments(self) -> list[str]:
        with closing(self._conn.cursor()) as cur:
            cur.execute("SELECT DISTINCT experiment FROM runs ORDER BY experiment")
            return [r["experiment"] for r in cur.fetchall()]

    def close(self) -> None:
        self._mirror()
        self._conn.close()
        with suppress(OSError):
            self._work.unlink()
