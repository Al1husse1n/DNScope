import threading
from datetime import UTC, datetime


class DailyCounter:
    """Simple in-memory daily counter. Resets at UTC midnight."""

    def __init__(self, cap: int) -> None:
        self.cap = cap
        self._lock = threading.Lock()
        self._current_date = datetime.now(UTC).date()
        self._count = 0

    def try_increment(self) -> bool:
        """Increment today's counter. Return True if below cap, False if cap reached.

        Thread-safe via Lock. Reset automatically when UTC date changes.
        """
        with self._lock:
            today = datetime.now(UTC).date()
            if today != self._current_date:
                self._current_date = today
                self._count = 0

            if self._count < self.cap:
                self._count += 1
                return True
            return False

