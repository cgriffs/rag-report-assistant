"""Application settings, read from environment variables.

The app runs fully offline in demo mode when no Azure OpenAI settings are
present. See the README for the full configuration table.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Azure OpenAI is optional. When endpoint, key and deployments are set,
    # answer generation uses the chat model and retrieval can use the
    # embedding deployment. When they are absent, the app uses the local
    # TF-IDF retriever and extractive answer composition.
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_chat_deployment: str | None = None
    azure_openai_embedding_deployment: str | None = None
    azure_openai_api_version: str = "2024-10-21"

    chunk_size: int = 900
    chunk_overlap: int = 150
    default_top_k: int = 4

    @property
    def llm_enabled(self) -> bool:
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_chat_deployment
        )


def load_settings() -> Settings:
    return Settings(
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT") or None,
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY") or None,
        azure_openai_chat_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or None,
        azure_openai_embedding_deployment=os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        )
        or None,
        azure_openai_api_version=os.getenv(
            "AZURE_OPENAI_API_VERSION", "2024-10-21"
        ),
    )
