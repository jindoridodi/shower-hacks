from __future__ import annotations

from typing import Any

import httpx

from apps.api.config import Settings
from apps.api.services.text_model import TextModelError


class OpenAICompatibleTextModel:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        if not settings.llm_configured:
            raise TextModelError("LLM_API_KEY and LLM_MODEL must be configured.")

        self.model = settings.llm_model
        self._client = client or httpx.Client(timeout=settings.llm_timeout_seconds)
        self._owns_client = client is None
        self._url = f"{settings.llm_base_url}/chat/completions"
        self._headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str) -> str:
        try:
            response = self._client.post(
                self._url,
                headers=self._headers,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise TextModelError(f"LLM request failed with status {error.response.status_code}.") from error
        except httpx.HTTPError as error:
            raise TextModelError("LLM request could not be completed.") from error

        try:
            payload: dict[str, Any] = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise TextModelError("LLM response did not contain message content.") from error

        if not isinstance(content, str):
            raise TextModelError("LLM response content must be text.")
        return content

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
