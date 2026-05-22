"""Model configuration manager for pawbench - supporting multiple providers like Harbor."""

import os
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ProviderType(Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    AZURE = "azure"
    DASHSCOPE = "dashscope"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    provider: ProviderType
    model_name: str
    api_key: str
    base_url: str
    api_version: Optional[str] = None  # For Azure
    extra_config: Optional[Dict[str, Any]] = None

    # Vision capability fields.
    # ``supports_vision`` is True when the model itself accepts image input
    # (i.e. it is a vision-language model like qwen-vl-max or gpt-4o).
    # ``vision_model`` is the companion VL model name (bare, no provider prefix)
    # that should be used for image-tool calls when the primary model is
    # text-only.  Both fields are populated by ModelConfigManager based on the
    # known-models registry below; they are left as defaults for unknown models.
    supports_vision: bool = False
    vision_model: Optional[str] = None

    def get_full_model_identifier(self) -> str:
        """Get the full model identifier in provider/model format."""
        return f"{self.provider.value}/{self.model_name}"

    # Treat this URL as "no explicit base_url" when the provider is not OpenAI.
    # AgentFactory always fills in this default when the caller omits --base-url,
    # so checking equality lets resolve_with() fall back to the provider-specific URL.
    _OPENAI_DEFAULT_URL: str = "https://api.openai.com/v1"

    def resolve_with(self, agent_config: Dict[str, Any]) -> "ResolvedModelConfig":
        """Return a ResolvedModelConfig applying agent_config overrides.

        Priority for api_key : agent_config["api_key"] > self.api_key (from env)
        Priority for base_url: agent_config["base_url"] > self.base_url (provider default)

        The generic OpenAI fallback URL is treated as "not explicit" for non-OpenAI
        providers, so DashScope / Anthropic / Google models fall back to their
        provider-specific endpoint even when AgentFactory injects the default.
        """
        api_key: str = agent_config.get("api_key") or self.api_key or ""

        config_url: str = agent_config.get("base_url") or ""
        explicit_base_url = bool(config_url) and not (
            config_url.rstrip("/") == self._OPENAI_DEFAULT_URL.rstrip("/")
            and self.provider != ProviderType.OPENAI
        )
        base_url = config_url if explicit_base_url else self.base_url

        return ResolvedModelConfig(
            model_config=self,
            api_key=api_key,
            base_url=base_url,
            explicit_base_url=explicit_base_url,
            supports_vision=self.supports_vision,
            vision_model=self.vision_model,
        )


@dataclass
class ResolvedModelConfig:
    """Result of ModelConfig.resolve_with(): api_key / base_url after agent overrides."""
    model_config: ModelConfig
    api_key: str
    base_url: str
    explicit_base_url: bool      # True only when caller explicitly provided a non-default URL
    supports_vision: bool        # mirrors model_config.supports_vision for convenience
    vision_model: Optional[str]  # mirrors model_config.vision_model for convenience


class ModelConfigManager:
    """Manages model configurations for different providers."""

    # ── vision capability registry ─────────────────────────────────────────
    # Model names (bare, no provider prefix) that support image input natively.
    # Used to set ModelConfig.supports_vision = True.
    _VISION_CAPABLE_MODELS: frozenset = frozenset({
        # OpenAI
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4-vision-preview",
        "gpt-5.4", "gpt-5.4-mini", "gpt-5.5", "gpt-5.5-medium",
        # Anthropic (Claude 3+ all support vision)
        "claude-3-opus-20240229", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307",
        "claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5",
        # Google (Gemini 1.5+ all support vision)
        "gemini-1.5-pro", "gemini-1.5-flash",
        "gemini-3.1-pro-preview", "gemini-3.0-flash",
        # DashScope — explicit VL models only; qwen3.x-plus are text-only
        "qwen-vl-max", "qwen-vl-max-latest", "qwen-vl-plus",
        "qwen2-vl-72b-instruct", "qwen2-vl-7b-instruct", "qwen2-vl-2b-instruct",
        "qvq-72b-preview",
    })

    # For text-only models: the recommended VL companion on the same provider.
    # Key = bare model name; value = bare VL model name (same provider assumed).
    # If a model is NOT in this dict and NOT in _VISION_CAPABLE_MODELS, no
    # vision companion is configured (agent must handle vision itself or skip).
    _VISION_COMPANION: Dict[str, str] = {
        # DashScope text-only models → qwen-vl-max (same key, same endpoint)
        "qwen3.6-plus":  "qwen-vl-max",
        "qwen3.5-plus":  "qwen-vl-max",
        "qwen3-max":     "qwen-vl-max",
        "qwen3-plus":    "qwen-vl-max",
        "qwen3-turbo":   "qwen-vl-max",
        # OpenAI text-only / legacy models → gpt-4o
        "gpt-3.5-turbo": "gpt-4o",
        "gpt-4":         "gpt-4o",
    }

    PROVIDER_DEFAULT_URLS = {
        ProviderType.ANTHROPIC: "https://api.anthropic.com",
        ProviderType.OPENAI: "https://api.openai.com/v1",
        ProviderType.GOOGLE: "https://generativelanguage.googleapis.com",
        ProviderType.AZURE: "",  # Azure needs specific endpoint
        # DashScope OpenAI-compatible endpoint; override with DASHSCOPE_BASE_URL for
        # the China mainland endpoint (https://dashscope.aliyuncs.com/compatible-mode/v1)
        ProviderType.DASHSCOPE: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        ProviderType.CUSTOM: "https://api.openai.com/v1",  # Default to OpenAI-compatible
    }

    @classmethod
    def parse_model_identifier(cls, model_identifier: str) -> ModelConfig:
        """Parse a model identifier in the format 'provider/model' or just 'model'.

        Args:
            model_identifier: String like 'anthropic/claude-3-5-sonnet' or 'gpt-4o'

        Returns:
            ModelConfig with appropriate provider and settings
        """
        aliases = cls.get_available_models()
        if model_identifier.strip() in aliases:
            model_identifier = aliases[model_identifier.strip()]

        if '/' in model_identifier:
            provider_str, model_name = model_identifier.split('/', 1)
            try:
                provider = ProviderType(provider_str.lower())
            except ValueError:
                # Unknown provider, treat as custom
                provider = ProviderType.CUSTOM
        else:
            # No provider specified, assume OpenAI
            provider = ProviderType.OPENAI
            model_name = model_identifier

        # Get API key from environment or config
        api_key = cls._get_api_key_for_provider(provider)

        # Get base URL
        base_url = cls._get_base_url_for_provider(provider, model_identifier)

        # Special handling for Azure (needs API version)
        api_version = None
        if provider == ProviderType.AZURE:
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

        supports_vision = model_name in cls._VISION_CAPABLE_MODELS
        vision_model = (
            None if supports_vision
            else cls._VISION_COMPANION.get(model_name)
        )

        return ModelConfig(
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            supports_vision=supports_vision,
            vision_model=vision_model,
        )

    @classmethod
    def _get_api_key_for_provider(cls, provider: ProviderType) -> str:
        """Get the appropriate API key from environment variables for the provider."""
        env_var_map = {
            ProviderType.ANTHROPIC: "ANTHROPIC_API_KEY",
            ProviderType.OPENAI: "OPENAI_API_KEY",
            ProviderType.GOOGLE: "GOOGLE_API_KEY",
            ProviderType.AZURE: "AZURE_OPENAI_API_KEY",
            ProviderType.DASHSCOPE: "DASHSCOPE_API_KEY",
            ProviderType.CUSTOM: "OPENAI_API_KEY",  # Default to OpenAI key
        }

        env_var = env_var_map[provider]
        api_key = os.getenv(env_var)

        if not api_key:
            # Fallback to a common variable if specific one isn't set
            if provider == ProviderType.ANTHROPIC:
                api_key = os.getenv("OPENAI_API_KEY", "")
            elif provider == ProviderType.GOOGLE:
                api_key = os.getenv("GOOGLE_GEMINI_API_KEY", os.getenv("GOOGLE_AI_STUDIO_API_KEY", ""))
            elif provider == ProviderType.DASHSCOPE:
                api_key = os.getenv("ALIYUN_API_KEY", "")
            elif provider == ProviderType.CUSTOM:
                api_key = os.getenv("OPENAI_API_KEY", os.getenv("CUSTOM_API_KEY", ""))

        return api_key or os.getenv("OPENAI_API_KEY", "")  # Final fallback

    @classmethod
    def _get_base_url_for_provider(cls, provider: ProviderType, full_identifier: str) -> str:
        """Get the appropriate base URL for the provider."""
        if provider == ProviderType.CUSTOM:
            if full_identifier.startswith(('http://', 'https://')):
                return full_identifier
            custom_base_url = os.getenv("CUSTOM_BASE_URL")
            if custom_base_url:
                return custom_base_url

        if provider == ProviderType.DASHSCOPE:
            # Allow override for China mainland or other regions
            dashscope_base_url = os.getenv("DASHSCOPE_BASE_URL")
            if dashscope_base_url:
                return dashscope_base_url

        # Check if it's an Azure deployment (format: azure/deployment-name@resource-name)
        if provider == ProviderType.AZURE and '@' in full_identifier:
            deployment_name, resource_name = full_identifier.split('@', 1)
            # Extract deployment name from provider/model format
            parts = deployment_name.split('/')
            if len(parts) > 1:
                deployment = parts[1]
                resource = resource_name
                return f"https://{resource}.openai.azure.com"

        return cls.PROVIDER_DEFAULT_URLS.get(provider, "https://api.openai.com/v1")

    @classmethod
    def validate_model_config(cls, config: ModelConfig) -> bool:
        """Validate that the model configuration is complete and valid."""
        if not config.api_key:
            print(f"Warning: No API key found for {config.provider.value} provider")
            return False

        if not config.base_url:
            print(f"Warning: No base URL found for {config.provider.value} provider")
            return False

        # For Azure, also need API version
        if config.provider == ProviderType.AZURE and not config.api_version:
            print("Warning: No API version found for Azure provider")
            return False

        return True

    @classmethod
    def get_available_models(cls) -> Dict[str, str]:
        """Get a mapping of common model names to their provider-specific names."""
        return {
            # Anthropic — current generation (see https://docs.anthropic.com/en/docs/about-claude/models)
            "claude-sonnet": "anthropic/claude-sonnet-4-6",
            "claude-opus": "anthropic/claude-opus-4-7",
            "claude-haiku": "anthropic/claude-haiku-4-5",
            # Anthropic — Claude 3.x (pinned snapshots)
            "claude-3-5-sonnet": "anthropic/claude-3-5-sonnet-20241022",
            "claude-3-opus": "anthropic/claude-3-opus-20240229",
            "claude-3-haiku": "anthropic/claude-3-haiku-20240307",

            # OpenAI — frontier (see https://platform.openai.com/docs/models)
            "gpt-5.4": "openai/gpt-5.4",
            "gpt-5.4-mini": "openai/gpt-5.4-mini",
            "gpt-5.4-nano": "openai/gpt-5.4-nano",
            # OpenAI — prior generations (still common in benchmarks)
            "gpt-4o": "openai/gpt-4o-2024-08-06",
            "gpt-4o-mini": "openai/gpt-4o-mini",
            "gpt-4-turbo": "openai/gpt-4-turbo",
            "gpt-4": "openai/gpt-4",
            "gpt-3.5-turbo": "openai/gpt-3.5-turbo",

            # Google — Gemini (see https://ai.google.dev/gemini-api/docs/models)
            "gemini-pro": "google/gemini-3.1-pro-preview",
            "gemini-3.1-pro": "google/gemini-3.1-pro-preview",
            "gemini-1.5-pro": "google/gemini-1.5-pro",
            "gemini-1.5-flash": "google/gemini-1.5-flash",

            # DashScope / Qwen (see https://www.alibabacloud.com/help/en/model-studio)
            # Latest: qwen3.6-plus (April 2026)
            "qwen": "dashscope/qwen3.6-plus",
            "qwen3.6-plus": "dashscope/qwen3.6-plus",
            "qwen3.5-plus": "dashscope/qwen3.5-plus",
            "qwen3-max": "dashscope/qwen3-max",
            "qwen3-plus": "dashscope/qwen3-plus",
            "qwen3-turbo": "dashscope/qwen3-turbo",
        }


def get_model_config(model_identifier: str) -> ModelConfig:
    """Convenience function to get model configuration from identifier."""
    return ModelConfigManager.parse_model_identifier(model_identifier)


def get_available_providers() -> Dict[str, str]:
    """Get human-readable list of available providers."""
    return {
        "Anthropic": "anthropic/claude-sonnet-4-6",
        "OpenAI": "openai/gpt-5.4",
        "Google": "google/gemini-3.1-pro-preview",
        "DashScope (Qwen)": "dashscope/qwen3.6-plus",
        "Custom (OpenAI-compatible)": "custom/my-model-name",
        "Azure OpenAI": "azure/deployment-name@resource-name",
    }
