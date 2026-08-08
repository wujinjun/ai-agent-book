# 商业发行权利核查协议

本协议用于出版社或具有相应专业能力的独立审阅者。它是工作清单，不是法律意见；最终结论必须由实际负责商业发行的主体确认。

## 必查范围

| 类别 | 核查内容 | 仓库起点 |
|---|---|---|
| 内容许可 | 教材许可、商业发行限制、署名和相同方式共享义务 | `LICENSE`、`COMMERCIAL_LICENSE.md` |
| 代码许可 | 示例代码许可、教材与代码边界 | `LICENSE-CODE` |
| 依赖 | 直接/传递依赖、许可证兼容性、发行是否包含依赖二进制 | `pyproject.toml`、锁定版本记录 |
| 贡献 | CLA、贡献者授权、第三方补丁 | `CLA.md`、Git 历史 |
| 字体 | PDF/EPUB/PPTX 字体嵌入和再分发权 | `assets/fonts/`、`notes/asset-provenance.yml`、发行预检报告 |
| 图片与图表 | 原创/生成来源、外部截图、Logo、照片和替代文本 | `assets/`、图形 manifest、培训课件 |
| 商标 | 产品名、比较表、封面与营销描述是否暗示背书 | 正文、README、封面和发布页 |
| 发行条款 | ISBN、平台条款、地域、付费课程、更新和撤回机制 | 商业合同与发布计划 |

审阅者还应核查最终发布包的 SHA-256 与目标 commit，避免对旧版材料出具结论。私有法律意见、合同和个人身份信息不得提交仓库；只记录受控档案编号或不可逆哈希。

先运行 `python scripts/audit_distribution_assets.py` 并阅读 `notes/distribution-asset-audit.json`。依赖清单从直接依赖和已选 Extra 解析传递闭包，同时保留依赖边、传统 `License`、SPDX `License-Expression`、Classifier 和随包许可证文件哈希；报告中的硬失败必须为 0。人工复核清单中的 OFL 通知、EPUB/PPTX 字体替换、依赖条款和印厂页面规范仍须逐项形成结论，不能因为自动预检通过而跳过。

## 通过标准

- 八类范围全部核查；
- 独立性和专业身份在私有原件中可验证；
- 所有 P0/P1 和发行前置条件已经关闭；
- 结论为无开放条件的 `approved`；
- 结论明确对应目标 commit、PDF、EPUB、HTML 和培训材料版本。

`approved_with_conditions` 只能推动修订，不能关闭商业出版门禁。
