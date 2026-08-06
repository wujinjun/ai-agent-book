"""Fixed, reproducible inputs for the attention mechanics experiment."""

from dataclasses import dataclass

import numpy as np

from attention_demo.domain import BoolArray, FloatArray


@dataclass(frozen=True)
class AttentionFixture:
    query: FloatArray
    key: FloatArray
    value: FloatArray
    mask: BoolArray
    labels: tuple[str, ...]


def fixed_attention_fixture() -> AttentionFixture:
    """Return three tokens and a lower-triangular causal mask."""
    query = np.array([[1.0, 0.0], [0.8, 0.2], [0.0, 1.0]], dtype=np.float64)
    key = np.array([[1.0, 0.0], [0.5, 0.5], [0.0, 1.0]], dtype=np.float64)
    value = np.array([[1.0, 0.0], [0.5, 0.5], [0.0, 1.0]], dtype=np.float64)
    return AttentionFixture(
        query=query,
        key=key,
        value=value,
        mask=np.tril(np.ones((3, 3), dtype=np.bool_)),
        labels=("Agent", "调用", "工具"),
    )
