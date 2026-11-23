import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Protocol

from dnscope.schemas.findings import BaseAgentFinding


class InvestigationAgent(Protocol):
    async def investigate(self, domain: str) -> BaseAgentFinding: ...


class Stopwatch:
    def __init__(self) -> None:
        self.elapsed_ms: int = 0


@contextmanager
def stopwatch() -> Generator[Stopwatch, None, None]:
    sw = Stopwatch()
    start = time.perf_counter()
    try:
        yield sw
    finally:
        sw.elapsed_ms = int((time.perf_counter() - start) * 1000)
