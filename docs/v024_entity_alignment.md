# Evolving Self AI V0.2.4 — 实体对齐与复用建议

## 目标和边界

新候选 `Retrieval-Augmented Generation (RAG)` 与已有 `RAG` 被识别为可能的同一概念；**不自动新建第二个节点，不自动覆盖正式节点**。审核中心新增「语义匹配/去重」标签。候选匹配采用标准化标题、已登记别名、明确缩写和保守的字符串相似度。它不等于完整的语义理解，不能保证识别中文翻译、上下文隐含的同义词或缩写歧义。模型驱动的语义匹配留待验证后接入。

## 安装

在 `evolving-jacky-ai` 仓库根目录，将本包中的 `app/`、`tests/`、`docs/` 内文件复制到同名目录。`app/review_ui.py` 基于上一个 **自动关系发现** 增量包版本更新，安装前备份你自行修改过的文件，使用 VS Code 的比较功能确认差异。**不要覆盖现有 `app/relation_tab.py`、`app/supabase_api.py`、`app/review_core.py`。**

```bash
python3 -m unittest discover -s tests -p 'test_entity_alignment.py' -v
python3 -m streamlit run app/review_ui.py --server.address 127.0.0.1
```

如果现有待审核记录只有 `Limitations`（RAG、Embeddings 均已批准），请使用 `ingest_semantic.py --mode upload` 将一份**新的、非敏感、未重复上传的**测试 Markdown 导入待审核队列；文档中写出 `Retrieval-Augmented Generation (RAG)` 的完整定义与证据原句。不要刻意污染正式节点。新候选出现后进入「语义匹配/去重」，查找建议复用的 RAG 节点。

## 此阶段的数据行为

- `knowledge_nodes`：不做写入。
- `knowledge_edges`：不做写入。
- `review_queue`：仅为已经检查过的候选创建一条 `proposal_type=merge`、`status=pending` 的二次审核建议。原候选不改变状态。
- `sources`：只读取引用。
- 所有更改通过已登录用户 JWT + Supabase RLS 进行，不使用管理员密钥。

此设计**有意不完成正式合并**：目前的节点证据仅放在 `metadata` 中，没有原子级多来源关联表。如果直接向 `metadata` PATCH，可能因为并发覆盖或跨表分步失败造成证据丢失。V0.2.5 应新增 `node_evidence` 表、唯一约束、版本化迁移、数据库事务审批函数，之后允许「批准复用已有节点」并保留每条来源证据，同时更新原候选和 merge 审核记录。

## 核对要求

- 跨 current / external / hypothetical 空间，即使同名也只允许人工比较，不自动提出复用。
- 匹配分数只衡量名称相似，不表示事实正确或内容可信。
- 前端目前最多读取 500 个节点；到达上限时给出警告。真正可扩展的全库匹配需要分页或服务器检索。
- 外部知识不能被转化为个人已掌握知识。
- Git 版本同步与任何真正的知识合并均尚未实现。
