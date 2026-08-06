"""Generate fixed attention weights and their SVG/PNG heatmaps."""

import argparse
import json
from pathlib import Path

from attention_demo.domain import scaled_dot_product_attention
from attention_demo.providers import fixed_attention_fixture
from attention_demo.visualization import write_heatmap_assets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("assets"))
    args = parser.parse_args()

    fixture = fixed_attention_fixture()
    result = scaled_dot_product_attention(
        fixture.query, fixture.key, fixture.value, mask=fixture.mask
    )
    svg_path, png_path = write_heatmap_assets(result.weights, fixture.labels, args.output)
    print(
        json.dumps(
            {
                "weights": result.weights.round(6).tolist(),
                "row_sums": result.weights.sum(axis=-1).round(6).tolist(),
                "svg": str(svg_path),
                "png": str(png_path),
                "warning": "注意力权重不等于因果解释",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
