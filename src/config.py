from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import dotenv
import yaml
from pydantic import BaseModel, ConfigDict

# Module-level singleton cache
_config: Optional[AppConfig] = None


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    data_dir: str = "./data"
    log_level: str = "INFO"


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    api_key: str
    api_base: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    models: Dict[str, ModelConfig]


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    max_tokens: int = 4096


class DebaterAgentConfig(AgentConfig):
    model_config = ConfigDict(extra="forbid")

    model: str = ""
    npc_model: str
    host_model: str
    max_rounds: int = 5
    npc_concurrent: bool = True


class SummarizerAgentConfig(AgentConfig):
    model_config = ConfigDict(extra="forbid")

    model: str
    max_tokens: int = 2048


class AgentsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    world_builder: AgentConfig
    plot_designer: AgentConfig
    writer: AgentConfig
    consistency_checker: AgentConfig
    style_polisher: AgentConfig
    emotion_risk_control: AgentConfig
    sandbox_debater: DebaterAgentConfig
    summarizer: SummarizerAgentConfig


class RAGConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    embedding_model: str
    vector_db_path: str
    chunk_size: int = 800
    chunk_overlap: int = 150
    top_k: int = 5


class MemoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    short_term_window: int = 3
    summary_max_tokens: int = 500


class WorkflowConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    auto_mode: bool = False
    review_points: List[str]
    # Automation-specific configs
    write_range_defaults: Dict[str, Any] = {}
    fallback_retry_policy: Dict[str, Any] = {}
    role_model_chains: Dict[str, List[str]] = {}
    trace_logging: Dict[str, Any] = {}


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: ProjectConfig
    llm: LLMConfig
    agents: AgentsConfig
    rag: RAGConfig
    memory: MemoryConfig
    workflow: WorkflowConfig


def _resolve_env_vars(data: Any) -> Any:
    """Recursively resolve ${ENV_VAR} patterns in dict/list structures."""
    if isinstance(data, dict):
        return {k: _resolve_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_env_vars(item) for item in data]
    elif isinstance(data, str):
        pattern = r"\$\{(\w+)\}"
        matches = re.findall(pattern, data)
        for var_name in matches:
            env_value = os.environ.get(var_name, "")
            data = data.replace(f"${{{var_name}}}", env_value)
        return data
    return data


def load_config(path: Union[str, Path] = "config/settings.yaml") -> AppConfig:
    """Load and validate configuration from YAML file with env var resolution."""
    global _config

    # Load .env file first
    dotenv.load_dotenv()

    # Read YAML file
    yaml_path = Path(path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)

    # Resolve environment variables
    resolved_data = _resolve_env_vars(raw_data)

    # Validate and create config instance
    _config = AppConfig(**resolved_data)

    return _config


def get_config() -> AppConfig:
    """Return cached config instance, raise error if not loaded."""
    if _config is None:
        raise RuntimeError(
            "Config not loaded. Call load_config() first or provide config path."
        )
    return _config
