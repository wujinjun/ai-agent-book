# 项目4：企业知识库 Agent

![PDF Word PPT Markdown 经过解析版面 Chunk 元数据 ACL 和质量报告形成版本化 pgvector 索引，用户身份进入混合检索权限过滤重排与压缩，最终生成带引用回答并用 Recall MRR Faithfulness 回归评估](../../docs/assets/infographics/png/project04-knowledge-agent-infographic-2x.png)

*图 P4-A　企业知识库的摄取、检索、引用与评估闭环。*

图把离线摄取质量和在线查询证据链放在同一视图中。索引必须绑定解析器、切分器和 Embedding 版本；权限过滤在召回阶段执行，引用则保留文档、页码和 Chunk 定位以支持复核。

## 需求、架构与数据流
技术选型：Python 3.12、Pydantic 2、FastAPI、pytest 与 Docker；在线供应商通过适配器接入。

项目同时覆盖离线摄取和在线查询，权限在检索前过滤，最终回答保留文档、页码、Chunk 与分数等可验证引用。

```mermaid
%% id: project4-knowledge-rag-pipeline
%% title: 企业知识库摄取与查询管线
%% alt: PDF Office Markdown 经解析切分索引后，查询经过租户权限过滤检索重排生成带页码引用的回答
flowchart LR
    Files["PDF / Office / Markdown"] --> Parse --> Chunk --> Index
    Query --> ACL["Tenant / ACL Filter"] --> Retrieve --> Rerank
    Index --> Retrieve
    Rerank --> Answer["Grounded Answer"] --> Citation["document + page + score"]
```

实现文档导入、切分、Embedding 接口、检索、重排、引用和评估。 离线模式使用确定性 Mock，使无 API Key 也能运行和测试；在线服务通过适配器替换，领域结果保持稳定 Schema。

```mermaid
%% id: project4-versioned-ingestion-architecture
%% title: 知识库版本化摄取架构
%% alt: 原始文档存储后由受限解析器生成带位置 Chunk，Embedding Worker 写候选 pgvector 索引并评估切换
flowchart LR
    Upload[受限文件上传] --> Raw[原始文件 hash 与 ACL]
    Raw --> Parser[PDF Office Markdown Parser]
    Parser --> Chunk[位置化 Chunk 与版本]
    Chunk --> Embed[Embedding Worker]
    Embed --> Candidate[候选 pgvector 索引]
    Candidate --> Eval{Recall 引用 ACL 评估}
    Eval -->|通过| Active[切换 active index]
    Eval -->|失败| Keep[保留旧索引]
```

解析器、切分器、Embedding 与权限快照共同定义索引版本；本地哈希向量只用于离线测试，不代表生产语义质量。

```mermaid
%% id: project4-rag-evaluation-loop
%% title: 企业 RAG 查询评估闭环
%% alt: 黄金问题经权限过滤混合检索重排和回答生成后分别计算 Recall MRR 引用与 Faithfulness 并回流失败样本
flowchart LR
    Dataset[黄金问题与权威证据] --> Retrieve[ACL + 混合检索]
    Retrieve --> Rerank[重排]
    Rerank --> Generate[带引用回答]
    Retrieve --> Metrics["Recall@K MRR"]
    Generate --> AnswerEval[正确性 Citation Faithfulness]
    Metrics --> Failures[失败分类]
    AnswerEval --> Failures
    Failures --> Dataset
```

检索与回答指标分开报告，才能判断问题来自文档、召回、重排还是生成。跨租户和注入文档属于发布必测项。

`输入 → PDF/DOCX/PPTX/Markdown 解析 → 重叠切分 → 哈希向量 → 租户过滤 → 混合检索/重排 → 页码引用 → 评估`。独立实现位于 `src/ai_agent_book/apps/knowledge_agent.py`，pgvector 表与 HNSW 索引位于 `schema.sql`，直接测试位于 `tests/test_knowledge_agent_app.py`。

## 运行、测试与部署
CLI 用于观察领域事件；`api.py` 提供持久 Run、幂等、租户隔离、取消、SSE 回放、Trace 与指标：
```bash
PYTHONPATH=src .venv/bin/python projects/04-knowledge-agent/main.py
PYTHONPATH=src DATABASE_PATH=.data/project-4.db .venv/bin/uvicorn --app-dir projects/04-knowledge-agent api:app --port 8104
PYTHONPATH=src .venv/bin/python -m pytest tests/test_knowledge_agent_app.py -q
docker build -f projects/04-knowledge-agent/Dockerfile -t ai-agent-book/project-4 .
docker run --rm ai-agent-book/project-4
```

配置只从环境读取，默认 `APP_MODE=offline`。常见问题：离线向量是测试替身，不能宣称真实语义效果。扩展方向：接入 PDF/Office 解析、pgvector 与黄金评估集。

## 实现说明与验收

`DocumentParser` 无需安装 Office 即可读取 DOCX/PPTX 的 XML，并限制解压后大小；PDF 使用 pypdf。`KnowledgeBase` 实现重叠切分、确定性本地 Embedding、稠密与词项混合评分、租户预过滤、重排和来源/页码/Chunk 引用。评估函数计算 Recall@K 与 MRR。离线向量用于教学和测试，生产部署用 `schema.sql` 的 pgvector 表替换存储层并接入正式 Embedding/Reranker。

`PgVectorKnowledgeRepository` 使用 Psycopg 实际创建 vector 扩展、写入 128 维教学向量、建立 HNSW 索引并执行带租户条件的余弦查询。根级 Compose 使用 `pgvector/pgvector:pg17`，数据库端口只绑定宿主 loopback；`scripts/verify_pgvector.py` 提供可重复的真实摄取与检索验收。

`VersionedKnowledgePipeline` 进一步把摄取变成持久队列：提交时绑定原文、Chunk 配置和黄金集指纹；Worker 构建候选版本，只有 Recall@K 与 MRR 同时达标才在一个事务中归档旧版本并激活新版本。每个版本还保存规范化 `chunks_json` 的 SHA-256，查询和回滚前重新校验，数据库内容被篡改时拒绝提供答案。进程中断留下的 `running` Job 会恢复到队列，失败只公开错误类型，原始异常与文档内容不会进入 API 响应。

```mermaid
%% id: project4-ingestion-release-state
%% title: 知识库摄取与索引发布状态机
%% alt: 摄取任务从排队运行到候选评估，达标后原子激活，不达标拒绝，进程中断可恢复排队
stateDiagram-v2
    [*] --> Queued
    Queued --> Running: worker lease
    Running --> Queued: process restart recovery
    Running --> Failed: parser or integrity failure
    Running --> Candidate: chunks + embeddings
    Candidate --> Active: Recall and MRR pass
    Candidate --> Rejected: release gate fails
    Active --> Archived: newer candidate passes
```

状态机把“文档处理成功”和“索引允许发布”分开。离线哈希向量仍只是测试 Adapter；正式 Embedding 或 Reranker 替换后必须使用同一黄金集门禁重新生成证据。

`rollback(tenant_id, version_id)` 只允许激活同租户的 `archived` 版本：它先校验 Chunk 摘要，再在同一事务中归档当前 Active 并恢复目标版本。`rejected` 候选不能借回滚绕过发布门禁，跨租户版本也不可见。回滚恢复的是仍保留的索引版本，不代表可以恢复因合规删除而销毁的原文、Chunk、Embedding 或缓存；删除传播必须拥有单独的墓碑、保留期和下游清理协议。

## 目录、配置与扩展

```text
04-knowledge-agent/  README.md  main.py  schema.sql  .env.example  Dockerfile  tests/
src/ai_agent_book/apps/knowledge_agent.py  # 解析、索引、检索、评估
```

导入文件在不可信解析边界中处理，生产环境应限制文件大小、页数和解压资源。常见问题是把本地哈希向量当成真实语义效果；它只用于离线教学。扩展方向包括 OCR、正式 Embedding、Cross-Encoder Reranker、pgvector Repository 和黄金集流水线。
