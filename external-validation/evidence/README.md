# 外部证据提交目录

真实活动完成后，从 `../templates/` 复制 YAML 到本目录。每份记录必须填写同一个冻结候选 commit 和 `../candidate/release-manifest.json` 的 SHA-256。当前没有任何通过记录；不要提交姓名、邮箱、电话、签字件、法律意见正文或含身份信息的截图。

完整验证命令：

```bash
.venv/bin/python scripts/validate_external_evidence.py external-validation/evidence
```

在七份证据齐全前，该命令失败是预期行为，也正是 P9 不能关闭的机器可读证明。
使用 `--allow-partial` 收集阶段性记录时，命令可能返回 `structurally_valid=True`，但只有七份记录全部满足阈值时 `complete` 才会为 `True`。
