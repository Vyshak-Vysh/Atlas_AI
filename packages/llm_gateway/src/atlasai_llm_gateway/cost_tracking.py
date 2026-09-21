"""Token/cost tracking. Pricing is a settings-driven table (not hardcoded
into call sites) since per-model rates change over the project's life —
current paid-tier rates as of this build, per MTok of text input/output:
Gemini 3.5 Flash-Lite $0.30/$2.50, Gemini 3.8 Flash $0.75/$3.75 (Google
has announced $1.50/$7.50 from 2027-01-01), Gemini 3.1 Pro Preview $2/$12
for prompts up to 200k tokens ($4/$18 above that — every prompt this
system builds is far below the threshold). Verified against Google's
current published pricing, not recalled from training data."""

from __future__ import annotations

from dataclasses import dataclass

_PRICE_PER_MTOK_USD: dict[str, tuple[float, float]] = {
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.1-pro-preview": (2.0, 12.0),
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
