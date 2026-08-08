# 15 分钟 Quick Start 验收

验收日期：2026-08-08

环境：macOS、Python 3.12.13、全新临时虚拟环境，当前仓库工作树；安装使用本机已有 pip 缓存，不外推首次下载速度。

## 实际路径

1. `python3.12 -m venv <temporary>/.venv`
2. `<temporary>/.venv/bin/python -m pip install -e '.[dev,docs]'`
3. `<temporary>/.venv/bin/python -m examples.tool_runtime.main`
4. `<temporary>/.venv/bin/python -m pytest tests/test_tool_runtime.py -q`
5. `<temporary>/.venv/bin/python scripts/build_html.py`

该路径在一次连续执行中约 28 秒完成；由于命中本地包缓存，该数字只证明 15 分钟预算有充足余量，不是网络环境性能承诺。随后又分别复核入口输出与测试结果：Tool Loop 输出 `最终回答：20 + 22 = 42`，5 项相关测试通过，`output/html/index.html` 成功重建。

## 验收边界

- 不要求 API Key，不发起模型供应商请求。
- 不要求 Node、Pandoc 或 Chrome；这些只在重建图形、PDF 和 EPUB 时需要。
- 用户仍需拥有 Python 3.12，并能从包索引安装根依赖。
- Windows 未作为本轮实机验收平台，使用说明按 `COMPATIBILITY.md` 标记为社区验证。
