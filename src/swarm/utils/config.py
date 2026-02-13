"""Configuration management for Claude Swarm."""

import yaml
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings


class BackendType(str, Enum):
    """Available execution backends."""
    CLAUDE = "claude"
    OLLAMA = "ollama"


class BackendEndpoint(BaseModel):
    """A single backend endpoint (Ollama instance, Claude API, etc.)."""
    name: str = Field(..., description="Unique name for this backend")
    type: BackendType = Field(default=BackendType.OLLAMA, description="Backend type")
    url: str = Field(default="http://localhost:11434", description="Backend URL")
    models: list[str] = Field(default_factory=list, description="Models available on this backend")
    api_key: Optional[str] = Field(default=None, description="API key (for Claude/OpenAI)")
    max_concurrent: int = Field(default=1, description="Max concurrent requests")
    priority: int = Field(default=0, description="Higher = preferred when equal scores")
    enabled: bool = Field(default=True, description="Whether this backend is active")


class ModelsConfig(BaseModel):
    """Model selection preferences."""
    preferred: list[str] = Field(default=["qwen2.5:14b", "devstral:24b"], description="Preferred models in priority order")
    fallback: str = Field(default="qwen2.5:7b", description="Fallback model if preferred unavailable")
    auto_select: bool = Field(default=True, description="Let router pick best model per task")


class SwarmConfig(BaseModel):
    """Swarm orchestrator configuration."""
    max_instances: int = Field(default=10, description="Maximum concurrent instances")
    default_timeout: int = Field(default=300, description="Default task timeout in seconds")
    workspace_root: str = Field(default=".", description="Root workspace directory")
    backend: BackendType = Field(default=BackendType.CLAUDE, description="Execution backend: claude or ollama")
    claude_command: str = Field(default="claude", description="Claude Code CLI command")
    ollama_url: str = Field(default="http://localhost:11434", description="Ollama API URL")
    ollama_model: str = Field(default="devstral:24b", description="Ollama model to use")
    models: ModelsConfig = Field(default_factory=ModelsConfig, description="Model selection preferences")
    backends: list[BackendEndpoint] = Field(default_factory=list, description="Multiple backend endpoints")

    @model_validator(mode="after")
    def _ensure_backends(self):
        """If no backends listed, synthesize one from the legacy single-backend fields."""
        if not self.backends and self.backend == BackendType.OLLAMA:
            self.backends = [
                BackendEndpoint(
                    name="local",
                    type=BackendType.OLLAMA,
                    url=self.ollama_url,
                    models=[self.ollama_model],
                    max_concurrent=1,
                    priority=0,
                )
            ]
        elif not self.backends and self.backend == BackendType.CLAUDE:
            self.backends = [
                BackendEndpoint(
                    name="claude",
                    type=BackendType.CLAUDE,
                    url="",
                    models=["claude"],
                    max_concurrent=2,
                    priority=0,
                )
            ]
        return self


class APIConfig(BaseModel):
    """API server configuration."""
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8765, description="API port")
    enable_websocket: bool = Field(default=True, description="Enable WebSocket support")
    cors_origins: list[str] = Field(default=["*"], description="CORS allowed origins")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level")
    file: Optional[str] = Field(default=None, description="Log file path")
    json_logs: bool = Field(default=False, description="Use JSON format for logs")


class Config(BaseSettings):
    """Main configuration model."""
    swarm: SwarmConfig = Field(default_factory=SwarmConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


def load_config(config_path: Optional[Path] = None) -> "Config":
    """Load configuration from YAML file."""
    if config_path and config_path.exists():
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
            return Config(**config_data)
    return Config()


def save_config(config: "Config", config_path: Path) -> None:
    """Save configuration to YAML file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False)
