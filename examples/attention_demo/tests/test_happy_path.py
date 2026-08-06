from pathlib import Path

import numpy as np

from attention_demo.domain import reshape_heads, scaled_dot_product_attention
from attention_demo.providers import fixed_attention_fixture
from attention_demo.visualization import write_heatmap_assets


def test_scaled_attention_has_expected_shape_and_normalized_rows() -> None:
    fixture = fixed_attention_fixture()

    result = scaled_dot_product_attention(
        fixture.query,
        fixture.key,
        fixture.value,
        mask=fixture.mask,
    )

    assert result.output.shape == (3, 2)
    assert result.weights.shape == (3, 3)
    np.testing.assert_allclose(result.weights.sum(axis=-1), np.ones(3))
    np.testing.assert_allclose(result.weights[0], np.array([1.0, 0.0, 0.0]))
    assert result.weights[1, 2] == 0.0


def test_multi_head_reshape_preserves_values_and_dimensions() -> None:
    tensor = np.arange(2 * 3 * 8, dtype=np.float64).reshape(2, 3, 8)

    heads = reshape_heads(tensor, number_of_heads=2)

    assert heads.shape == (2, 2, 3, 4)
    restored = heads.transpose(0, 2, 1, 3).reshape(2, 3, 8)
    np.testing.assert_array_equal(restored, tensor)


def test_heatmap_exports_svg_and_png_with_interpretation_warning(tmp_path: Path) -> None:
    fixture = fixed_attention_fixture()
    weights = scaled_dot_product_attention(
        fixture.query, fixture.key, fixture.value, mask=fixture.mask
    ).weights

    svg_path, png_path = write_heatmap_assets(weights, fixture.labels, tmp_path)

    assert "不等于因果解释" in svg_path.read_text(encoding="utf-8")
    assert png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
