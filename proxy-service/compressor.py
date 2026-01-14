"""
Compression module using OpenRouter API to summarize large text responses.
"""

import os
from openai import AsyncOpenAI

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-flash-1.5-8b")


def get_client() -> AsyncOpenAI:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )


async def compress(content: str, max_tokens: int = 500) -> str:
    """
    Compress content using a cheap LLM via OpenRouter.

    Args:
        content: The raw text to compress
        max_tokens: Target output length

    Returns:
        Compressed text summary

    Raises:
        Exception if compression fails
    """
    client = get_client()

    response = await client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {
                "role": "system",
                "content": f"Summarize the following content concisely. Target approximately {max_tokens} tokens. Preserve key facts, names, numbers, and actionable information. Output only the summary, no preamble."
            },
            {
                "role": "user",
                "content": content
            }
        ],
        max_tokens=max_tokens + 100,  # Small buffer
    )

    return response.choices[0].message.content
