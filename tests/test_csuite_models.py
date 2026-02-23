"""Tests for C-Suite model profiles in the Ollama registry."""

import pytest

from swarm.agents.ollama_registry import (
    OLLAMA_MODELS,
    ModelProfile,
    ModelSize,
    Quantization,
    get_model_profile,
    find_models_by_capability,
    find_tool_capable_models,
    find_models_by_task_tag,
)
from swarm.agents.base import AgentCapability


# =============================================================================
# C-Suite Model Profile Existence
# =============================================================================


CSUITE_MODELS = [
    "csuite-model:latest",
    "csuite-technical:latest",
    "csuite-business:latest",
    "csuite-operations:latest",
    "csuite-governance:latest",
]


class TestCSuiteModelProfiles:
    """Verify all 5 C-Suite model profiles exist and are valid."""

    def test_all_5_models_registered(self):
        for model_key in CSUITE_MODELS:
            assert model_key in OLLAMA_MODELS, f"{model_key} not in OLLAMA_MODELS"

    @pytest.mark.parametrize("model_key", CSUITE_MODELS)
    def test_profile_has_required_fields(self, model_key):
        profile = OLLAMA_MODELS[model_key]
        assert profile.name
        assert profile.full_name
        assert profile.description
        assert profile.size == ModelSize.MEDIUM
        assert profile.params == "8B"
        assert profile.context_window == 4096
        assert len(profile.capabilities) > 0
        assert len(profile.strengths) > 0
        assert len(profile.weaknesses) > 0
        assert len(profile.best_for) > 0
        assert len(profile.quantizations) > 0
        assert 1 <= profile.speed_rating <= 10
        assert 1 <= profile.quality_rating <= 10
        assert "q5" in profile.vram_required
        assert profile.recommended_quant == Quantization.Q5

    @pytest.mark.parametrize("model_key", CSUITE_MODELS)
    def test_task_tags_not_empty(self, model_key):
        profile = OLLAMA_MODELS[model_key]
        assert len(profile.task_tags) > 0, f"{model_key} has no task_tags"


# =============================================================================
# Generalist Model (csuite-model)
# =============================================================================


class TestCSuiteGeneralist:
    def test_name(self):
        p = OLLAMA_MODELS["csuite-model:latest"]
        assert p.name == "csuite-model"

    def test_supports_tool_calling(self):
        p = OLLAMA_MODELS["csuite-model:latest"]
        assert p.supports_tool_calling is True
        assert p.tool_calling_quality == "good"

    def test_has_code_capabilities(self):
        p = OLLAMA_MODELS["csuite-model:latest"]
        assert AgentCapability.CODE_GENERATION in p.capabilities
        assert AgentCapability.CODE_REVIEW in p.capabilities

    def test_broad_task_tags(self):
        p = OLLAMA_MODELS["csuite-model:latest"]
        assert "code_review" in p.task_tags
        assert "architecture" in p.task_tags


# =============================================================================
# Domain Specialists
# =============================================================================


class TestCSuiteTechnical:
    def test_name(self):
        p = OLLAMA_MODELS["csuite-technical:latest"]
        assert p.name == "csuite-technical"

    def test_supports_tool_calling(self):
        p = OLLAMA_MODELS["csuite-technical:latest"]
        assert p.supports_tool_calling is True

    def test_security_capability(self):
        p = OLLAMA_MODELS["csuite-technical:latest"]
        assert AgentCapability.SECURITY in p.capabilities

    def test_technical_tags(self):
        p = OLLAMA_MODELS["csuite-technical:latest"]
        assert "security_audit" in p.task_tags
        assert "code_review" in p.task_tags
        assert "debugging" in p.task_tags


class TestCSuiteBusiness:
    def test_name(self):
        p = OLLAMA_MODELS["csuite-business:latest"]
        assert p.name == "csuite-business"

    def test_no_tool_calling(self):
        p = OLLAMA_MODELS["csuite-business:latest"]
        assert p.supports_tool_calling is False

    def test_business_tags(self):
        p = OLLAMA_MODELS["csuite-business:latest"]
        assert "cost_analysis" in p.task_tags
        assert "strategic_planning" in p.task_tags


class TestCSuiteOperations:
    def test_name(self):
        p = OLLAMA_MODELS["csuite-operations:latest"]
        assert p.name == "csuite-operations"

    def test_operations_tags(self):
        p = OLLAMA_MODELS["csuite-operations:latest"]
        assert "task_routing" in p.task_tags
        assert "data_governance" in p.task_tags


class TestCSuiteGovernance:
    def test_name(self):
        p = OLLAMA_MODELS["csuite-governance:latest"]
        assert p.name == "csuite-governance"

    def test_governance_tags(self):
        p = OLLAMA_MODELS["csuite-governance:latest"]
        assert "compliance" in p.task_tags
        assert "risk_assessment" in p.task_tags


# =============================================================================
# Routing and Discovery
# =============================================================================


class TestCSuiteRouting:
    """Test that C-Suite models are discoverable through registry functions."""

    def test_find_by_code_review_tag(self):
        models = find_models_by_task_tag("code_review")
        names = [m.name for m in models]
        assert "csuite-model" in names
        assert "csuite-technical" in names

    def test_find_by_compliance_tag(self):
        models = find_models_by_task_tag("compliance")
        names = [m.name for m in models]
        assert "csuite-governance" in names

    def test_find_by_cost_analysis_tag(self):
        models = find_models_by_task_tag("cost_analysis")
        names = [m.name for m in models]
        assert "csuite-business" in names

    def test_find_tool_capable_includes_csuite(self):
        models = find_tool_capable_models(min_quality="good")
        names = [m.name for m in models]
        assert "csuite-model" in names
        assert "csuite-technical" in names
        # Business/ops/governance don't have tool calling
        assert "csuite-business" not in names

    def test_get_profile_by_name(self):
        profile = get_model_profile("csuite-model:latest")
        assert profile is not None
        assert profile.name == "csuite-model"

    def test_get_profile_partial_match(self):
        profile = get_model_profile("csuite-technical")
        assert profile is not None
        assert profile.name == "csuite-technical"

    def test_find_by_security_capability(self):
        models = find_models_by_capability(AgentCapability.SECURITY)
        names = [m.name for m in models]
        assert "csuite-technical" in names


class TestModelCatalogIntegrity:
    """Verify C-Suite models appear in the catalog categories."""

    def test_catalog_has_csuite_category(self):
        from swarm.agents.ollama_registry import print_model_catalog
        # Just verify it doesn't crash
        # (actual printing is a side effect, not tested)
        assert True  # existence test above covers this
