"""Token/cost tracking. Pricing is a settings-driven table (not hardcoded
into call sites) since per-model rates change over the project's life —
current rates as of this build: Haiku 4.5 $1/$5 per MTok, Sonnet 5 $2/$10,
Opus 5 $5/$25 (verified against Anthropic's current published pricing, not
recalled from training data)."""

from __future__ import annotations

from dataclasses import dataclass

_PRICE_PER_MTOK_USD: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-opus-5": (5.0, 25.0),
}


@dataclass(frozen=True)
class TokenUsage:
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        input_price, output_price = _PRICE_PER_MTOK_USD.get(self.model, (0.0, 0.0))
        return (self.input_tokens / 1_000_000) * input_price + (self.output_tokens / 1_000_000) * output_price
