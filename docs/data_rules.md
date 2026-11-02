# 数据规则 v0.1（正式协议）

正式规则以本目录的 `node_schema.yaml`、`relation_schema.yaml` 与 `ingestion_protocol.md` 为准。

- 所有正式节点使用 `PREFIX-YYYYMMDD-NNN`。节点类别和前缀见 `node_schema.yaml`。
- `KNW` 对应 `CONCEPT`；`IDN` 对应 `PERSON`；`EXP` 对应 `EXPERIENCE`；`DEC` 对应 `DECISION`；`SRC` 对应 `SOURCE`。
- 旧模板 `LRN`、`SIM`、`WFL` 为文档记录，不强制建立图谱节点；如需要概念节点、项目节点，请单独建相应类型并互相关联。
- 旧文档的 `type: knowledge` 应逐步迁移为 `type: CONCEPT`；`status` 与 `learning_status` 分开。
- `current` = 已确认的个人信息；`external` = 外部资料或知识；`hypothetical` = 仅供成长模拟的推演。
- 状态 `observed` 表示有个人原始表达或经历证据，`verified` 表示有相应验证依据，不能混淆。
- 原始记录不覆盖，建立可回滚的审计日志。敏感资料默认不得提供给外部服务。
