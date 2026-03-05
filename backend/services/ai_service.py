import asyncio
import itertools
import logging
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)

_key_cycle: Optional[itertools.cycle] = None


def _get_key_cycle() -> itertools.cycle:
    global _key_cycle
    if _key_cycle is None:
        keys = settings.get_api_keys()
        if not keys:
            keys = ["dummy-key"]
        _key_cycle = itertools.cycle(keys)
    return _key_cycle


def _next_client() -> AsyncOpenAI:
    key = next(_get_key_cycle())
    return AsyncOpenAI(api_key=key, base_url=settings.openai_base_url)


async def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.8,
    response_format: Optional[Dict] = None,
) -> Tuple[str, int, int]:
    """
    Returns (content, prompt_tokens, completion_tokens).
    """
    client = _next_client()
    model = model or settings.openai_model
    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        kwargs["response_format"] = response_format

    response = await client.chat.completions.create(**kwargs)
    choice = response.choices[0]
    usage = response.usage
    return (
        choice.message.content or "",
        usage.prompt_tokens,
        usage.completion_tokens,
    )


async def parallel_chat_completions(
    prompts: List[List[Dict[str, str]]],
    model: Optional[str] = None,
    temperature: float = 0.8,
    concurrency: int = 10,
) -> List[Tuple[str, int, int]]:
    """Run multiple chat completions with bounded concurrency."""
    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded(msgs):
        async with semaphore:
            try:
                return await chat_completion(msgs, model=model, temperature=temperature)
            except Exception as exc:
                logger.warning("AI call failed: %s", exc)
                return ("", 0, 0)

    tasks = [_bounded(msgs) for msgs in prompts]
    return await asyncio.gather(*tasks)
