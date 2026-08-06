# 固定 Logit 采样频率

每种配置使用种子 0..499 各运行一次；这是玩具分布，不是 LLM 评测。

| 配置 | Token | 次数 | 频率 |
|---|---|---:|---:|
| baseline | `A` | 353 | 0.7060 |
| baseline | `B` | 116 | 0.2320 |
| baseline | `<STOP>` | 29 | 0.0580 |
| baseline | `?` | 2 | 0.0040 |
| cool_top_k | `A` | 437 | 0.8740 |
| cool_top_k | `B` | 63 | 0.1260 |
| cool_top_k | `<STOP>` | 0 | 0.0000 |
| cool_top_k | `?` | 0 | 0.0000 |
| nucleus | `A` | 370 | 0.7400 |
| nucleus | `B` | 130 | 0.2600 |
| nucleus | `<STOP>` | 0 | 0.0000 |
| nucleus | `?` | 0 | 0.0000 |
