"""In-memory task store for Agentic Boss runs plus cancellation flags."""

from __future__ import annotations

import asyncio
import time

from src.agentic.core import TaskRecord, TaskState


class TaskStore:
    """Holds live TaskRecord objects so SSE flows can resume a planned run."""

    def __init__(self, max_tasks: int = 200) -> None:
        self._records: dict[str, TaskRecord] = {}
        self._cancelled: set[str] = set()
        self._max = max_tasks

    def put(self, record: TaskRecord) -> None:
        self._records[record.id] = record
        while len(self._records) > self._max:
            oldest = min(self._records.keys(), key=lambda k: getattr(self._records[k], "created_at", 0.0))
            self._records.pop(oldest, None)

    def get(self, task_id: str) -> TaskRecord | None:
        return self._records.get(task_id)

    def list(self) -> list[TaskRecord]:
        ordered = sorted(self._records.values(), key=lambda r: getattr(r, "created_at", 0.0), reverse=True)
        return ordered[:50]

    def request_cancel(self, task_id: str) -> bool:
        if task_id not in self._records:
            return False
        self._cancelled.add(task_id)
        return True

    def clear_cancel(self, task_id: str) -> None:
        self._cancelled.discard(task_id)

    def is_cancelled(self, task_id: str) -> bool:
        return task_id in self._cancelled

    async def wait_for_cancellation(self, task_id: str, poll_seconds: float = 0.8) -> None:
        while not self.is_cancelled(task_id):
            await asyncio.sleep(poll_seconds)


store = TaskStore()