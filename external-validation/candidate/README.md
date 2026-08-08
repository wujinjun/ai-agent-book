# 冻结候选清单

外部验收开始前，在干净 Git 工作区运行打包器，将生成的
`RELEASE_MANIFEST-<版本>.json` 复制到本目录并命名为 `release-manifest.json`。清单必须来自
已经推送且不再修改的候选 commit；打包器默认拒绝把含未提交修改的本地产物绑定到 `HEAD`。

七份证据记录同时填写该文件的 SHA-256。最终标签门禁会验证：

1. 七份记录引用同一个候选 commit 和同一个清单哈希；
2. 清单内容中的 `source_commit` 与证据一致；
3. 清单包含 PDF、EPUB、培训 PPTX 和发行说明四类产物；
4. 候选 commit 是最终标签 commit 的祖先；
5. 两个 commit 之间只修改 `external-validation/candidate/`、
   `external-validation/evidence/` 和少量最终状态文件，不修改教材正文、项目或构建代码。

当前只保留说明文件。没有真实候选清单和七份外部记录时，最终标签必须失败。
