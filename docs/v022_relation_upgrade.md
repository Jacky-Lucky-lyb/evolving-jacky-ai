# Evolving Self AI — V0.2.2 关系发现增量包

## 覆盖方式

将 `app/` 内四个 `.py` 文件复制到当前 `evolving-jacky-ai/app/`（覆盖同名文件），新增 `tests/test_relation_discovery.py` 到 `tests/`；旧的 `scripts/`、`migrations/`、`schemas/` 和原先的审核数据无需修改。

**先备份旧版 `app/review_ui.py`，不要上传 `.env` 或密钥。**

## 运行

```bash
python3 -m unittest discover -s tests -p 'test_relation_discovery.py' -v
python3 -m unittest discover -s tests -p 'test_review_core.py' -v
python3 -m streamlit run app/review_ui.py --server.address 127.0.0.1
```

打开「自动关系发现」标签，至少有 2 个已批准的节点。粘贴一段原文，选择无需 API 的规则模式或可选 AI 模式，点击分析。证据不足返回零条是正常情况。选择「加入待审核队列」后，再在本标签顶部明确批准，关系才会写入 `knowledge_edges`。

示例：先将 `Embeddings` 作为 external CONCEPT 节点审核入库；输入 `RAG uses Embeddings.` 并采用规则模式，即可得到一条 `RAG → APPLIES → Embeddings` 的候选建议（需人工判断此来源和表达在具体语境下是否成立）。

## 数据规则

- 只允许 V0.1 的预定义关系类型；提议必须有原文证据；不根据共同出现就自动生成边。
- 不改写知识归属空间，不能因为上传教材就自动认定用户已经掌握该知识。
- 待审核边存入 `review_queue` 的 `proposal_type=edge`，只有人工批准才写入 `knowledge_edges`。
- 可选 OpenAI API 模式会传递粘贴文本及节点名称；会产生 API 费用。需在使用前检查服务商数据使用政策，勿输入敏感资料。该模式尚未经过真实 API 的联机测试。
- 本版未做事务化审批、幂等保护、自动 Git 同步或图形可视化。已批准关系若写入成功而更新待审核状态失败，不要重复批准，应先检查数据库。
- 不应把本版视为专业级事实核查或安全审计。
