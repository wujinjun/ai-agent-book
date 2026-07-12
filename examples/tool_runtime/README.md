# 离线工具调用运行时

这个示例用一个确定性的“决策函数”代替在线 LLM，以便在没有 API Key 时观察完整 Tool Loop。运行时负责工具注册、Pydantic 参数校验、异步超时、观察回传和最大步数终止。

```bash
cd ai-agent-book
PYTHONPATH=src .venv/bin/python examples/tool_runtime/main.py
```

预期输出：`最终回答：20 + 22 = 42`。模型接入属于决策函数的另一种实现，不会改变工具执行边界。

测试：

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_tool_runtime.py -q
```

