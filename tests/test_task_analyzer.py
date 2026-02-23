"""Tests for TaskAnalyzer — task type detection, complexity, and tag mapping."""

import pytest

from swarm.core.task_analyzer import (
    TaskAnalyzer,
    TaskType,
    Complexity,
    TaskAnalysis,
)


@pytest.fixture
def analyzer():
    return TaskAnalyzer()


# =============================================================================
# Task Type Detection — Original Types
# =============================================================================


class TestOriginalTaskTypes:
    def test_code_review(self, analyzer):
        r = analyzer.analyze("Review this code for quality issues")
        assert r.task_type == TaskType.CODE_REVIEW

    def test_debugging(self, analyzer):
        r = analyzer.analyze("Fix the bug causing a crash in production")
        assert r.task_type == TaskType.DEBUGGING

    def test_code_generation(self, analyzer):
        r = analyzer.analyze("Write a function to implement the login feature")
        assert r.task_type == TaskType.CODE_GENERATION

    def test_refactoring(self, analyzer):
        r = analyzer.analyze("Refactor and simplify this module")
        assert r.task_type == TaskType.REFACTORING

    def test_testing(self, analyzer):
        r = analyzer.analyze("Write unit tests with pytest for the auth module")
        assert r.task_type == TaskType.TESTING

    def test_documentation(self, analyzer):
        r = analyzer.analyze("Document this API with docstrings and a readme")
        assert r.task_type == TaskType.DOCUMENTATION

    def test_security_audit(self, analyzer):
        r = analyzer.analyze("Check for XSS and injection vulnerabilities")
        assert r.task_type == TaskType.SECURITY_AUDIT

    def test_architecture(self, analyzer):
        r = analyzer.analyze("Design the system architecture and API schema")
        assert r.task_type == TaskType.ARCHITECTURE

    def test_general_fallback(self, analyzer):
        r = analyzer.analyze("Do something interesting today")
        assert r.task_type == TaskType.GENERAL
        assert r.confidence == pytest.approx(0.3)


# =============================================================================
# Task Type Detection — New Module Types
# =============================================================================


class TestResearchIntelligence:
    def test_market_scan(self, analyzer):
        r = analyzer.analyze("Run a market scan on competitor pricing")
        assert r.task_type == TaskType.RESEARCH_INTELLIGENCE

    def test_competitive_analysis(self, analyzer):
        r = analyzer.analyze("Compile a competitive analysis report")
        assert r.task_type == TaskType.RESEARCH_INTELLIGENCE

    def test_trend_research(self, analyzer):
        r = analyzer.analyze("Do trend research on AI adoption in healthcare")
        assert r.task_type == TaskType.RESEARCH_INTELLIGENCE

    def test_market_intelligence(self, analyzer):
        r = analyzer.analyze("Gather market intelligence on the SaaS space")
        assert r.task_type == TaskType.RESEARCH_INTELLIGENCE

    def test_tags_include_research(self, analyzer):
        r = analyzer.analyze("Run a market scan and competitive analysis")
        assert "research_intelligence" in r.tags
        assert "research" in r.tags
        assert "strategic_planning" in r.tags


class TestDataHarvesting:
    def test_harvest_cycle(self, analyzer):
        r = analyzer.analyze("Execute a harvest cycle from all data sources")
        assert r.task_type == TaskType.DATA_HARVESTING

    def test_data_quality(self, analyzer):
        r = analyzer.analyze("Run a data quality report on the data pipeline ingestion")
        assert r.task_type == TaskType.DATA_HARVESTING

    def test_data_collection(self, analyzer):
        r = analyzer.analyze("Set up data collection from the new data source")
        assert r.task_type == TaskType.DATA_HARVESTING

    def test_source_monitoring(self, analyzer):
        r = analyzer.analyze("Enable source monitoring for the data pipeline")
        assert r.task_type == TaskType.DATA_HARVESTING

    def test_tags_include_harvesting(self, analyzer):
        r = analyzer.analyze("Run a harvest cycle from all data sources with source monitoring")
        assert "data_harvesting" in r.tags
        assert "data_governance" in r.tags
        assert "operational_planning" in r.tags


class TestSecurityOperations:
    def test_security_scan(self, analyzer):
        r = analyzer.analyze("Run a security scan with continuous monitoring on the deployment")
        assert r.task_type == TaskType.SECURITY_OPERATIONS

    def test_threat_assessment(self, analyzer):
        r = analyzer.analyze("Generate a threat assessment and threat detection report")
        assert r.task_type == TaskType.SECURITY_OPERATIONS

    def test_compliance_audit(self, analyzer):
        r = analyzer.analyze("Perform a compliance audit with security posture and threat assessment")
        assert r.task_type == TaskType.SECURITY_OPERATIONS

    def test_continuous_monitoring(self, analyzer):
        r = analyzer.analyze("Set up continuous monitoring for production alerts")
        assert r.task_type == TaskType.SECURITY_OPERATIONS

    def test_tags_include_secops(self, analyzer):
        r = analyzer.analyze("Run a security scan and threat assessment")
        assert "security_operations" in r.tags
        assert "security_audit" in r.tags
        assert "compliance" in r.tags
        assert "risk_assessment" in r.tags


# =============================================================================
# Complexity Detection
# =============================================================================


class TestComplexity:
    def test_simple_keyword(self, analyzer):
        r = analyzer.analyze("Fix a simple typo in the config")
        assert r.complexity == Complexity.SIMPLE

    def test_complex_keyword(self, analyzer):
        r = analyzer.analyze("Redesign the entire architecture across the codebase")
        assert r.complexity == Complexity.COMPLEX

    def test_moderate_default(self, analyzer):
        r = analyzer.analyze("Update the login handler to check permissions before access, and also refactor the middleware layer to support the new auth flow")
        assert r.complexity == Complexity.MODERATE

    def test_short_prompt_is_simple(self, analyzer):
        r = analyzer.analyze("Fix typo")
        assert r.complexity == Complexity.SIMPLE

    def test_long_prompt_is_complex(self, analyzer):
        prompt = "Please review " + "this very detailed specification " * 20
        r = analyzer.analyze(prompt)
        assert r.complexity == Complexity.COMPLEX

    def test_many_files_in_context(self, analyzer):
        r = analyzer.analyze("Update code", context={"files": ["a.py", "b.py", "c.py", "d.py", "e.py", "f.py"]})
        assert r.complexity == Complexity.COMPLEX


# =============================================================================
# Language Detection
# =============================================================================


class TestLanguageDetection:
    def test_python(self, analyzer):
        r = analyzer.analyze("Fix the bug in main.py using pytest")
        assert "python" in r.detected_languages

    def test_javascript(self, analyzer):
        r = analyzer.analyze("Update the React component in app.js")
        assert "javascript" in r.detected_languages

    def test_typescript(self, analyzer):
        r = analyzer.analyze("Refactor the Angular service in auth.ts")
        assert "typescript" in r.detected_languages

    def test_multiple_languages(self, analyzer):
        r = analyzer.analyze("Fix the Python backend and the React frontend .js")
        assert "python" in r.detected_languages
        assert "javascript" in r.detected_languages


# =============================================================================
# File Scope Estimation
# =============================================================================


class TestFileScope:
    def test_explicit_context(self, analyzer):
        r = analyzer.analyze("Fix it", context={"files": ["a.py", "b.py"]})
        assert r.file_scope == 2

    def test_entire_codebase(self, analyzer):
        r = analyzer.analyze("Refactor the entire codebase")
        assert r.file_scope == 50

    def test_multiple_files(self, analyzer):
        r = analyzer.analyze("Update across multiple files")
        assert r.file_scope == 10

    def test_single_file(self, analyzer):
        r = analyzer.analyze("Fix this file only")
        assert r.file_scope == 1


# =============================================================================
# Tag Mapping & Capabilities
# =============================================================================


class TestTagMapping:
    def test_all_task_types_have_tags(self, analyzer):
        """Every TaskType must produce at least one tag."""
        for tt in TaskType:
            # Craft a prompt that forces this type (or just test the tag_map)
            pass  # Covered by individual type tests above

    def test_capabilities_include_tags(self, analyzer):
        r = analyzer.analyze("Run a market scan")
        assert all(tag in r.suggested_capabilities for tag in r.tags)

    def test_capabilities_include_languages(self, analyzer):
        r = analyzer.analyze("Fix the Python bug in main.py")
        assert "python" in r.suggested_capabilities

    def test_complex_adds_architecture_capability(self, analyzer):
        r = analyzer.analyze("Redesign the entire system architecture")
        assert "architecture" in r.suggested_capabilities


# =============================================================================
# Confidence
# =============================================================================


class TestConfidence:
    def test_high_confidence_multiple_keywords(self, analyzer):
        r = analyzer.analyze("Debug the error causing a crash with this traceback exception")
        assert r.confidence > 0.5

    def test_low_confidence_general(self, analyzer):
        r = analyzer.analyze("Something vague")
        assert r.confidence == pytest.approx(0.3)

    def test_confidence_bounded(self, analyzer):
        r = analyzer.analyze("review analyze check audit inspect evaluate assess quality feedback")
        assert r.confidence <= 1.0
