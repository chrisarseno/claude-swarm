"""Tests for SwarmRouter — scoring, routing decisions, and feedback."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from swarm.core.swarm_router import (
    SwarmRouter,
    RoutingDecision,
    RoutingOutcome,
    CAPABILITY_WEIGHT,
    QUALITY_WEIGHT,
    SPEED_WEIGHT,
    CONTEXT_WEIGHT,
)
from swarm.core.task_analyzer import TaskAnalysis, TaskType, Complexity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_analysis(
    task_type=TaskType.CODE_GENERATION,
    complexity=Complexity.MODERATE,
    tags=None,
    confidence=0.8,
):
    """Create a TaskAnalysis for testing."""
    return TaskAnalysis(
        task_type=task_type,
        complexity=complexity,
        tags=tags or ["code", "debugging"],
        detected_languages=["python"],
        file_scope=5,
        confidence=confidence,
        suggested_capabilities=tags or ["code", "debugging"],
    )


def make_profile(
    name="qwen2.5:7b",
    quality_rating=8,
    speed_rating=7,
    context_window=32768,
    task_tags=None,
    tool_calling_quality="good",
):
    """Create a mock ModelProfile."""
    p = MagicMock()
    p.name = name
    p.quality_rating = quality_rating
    p.speed_rating = speed_rating
    p.context_window = context_window
    p.task_tags = task_tags or ["code", "debugging", "code_review"]
    p.tool_calling_quality = tool_calling_quality
    return p


def make_registry(candidates=None, all_models=None):
    """Create a mock LiveModelRegistry."""
    registry = MagicMock()
    registry.get_best_model_for = AsyncMock(return_value=candidates or [])
    registry.get_installed_models = AsyncMock(return_value=all_models or [])
    return registry


# =============================================================================
# Dataclasses
# =============================================================================


class TestRoutingDecision:
    def test_defaults(self):
        d = RoutingDecision(model="test", score=42.0, reason="test")
        assert d.backend_name is None
        assert d.analysis is None
        assert d.alternatives == []


class TestRoutingOutcome:
    def test_creation(self):
        o = RoutingOutcome(model="m", task_type="code", success=True, duration_ms=100)
        assert o.model == "m"
        assert o.timestamp > 0


# =============================================================================
# Scoring Weights
# =============================================================================


class TestWeights:
    def test_weights_sum_to_one(self):
        total = CAPABILITY_WEIGHT + QUALITY_WEIGHT + SPEED_WEIGHT + CONTEXT_WEIGHT
        assert total == pytest.approx(1.0)


# =============================================================================
# _score_model
# =============================================================================


class TestScoreModel:
    @pytest.fixture
    def router(self):
        return SwarmRouter(model_registry=make_registry())

    def test_capability_match_full(self, router):
        profile = make_profile(task_tags=["code", "debugging"])
        analysis = make_analysis(tags=["code", "debugging"])
        score = router._score_model(profile, analysis, prefer_speed=False)
        # Full capability match = 100 * 0.4 = 40
        assert score > 30

    def test_capability_match_partial(self, router):
        profile = make_profile(task_tags=["code"])
        analysis = make_analysis(tags=["code", "debugging"])
        score_partial = router._score_model(profile, analysis, prefer_speed=False)

        profile_full = make_profile(task_tags=["code", "debugging"])
        score_full = router._score_model(profile_full, analysis, prefer_speed=False)
        assert score_full > score_partial

    def test_capability_match_none(self, router):
        profile = make_profile(task_tags=["unrelated"])
        analysis = make_analysis(tags=["code", "debugging"])
        score = router._score_model(profile, analysis, prefer_speed=False)
        # No capability match, but still gets quality/speed/context
        assert score > 0

    def test_prefer_speed_doubles_speed_weight(self, router):
        profile = make_profile(speed_rating=9, quality_rating=5)
        analysis = make_analysis()
        score_normal = router._score_model(profile, analysis, prefer_speed=False)
        score_fast = router._score_model(profile, analysis, prefer_speed=True)
        assert score_fast > score_normal

    def test_complex_needs_large_context(self, router):
        analysis = make_analysis(complexity=Complexity.COMPLEX)

        large = make_profile(context_window=131072)
        small = make_profile(context_window=4096)

        score_large = router._score_model(large, analysis, prefer_speed=False)
        score_small = router._score_model(small, analysis, prefer_speed=False)
        assert score_large > score_small

    def test_tool_calling_bonus(self, router):
        excellent = make_profile(tool_calling_quality="excellent")
        none_ = make_profile(tool_calling_quality="none")
        analysis = make_analysis()

        score_ex = router._score_model(excellent, analysis, prefer_speed=False)
        score_none = router._score_model(none_, analysis, prefer_speed=False)
        assert score_ex > score_none

    def test_complexity_quality_alignment(self, router):
        high_quality = make_profile(quality_rating=9)
        low_quality = make_profile(quality_rating=5)
        complex_analysis = make_analysis(complexity=Complexity.COMPLEX)

        score_hq = router._score_model(high_quality, complex_analysis, prefer_speed=False)
        score_lq = router._score_model(low_quality, complex_analysis, prefer_speed=False)
        # High quality gets +10 alignment bonus for complex tasks
        assert score_hq > score_lq

    def test_simple_speed_alignment(self, router):
        fast = make_profile(speed_rating=9)
        slow = make_profile(speed_rating=3)
        simple = make_analysis(complexity=Complexity.SIMPLE)

        score_fast = router._score_model(fast, simple, prefer_speed=False)
        score_slow = router._score_model(slow, simple, prefer_speed=False)
        assert score_fast > score_slow

    def test_empty_tags_no_crash(self, router):
        profile = make_profile(task_tags=[])
        analysis = make_analysis(tags=[])
        score = router._score_model(profile, analysis, prefer_speed=False)
        assert score >= 0


# =============================================================================
# _performance_adjustment
# =============================================================================


class TestPerformanceAdjustment:
    @pytest.fixture
    def router(self):
        return SwarmRouter(model_registry=make_registry())

    def test_no_history_returns_zero(self, router):
        assert router._performance_adjustment("model", "code") == 0.0

    def test_fewer_than_3_returns_zero(self, router):
        router.record_outcome("m", "code", True, 100)
        router.record_outcome("m", "code", True, 100)
        assert router._performance_adjustment("m", "code") == 0.0

    def test_all_success_positive(self, router):
        for _ in range(5):
            router.record_outcome("m", "code", True, 100)
        adj = router._performance_adjustment("m", "code")
        assert adj > 0

    def test_all_failure_negative(self, router):
        for _ in range(5):
            router.record_outcome("m", "code", False, 100)
        adj = router._performance_adjustment("m", "code")
        assert adj < 0

    def test_mixed_proportional(self, router):
        for _ in range(7):
            router.record_outcome("m", "code", True, 100)
        for _ in range(3):
            router.record_outcome("m", "code", False, 100)
        adj = router._performance_adjustment("m", "code")
        # 70% success -> (0.7 - 0.5) * 20 = 4.0
        assert adj == pytest.approx(4.0)


# =============================================================================
# record_outcome / get_stats
# =============================================================================


class TestOutcomeTracking:
    @pytest.fixture
    def router(self):
        return SwarmRouter(model_registry=make_registry())

    def test_record_and_stats(self, router):
        router.record_outcome("m1", "code", True, 100)
        router.record_outcome("m1", "code", False, 200)
        router.record_outcome("m1", "debug", True, 150)

        stats = router.get_stats()
        assert "m1" in stats
        assert stats["m1"]["code"]["total"] == 2
        assert stats["m1"]["code"]["success_rate"] == 0.5
        assert stats["m1"]["code"]["avg_duration_ms"] == 150.0
        assert stats["m1"]["debug"]["total"] == 1

    def test_empty_stats(self, router):
        assert router.get_stats() == {}

    def test_bounded_deque(self, router):
        for i in range(150):
            router.record_outcome("m", "code", True, float(i))
        stats = router.get_stats()
        assert stats["m"]["code"]["total"] == 100  # maxlen=100


# =============================================================================
# _explain_choice
# =============================================================================


class TestExplainChoice:
    @pytest.fixture
    def router(self):
        return SwarmRouter(model_registry=make_registry())

    def test_with_profile(self, router):
        profile = make_profile(name="test-model", quality_rating=8, speed_rating=7)
        info = {"name": "test-model", "profile": profile}
        analysis = make_analysis(tags=["code", "debugging"])
        explanation = router._explain_choice(info, analysis, backend_name="local")
        assert "quality=8/10" in explanation
        assert "speed=7/10" in explanation
        assert "backend=local" in explanation

    def test_without_profile(self, router):
        info = {"name": "test-model", "profile": None}
        analysis = make_analysis()
        explanation = router._explain_choice(info, analysis, backend_name=None)
        assert "no profile" in explanation

    def test_matching_tags_shown(self, router):
        profile = make_profile(task_tags=["code", "debugging"])
        info = {"name": "m", "profile": profile}
        analysis = make_analysis(tags=["code", "debugging"])
        explanation = router._explain_choice(info, analysis, backend_name=None)
        assert "matches tags" in explanation


# =============================================================================
# route() — full routing
# =============================================================================


class TestRoute:
    @pytest.mark.asyncio
    async def test_route_selects_best_candidate(self):
        profile = make_profile(name="qwen2.5:7b")
        registry = make_registry(
            candidates=[
                {"name": "qwen2.5:7b", "profile": profile, "backends": ["local"]},
            ]
        )
        router = SwarmRouter(model_registry=registry)
        analysis = make_analysis(tags=["code", "debugging"])

        decision = await router.route(analysis)
        assert decision.model == "qwen2.5:7b"
        assert decision.score > 0

    @pytest.mark.asyncio
    async def test_route_no_candidates_uses_fallback(self):
        registry = make_registry(candidates=[])
        router = SwarmRouter(model_registry=registry)
        analysis = make_analysis()

        decision = await router.route(analysis, fallback_model="llama3:8b")
        assert decision.model == "llama3:8b"
        assert decision.score == 0.0
        assert "fallback" in decision.reason

    @pytest.mark.asyncio
    async def test_route_no_candidates_uses_first_installed(self):
        registry = make_registry(
            candidates=[],
            all_models=[{"name": "gemma2:9b", "backends": ["local"]}],
        )
        router = SwarmRouter(model_registry=registry)
        analysis = make_analysis()

        decision = await router.route(analysis)
        assert decision.model == "gemma2:9b"
        assert "default" in decision.reason

    @pytest.mark.asyncio
    async def test_route_no_models_at_all(self):
        registry = make_registry(candidates=[], all_models=[])
        router = SwarmRouter(model_registry=registry)
        analysis = make_analysis()

        decision = await router.route(analysis)
        assert decision.model == "qwen2.5:7b"  # hardcoded fallback
        assert "hardcoded" in decision.reason

    @pytest.mark.asyncio
    async def test_preferred_models_get_boost(self):
        p1 = make_profile(name="slow-good", quality_rating=9, speed_rating=3)
        p2 = make_profile(name="fast-ok", quality_rating=6, speed_rating=9)
        registry = make_registry(
            candidates=[
                {"name": "slow-good", "profile": p1, "backends": ["local"]},
                {"name": "fast-ok", "profile": p2, "backends": ["local"]},
            ]
        )
        router = SwarmRouter(model_registry=registry)
        analysis = make_analysis()

        # Without preference, slow-good wins on quality
        d1 = await router.route(analysis)

        # With preference for fast-ok, it gets +20 boost
        d2 = await router.route(analysis, preferred_models=["fast-ok"])
        assert d2.model == "fast-ok"

    @pytest.mark.asyncio
    async def test_route_returns_alternatives(self):
        profiles = [
            make_profile(name=f"model-{i}", quality_rating=9 - i)
            for i in range(4)
        ]
        candidates = [
            {"name": f"model-{i}", "profile": profiles[i], "backends": ["local"]}
            for i in range(4)
        ]
        registry = make_registry(candidates=candidates)
        router = SwarmRouter(model_registry=registry)
        analysis = make_analysis()

        decision = await router.route(analysis)
        assert len(decision.alternatives) <= 3

    @pytest.mark.asyncio
    async def test_route_no_profiles_scored(self):
        """Candidates with no profile should be skipped."""
        registry = make_registry(
            candidates=[{"name": "broken", "profile": None, "backends": []}]
        )
        router = SwarmRouter(model_registry=registry)
        analysis = make_analysis()

        decision = await router.route(analysis)
        assert decision.score == 0.0
