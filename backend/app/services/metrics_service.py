"""Simple in-memory metrics counters for observability."""
import threading
from collections import defaultdict
from typing import Dict, Optional


class MetricsService:
    """Thread-safe in-memory counter service.
    No external dependencies — suitable for single-process or Celery worker.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)

    def increment(self, metric: str, amount: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a named metric counter."""
        key = metric
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            key = f"{metric}{{{label_str}}}"
        with self._lock:
            self._counters[key] += amount

    def get_counts(self) -> Dict[str, int]:
        """Return a snapshot of all counters."""
        with self._lock:
            return dict(self._counters)

    def reset(self):
        """Reset all counters (for testing)."""
        with self._lock:
            self._counters.clear()


# Singleton instance
metrics = MetricsService()
