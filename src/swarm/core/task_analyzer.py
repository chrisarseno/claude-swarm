"""
Task Analyzer.

Analyzes incoming prompts to determine task type, complexity,
required capabilities, and suggested model tags.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TaskType(str, Enum):
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    CODE_GENERATION = "code_generation"
    REFACTORING = "refactoring"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    SECURITY_AUDIT = "security_audit"
    ARCHITECTURE = "architecture"
    RESEARCH_INTELLIGENCE = "research_intelligence"
    DATA_HARVESTING = "data_harvesting"
    SECURITY_OPERATIONS = "security_operations"
    GENERAL = "general"


class Complexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


@dataclass
class TaskAnalysis:
    """Result of analyzing a task prompt."""

    task_type: TaskType
    complexity: Complexity
    tags: List[str] = field(default_factory=list)
    detected_languages: List[str] = field(default_factory=list)
    file_scope: int = 0  # estimated number of files involved
    suggested_capabilities: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0-1, how confident the analysis is


# Keyword patterns for task type detection
_TASK_PATTERNS: Dict[TaskType, List[str]] = {
    TaskType.CODE_REVIEW: [
        "review", "analyze", "check", "audit", "inspect", "look at",
        "quality", "feedback", "evaluate", "assess",
    ],
    TaskType.DEBUGGING: [
        "debug", "fix", "bug", "error", "issue", "problem", "crash",
        "broken", "failing", "exception", "traceback", "stack trace",
    ],
    TaskType.CODE_GENERATION: [
        "write", "create", "implement", "build", "develop", "generate",
        "add", "make", "construct", "scaffold",
    ],
    TaskType.REFACTORING: [
        "refactor", "restructure", "reorganize", "improve", "optimize",
        "clean up", "simplify", "extract", "decompose",
    ],
    TaskType.TESTING: [
        "test", "testing", "unit test", "integration test", "pytest",
        "coverage", "spec", "assertion", "mock",
    ],
    TaskType.DOCUMENTATION: [
        "document", "documentation", "docstring", "readme", "comment",
        "explain", "describe", "annotate",
    ],
    TaskType.SECURITY_AUDIT: [
        "security", "vulnerability", "exploit", "injection", "xss",
        "auth", "permission", "csrf", "owasp", "hardening",
    ],
    TaskType.ARCHITECTURE: [
        "architecture", "design", "pattern", "structure", "diagram",
        "system design", "microservice", "api design", "schema",
    ],
    TaskType.RESEARCH_INTELLIGENCE: [
        "market scan", "competitive analysis", "market intelligence",
        "technology radar", "trend research", "trend analysis",
        "insights", "research report", "competitive landscape",
        "industry analysis", "market research",
    ],
    TaskType.DATA_HARVESTING: [
        "harvest", "data collection", "data source", "data quality",
        "data pipeline", "data ingestion", "source monitoring",
        "data audit", "scrape", "crawl", "extract data",
    ],
    TaskType.SECURITY_OPERATIONS: [
        "threat assessment", "security scan", "compliance audit",
        "security posture", "alert management", "continuous monitoring",
        "threat detection", "incident response", "access review",
        "security monitoring", "vulnerability scan",
    ],
}

_COMPLEXITY_INDICATORS = {
    Complexity.SIMPLE: [
        "simple", "quick", "small", "minor", "typo", "rename",
        "one file", "single", "trivial",
    ],
    Complexity.COMPLEX: [
        "complex", "architecture", "redesign", "migrate", "entire",
        "all files", "multiple files", "large", "comprehensive",
        "across the codebase", "system-wide",
    ],
}

_LANGUAGE_PATTERNS = {
    "python": [r"\.py\b", r"\bpython\b", r"\bpytest\b", r"\bdjango\b", r"\bflask\b"],
    "javascript": [r"\.js\b", r"\bjavascript\b", r"\bnode\b", r"\breact\b", r"\bnpm\b"],
    "typescript": [r"\.ts\b", r"\btypescript\b", r"\bangular\b", r"\.tsx\b"],
    "rust": [r"\.rs\b", r"\brust\b", r"\bcargo\b"],
    "go": [r"\.go\b", r"\bgolang\b"],
    "java": [r"\.java\b", r"\bjava\b", r"\bspring\b", r"\bmaven\b"],
    "sql": [r"\bsql\b", r"\bquery\b", r"\bdatabase\b", r"\btable\b"],
}


class TaskAnalyzer:
    """Analyzes task prompts to determine requirements."""

    def analyze(self, prompt: str, context: Optional[Dict] = None) -> TaskAnalysis:
        """Analyze a task prompt and return structured analysis."""
        context = context or {}
        prompt_lower = prompt.lower()

        # Detect task type
        task_type, type_confidence = self._detect_task_type(prompt_lower)

        # Detect complexity
        complexity = self._detect_complexity(prompt_lower, context)

        # Detect languages
        languages = self._detect_languages(prompt)

        # Estimate file scope
        file_scope = self._estimate_file_scope(prompt_lower, context)

        # Build tags from task type
        tag_map = {
            TaskType.CODE_REVIEW: ["code_review"],
            TaskType.DEBUGGING: ["debugging"],
            TaskType.CODE_GENERATION: ["code_generation"],
            TaskType.REFACTORING: ["refactoring"],
            TaskType.TESTING: ["testing"],
            TaskType.DOCUMENTATION: ["documentation"],
            TaskType.SECURITY_AUDIT: ["security_audit"],
            TaskType.ARCHITECTURE: ["architecture"],
            TaskType.RESEARCH_INTELLIGENCE: ["research_intelligence", "research", "strategic_planning"],
            TaskType.DATA_HARVESTING: ["data_harvesting", "data_governance", "operational_planning"],
            TaskType.SECURITY_OPERATIONS: ["security_operations", "security_audit", "compliance", "risk_assessment"],
            TaskType.GENERAL: ["general"],
        }
        tags = tag_map.get(task_type, ["general"])

        # Suggested capabilities
        capabilities = list(tags)
        if languages:
            capabilities.extend(languages)
        if complexity == Complexity.COMPLEX:
            capabilities.append("architecture")

        return TaskAnalysis(
            task_type=task_type,
            complexity=complexity,
            tags=tags,
            detected_languages=languages,
            file_scope=file_scope,
            suggested_capabilities=capabilities,
            confidence=type_confidence,
        )

    def _detect_task_type(self, prompt_lower: str) -> tuple:
        """Detect the primary task type and confidence."""
        scores: Dict[TaskType, float] = {}
        for task_type, keywords in _TASK_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > 0:
                scores[task_type] = score

        if not scores:
            return TaskType.GENERAL, 0.3

        best_type = max(scores, key=scores.get)
        max_score = scores[best_type]
        total_keywords = len(_TASK_PATTERNS[best_type])
        confidence = min(max_score / max(total_keywords * 0.3, 1), 1.0)

        return best_type, confidence

    def _detect_complexity(self, prompt_lower: str, context: Dict) -> Complexity:
        """Estimate task complexity."""
        for kw in _COMPLEXITY_INDICATORS[Complexity.COMPLEX]:
            if kw in prompt_lower:
                return Complexity.COMPLEX

        for kw in _COMPLEXITY_INDICATORS[Complexity.SIMPLE]:
            if kw in prompt_lower:
                return Complexity.SIMPLE

        # Check context for hints
        file_count = len(context.get("files", []))
        if file_count > 5:
            return Complexity.COMPLEX
        if file_count > 2:
            return Complexity.MODERATE

        # Length heuristic
        if len(prompt_lower) > 500:
            return Complexity.COMPLEX
        if len(prompt_lower) < 100:
            return Complexity.SIMPLE

        return Complexity.MODERATE

    def _detect_languages(self, prompt: str) -> List[str]:
        """Detect programming languages mentioned or referenced."""
        detected = []
        for lang, patterns in _LANGUAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, prompt, re.IGNORECASE):
                    detected.append(lang)
                    break
        return detected

    def _estimate_file_scope(self, prompt_lower: str, context: Dict) -> int:
        """Estimate how many files the task involves."""
        if context.get("files"):
            return len(context["files"])

        if any(w in prompt_lower for w in ["entire", "all files", "codebase", "whole project"]):
            return 50
        if any(w in prompt_lower for w in ["multiple files", "several files", "across"]):
            return 10
        if any(w in prompt_lower for w in ["this file", "single file", "one file"]):
            return 1

        # Count file path mentions
        path_pattern = re.compile(r'[\w./\\-]+\.(?:py|js|ts|go|rs|java)\b')
        paths = path_pattern.findall(prompt_lower)
        return max(len(set(paths)), 1)
