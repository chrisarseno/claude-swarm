"""
Swarm Router.

Intelligent task-to-model routing using task analysis,
model capabilities, backend availability, and historical performance data.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .task_analyzer import TaskAnalysis, TaskType, Complexity
from ..agents.model_registry import LiveModelRegistry
from ..agents.ollama_registry import ModelProfile
from ..utils.logger import get_logger

logger = get_logger(__name__)

# Scoring weights
CAPABILITY_WEIGHT = 0.40
QUALITY_WEIGHT = 0.25
SPEED_WEIGHT = 0.20
CONTEXT_WEIGHT = 0.15


@dataclass
class RoutingDecision:
    """Result of a routing decision."""

    model: str
    score: float
    reason: str
    backend_name: Optional[str] = None
    analysis: Optional[TaskAnalysis] = None
    alternatives: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RoutingOutcome:
    """Recorded outcome of a routing decision for feedback."""

    model: str
    task_type: str
    success: bool
    duration_ms: float
    backend_name: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class SwarmRouter:
    """
    Routes tasks to the best available (backend, model) pair based on
    capability matching, quality, speed, backend load, and historical
    performance.
    """

    def __init__(self, model_registry: LiveModelRegistry, backend_manager=None):
        self.model_registry = model_registry
        self._backend_manager = backend_manager
        # Performance tracking: model -> task_type -> deque of outcomes
        self._outcomes: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=100))
        )

    async def route(
        self,
        analysis: TaskAnalysis,
        prefer_speed: bool = False,
        preferred_models: Optional[List[str]] = None,
        fallback_model: Optional[str] = None,
    ) -> RoutingDecision:
        """
        Select the best (backend, model) pair for a task.

        Args:
            analysis: Output from TaskAnalyzer.
            prefer_speed: Bias towards faster models.
            preferred_models: User's preferred models (try first).
            fallback_model: Fallback if nothing else works.

        Returns:
            RoutingDecision with selected model, backend, and alternatives.
        """
        candidates = await self.model_registry.get_best_model_for(
            task_tags=analysis.tags,
            min_quality="basic" if analysis.complexity == Complexity.SIMPLE else "good",
            prefer_speed=prefer_speed,
        )

        if not candidates:
            # Fall back to any installed model
            all_models = await self.model_registry.get_installed_models()
            if fallback_model:
                backend_name = await self._pick_backend_for_model(fallback_model)
                return RoutingDecision(
                    model=fallback_model,
                    score=0.0,
                    reason="fallback (no matching models found)",
                    backend_name=backend_name,
                    analysis=analysis,
                )
            if all_models:
                first = all_models[0]
                backends = first.get("backends", [])
                backend_name = await self._pick_backend_from_list(backends, first["name"])
                return RoutingDecision(
                    model=first["name"],
                    score=0.0,
                    reason="default (no matching models)",
                    backend_name=backend_name,
                    analysis=analysis,
                )
            return RoutingDecision(
                model="qwen2.5:7b",
                score=0.0,
                reason="hardcoded fallback (no models found)",
                analysis=analysis,
            )

        # Score candidates, considering backend availability
        scored = []
        for info in candidates:
            profile = info.get("profile")
            if not profile:
                continue

            base_score = self._score_model(profile, analysis, prefer_speed)

            # Boost preferred models
            if preferred_models and info["name"] in preferred_models:
                base_score += 20

            # Apply historical performance adjustment
            perf_adj = self._performance_adjustment(info["name"], analysis.task_type.value)
            base_score += perf_adj

            # For each backend that has this model, compute a final score
            backends = info.get("backends", [])
            best_backend, backend_bonus = await self._score_backends(backends, info["name"])

            final_score = base_score + backend_bonus
            scored.append((final_score, info, best_backend))

        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            return RoutingDecision(
                model=fallback_model or "qwen2.5:7b",
                score=0.0,
                reason="no candidates scored",
                analysis=analysis,
            )

        best_score, best_info, best_backend = scored[0]
        alternatives = [
            {"model": info["name"], "score": round(s, 2), "backend": b}
            for s, info, b in scored[1:4]
        ]

        reason = self._explain_choice(best_info, analysis, best_backend)

        return RoutingDecision(
            model=best_info["name"],
            score=round(best_score, 2),
            reason=reason,
            backend_name=best_backend,
            analysis=analysis,
            alternatives=alternatives,
        )

    async def _score_backends(
        self, backend_names: List[str], model: str
    ) -> tuple[Optional[str], float]:
        """Score backends and pick the best one for this model."""
        if not self._backend_manager or not backend_names:
            return (backend_names[0] if backend_names else None), 0.0

        best_name = None
        best_bonus = -100.0

        for name in backend_names:
            state = self._backend_manager.get_backend(name)
            if not state or not state.is_available:
                continue

            bonus = 0.0
            # Priority bonus
            bonus += state.config.priority * 5
            # Load penalty: fuller backends get lower scores
            bonus -= state.load_ratio * 15
            # Latency bonus: faster backends get higher scores
            if state.avg_latency_ms > 0:
                if state.avg_latency_ms < 5000:
                    bonus += 5
                elif state.avg_latency_ms < 15000:
                    bonus += 0
                else:
                    bonus -= 5
            # Error rate penalty
            total = state.total_completed + state.total_errors
            if total > 5:
                error_rate = state.total_errors / total
                bonus -= error_rate * 20

            if bonus > best_bonus:
                best_bonus = bonus
                best_name = name

        return best_name, max(best_bonus, 0.0)

    async def _pick_backend_for_model(self, model: str) -> Optional[str]:
        """Pick the best backend for a specific model."""
        if not self._backend_manager:
            return None
        state = self._backend_manager.get_best_backend_for_model(model)
        return state.config.name if state else None

    async def _pick_backend_from_list(
        self, backend_names: List[str], model: str
    ) -> Optional[str]:
        """Pick best backend from a list."""
        name, _ = await self._score_backends(backend_names, model)
        return name

    def _score_model(
        self,
        profile: ModelProfile,
        analysis: TaskAnalysis,
        prefer_speed: bool,
    ) -> float:
        """Score a model for a task analysis."""
        score = 0.0

        # Capability match: how many task tags does this model cover?
        if profile.task_tags and analysis.tags:
            matching = len(set(analysis.tags) & set(profile.task_tags))
            total = max(len(analysis.tags), 1)
            score += (matching / total) * 100 * CAPABILITY_WEIGHT

        # Quality rating
        score += profile.quality_rating * 10 * QUALITY_WEIGHT

        # Speed rating
        speed_mult = SPEED_WEIGHT * (2.0 if prefer_speed else 1.0)
        score += profile.speed_rating * 10 * speed_mult

        # Context window fit
        if analysis.complexity == Complexity.COMPLEX:
            if profile.context_window >= 32768:
                score += 100 * CONTEXT_WEIGHT
            elif profile.context_window >= 16384:
                score += 50 * CONTEXT_WEIGHT
        else:
            score += 50 * CONTEXT_WEIGHT  # any context window is fine for simple tasks

        # Tool calling bonus for agent tasks
        tc_bonus = {"excellent": 15, "good": 10, "basic": 5, "none": 0}
        score += tc_bonus.get(profile.tool_calling_quality, 0)

        # Complexity-quality alignment
        if analysis.complexity == Complexity.COMPLEX and profile.quality_rating >= 8:
            score += 10
        if analysis.complexity == Complexity.SIMPLE and profile.speed_rating >= 8:
            score += 10

        return score

    def _performance_adjustment(self, model: str, task_type: str) -> float:
        """Adjust score based on historical performance."""
        outcomes = self._outcomes.get(model, {}).get(task_type, deque())
        if len(outcomes) < 3:
            return 0.0

        recent = list(outcomes)[-10:]
        success_rate = sum(1 for o in recent if o.success) / len(recent)

        # Boost good performers, penalize poor ones
        return (success_rate - 0.5) * 20

    def _explain_choice(
        self, info: Dict[str, Any], analysis: TaskAnalysis, backend_name: Optional[str]
    ) -> str:
        """Build a human-readable explanation of the routing decision."""
        profile = info.get("profile")
        if not profile:
            return f"selected {info['name']} (no profile)"

        parts = [f"{profile.tool_calling_quality} tool calling"]
        if analysis.tags and profile.task_tags:
            matching = set(analysis.tags) & set(profile.task_tags)
            if matching:
                parts.append(f"matches tags: {', '.join(matching)}")
        parts.append(f"quality={profile.quality_rating}/10")
        parts.append(f"speed={profile.speed_rating}/10")
        if backend_name:
            parts.append(f"backend={backend_name}")
        return "; ".join(parts)

    def record_outcome(
        self,
        model: str,
        task_type: str,
        success: bool,
        duration_ms: float,
        backend_name: Optional[str] = None,
    ) -> None:
        """Record a routing outcome for feedback learning."""
        outcome = RoutingOutcome(
            model=model,
            task_type=task_type,
            success=success,
            duration_ms=duration_ms,
            backend_name=backend_name,
        )
        self._outcomes[model][task_type].append(outcome)
        logger.info("routing_outcome_recorded", model=model,
                     task_type=task_type, success=success,
                     backend=backend_name)

    def get_stats(self) -> Dict[str, Any]:
        """Get routing performance statistics."""
        stats = {}
        for model, task_types in self._outcomes.items():
            model_stats = {}
            for task_type, outcomes in task_types.items():
                if not outcomes:
                    continue
                recent = list(outcomes)
                model_stats[task_type] = {
                    "total": len(recent),
                    "success_rate": round(
                        sum(1 for o in recent if o.success) / len(recent), 3
                    ),
                    "avg_duration_ms": round(
                        sum(o.duration_ms for o in recent) / len(recent), 1
                    ),
                }
            if model_stats:
                stats[model] = model_stats
        return stats
