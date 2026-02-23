"""
Live Model Registry.

Discovers locally installed models via Ollama (across multiple endpoints)
and merges with static model profiles for intelligent model selection.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from .ollama_registry import (
    OLLAMA_MODELS,
    ModelProfile,
    get_model_profile,
    find_tool_capable_models,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Refresh interval for model discovery (seconds)
REFRESH_INTERVAL = 60


class LiveModelRegistry:
    """
    Runtime model registry that merges Ollama API discovery
    with static model profiles.  Supports multiple Ollama endpoints.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        backend_manager=None,
    ):
        self.ollama_url = ollama_url
        self._backend_manager = backend_manager
        # model_name -> { "name", "size_bytes", "profile", "backends": [backend_name, ...] }
        self._installed_models: Dict[str, Dict[str, Any]] = {}
        self._last_refresh: float = 0.0
        self._lock = asyncio.Lock()

    async def refresh(self, force: bool = False) -> None:
        """Query all Ollama endpoints for installed models and merge with profiles."""
        now = time.time()
        if not force and (now - self._last_refresh) < REFRESH_INTERVAL:
            return

        async with self._lock:
            self._installed_models.clear()

            if self._backend_manager:
                await self._refresh_from_backends()
            else:
                await self._refresh_single(self.ollama_url, "local")

            self._last_refresh = time.time()
            logger.info("model_registry_refreshed", count=len(self._installed_models))

    async def _refresh_single(self, url: str, backend_name: str) -> None:
        """Query a single Ollama endpoint."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        logger.warning("model_registry_refresh_failed",
                                       backend=backend_name, status=resp.status)
                        return
                    data = await resp.json()

            for model in data.get("models", []):
                name = model.get("name", "")
                self._merge_model(name, model, backend_name)

        except Exception as e:
            logger.warning("model_registry_refresh_error",
                           backend=backend_name, error=str(e))

    async def _refresh_from_backends(self) -> None:
        """Query all backends from the BackendManager concurrently."""
        from ..utils.config import BackendType

        tasks = []
        for state in self._backend_manager.list_backends():
            if state.config.type == BackendType.OLLAMA and state.config.enabled:
                tasks.append(self._refresh_single(state.config.url, state.config.name))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _merge_model(self, name: str, raw: Dict[str, Any], backend_name: str) -> None:
        """Merge a discovered model into the registry, tracking which backends have it."""
        if name in self._installed_models:
            # Model already known — just add this backend
            existing = self._installed_models[name]
            if backend_name not in existing["backends"]:
                existing["backends"].append(backend_name)
            return

        profile = get_model_profile(name)
        self._installed_models[name] = {
            "name": name,
            "size_bytes": raw.get("size", 0),
            "modified": raw.get("modified_at", ""),
            "digest": raw.get("digest", ""),
            "profile": profile,
            "backends": [backend_name],
        }

    async def get_installed_models(self) -> List[Dict[str, Any]]:
        """Get all locally installed models with their profiles."""
        await self.refresh()
        return list(self._installed_models.values())

    async def get_tool_capable_models(self) -> List[Dict[str, Any]]:
        """Get installed models that support tool calling."""
        await self.refresh()
        results = []
        for info in self._installed_models.values():
            profile = info.get("profile")
            if profile and profile.supports_tool_calling:
                results.append(info)

        # Also check via name heuristics for models not in static registry
        tool_names = ["qwen2.5", "qwen2:", "devstral", "mistral-nemo",
                       "llama3.1", "llama3.2", "llama3.3", "command-r",
                       "firefunction", "hermes", "csuite-model", "csuite-technical"]
        for info in self._installed_models.values():
            if info not in results:
                name_lower = info["name"].lower()
                if any(t in name_lower for t in tool_names):
                    results.append(info)

        return results

    async def get_best_model_for(
        self,
        task_tags: Optional[List[str]] = None,
        min_quality: str = "basic",
        prefer_speed: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Rank installed models by suitability for the given task.

        Returns models sorted by score (best first).
        Each entry includes a "backends" list showing which endpoints have it.
        """
        await self.refresh()

        scored = []
        for info in self._installed_models.values():
            profile = info.get("profile")
            if not profile:
                continue

            score = 0.0

            # Tool calling bonus
            quality_scores = {"none": 0, "basic": 5, "good": 15, "excellent": 25}
            tc_quality = quality_scores.get(profile.tool_calling_quality, 0)
            min_level = quality_scores.get(min_quality, 0)
            if tc_quality < min_level:
                continue  # Filter out models below minimum quality
            score += tc_quality

            # Task tag matching
            if task_tags and profile.task_tags:
                matching_tags = len(set(task_tags) & set(profile.task_tags))
                score += matching_tags * 10

            # Quality rating
            score += profile.quality_rating * 3

            # Speed preference
            if prefer_speed:
                score += profile.speed_rating * 4
            else:
                score += profile.speed_rating * 1

            # Context window (larger is generally better)
            if profile.context_window >= 32768:
                score += 5
            if profile.context_window >= 128000:
                score += 5

            scored.append((score, info))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [info for _, info in scored]

    async def get_backends_for_model(self, model_name: str) -> List[str]:
        """Get which backend endpoints have a model installed."""
        await self.refresh()
        info = self._installed_models.get(model_name)
        if info:
            return info.get("backends", [])
        # Try partial match
        for name, info in self._installed_models.items():
            if model_name.split(":")[0] in name:
                return info.get("backends", [])
        return []

    async def is_model_installed(self, model_name: str) -> bool:
        """Check if a model is locally installed."""
        await self.refresh()
        if model_name in self._installed_models:
            return True
        # Partial match
        return any(
            model_name.split(":")[0] in name
            for name in self._installed_models
        )

    async def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        await self.refresh()
        total_size = sum(
            m.get("size_bytes", 0) for m in self._installed_models.values()
        )
        profiled = sum(
            1 for m in self._installed_models.values() if m.get("profile")
        )
        tool_capable = len(await self.get_tool_capable_models())

        # Count unique backends
        all_backends = set()
        for m in self._installed_models.values():
            all_backends.update(m.get("backends", []))

        return {
            "total_installed": len(self._installed_models),
            "with_profiles": profiled,
            "tool_capable": tool_capable,
            "total_size_gb": round(total_size / (1024 ** 3), 2),
            "static_profiles": len(OLLAMA_MODELS),
            "backends_queried": len(all_backends),
        }
