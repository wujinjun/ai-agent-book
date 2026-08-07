# 独立示例工程

正文中的短代码用于解释单一原理，本目录索引对应可以单独安装、运行和测试的工程示例。示例默认采用确定性的 Fixture 或 Fake 适配器，不要求付费 API，也不会在未说明时访问网络。在线供应商适配器只作为可选路径，并要求通过环境变量注入密钥、设置超时与预算。

```mermaid
flowchart LR
    Chapter["章节原理与内联代码"] --> Contract["示例工程契约"]
    Contract --> Offline["离线 Fixture / Fake"]
    Contract --> Online["可选在线 Adapter"]
    Offline --> Tests["成功与失败路径测试"]
    Online --> Tests
    Tests --> Evidence["可复现实验与预期输出"]
```

这张图说明示例的证据链：章节先定义问题和边界，独立工程再用离线适配器验证控制逻辑；可选在线路径不能取代确定性测试。只有安装、离线运行、测试与章节链接全部通过，示例才会在清单中标记为完成。

## P2 交付清单

| 示例 | 对应章节 | 重点 | 当前状态 |
|---|---:|---|---|
| [Token Counter](https://github.com/wujinjun/ai-agent-book/tree/main/examples/token_counter) | 2 | 多语言计数与上下文预算 | 已完成：离线测试通过 |
| [Attention Demo](https://github.com/wujinjun/ai-agent-book/tree/main/examples/attention_demo) | 3 | 缩放点积注意力、Mask 与 SVG/PNG 热力图 | 已完成：固定 NumPy 2.5.1 |
| [Sampling Lab](https://github.com/wujinjun/ai-agent-book/tree/main/examples/sampling_lab) | 4 | Temperature、top-k、top-p、终止与频率报告 | 已完成：离线可重复 |
| [Local Semantic Search](https://github.com/wujinjun/ai-agent-book/tree/main/examples/local_semantic_search) | 5 | 稀疏、Hash 稠密、RRF、ACL 与评估 | 已完成：离线黄金集 |
| [Prompt Registry](https://github.com/wujinjun/ai-agent-book/tree/main/examples/prompt_registry) | 6 | 不可变版本、哈希、灰度与回滚 | 已完成：文件式 Fixture |
| [Structured Extractor](https://github.com/wujinjun/ai-agent-book/tree/main/examples/structured_extractor) | 7 | Pydantic 校验、有限修复与脱敏错误 | 已完成：Pydantic 2.11.7 |
| [Minimal Agent](https://github.com/wujinjun/ai-agent-book/tree/main/examples/minimal_agent) | 9、17 | 可恢复 Runtime、权限与终止策略 | 已完成：崩溃恢复验证 |
| [Long-term Memory](https://github.com/wujinjun/ai-agent-book/tree/main/examples/long_term_memory) | 15 | 写入治理、来源、TTL、更正与删除 | 已完成：SQLite + Fake Clock |
| [OpenAI Agents SDK](https://github.com/wujinjun/ai-agent-book/tree/main/examples/openai_agents_sdk) | 18 | 工具、结构化输出、Handoff、Agent-as-tool、Guardrail、Session 与 Trace | 已完成：固定并实测 0.18.3 |
| [PydanticAI Service](https://github.com/wujinjun/ai-agent-book/tree/main/examples/pydanticai_service) | 19 | 类型化依赖、工具与输出，有限重试和 FastAPI 错误映射 | 已完成：固定并实测 2.25.0 |
| [Framework Comparison](https://github.com/wujinjun/ai-agent-book/tree/main/examples/framework_comparison) | 38 | 三个隔离候选的同题实跑、故障注入、加权敏感性与可逆 ADR | 已完成：20 次实跑证据 + 源码哈希 |

机器可读的真实状态记录在 `notes/example-matrix.yml`。表中未完成示例不会链接到不存在的目录；各示例交付后，本页将增加安装命令、预期输出和源码入口。

## 统一运行边界

每个工程要求 Python 3.12，并拥有自己的 `pyproject.toml`。根环境只运行仓库契约测试；框架依赖存在冲突时使用示例自己的虚拟环境，禁止把多个框架的可选依赖强行合并为一套无法复现的锁文件。

```bash
cd examples/<example-name>
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest -q
```

具体命令以各示例 README 为准。任何真实密钥都不得写入仓库；`.env.example` 只声明变量名和安全默认值。

仓库维护者可用根级编排器为 11 个示例分别创建虚拟环境，禁止把框架依赖合并成一个环境：

```bash
.venv/bin/python scripts/verify_examples.py \
  --python /path/to/python3.12 \
  --venv-root /tmp/ai-agent-book-example-venvs
```

编排器依次执行独立安装、离线入口、pytest、Ruff 和 mypy；框架对照还会跨 OpenAI Agents SDK 与 PydanticAI 两个解释器重生成同题证据。结果写入 `tmp/p2-example-verification.json`，任一检查失败都会返回非零退出码并保留对应命令与输出尾部。
