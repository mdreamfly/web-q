"""
Compression module using LLM API to summarize large text responses.
Supports multiple providers: OpenAI, OpenRouter, or any OpenAI-compatible API.
"""

import os
from openai import AsyncOpenAI

# LLM Provider configuration
# Supported values: "openai", "openrouter", "custom"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")

# Provider-specific settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-001")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Custom provider (any OpenAI-compatible API, e.g. local Ollama, vLLM, etc.)
CUSTOM_API_KEY = os.getenv("CUSTOM_API_KEY", "")
CUSTOM_MODEL = os.getenv("CUSTOM_MODEL", "")
CUSTOM_BASE_URL = os.getenv("CUSTOM_BASE_URL", "")

COMPRESSION_PROMPT = os.getenv(
    "COMPRESSION_PROMPT",
    "Process the following content according to the user's instruction. Preserve key facts, names, numbers, and actionable information. Output only the result, no preamble."
)

# Provider configurations
PROVIDER_CONFIGS = {
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "get_api_key": lambda: OPENAI_API_KEY,
        "get_base_url": lambda: OPENAI_BASE_URL,
        "get_model": lambda: OPENAI_MODEL,
    },
    "openrouter": {
        "api_key_env": "OPENROUTER_API_KEY",
        "get_api_key": lambda: OPENROUTER_API_KEY,
        "get_base_url": lambda: OPENROUTER_BASE_URL,
        "get_model": lambda: OPENROUTER_MODEL,
    },
    "custom": {
        "api_key_env": "CUSTOM_API_KEY",
        "get_api_key": lambda: CUSTOM_API_KEY,
        "get_base_url": lambda: CUSTOM_BASE_URL,
        "get_model": lambda: CUSTOM_MODEL,
    },
}


def get_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client based on the configured LLM provider."""
    provider = LLM_PROVIDER.lower()

    if provider not in PROVIDER_CONFIGS:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: '{provider}'. "
            f"Supported providers: {', '.join(PROVIDER_CONFIGS.keys())}"
        )

    config = PROVIDER_CONFIGS[provider]
    api_key = config["get_api_key"]()
    base_url = config["get_base_url"]()

    if not api_key:
        raise ValueError(
            f"{config['api_key_env']} environment variable not set. "
            f"Required for LLM_PROVIDER='{provider}'"
        )

    client_kwargs = {"api_key": api_key}

    # For OpenAI official API, no need to override base_url (use default)
    # For other providers, set the custom base_url
    if provider != "openai" or base_url != "https://api.openai.com/v1":
        client_kwargs["base_url"] = base_url

    return AsyncOpenAI(**client_kwargs)


def get_model() -> str:
    """Get the model name for the configured LLM provider."""
    provider = LLM_PROVIDER.lower()
    if provider not in PROVIDER_CONFIGS:
        raise ValueError(f"Unsupported LLM_PROVIDER: '{provider}'")
    return PROVIDER_CONFIGS[provider]["get_model"]()


async def compress(content: str, instruction: str = "summarize briefly", timeout: float = 15.0) -> str:
    """
    Compress/transform content using an LLM.

    Supports multiple providers via LLM_PROVIDER environment variable:
    - "openai": OpenAI official API (GPT-4o, GPT-4o-mini, etc.)
    - "openrouter": OpenRouter API (access to many models)
    - "custom": Any OpenAI-compatible API (Ollama, vLLM, etc.)

    Args:
        content: The raw text to process
        instruction: Natural language instruction for how to process (e.g.,
                     "brief summary", "detailed with all facts", "just urls and titles")
        timeout: Maximum seconds to wait for LLM response (default: 15s)

    Returns:
        Processed text

    Raises:
        asyncio.TimeoutError if LLM takes too long
        Exception if compression fails
    """
    import asyncio

    client = get_client()
    model = get_model()

    async def _call_llm():
        return await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": COMPRESSION_PROMPT
                },
                {
                    "role": "user",
                    "content": f"Instruction: {instruction}\n\nContent:\n{content}"
                }
            ],
            max_tokens=512,
            temperature=0,
        )

    response = await asyncio.wait_for(_call_llm(), timeout=timeout)

    return response.choices[0].message.content

