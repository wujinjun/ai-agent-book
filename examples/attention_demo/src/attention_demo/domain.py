"""Numerically stable attention primitives without a deep-learning framework."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]


@dataclass(frozen=True)
class AttentionResult:
    weights: FloatArray
    output: FloatArray


def scaled_dot_product_attention(
    query: FloatArray,
    key: FloatArray,
    value: FloatArray,
    *,
    mask: BoolArray | None = None,
) -> AttentionResult:
    """Compute ``softmax(QKᵀ / sqrt(d))V`` for two-dimensional arrays."""
    if query.ndim != 2 or key.ndim != 2 or value.ndim != 2:
        raise ValueError("Query、Key 与 Value 必须是二维数组")
    if query.shape[1] != key.shape[1]:
        raise ValueError("Query 与 Key 的特征维度必须一致")
    if key.shape[0] != value.shape[0]:
        raise ValueError("Key 与 Value 的序列长度必须一致")
    if query.shape[1] == 0:
        raise ValueError("注意力特征维度不能为空")

    scores = query @ key.T / np.sqrt(float(query.shape[1]))
    if mask is not None:
        if mask.shape != scores.shape:
            raise ValueError("Mask 形状必须与注意力分数一致")
        if np.any(~mask.any(axis=-1)):
            raise ValueError("每个 Query 必须保留至少一个可见 Key")
        scores = np.where(mask, scores, -np.inf)

    row_max = np.max(scores, axis=-1, keepdims=True)
    exponentials = np.exp(scores - row_max)
    weights = exponentials / exponentials.sum(axis=-1, keepdims=True)
    return AttentionResult(weights=weights, output=weights @ value)


def reshape_heads(tensor: FloatArray, *, number_of_heads: int) -> FloatArray:
    """Transform ``[batch, sequence, model]`` into ``[batch, heads, sequence, head]``."""
    if tensor.ndim != 3:
        raise ValueError("输入必须使用 [batch, sequence, model] 形状")
    if number_of_heads <= 0:
        raise ValueError("number_of_heads 必须为正数")
    batch, sequence, model_dimension = tensor.shape
    if model_dimension % number_of_heads != 0:
        raise ValueError("model_dimension 必须能被 number_of_heads 整除")
    head_dimension = model_dimension // number_of_heads
    return tensor.reshape(batch, sequence, number_of_heads, head_dimension).transpose(
        0, 2, 1, 3
    )
