"""
Ollama Model Registry
Comprehensive catalog of available Ollama models with capability profiles
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from .base import AgentCapability


class ModelSize(Enum):
    """Model size categories"""
    TINY = "tiny"          # < 1B params
    SMALL = "small"        # 1-7B params
    MEDIUM = "medium"      # 7-15B params
    LARGE = "large"        # 15-35B params
    XLARGE = "xlarge"      # 35B+ params


class Quantization(Enum):
    """Quantization levels"""
    Q2 = "q2"      # 2-bit (smallest, fastest, lowest quality)
    Q3 = "q3"      # 3-bit
    Q4 = "q4"      # 4-bit (good balance)
    Q5 = "q5"      # 5-bit
    Q6 = "q6"      # 6-bit
    Q8 = "q8"      # 8-bit (high quality)
    FP16 = "fp16"  # Full precision (largest, best quality)


@dataclass
class ModelProfile:
    """Profile for an Ollama model"""
    name: str
    full_name: str
    description: str
    size: ModelSize
    params: str  # e.g., "7B", "13B", "34B"
    context_window: int
    capabilities: List[AgentCapability]
    strengths: List[str]
    weaknesses: List[str]
    best_for: List[str]
    quantizations: List[Quantization]
    speed_rating: int  # 1-10 (10 = fastest)
    quality_rating: int  # 1-10 (10 = best)
    vram_required: Dict[str, str]  # GB by quantization
    recommended_quant: Quantization
    # --- Capability tags (Phase 2) ---
    supports_tool_calling: bool = False
    tool_calling_quality: str = "none"  # "excellent", "good", "basic", "none"
    task_tags: List[str] = None  # e.g. ["code_review", "debugging"]

    def __post_init__(self):
        if self.task_tags is None:
            self.task_tags = []


# Comprehensive Model Registry
OLLAMA_MODELS = {
    # === Code-Specialized Models ===

    "deepseek-coder-1.3b": ModelProfile(
        name="deepseek-coder",
        full_name="DeepSeek Coder 1.3B",
        description="Tiny but capable code model, excellent for simple tasks",
        size=ModelSize.SMALL,
        params="1.3B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.DEBUGGING,
            AgentCapability.CODE_REVIEW
        ],
        strengths=[
            "Very fast",
            "Low memory usage",
            "Good for simple code tasks",
            "Excellent code completion"
        ],
        weaknesses=[
            "Limited reasoning",
            "Struggles with complex logic",
            "Less accurate than larger models"
        ],
        best_for=[
            "Code completion",
            "Simple functions",
            "Quick prototypes",
            "Syntax fixes"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=10,
        quality_rating=6,
        vram_required={"q4": "1GB", "q5": "1.5GB", "q8": "2GB"},
        recommended_quant=Quantization.Q4,
        supports_tool_calling=False,
        tool_calling_quality="none",
        task_tags=["code_completion", "syntax_fix", "simple_generation"],
    ),

    "deepseek-coder-6.7b": ModelProfile(
        name="deepseek-coder",
        full_name="DeepSeek Coder 6.7B",
        description="Balanced code model, good for most coding tasks",
        size=ModelSize.MEDIUM,
        params="6.7B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.REFACTORING,
            AgentCapability.TESTING,
            AgentCapability.DOCUMENTATION
        ],
        strengths=[
            "Fast inference",
            "Good code quality",
            "Handles multiple languages well",
            "Strong at bug detection"
        ],
        weaknesses=[
            "Less creative than larger models",
            "Can miss edge cases"
        ],
        best_for=[
            "General coding",
            "Code reviews",
            "Bug fixing",
            "Test generation",
            "Documentation"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=7,
        vram_required={"q4": "4GB", "q5": "5GB", "q8": "7GB"},
        recommended_quant=Quantization.Q4
    ),

    "deepseek-coder-33b": ModelProfile(
        name="deepseek-coder",
        full_name="DeepSeek Coder 33B",
        description="Large, high-quality code model for complex tasks",
        size=ModelSize.LARGE,
        params="33B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.REFACTORING,
            AgentCapability.TESTING,
            AgentCapability.DOCUMENTATION,
            AgentCapability.SECURITY,
            AgentCapability.PERFORMANCE,
            AgentCapability.ANALYSIS
        ],
        strengths=[
            "Excellent code quality",
            "Strong reasoning",
            "Good architecture suggestions",
            "Handles complex refactoring",
            "Security-aware"
        ],
        weaknesses=[
            "Slower inference",
            "Requires more VRAM"
        ],
        best_for=[
            "Complex refactoring",
            "Architecture design",
            "Security analysis",
            "Performance optimization",
            "Large codebases"
        ],
        quantizations=[Quantization.Q2, Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=5,
        quality_rating=9,
        vram_required={"q2": "11GB", "q4": "18GB", "q5": "22GB", "q8": "33GB"},
        recommended_quant=Quantization.Q4
    ),

    "codellama-7b": ModelProfile(
        name="codellama",
        full_name="Code Llama 7B",
        description="Meta's code model, good general-purpose coding",
        size=ModelSize.MEDIUM,
        params="7B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.DEBUGGING,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DOCUMENTATION
        ],
        strengths=[
            "Well-trained on many languages",
            "Good explanations",
            "Reliable",
            "Fast"
        ],
        weaknesses=[
            "Less specialized than DeepSeek Coder",
            "Can be verbose"
        ],
        best_for=[
            "General coding",
            "Learning/teaching",
            "Code explanations",
            "Multi-language support"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=7,
        vram_required={"q4": "4GB", "q5": "5GB", "q8": "7GB"},
        recommended_quant=Quantization.Q4
    ),

    "codellama-13b": ModelProfile(
        name="codellama",
        full_name="Code Llama 13B",
        description="Larger Code Llama, better reasoning",
        size=ModelSize.MEDIUM,
        params="13B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.DEBUGGING,
            AgentCapability.CODE_REVIEW,
            AgentCapability.REFACTORING,
            AgentCapability.TESTING,
            AgentCapability.DOCUMENTATION
        ],
        strengths=[
            "Good reasoning",
            "Handles complexity well",
            "Clear explanations"
        ],
        weaknesses=[
            "Slower than 7B",
            "More VRAM"
        ],
        best_for=[
            "Complex algorithms",
            "Code refactoring",
            "Detailed reviews"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=6,
        quality_rating=8,
        vram_required={"q4": "7GB", "q5": "9GB", "q8": "13GB"},
        recommended_quant=Quantization.Q4
    ),

    "codellama-34b": ModelProfile(
        name="codellama",
        full_name="Code Llama 34B",
        description="Largest Code Llama, best quality",
        size=ModelSize.LARGE,
        params="34B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.REFACTORING,
            AgentCapability.TESTING,
            AgentCapability.DOCUMENTATION,
            AgentCapability.ANALYSIS,
            AgentCapability.SECURITY
        ],
        strengths=[
            "Excellent quality",
            "Strong reasoning",
            "Complex problem solving"
        ],
        weaknesses=[
            "Slow",
            "High VRAM requirements"
        ],
        best_for=[
            "Critical code",
            "Architecture design",
            "Complex refactoring"
        ],
        quantizations=[Quantization.Q2, Quantization.Q4, Quantization.Q5],
        speed_rating=4,
        quality_rating=9,
        vram_required={"q2": "11GB", "q4": "18GB", "q5": "22GB"},
        recommended_quant=Quantization.Q4
    ),

    "phind-codellama-34b": ModelProfile(
        name="phind-codellama",
        full_name="Phind Code Llama 34B",
        description="Fine-tuned for code Q&A and debugging",
        size=ModelSize.LARGE,
        params="34B",
        context_window=16384,
        capabilities=[
            AgentCapability.DEBUGGING,
            AgentCapability.CODE_REVIEW,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_GENERATION
        ],
        strengths=[
            "Excellent at explaining code",
            "Great for debugging",
            "Good at finding bugs",
            "Clear communication"
        ],
        weaknesses=[
            "Can be verbose",
            "Slower"
        ],
        best_for=[
            "Debugging",
            "Code explanation",
            "Finding bugs",
            "Code Q&A"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5],
        speed_rating=4,
        quality_rating=8,
        vram_required={"q4": "18GB", "q5": "22GB"},
        recommended_quant=Quantization.Q4
    ),

    "wizardcoder-7b": ModelProfile(
        name="wizardcoder",
        full_name="WizardCoder 7B",
        description="Instruction-tuned code model",
        size=ModelSize.MEDIUM,
        params="7B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.DEBUGGING,
            AgentCapability.CODE_REVIEW
        ],
        strengths=[
            "Good at following instructions",
            "Fast",
            "Reliable"
        ],
        weaknesses=[
            "Less creative",
            "Struggles with novel problems"
        ],
        best_for=[
            "Straightforward coding tasks",
            "Following specs",
            "Standard patterns"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=7,
        vram_required={"q4": "4GB", "q5": "5GB", "q8": "7GB"},
        recommended_quant=Quantization.Q4
    ),

    "wizardcoder-13b": ModelProfile(
        name="wizardcoder",
        full_name="WizardCoder 13B",
        description="Larger instruction-tuned code model",
        size=ModelSize.MEDIUM,
        params="13B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.DEBUGGING,
            AgentCapability.CODE_REVIEW,
            AgentCapability.REFACTORING
        ],
        strengths=[
            "Better reasoning than 7B",
            "Good quality output",
            "Follows complex instructions"
        ],
        weaknesses=[
            "Slower than 7B"
        ],
        best_for=[
            "Complex coding tasks",
            "Multi-step instructions",
            "Refactoring"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5],
        speed_rating=6,
        quality_rating=7,
        vram_required={"q4": "7GB", "q5": "9GB"},
        recommended_quant=Quantization.Q4
    ),

    "wizardcoder-python-7b": ModelProfile(
        name="wizardcoder-python",
        full_name="WizardCoder Python 7B",
        description="Python-specialized version of WizardCoder",
        size=ModelSize.MEDIUM,
        params="7B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.DEBUGGING,
            AgentCapability.CODE_REVIEW,
            AgentCapability.TESTING
        ],
        strengths=[
            "Excellent Python knowledge",
            "Fast",
            "Good at Python idioms",
            "Strong testing capabilities"
        ],
        weaknesses=[
            "Python only",
            "Limited other languages"
        ],
        best_for=[
            "Python development",
            "Python testing",
            "Django/Flask",
            "Data science code"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=8,
        vram_required={"q4": "4GB", "q5": "5GB", "q8": "7GB"},
        recommended_quant=Quantization.Q4
    ),

    "codebooga-34b": ModelProfile(
        name="codebooga",
        full_name="CodeBooga 34B",
        description="Merge of Code Llama and Phind, creative coder",
        size=ModelSize.LARGE,
        params="34B",
        context_window=32768,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.REFACTORING,
            AgentCapability.ANALYSIS,
            AgentCapability.CODE_REVIEW
        ],
        strengths=[
            "Creative solutions",
            "Large context",
            "Good at complex problems",
            "Handles large codebases"
        ],
        weaknesses=[
            "Can be unpredictable",
            "Slower"
        ],
        best_for=[
            "Creative problem solving",
            "Large context needs",
            "Novel approaches",
            "Architecture design"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5],
        speed_rating=4,
        quality_rating=8,
        vram_required={"q4": "18GB", "q5": "22GB"},
        recommended_quant=Quantization.Q4
    ),

    # === General Purpose (good at coding too) ===

    "mistral-7b": ModelProfile(
        name="mistral",
        full_name="Mistral 7B",
        description="Excellent general-purpose model, surprisingly good at code",
        size=ModelSize.MEDIUM,
        params="7B",
        context_window=8192,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.ANALYSIS,
            AgentCapability.DOCUMENTATION,
            AgentCapability.GENERAL
        ],
        strengths=[
            "Very fast",
            "Good reasoning",
            "Versatile",
            "Concise output"
        ],
        weaknesses=[
            "Not specialized for code",
            "Smaller context than code models"
        ],
        best_for=[
            "Quick tasks",
            "General coding",
            "Documentation",
            "Analysis"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=9,
        quality_rating=7,
        vram_required={"q4": "4GB", "q5": "5GB", "q8": "7GB"},
        recommended_quant=Quantization.Q4
    ),

    "mixtral-8x7b": ModelProfile(
        name="mixtral",
        full_name="Mixtral 8x7B (MoE)",
        description="Mixture of Experts model, very capable",
        size=ModelSize.LARGE,
        params="8x7B",
        context_window=32768,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.ANALYSIS,
            AgentCapability.REFACTORING,
            AgentCapability.GENERAL
        ],
        strengths=[
            "Excellent quality",
            "Large context",
            "Good at complex tasks",
            "Strong reasoning"
        ],
        weaknesses=[
            "High VRAM",
            "Slower"
        ],
        best_for=[
            "Complex problems",
            "Large context",
            "High-quality output needed",
            "Multi-step reasoning"
        ],
        quantizations=[Quantization.Q2, Quantization.Q4, Quantization.Q5],
        speed_rating=4,
        quality_rating=9,
        vram_required={"q2": "16GB", "q4": "26GB", "q5": "32GB"},
        recommended_quant=Quantization.Q4
    ),

    "llama3-8b": ModelProfile(
        name="llama3",
        full_name="Llama 3 8B",
        description="Meta's latest, excellent all-around model",
        size=ModelSize.MEDIUM,
        params="8B",
        context_window=8192,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.ANALYSIS,
            AgentCapability.GENERAL,
            AgentCapability.DOCUMENTATION
        ],
        strengths=[
            "Latest architecture",
            "Good code understanding",
            "Fast",
            "Well-rounded"
        ],
        weaknesses=[
            "Not code-specialized",
            "Smaller context"
        ],
        best_for=[
            "General tasks",
            "Quick coding",
            "Analysis",
            "Documentation"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=8,
        vram_required={"q4": "5GB", "q5": "6GB", "q8": "8GB"},
        recommended_quant=Quantization.Q4
    ),

    "llama3-70b": ModelProfile(
        name="llama3",
        full_name="Llama 3 70B",
        description="Large Llama 3, very high quality",
        size=ModelSize.XLARGE,
        params="70B",
        context_window=8192,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.ANALYSIS,
            AgentCapability.REFACTORING,
            AgentCapability.GENERAL,
            AgentCapability.SECURITY
        ],
        strengths=[
            "Excellent quality",
            "Strong reasoning",
            "Reliable",
            "Comprehensive"
        ],
        weaknesses=[
            "Very high VRAM",
            "Slow"
        ],
        best_for=[
            "Critical tasks",
            "High quality needed",
            "Complex reasoning",
            "Security review"
        ],
        quantizations=[Quantization.Q2, Quantization.Q4],
        speed_rating=2,
        quality_rating=9,
        vram_required={"q2": "24GB", "q4": "40GB"},
        recommended_quant=Quantization.Q2
    ),

    # === Specialized Models ===

    "sqlcoder-7b": ModelProfile(
        name="sqlcoder",
        full_name="SQLCoder 7B",
        description="Specialized for SQL generation and database queries",
        size=ModelSize.MEDIUM,
        params="7B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.ANALYSIS
        ],
        strengths=[
            "Excellent SQL knowledge",
            "Query optimization",
            "Schema understanding",
            "Fast"
        ],
        weaknesses=[
            "SQL only",
            "Not for general code"
        ],
        best_for=[
            "SQL generation",
            "Query optimization",
            "Database schema design",
            "SQL debugging"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=9,
        vram_required={"q4": "4GB", "q5": "5GB", "q8": "7GB"},
        recommended_quant=Quantization.Q4
    ),

    "magicoder-7b": ModelProfile(
        name="magicoder",
        full_name="Magicoder 7B",
        description="Code model trained on synthetic data, creative",
        size=ModelSize.MEDIUM,
        params="7B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.REFACTORING,
            AgentCapability.DEBUGGING
        ],
        strengths=[
            "Creative solutions",
            "Good at novel problems",
            "Fast",
            "Concise code"
        ],
        weaknesses=[
            "Can be unconventional",
            "Less tested patterns"
        ],
        best_for=[
            "Creative coding",
            "Novel problems",
            "Prototyping",
            "Algorithm design"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=7,
        vram_required={"q4": "4GB", "q5": "5GB", "q8": "7GB"},
        recommended_quant=Quantization.Q4
    ),

    "starcoder2-7b": ModelProfile(
        name="starcoder2",
        full_name="StarCoder2 7B",
        description="Latest StarCoder, trained on The Stack v2",
        size=ModelSize.MEDIUM,
        params="7B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING
        ],
        strengths=[
            "Trained on diverse code",
            "Good language coverage",
            "Fast",
            "Up-to-date patterns"
        ],
        weaknesses=[
            "Can be too literal",
            "Less creative"
        ],
        best_for=[
            "Multi-language projects",
            "Standard patterns",
            "Code completion",
            "Library usage"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=7,
        vram_required={"q4": "4GB", "q5": "5GB", "q8": "7GB"},
        recommended_quant=Quantization.Q4
    ),

    "starcoder2-15b": ModelProfile(
        name="starcoder2",
        full_name="StarCoder2 15B",
        description="Larger StarCoder2, better quality",
        size=ModelSize.MEDIUM,
        params="15B",
        context_window=16384,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.REFACTORING
        ],
        strengths=[
            "High quality code",
            "Comprehensive coverage",
            "Good reasoning",
            "Modern patterns"
        ],
        weaknesses=[
            "Slower than 7B",
            "More VRAM"
        ],
        best_for=[
            "Production code",
            "Complex projects",
            "Refactoring",
            "Architecture"
        ],
        quantizations=[Quantization.Q4, Quantization.Q5],
        speed_rating=6,
        quality_rating=8,
        vram_required={"q4": "8GB", "q5": "10GB"},
        recommended_quant=Quantization.Q4,
        supports_tool_calling=False,
        tool_calling_quality="none",
        task_tags=["code_generation", "refactoring", "code_review"],
    ),

    # === Tool-Capable Models (Phase 2) ===

    "qwen2.5:7b": ModelProfile(
        name="qwen2.5",
        full_name="Qwen 2.5 7B",
        description="Alibaba's latest, excellent tool calling and coding",
        size=ModelSize.MEDIUM,
        params="7B",
        context_window=32768,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.REFACTORING,
            AgentCapability.ANALYSIS,
            AgentCapability.GENERAL,
        ],
        strengths=["Native tool calling", "Fast", "Large context", "Strong reasoning"],
        weaknesses=["Smaller than 14B variant"],
        best_for=["Agent tasks", "Tool-assisted coding", "General analysis"],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=7,
        vram_required={"q4": "5GB", "q5": "6GB", "q8": "8GB"},
        recommended_quant=Quantization.Q4,
        supports_tool_calling=True,
        tool_calling_quality="good",
        task_tags=["code_review", "debugging", "refactoring", "testing", "documentation", "architecture"],
    ),

    "qwen2.5:14b": ModelProfile(
        name="qwen2.5",
        full_name="Qwen 2.5 14B",
        description="Best balance of quality and tool calling support",
        size=ModelSize.MEDIUM,
        params="14B",
        context_window=32768,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.REFACTORING,
            AgentCapability.TESTING,
            AgentCapability.DOCUMENTATION,
            AgentCapability.SECURITY,
            AgentCapability.ANALYSIS,
            AgentCapability.GENERAL,
        ],
        strengths=["Excellent tool calling", "Strong reasoning", "Large context", "Good code quality"],
        weaknesses=["Needs 8GB+ VRAM"],
        best_for=["Agent loop tasks", "Complex analysis", "Security review", "Architecture"],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=6,
        quality_rating=9,
        vram_required={"q4": "8GB", "q5": "10GB", "q8": "14GB"},
        recommended_quant=Quantization.Q4,
        supports_tool_calling=True,
        tool_calling_quality="excellent",
        task_tags=["code_review", "debugging", "refactoring", "testing", "security_audit", "documentation", "architecture"],
    ),

    "devstral:24b": ModelProfile(
        name="devstral",
        full_name="Devstral 24B",
        description="Mistral's coding model with tool calling support",
        size=ModelSize.LARGE,
        params="24B",
        context_window=32768,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.REFACTORING,
            AgentCapability.TESTING,
            AgentCapability.DOCUMENTATION,
            AgentCapability.ANALYSIS,
            AgentCapability.SECURITY,
        ],
        strengths=["Strong coding", "Native tool calling", "Large model quality", "Good architecture sense"],
        weaknesses=["High VRAM", "Slower inference"],
        best_for=["Complex coding", "Agent tasks", "Architecture review", "Security"],
        quantizations=[Quantization.Q4, Quantization.Q5],
        speed_rating=4,
        quality_rating=9,
        vram_required={"q4": "14GB", "q5": "18GB"},
        recommended_quant=Quantization.Q4,
        supports_tool_calling=True,
        tool_calling_quality="excellent",
        task_tags=["code_review", "debugging", "refactoring", "testing", "security_audit", "documentation", "architecture"],
    ),

    "llama3.1:8b": ModelProfile(
        name="llama3.1",
        full_name="Llama 3.1 8B",
        description="Meta's Llama 3.1 with native tool calling",
        size=ModelSize.MEDIUM,
        params="8B",
        context_window=131072,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.ANALYSIS,
            AgentCapability.GENERAL,
            AgentCapability.DOCUMENTATION,
        ],
        strengths=["Massive context window", "Tool calling", "Fast", "Versatile"],
        weaknesses=["Not code-specialized"],
        best_for=["Large context tasks", "General coding", "Documentation"],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=7,
        vram_required={"q4": "5GB", "q5": "6GB", "q8": "8GB"},
        recommended_quant=Quantization.Q4,
        supports_tool_calling=True,
        tool_calling_quality="good",
        task_tags=["documentation", "code_review", "debugging", "general"],
    ),

    "mistral-nemo:12b": ModelProfile(
        name="mistral-nemo",
        full_name="Mistral Nemo 12B",
        description="Mistral's compact model with excellent tool calling",
        size=ModelSize.MEDIUM,
        params="12B",
        context_window=128000,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.ANALYSIS,
            AgentCapability.GENERAL,
        ],
        strengths=["Strong tool calling", "Huge context", "Good reasoning", "Fast"],
        weaknesses=["Less specialized for code"],
        best_for=["Agent tasks", "Large context analysis", "General coding"],
        quantizations=[Quantization.Q4, Quantization.Q5],
        speed_rating=7,
        quality_rating=8,
        vram_required={"q4": "7GB", "q5": "9GB"},
        recommended_quant=Quantization.Q4,
        supports_tool_calling=True,
        tool_calling_quality="excellent",
        task_tags=["code_review", "debugging", "documentation", "architecture"],
    ),

    # === C-Suite Fine-Tuned Models ===

    "csuite-model:latest": ModelProfile(
        name="csuite-model",
        full_name="C-Suite Generalist (Llama 3.1 8B LoRA)",
        description="Fine-tuned model with 16-executive identity, personality coherence, and domain routing",
        size=ModelSize.MEDIUM,
        params="8B",
        context_window=4096,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.REFACTORING,
            AgentCapability.ANALYSIS,
            AgentCapability.GENERAL,
        ],
        strengths=["C-Suite executive personas", "Personality consistency", "Cross-domain routing", "Identity grounding"],
        weaknesses=["Smaller context than base models", "Domain depth limited vs specialists"],
        best_for=["C-Suite orchestration", "Executive decision support", "Multi-domain coordination"],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=7,
        vram_required={"q4": "5GB", "q5": "6GB", "q8": "8GB"},
        recommended_quant=Quantization.Q5,
        supports_tool_calling=True,
        tool_calling_quality="good",
        task_tags=["code_review", "debugging", "refactoring", "architecture", "documentation", "strategic_planning"],
    ),

    "csuite-technical:latest": ModelProfile(
        name="csuite-technical",
        full_name="C-Suite Technical Specialist (CTO/CEngO/CIO/CSecO)",
        description="Domain LoRA for code, architecture, security, and infrastructure tasks",
        size=ModelSize.MEDIUM,
        params="8B",
        context_window=4096,
        capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.REFACTORING,
            AgentCapability.SECURITY,
            AgentCapability.PERFORMANCE,
        ],
        strengths=["Deep technical reasoning", "Security-aware", "Architecture design", "Code quality focus"],
        weaknesses=["Limited business/operations context"],
        best_for=["Code review", "Security audit", "Architecture design", "Technical debugging"],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=8,
        vram_required={"q4": "5GB", "q5": "6GB", "q8": "8GB"},
        recommended_quant=Quantization.Q5,
        supports_tool_calling=True,
        tool_calling_quality="good",
        task_tags=["code_review", "debugging", "refactoring", "security_audit", "architecture", "testing", "security_operations"],
    ),

    "csuite-business:latest": ModelProfile(
        name="csuite-business",
        full_name="C-Suite Business Specialist (CFO/CRevO/CSO/CPO)",
        description="Domain LoRA for finance, revenue, strategy, and product tasks",
        size=ModelSize.MEDIUM,
        params="8B",
        context_window=4096,
        capabilities=[
            AgentCapability.ANALYSIS,
            AgentCapability.GENERAL,
            AgentCapability.DOCUMENTATION,
        ],
        strengths=["Financial analysis", "Revenue modeling", "Strategic planning", "Product roadmap"],
        weaknesses=["Limited code generation ability"],
        best_for=["Cost analysis", "Revenue forecasting", "Strategic planning", "Product prioritization"],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=7,
        vram_required={"q4": "5GB", "q5": "6GB", "q8": "8GB"},
        recommended_quant=Quantization.Q5,
        supports_tool_calling=False,
        tool_calling_quality="none",
        task_tags=["cost_analysis", "revenue_analysis", "strategic_planning", "product_planning", "research_intelligence"],
    ),

    "csuite-operations:latest": ModelProfile(
        name="csuite-operations",
        full_name="C-Suite Operations Specialist (CoS/COO/CDO/CRO)",
        description="Domain LoRA for coordination, data governance, research, and operations",
        size=ModelSize.MEDIUM,
        params="8B",
        context_window=4096,
        capabilities=[
            AgentCapability.ANALYSIS,
            AgentCapability.GENERAL,
            AgentCapability.DOCUMENTATION,
        ],
        strengths=["Task coordination", "Data governance", "Research synthesis", "Operational planning"],
        weaknesses=["Limited deep technical or financial reasoning"],
        best_for=["Task routing", "Data governance", "Research coordination", "Operational planning"],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=7,
        vram_required={"q4": "5GB", "q5": "6GB", "q8": "8GB"},
        recommended_quant=Quantization.Q5,
        supports_tool_calling=False,
        tool_calling_quality="none",
        task_tags=["task_routing", "data_governance", "research", "operational_planning", "data_harvesting"],
    ),

    "csuite-governance:latest": ModelProfile(
        name="csuite-governance",
        full_name="C-Suite Governance Specialist (CComO/CRiO/CCO/CMO)",
        description="Domain LoRA for compliance, risk, customer success, and marketing",
        size=ModelSize.MEDIUM,
        params="8B",
        context_window=4096,
        capabilities=[
            AgentCapability.ANALYSIS,
            AgentCapability.GENERAL,
            AgentCapability.DOCUMENTATION,
        ],
        strengths=["Compliance assessment", "Risk analysis", "Customer strategy", "Marketing planning"],
        weaknesses=["Limited code or technical reasoning"],
        best_for=["Compliance review", "Risk assessment", "Customer success", "Marketing strategy"],
        quantizations=[Quantization.Q4, Quantization.Q5, Quantization.Q8],
        speed_rating=8,
        quality_rating=7,
        vram_required={"q4": "5GB", "q5": "6GB", "q8": "8GB"},
        recommended_quant=Quantization.Q5,
        supports_tool_calling=False,
        tool_calling_quality="none",
        task_tags=["compliance", "risk_assessment", "customer_success", "marketing", "security_operations"],
    ),
}


def get_model_profile(model_name: str) -> Optional[ModelProfile]:
    """Get profile for a model"""
    # Extract base model name (handle tags like :7b, :13b, :q4, etc.)
    base_name = model_name.split(":")[0]

    # Try exact match first
    if model_name in OLLAMA_MODELS:
        return OLLAMA_MODELS[model_name]

    # Try base name
    if base_name in OLLAMA_MODELS:
        return OLLAMA_MODELS[base_name]

    # Try finding by size in name
    for key, profile in OLLAMA_MODELS.items():
        if base_name in key:
            return profile

    return None


def find_models_by_capability(capability: AgentCapability) -> List[ModelProfile]:
    """Find all models with a specific capability"""
    return [
        profile for profile in OLLAMA_MODELS.values()
        if capability in profile.capabilities
    ]


def find_models_by_size(size: ModelSize) -> List[ModelProfile]:
    """Find all models of a specific size"""
    return [
        profile for profile in OLLAMA_MODELS.values()
        if profile.size == size
    ]


def recommend_model_for_task(
    task_description: str,
    max_vram_gb: int = 8,
    prefer_speed: bool = False,
    prefer_quality: bool = False
) -> List[ModelProfile]:
    """
    Recommend models for a task based on description and constraints.

    Returns list of recommended models, sorted by suitability.
    """
    task_lower = task_description.lower()
    recommendations = []

    # Detect task type
    is_sql = any(word in task_lower for word in ["sql", "query", "database"])
    is_python = "python" in task_lower
    is_debugging = any(word in task_lower for word in ["debug", "bug", "fix", "error"])
    is_complex = any(word in task_lower for word in [
        "complex", "architecture", "refactor", "design", "large"
    ])
    is_simple = any(word in task_lower for word in [
        "simple", "quick", "small", "typo", "format"
    ])

    # Filter by VRAM
    for profile in OLLAMA_MODELS.values():
        vram = profile.vram_required.get(profile.recommended_quant.value, "999GB")
        vram_num = int(vram.replace("GB", ""))

        if vram_num > max_vram_gb:
            continue

        score = 0

        # Task-specific scoring
        if is_sql and "sql" in profile.name:
            score += 50
        if is_python and "python" in profile.name:
            score += 30
        if is_debugging and "phind" in profile.name:
            score += 20
        if is_debugging and AgentCapability.DEBUGGING in profile.capabilities:
            score += 10

        # Complexity scoring
        if is_complex:
            score += profile.quality_rating * 5
            score += (profile.size.value == ModelSize.LARGE.value) * 20
        if is_simple:
            score += profile.speed_rating * 3
            score += (profile.size.value == ModelSize.SMALL.value) * 15

        # Preference scoring
        if prefer_speed:
            score += profile.speed_rating * 5
        if prefer_quality:
            score += profile.quality_rating * 5

        # General capability scoring
        score += len(profile.capabilities) * 2

        recommendations.append((score, profile))

    # Sort by score
    recommendations.sort(key=lambda x: x[0], reverse=True)

    return [profile for score, profile in recommendations[:5]]


def find_tool_capable_models(min_quality: str = "basic") -> List[ModelProfile]:
    """Find models that support tool calling at or above the given quality."""
    quality_order = {"none": 0, "basic": 1, "good": 2, "excellent": 3}
    min_level = quality_order.get(min_quality, 0)
    return [
        p for p in OLLAMA_MODELS.values()
        if p.supports_tool_calling
        and quality_order.get(p.tool_calling_quality, 0) >= min_level
    ]


def find_models_by_task_tag(tag: str) -> List[ModelProfile]:
    """Find models tagged for a specific task type."""
    return [
        p for p in OLLAMA_MODELS.values()
        if tag in (p.task_tags or [])
    ]


def get_all_model_names() -> List[str]:
    """Get list of all available model names"""
    return list(OLLAMA_MODELS.keys())


def print_model_catalog():
    """Print formatted model catalog"""
    # CLI output - interactive terminal display for catalog browsing
    print("\n" + "=" * 80)
    print("OLLAMA MODEL CATALOG")
    print("=" * 80)

    categories = {
        "Code-Specialized Models": [
            "deepseek-coder-1.3b", "deepseek-coder-6.7b", "deepseek-coder-33b",
            "codellama-7b", "codellama-13b", "codellama-34b",
            "phind-codellama-34b", "wizardcoder-7b", "wizardcoder-13b",
            "wizardcoder-python-7b", "codebooga-34b"
        ],
        "General Purpose": [
            "mistral-7b", "mixtral-8x7b", "llama3-8b", "llama3-70b"
        ],
        "Specialized": [
            "sqlcoder-7b", "magicoder-7b", "starcoder2-7b", "starcoder2-15b"
        ],
        "C-Suite Fine-Tuned": [
            "csuite-model:latest", "csuite-technical:latest",
            "csuite-business:latest", "csuite-operations:latest",
            "csuite-governance:latest"
        ],
    }

    for category, models in categories.items():
        print(f"\n{category}:")
        print("-" * 80)

        for model_key in models:
            if model_key in OLLAMA_MODELS:
                profile = OLLAMA_MODELS[model_key]
                vram = profile.vram_required.get(profile.recommended_quant.value, "?")

                print(f"\n  {profile.full_name} ({profile.params})")
                print(f"  {profile.description}")
                print(f"  Speed: {'⚡' * profile.speed_rating}/10  "
                      f"Quality: {'⭐' * profile.quality_rating}/10  "
                      f"VRAM: {vram}")
                print(f"  Best for: {', '.join(profile.best_for[:3])}")
