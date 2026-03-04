"""
Modular LLM client with provider abstraction.
Default provider: Ollama (local). Future: OpenAI, Anthropic.

All agent reasoning, summarization, and generation MUST call this module
rather than communicating with Ollama or any LLM directly.
"""
import httpx
import time
from abc import ABC, abstractmethod
from config import OLLAMA_BASE_URL, MODEL_NAME, REQUEST_TIMEOUT, FALLBACK_MODELS


class LLMClient(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Send a prompt and return the generated text."""
        ...

    @abstractmethod
    def check_health(self) -> bool:
        """Check if the LLM service is available."""
        ...


class OllamaClient(LLMClient):
    """Client for local Ollama server."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = MODEL_NAME):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._healthy: bool | None = None

    def check_health(self) -> bool:
        """Ping Ollama's /api/tags endpoint to verify it's running."""
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=10)
            self._healthy = r.status_code == 200
            return self._healthy
        except (httpx.ConnectError, httpx.TimeoutException):
            self._healthy = False
            return False

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Send a prompt to Ollama's /api/generate endpoint.
        Streaming is disabled (stream: false) — returns full response at once.
        """
        if not self.check_health():
            raise ConnectionError(
                "Ollama server is not running. "
                "Please start Ollama before using the assistant.\n"
                f"Expected at: {self.base_url}"
            )

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
        }

        start = time.time()
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        elapsed = time.time() - start

        result = response.json()
        generated_text = result.get("response", "")

        # Log latency for diagnostics (will be picked up by logging_config)
        from logging_config.logger import llm_logger
        llm_logger.info(
            f"model={self.model} | latency={elapsed:.2f}s | "
            f"prompt_len={len(full_prompt)} | response_len={len(generated_text)}"
        )

        return generated_text


class OpenAICompatibleClient(LLMClient):
    """
    Client for OpenAI-compatible APIs (OpenAI, Anthropic via proxy, etc.).
    Placeholder — will be implemented when needed.
    """

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def check_health(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/models", timeout=10,
                          headers={"Authorization": f"Bearer {self.api_key}"})
            return r.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            json={"model": self.model, "messages": messages, "stream": False},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


# ── Factory ───────────────────────────────────────────────────────────────────

_client_instance: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Return a singleton LLM client based on config."""
    global _client_instance
    if _client_instance is not None:
        return _client_instance

    from config import MODEL_PROVIDER
    import os

    if MODEL_PROVIDER == "ollama":
        _client_instance = OllamaClient()
    elif MODEL_PROVIDER == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        _client_instance = OpenAICompatibleClient(api_key, base_url, model)
    else:
        raise ValueError(f"Unknown MODEL_PROVIDER: {MODEL_PROVIDER}")

    return _client_instance
