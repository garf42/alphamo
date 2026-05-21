"""Provider factory — name → instance, env-driven key resolution.

Sprint 14: the CLI / orchestrator constructs providers by name from
Hyperparameters fields (`hp.provider_proposer`, etc.). The factory
resolves "anthropic" → AnthropicProvider(anthropic.Anthropic(max_retries=3))
and "fireworks" → FireworksProvider(api_key=os.environ['FIREWORKS_API_KEY']).

Cached per (name, key) so per-component routing with the same name
shares one underlying SDK client — keeps connection pooling and cache
warmups intact when the proposer / Stage 3 / curator all use the same
provider (the default).
"""

from __future__ import annotations

import os
from typing import Any

from alphamo.providers.anthropic_provider import AnthropicProvider
from alphamo.providers.base import BaseProvider
from alphamo.providers.fireworks_provider import FireworksProvider

_PROVIDER_CACHE: dict[str, BaseProvider] = {}


def build_provider(name: str, **kw: Any) -> BaseProvider:
    """Construct (or fetch from per-process cache) a provider by name.

    Recognized names: "anthropic", "fireworks". Anything else raises
    ValueError — silent fallback hides config typos in run-row
    hyperparameters.

    Env vars consulted:
      - ANTHROPIC_API_KEY (Anthropic SDK reads this directly)
      - FIREWORKS_API_KEY (passed into openai.OpenAI(api_key=...))

    Pass `client=` to inject a pre-built underlying SDK client (used
    only in tests / advanced wiring); bypasses the per-process cache.
    """
    explicit_client = kw.pop("client", None)
    if explicit_client is not None:
        if name == "anthropic":
            return AnthropicProvider(explicit_client)
        if name == "fireworks":
            return FireworksProvider(client=explicit_client)
        raise ValueError(f"unknown provider: {name!r}")

    if name in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[name]

    if name == "anthropic":
        import anthropic

        provider: BaseProvider = AnthropicProvider(
            anthropic.Anthropic(max_retries=3)
        )
    elif name == "fireworks":
        api_key = os.environ.get("FIREWORKS_API_KEY")
        if not api_key:
            raise RuntimeError(
                "FIREWORKS_API_KEY is not set — load it via terminal before "
                "starting a Fireworks-routed run"
            )
        provider = FireworksProvider(api_key=api_key, max_retries=3)
    else:
        raise ValueError(
            f"unknown provider: {name!r} (expected 'anthropic' or 'fireworks')"
        )

    _PROVIDER_CACHE[name] = provider
    return provider


def reset_provider_cache() -> None:
    """Drop cached providers — useful for tests that need a fresh client."""
    _PROVIDER_CACHE.clear()
