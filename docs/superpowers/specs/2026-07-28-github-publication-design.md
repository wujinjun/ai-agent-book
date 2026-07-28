# GitHub 发布设计

日期：2026-07-28

## 目标

将教材以三种互补形式发布到 `wujinjun/ai-agent-book`：

1. `main` 保存可维护的 Markdown、代码、图源和构建脚本。
2. GitHub Pages 提供可直接阅读的 MkDocs HTML 站点。
3. GitHub Release 提供带版本号的 PDF 与 EPUB 下载。

## 触发规则

- 推送 `main`：运行完整出版构建并部署 GitHub Pages。
- 推送 `v*` 标签：运行同一构建，创建对应 Release，并上传 PDF、EPUB。
- `workflow_dispatch`：允许从 GitHub Actions 页面手动重跑。

## 构建与数据流

工作流使用 Python 3.12、Node.js 22、固定的 Python/Node 依赖和 Pandoc。构建顺序为：

```text
检出源码
  -> 安装 Python/Node/Pandoc
  -> 生成索引
  -> 生成 SVG/PNG
  -> 构建 HTML/PDF/EPUB
  -> 运行统一出版审计
  -> 上传 Actions artifact
  -> Pages 部署或 Release 上传
```

HTML 站点内额外提供 `downloads/`，包含本次构建的 PDF 与 EPUB，使 Pages
读者无需进入 Release 页面也能下载离线版本。

## 权限与安全

- 构建任务只需要 `contents: read`。
- Pages 部署任务只授予 `pages: write` 与 `id-token: write`。
- Release 任务只在版本标签触发，并授予 `contents: write`。
- 不使用长期个人令牌，不引入第三方 Release Action；发布通过 Runner 自带的
  `gh` 和短期 `GITHUB_TOKEN` 完成。
- 不强制推送、不改写远端历史。

## 失败处理与验收

任何索引漂移、图示构建失败、HTML/PDF/EPUB 构建失败或出版审计失败都会阻止部署。
工作流文件由本地测试验证触发器、权限、构建命令、Pages artifact 和 Release
附件配置。发布后再读取远端引用，确认主分支与版本标签指向预期提交。

