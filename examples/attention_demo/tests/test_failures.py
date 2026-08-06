import numpy as np
import pytest

from attention_demo.domain import reshape_heads, scaled_dot_product_attention


def test_rejects_incompatible_query_and_key_dimensions() -> None:
    query = np.ones((2, 3))
    key = np.ones((2, 4))
    value = np.ones((2, 2))

    with pytest.raises(ValueError, match="Query 与 Key"):
        scaled_dot_product_attention(query, key, value)


def test_rejects_a_row_with_no_visible_key() -> None:
    values = np.eye(2)
    mask = np.array([[False, False], [True, True]])

    with pytest.raises(ValueError, match="至少一个可见 Key"):
        scaled_dot_product_attention(values, values, values, mask=mask)


def test_rejects_model_dimension_not_divisible_by_heads() -> None:
    with pytest.raises(ValueError, match="整除"):
        reshape_heads(np.ones((1, 2, 5)), number_of_heads=2)
