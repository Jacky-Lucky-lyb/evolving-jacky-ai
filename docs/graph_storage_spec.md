# 图谱存储约定 v0.1

## 原始文件与索引

- `01_Identity` 至 `08_Sources`：Markdown 原始知识与来源文件，文件名可以变，frontmatter `id` 不变。
- `09_System/nodes.json`：从 Markdown 扫描生成的索引；不可手工维护，为缓存。
- `09_System/relations.json`：已提交的正式关系及证据；是关系权威记录。
- `09_System/review_queue.json`：候选关系，未批准不进入正式图。
- `09_System/audit_log.jsonl`：提交记录，追加写，不覆盖。

## 与 Obsidian 链接的关系

`[[RAG]]` 是方便阅读的导航链接；它不等于具有语义的关系。
结构化图谱以 `relations.json` 的 `from / relation / to` 为准。
后续程序可由图谱生成 Obsidian 双向链接、关系视图，但不可把普通链接自动升级为因果/先修关系。

## ID 和路径

索引以 YAML Frontmatter 的 `id` 定位文件，禁止仅靠文件名匹配。
若某个 ID 重复、节点缺失、关系端点无效，验证失败且停止提交。
每一条审核通过的关系需保存精确来源定位（章节/页码/原文片段/消息标识等）。
