# Evolving Self AI V0.2.5 — 多来源证据与原子复用

## 做到了什么

1. 新增 `knowledge_node_evidence` 表：每条审核复用建议对应一条证据记录，保留来源、原文引用、原始定位以及创建时间。
2. 复用已有节点时不改变节点 ID、名称、知识空间与状态；新来源只添加证据。
3. `approve_node_reuse` RPC 单事务完成：锁定 merge 和原候选 → 校验目标和所有权 → 新增证据 → 关闭两条审核记录 → 写入变更事件 → 排队待 Git 同步任务。
4. 再次调用已经成功的审核会返回 `already_approved`，不会重复新增证据。
5. 前端通过普通 Supabase Auth 用户 JWT 调用 RPC，不使用 `service_role`。数据库函数用 `SECURITY DEFINER` 且 **显式核对每个涉及记录的 owner_id**，避免直接授予客户端证据写权限。

## 安装与执行

1. 把 `migrations/0004_node_evidence_merge.sql`、`0004_verify.sql` 放在公开仓库的 `migrations/`；**先备份并检查项目是否正确**。
2. Supabase SQL Editor 运行 `0004_node_evidence_merge.sql`，再运行只读 `0004_verify.sql`。预期 7 行 `passed=true`。
3. 把 `app/evidence_merge_tab.py` 放入公开仓库 `app/`，根据 `app/api_rpc_patch.md` 在两个现有文件中作小幅增量修改。不要覆盖你的现有审核中心。
4. 把 `tests/test_v025_contract.py` 放到 `tests/`，运行 `python3 -m unittest discover -s tests -p 'test_v025_contract.py' -v`。
5. 在审核中心打开“来源证据/安全复用”，选择你前面产生的 RAG 匹配建议并审核。若之前只生成了候选而没有提交 merge 建议，先到“语义匹配/去重”提交复用建议。
6. 在“当前图谱”核对仍然只有一个 RAG 节点；在“来源证据/安全复用”核对证据新增；SQL Editor 中查询 `review_queue` 和 `sync_jobs` 检查状态。

## 安全边界和后续工作

- 这是**未经过你自己的 Supabase 端到端测试的开发增量**。本地 6 项静态契约测试不能代替数据库实际事务测试和多用户测试。
- 函数使用 `SECURITY DEFINER`，该模式可能绕过 RLS，因此代码对 `review_queue`、`knowledge_nodes`、`sources` 等涉及记录逐一检查 `owner_id = auth.uid()`。必须重新执行双用户隔离测试后才导入真实隐私资料。
- `change_events` 目前允许普通登录用户直接插入；未来应限制其写入路径，提高审计可信性。
- `sync_jobs` 只记录 **queued** 任务，不会自动 Push GitHub。V0.2.6 才开发 Git 同步消费者。
- 当前没有覆盖外部资料与个人知识的跨空间合并，也未自动回填旧节点证据。
- 原文引用存在来源证据表中，但上传后是否确实对应文件原文，仍依赖已有文本提取和人工确认；数据库本身不验证 Storage 文件内容。
- 如果产生任何 SQL 错误，不要反复执行或人工修改审核状态，请保留完整错误文本供排查。
