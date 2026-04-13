"""ReplayWriter — SQLite-based interaction logger."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class ReplayWriter:
    """Writes agent interactions to a SQLite database for later replay."""

    def __init__(self, db_path: Path | str):
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    async def init(self):
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER,
                prompt TEXT,
                response TEXT,
                timestamp TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    async def write_interaction(
        self,
        agent_id: int,
        prompt: str,
        response: str,
        timestamp: datetime | None = None,
    ):
        if self._conn is None:
            await self.init()
        ts = (timestamp or datetime.now()).isoformat()
        self._conn.execute(
            "INSERT INTO interactions (agent_id, prompt, response, timestamp) VALUES (?, ?, ?, ?)",
            (agent_id, prompt, response, ts),
        )
        self._conn.commit()

    async def read_all(self) -> list[dict[str, Any]]:
        if self._conn is None:
            await self.init()
        cursor = self._conn.execute(
            "SELECT id, agent_id, prompt, response, timestamp FROM interactions ORDER BY id"
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "agent_id": r[1],
                "prompt": r[2],
                "response": r[3],
                "timestamp": r[4],
            }
            for r in rows
        ]

    async def get_stats(self) -> dict[str, Any]:
        if self._conn is None:
            await self.init()
        cursor = self._conn.execute("SELECT COUNT(*), COUNT(DISTINCT agent_id) FROM interactions")
        total, agents = cursor.fetchone()
        return {"total_interactions": total, "unique_agents": agents}

    async def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
