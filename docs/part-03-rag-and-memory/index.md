# 第三篇：MCP、RAG 与 Memory

本篇承接第二篇的 Agent Runtime。MCP、RAG 与 Memory 都向 Agent 提供外部上下文，但解决的问题和生命周期不同：MCP 连接能力，RAG 在查询时取得证据，Memory 保存受治理的跨时间状态。完成本篇后，读者应能为知识助手建立协议、检索、记忆与索引边界。

```mermaid
%% id: external-context-and-state-map
%% title: 外部上下文与持久状态地图
%% alt: Agent Runtime 通过 MCP 连接能力，通过 RAG 检索证据，通过 Memory 保留状态并使用向量数据库
flowchart TB
    Agent["Agent Runtime"] --> MCP["MCP<br/>发现并调用能力"]
    Agent --> RAG["RAG<br/>按问题获取证据"]
    Agent --> Memory["Memory<br/>跨步骤与会话保留信息"]
    MCP --> Systems["文件 / 数据库 / 外部服务"]
    RAG --> Vector["向量库与关键词索引"]
    Memory --> Store["会话库 / Memory Store"]
    Memory -.检索式记忆.-> Vector
```

从 Agent Runtime 向下阅读：MCP 管连接协议，RAG 管查询时证据，Memory 管跨时间状态；向量数据库只是可被后两者使用的存储与索引实现。

## 主案例在本篇的演进

本篇继续使用第二篇定义的“设备研发企业知识助手”，不更换角色和领域对象。MCP Server 只暴露租户限定的文档目录、受控读取和工单能力；RAG 返回带 `Document.version` 与 `Citation` 的证据；Memory 只能保存经治理的用户偏好和任务事实，不能把文档正文或权限决定写成个人记忆；向量索引始终是 `Document` 主记录的可重建派生物。

```mermaid
%% id: knowledge-assistant-evidence-state-evolution
%% title: 企业知识助手从协议连接到证据与记忆
%% alt: 员工问题经 Agent Runtime 通过 MCP 访问文档服务，RAG 产生带版本引用的证据，Memory 只保存治理后的偏好与事实，向量索引是文档主记录的派生物
flowchart TB
    User["员工 reader"] --> Runtime["Agent Runtime"]
    Runtime --> MCP["MCP：文档/工单能力"]
    MCP --> Master["Document 主记录 + ACL"]
    Master --> Index["关键词/向量派生索引"]
    Index --> RAG["RAG Evidence + Citation"] --> Runtime
    Runtime --> Memory["受治理偏好/任务事实"]
```

图中主记录拥有版本和权限，索引、摘要与 Memory 都不能反向成为文档真值。后续章节若使用维修手册或制度文档，均视为该案例中的不同 `Document` 类型。

| 章 | 主题 | 核心问题 |
|---:|---|---|
| 11 | [MCP 基础](ch11-mcp.md) | 协议怎样统一暴露能力？ |
| 12 | [MCP Server](ch12-mcp-server.md) | 如何测试、授权和部署？ |
| 13 | [RAG 基础](ch13-rag.md) | 如何建立可引用链路？ |
| 14 | [高级 RAG](ch14-advanced-rag.md) | 高级策略何时有效？ |
| 15 | [Memory](ch15-memory.md) | 写入、遗忘与隐私？ |
| 16 | [向量数据库](ch16-vector-databases.md) | 如何选型与压测？ |

MCP 解决连接协议问题，RAG 解决按查询获取知识的问题，Memory 解决跨时间保留有用状态的问题。三者可以组合，但不能互相替代。第四篇会在同一问题上比较原生实现与不同框架，读者应带着本篇的数据和状态边界判断框架抽象是否健康。
