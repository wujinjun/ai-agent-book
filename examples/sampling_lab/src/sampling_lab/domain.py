"""Provider-neutral filtering, sampling and termination."""

import math
import random
from dataclasses import dataclass

from sampling_lab.providers import LogitProvider


@dataclass(frozen=True)
class SamplingConfig:
    temperature: float = 1.0
    top_k: int | None = None
    top_p: float = 1.0
    max_tokens: int = 16
    stop_tokens: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("max_tokens 必须为正数")


@dataclass(frozen=True)
class GenerationResult:
    tokens: tuple[str, ...]
    finish_reason: str
    seed: int


def probability_distribution(
    logits: tuple[float, ...],
    *,
    temperature: float = 1.0,
    top_k: int | None = None,
    top_p: float = 1.0,
) -> tuple[float, ...]:
    """Apply temperature, top-k, then top-p and return normalized probabilities."""
    if not logits:
        raise ValueError("logits 不能为空")
    if not all(math.isfinite(value) for value in logits):
        raise ValueError("logits 必须全部为有限数")
    if temperature <= 0 or not math.isfinite(temperature):
        raise ValueError("temperature 必须为有限正数")
    if top_k is not None and top_k <= 0:
        raise ValueError("top_k 必须为正数")
    if not 0.0 < top_p <= 1.0:
        raise ValueError("top_p 必须位于 (0, 1]")

    scaled = [value / temperature for value in logits]
    active = set(range(len(scaled)))
    if top_k is not None and top_k < len(scaled):
        active = set(sorted(active, key=scaled.__getitem__, reverse=True)[:top_k])

    maximum = max(scaled[index] for index in active)
    weights = [
        math.exp(value - maximum) if index in active else 0.0
        for index, value in enumerate(scaled)
    ]
    total = sum(weights)
    probabilities = [weight / total for weight in weights]

    if top_p < 1.0:
        ordered = sorted(active, key=probabilities.__getitem__, reverse=True)
        retained: set[int] = set()
        cumulative = 0.0
        for index in ordered:
            retained.add(index)
            cumulative += probabilities[index]
            if cumulative >= top_p:
                break
        probabilities = [
            value if index in retained else 0.0
            for index, value in enumerate(probabilities)
        ]
        retained_total = sum(probabilities)
        probabilities = [value / retained_total for value in probabilities]

    return tuple(probabilities)


def _sample_index(probabilities: tuple[float, ...], random_source: random.Random) -> int:
    threshold = random_source.random()
    cumulative = 0.0
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if threshold < cumulative:
            return index
    return len(probabilities) - 1


def generate(
    provider: LogitProvider,
    *,
    config: SamplingConfig,
    seed: int,
) -> GenerationResult:
    random_source = random.Random(seed)
    generated: list[str] = []
    for _ in range(config.max_tokens):
        logits = provider.next_logits(generated)
        if len(logits) != len(provider.vocabulary):
            raise ValueError("logits 数量必须与 vocabulary 一致")
        probabilities = probability_distribution(
            logits,
            temperature=config.temperature,
            top_k=config.top_k,
            top_p=config.top_p,
        )
        token = provider.vocabulary[_sample_index(probabilities, random_source)]
        generated.append(token)
        if token in config.stop_tokens:
            return GenerationResult(tuple(generated), "stop", seed)
    return GenerationResult(tuple(generated), "max_tokens", seed)
