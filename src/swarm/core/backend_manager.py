"""
Backend Manager.

Manages multiple inference endpoints (local Ollama, remote Ollama,
Claude API, OpenAI, etc.) with health monitoring and load tracking.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..utils.config import BackendEndpoint, BackendType
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BackendHealth(str, Enum):
    """Health status of a backend endpoint."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class BackendState:
    """Runtime state for a single backend endpoint."""
    config: BackendEndpoint
    health: BackendHealth = BackendHealth.UNKNOWN
    active_requests: int = 0
    total_completed: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    last_check: float = 0.0
    last_error: Optional[str] = None
    discovered_models: list[str] = field(default_factory=list)
    _session: Any = field(default=None, repr=False)

    @property
    def available_slots(self) -> int:
        return max(0, self.config.max_concurrent - self.active_requests)

    @property
    def is_available(self) -> bool:
        return (
            self.config.enabled
            and self.health in (BackendHealth.HEALTHY, BackendHealth.UNKNOWN)
            and self.available_slots > 0
        )

    @property
    def load_ratio(self) -> float:
        if self.config.max_concurrent == 0:
            return 1.0
        return self.active_requests / self.config.max_concurrent


class BackendManager:
    """
    Manages multiple backend endpoints with health checks,
    load balancing, and session reuse.
    """

    def __init__(self, backends: List[BackendEndpoint]):
        self._backends: Dict[str, BackendState] = {}
        for cfg in backends:
            if cfg.enabled:
                self._backends[cfg.name] = BackendState(config=cfg)
        self._lock = asyncio.Lock()
        self._health_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start health monitoring and initial checks."""
        await self._check_all_health()
        self._health_task = asyncio.create_task(self._health_loop())
        logger.info("backend_manager_started", backends=list(self._backends.keys()))

    async def stop(self) -> None:
        """Stop health monitoring and close sessions."""
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        # Close any aiohttp sessions
        for state in self._backends.values():
            if state._session and not state._session.closed:
                await state._session.close()
                state._session = None
        logger.info("backend_manager_stopped")

    async def get_session(self, backend_name: str):
        """Get or create a reusable aiohttp session for a backend."""
        import aiohttp

        state = self._backends.get(backend_name)
        if not state:
            raise ValueError(f"Unknown backend: {backend_name}")

        if state._session is None or state._session.closed:
            state._session = aiohttp.ClientSession()

        return state._session

    def get_backend(self, name: str) -> Optional[BackendState]:
        """Get a backend by name."""
        return self._backends.get(name)

    def list_backends(self) -> List[BackendState]:
        """List all backends."""
        return list(self._backends.values())

    def get_available_backends(
        self,
        backend_type: Optional[BackendType] = None,
        model: Optional[str] = None,
    ) -> List[BackendState]:
        """Get backends that are available for new work."""
        results = []
        for state in self._backends.values():
            if not state.is_available:
                continue
            if backend_type and state.config.type != backend_type:
                continue
            if model:
                all_models = set(state.config.models) | set(state.discovered_models)
                # Match by exact name or base name (e.g. "qwen2.5" matches "qwen2.5:14b")
                matched = any(
                    model == m or model.split(":")[0] in m
                    for m in all_models
                )
                if not matched:
                    continue
            results.append(state)
        return results

    def get_best_backend_for_model(self, model: str) -> Optional[BackendState]:
        """Pick the best available backend that can serve a given model."""
        candidates = self.get_available_backends(model=model)
        if not candidates:
            return None
        # Sort by: priority (descending), load (ascending)
        candidates.sort(key=lambda s: (-s.config.priority, s.load_ratio))
        return candidates[0]

    async def acquire(self, backend_name: str) -> bool:
        """Increment active_requests for a backend. Returns False if full."""
        async with self._lock:
            state = self._backends.get(backend_name)
            if not state or not state.is_available:
                return False
            state.active_requests += 1
            return True

    async def release(
        self,
        backend_name: str,
        success: bool = True,
        latency_ms: float = 0.0,
        error: Optional[str] = None,
    ) -> None:
        """Decrement active_requests and record outcome."""
        async with self._lock:
            state = self._backends.get(backend_name)
            if not state:
                return
            state.active_requests = max(0, state.active_requests - 1)
            if success:
                state.total_completed += 1
            else:
                state.total_errors += 1
                state.last_error = error
            # Exponential moving average for latency
            if latency_ms > 0:
                alpha = 0.3
                state.avg_latency_ms = (
                    alpha * latency_ms + (1 - alpha) * state.avg_latency_ms
                )

    # ── Health Checking ──────────────────────────────────────

    async def _health_loop(self) -> None:
        """Periodically check all backend health."""
        while True:
            try:
                await asyncio.sleep(30)
                await self._check_all_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("health_check_error", error=str(e))

    async def _check_all_health(self) -> None:
        """Check health of every backend concurrently."""
        tasks = [
            self._check_backend_health(name)
            for name in self._backends
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_backend_health(self, name: str) -> None:
        """Check health of a single backend."""
        state = self._backends.get(name)
        if not state:
            return

        if state.config.type == BackendType.OLLAMA:
            await self._check_ollama_health(state)
        elif state.config.type == BackendType.CLAUDE:
            # Claude API: assume healthy if api_key is set
            state.health = BackendHealth.HEALTHY if state.config.api_key else BackendHealth.UNKNOWN
            state.last_check = time.time()

    async def _check_ollama_health(self, state: BackendState) -> None:
        """Check an Ollama endpoint and discover its models."""
        import aiohttp

        try:
            session = await self.get_session(state.config.name)
            async with session.get(
                f"{state.config.url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    state.health = BackendHealth.UNHEALTHY
                    state.last_error = f"HTTP {resp.status}"
                    logger.warning("backend_unhealthy", name=state.config.name, status=resp.status)
                    return

                data = await resp.json()
                discovered = [m["name"] for m in data.get("models", [])]
                state.discovered_models = discovered
                state.health = BackendHealth.HEALTHY
                state.last_check = time.time()

                logger.info("backend_healthy", name=state.config.name,
                            models=len(discovered))

        except Exception as e:
            state.health = BackendHealth.UNHEALTHY
            state.last_error = str(e)
            state.last_check = time.time()
            logger.warning("backend_health_check_failed",
                           name=state.config.name, error=str(e))

    # ── Status / Info ────────────────────────────────────────

    def get_status(self) -> List[Dict[str, Any]]:
        """Get status of all backends."""
        results = []
        for state in self._backends.values():
            results.append({
                "name": state.config.name,
                "type": state.config.type.value,
                "url": state.config.url,
                "health": state.health.value,
                "enabled": state.config.enabled,
                "configured_models": state.config.models,
                "discovered_models": state.discovered_models,
                "max_concurrent": state.config.max_concurrent,
                "active_requests": state.active_requests,
                "available_slots": state.available_slots,
                "total_completed": state.total_completed,
                "total_errors": state.total_errors,
                "avg_latency_ms": round(state.avg_latency_ms, 1),
                "priority": state.config.priority,
                "last_check": state.last_check,
                "last_error": state.last_error,
            })
        return results
