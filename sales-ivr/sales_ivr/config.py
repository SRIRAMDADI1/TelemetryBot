from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from sales_ivr.models.enums import ProductLine


class CarrierConfig(BaseModel):
    id: str
    name: str
    supported_states: list[str]


class RuntimeConfig(BaseModel):
    max_objection_loops: int = 2
    max_verification_attempts: int = 2
    after_hours_start: str = "18:00"
    after_hours_end: str = "08:00"
    max_agent_tool_rounds: int = 4


class LLMConfig(BaseModel):
    """Azure OpenAI (or mock for offline tests)."""

    provider: str = "azure"  # azure | mock
    api_key_env: str = "AZURE_OPENAI_API_KEY"
    endpoint_env: str = "AZURE_OPENAI_ENDPOINT"
    api_version: str = "2024-10-21"
    # Deployment name in Azure (not the model family name)
    deployment: str = "gpt-4o-mini"
    # Optional stronger model for quote/handoff
    deployment_capable: str | None = None
    temperature: float = 0.2
    max_tokens: int = 1200


class PathsConfig(BaseModel):
    catalog_dir: str
    compliance_dir: str
    objections_dir: str
    fixtures_dir: str
    mock_crm_path: str


class AppConfig(BaseModel):
    carrier: CarrierConfig
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    paths: PathsConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SALES_IVR_", extra="ignore")

    config_path: Path = Path("config.yaml")


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or Settings().config_path
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config not found at {config_path}. Copy config.example.yaml to config.yaml."
        )
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(raw)


def resolve_path(config: AppConfig, relative: str, base: Path | None = None) -> Path:
    """Resolve a config path relative to the sales-ivr project root."""

    root = base or Path(__file__).resolve().parent.parent
    candidate = Path(relative)
    if candidate.is_absolute():
        return candidate
    return (root / candidate).resolve()


class ProductTier(BaseModel):
    tier_id: str
    name: str
    base_premium_monthly: float
    coverage_limit: str


class InsuranceProduct(BaseModel):
    product_id: str
    product_line: ProductLine
    name: str
    description: str
    eligible_states: list[str]
    min_age: int = 18
    tiers: list[ProductTier]
    required_factors: list[str]
