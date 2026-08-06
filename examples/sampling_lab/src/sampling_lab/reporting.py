"""Reproducible empirical-frequency report writer."""

import csv
from pathlib import Path

from sampling_lab.domain import SamplingConfig, generate
from sampling_lab.providers import FixedLogitModel


def empirical_rows(runs: int = 500) -> list[dict[str, str | int | float]]:
    if runs <= 0:
        raise ValueError("runs 必须为正数")
    model = FixedLogitModel()
    configurations = (
        ("baseline", SamplingConfig(max_tokens=1)),
        ("cool_top_k", SamplingConfig(temperature=0.5, top_k=2, max_tokens=1)),
        ("nucleus", SamplingConfig(top_p=0.75, max_tokens=1)),
    )
    rows: list[dict[str, str | int | float]] = []
    for name, config in configurations:
        counts = {token: 0 for token in model.vocabulary}
        for seed in range(runs):
            result = generate(model, config=config, seed=seed)
            counts[result.tokens[0]] += 1
        for token, count in counts.items():
            rows.append(
                {
                    "configuration": name,
                    "token": token,
                    "count": count,
                    "frequency": round(count / runs, 4),
                }
            )
    return rows


def write_reports(output_directory: Path, *, runs: int = 500) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    rows = empirical_rows(runs)
    csv_path = output_directory / "sampling-comparison.csv"
    markdown_path = output_directory / "sampling-comparison.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# 固定 Logit 采样频率",
        "",
        f"每种配置使用种子 0..{runs - 1} 各运行一次；这是玩具分布，不是 LLM 评测。",
        "",
        "| 配置 | Token | 次数 | 频率 |",
        "|---|---|---:|---:|",
    ]
    lines.extend(
        f"| {row['configuration']} | `{row['token']}` | {row['count']} | {row['frequency']:.4f} |"
        for row in rows
    )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path, markdown_path
