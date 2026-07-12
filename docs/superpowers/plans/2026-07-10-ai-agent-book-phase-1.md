# AI Agent 教材第一阶段 Implementation Plan

> **For agentic workers:** 后续实施应使用测试驱动与完成前验证；步骤以复选框跟踪。

**Goal:** 建立可构建、可测试、可持续扩写的中文 AI Agent 教材仓库，并完成第一篇与最小运行时纵切面。

**Architecture:** MkDocs Material 承载分篇正文，Python 包承载离线教学实现，pytest 验证核心行为，`PROJECT_STATUS.md` 逐章记录真实完成度。版本敏感 API 与稳定原理分离维护。

**Tech Stack:** Python 3.12、Pydantic 2、httpx、pytest、MkDocs Material、Mermaid。

---

### Task 1: 仓库与站点骨架

- [x] 创建工程元数据、MkDocs 配置、首页、学习指南和术语表。
- [x] 建立七篇导航和 38 章入口。
- [x] 运行 `mkdocs build --strict` 并修复错误。

### Task 2: 第一篇教材正文

- [x] 完整撰写第一节“什么是大语言模型”。
- [ ] 按统一模板完成第 2—5 章。
- [ ] 核对第一篇的图、链接、术语一致性。

### Task 3: 离线工具调用运行时（TDD）

- [x] 先编写参数校验、工具执行、循环终止测试并确认失败。
- [x] 实现最小运行时并使测试通过。
- [x] 补充独立示例 README 与运行命令。

### Task 4: 版本与完成度治理

- [x] 创建版本核查清单。
- [x] 创建精确的项目状态报告。
- [ ] 每完成一章同步更新状态，禁止以文件存在代替内容完成。

### Task 5: 最终验证

- [x] 运行全部 Python 测试、静态检查和 MkDocs 严格构建。
- [x] 检查密钥、TODO、空文件和失效内部链接。
- [ ] 将新鲜命令输出写入最终交付说明。
