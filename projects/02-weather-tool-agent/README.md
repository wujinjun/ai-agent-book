# 项目2：天气与工具调用 Agent

## 需求、架构与数据流
技术选型：Python 3.12、Pydantic 2、FastAPI、pytest 与 Docker；在线供应商通过适配器接入。

```mermaid
flowchart LR
    User --> Runtime --> Schema{"参数有效？"}
    Schema -->|否| Repair["有限修复"]
    Schema -->|是| Weather["WeatherService"]
    Weather --> Retry{"瞬时错误？"}
    Retry -->|是且预算内| Weather
    Retry -->|否| Result["来源 + attempts"]
```

实现多工具选择、参数校验、Tool Loop、有限重试和写操作审批。 离线模式使用确定性 Mock，使无 API Key 也能运行和测试；在线服务通过适配器替换，领域结果保持稳定 Schema。

`输入 → Planner → ToolCall 列表 → Pydantic 校验 → 审批策略 → 并行工具 → Observation`。独立实现位于 `src/ai_agent_book/apps/weather_agent.py`，测试位于 `tests/test_weather_agent_app.py`。

## 运行、测试与部署
```bash
PYTHONPATH=src .venv/bin/python projects/02-weather-tool-agent/main.py
PYTHONPATH=src .venv/bin/python -m pytest tests/test_weather_agent_app.py -q
docker build -f projects/02-weather-tool-agent/Dockerfile -t ai-agent-book/project-2 .
docker run --rm ai-agent-book/project-2
```

配置只从环境读取，默认 `APP_MODE=offline`。常见问题：Mock 天气是教学数据，不可用于业务告警。扩展方向：接入天气供应商、幂等审批和并行只读工具。

## 实现说明与验收

`ToolAgent` 接收可替换 Planner 的多个 ToolCall，只读工具可并行执行；天气工具在三次预算内重试瞬时错误，计算器只允许 AST 白名单运算，外部告警必须匹配 `call_id` 的批准决定。测试覆盖多工具、参数错误和审批前后行为。在线模型只需实现同一 Planner 协议。

## 目录、配置与扩展

```text
02-weather-tool-agent/  README.md  main.py  .env.example  Dockerfile  tests/
src/ai_agent_book/apps/weather_agent.py  # Tool Loop 与三个工具
```

天气密钥为空时使用 Fixture。常见问题是把所有错误都重试；本项目只重试瞬时故障，参数错误直接回传 Observation。扩展方向包括真实天气 Provider、并行调用 Trace、审批存储和幂等告警投递。
