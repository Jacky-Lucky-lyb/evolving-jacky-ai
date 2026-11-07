# Evolving Self AI · 0006 审核冲突防护

## 为什么需要它

之前的旧审核中心先 `INSERT knowledge_nodes` 再 `UPDATE review_queue`，两步不是原子事务。即使有复用建议，另一入口仍能单独批准，从而产生重复 RAG。0005 已修复一次历史数据；0006 防止此类审批流程冲突再次发生。

## 安装顺序（重要）

1. 保留数据库备份/快照；确认已执行 0001—0005。不要修改已经运行过的迁移文件。
2. 将本包 `migrations/`、`app/guarded_node_tab.py`、`scripts/apply_v0006_ui_patch.py`、`tests/test_v0006_patch.py` 放入公开仓库对应目录。
3. **先升级本地 UI：** 在仓库根目录执行 `python3 scripts/apply_v0006_ui_patch.py --check`，确认可以匹配后执行 `python3 scripts/apply_v0006_ui_patch.py --apply`。这会自动备份改动文件为 `.pre0006.bak`，不要把这些备份提交 Git。
4. 执行 `python3 -m unittest discover -s tests -p 'test_v0006_patch.py' -v` 和 `python3 -m py_compile app/review_ui.py app/guarded_node_tab.py app/alignment_tab.py app/relation_tab.py app/supabase_api.py`。
5. 停止旧的 Streamlit 应用，**确认 UI 已修改**，再在 Supabase SQL Editor 执行 `migrations/0006_review_conflict_guard.sql`。若执行异常应当整笔回滚，请报告错误，不要直接重跑。
6. 执行 `migrations/0006_verify.sql`；所有 `passed` 应为 `true`。然后重新启动 Streamlit。
7. 用**新建的、不含个人数据的测试候选**开展真实账户测试；通过之前请勿将此版本标为完全验证。
8. 验证后 Commit + Push 到公开仓库；私有数据仍应保存在私有仓库。

## 修复机制

- 创建 `merge` 待审建议时，对对应原始候选加 `FOR UPDATE` 锁；原始候选必须仍为 `pending`。
- 普通节点审核改为 `review_node_proposal` RPC：在一个事务里锁候选、检查有没有未决复用、创建节点、更新审核记录、写审计和创建同步任务。
- `reject_merge_proposal` 允许拒绝复用，恢复普通节点审核。
- 关系审核改为 `review_edge_proposal`，避免禁用直接审核更新后破坏旧的关系审核流程。
- 客户端不再拥有直接 `INSERT knowledge_nodes` / `UPDATE review_queue` / `DELETE review_queue` 权限。
- 通过数据库函数处理的操作仍使用调用者 Auth 身份校验用户归属；不使用 `service_role` 进行客户端测试。

## 重要边界

- 0006 **不会自动把 RAG 的同义表达合并**。它实现的是审核互斥与部分一致性保护，不是完整的全库语义唯一性约束。
- 既有的 `approve_node_reuse` RPC 继续可用；0006 不会覆盖该函数。
- 为防止把外部资料当作个人能力，**此版普通节点批准 RPC 只支持 `external`**。个人能力或观点的人工认证需要未来独立审批流程。
- 旧项目中若存在其他写 `knowledge_nodes` 或更新 `review_queue` 的客户端调用，升级权限后会失败，必须改为受控 RPC。
- 已批准的旧节点、旧证据、旧关系不会被这份迁移删除。Git 同步任务仅入队，不会自动 Push。
- 允许 API 角色和管理员角色之间仍存在权限区别；管理员与 `service_role` 的高权限操作要在服务端单独审计。

## 必做回归测试（真实 Supabase，使用测试数据）

1. 创建测试 Node 候选 P（外部知识），随后提出针对 P 的 pending merge M。
2. 普通节点审核 P 应被阻止；节点数不得增加。**先不要批准 M。**
3. 拒绝 M；普通审核 P 才应恢复可操作。
4. 普通批准 P 一次，检查新增一个节点、P 已批准、审计事件和 sync_job 已创建。
5. 对已批准 P 再次尝试提交 merge：应被数据库拒绝。
6. 两个不同普通 Auth 用户互相传递候选 ID：RPC 必须拒绝跨用户审批。
7. 记录实际截图与 SQL 查询结果；确认无孤立新节点、未完成审计或重复的同步任务。

### 如果 --check 不通过

它不修改任何文件。请保留错误原文，并根据当前 `app/review_ui.py`、`app/alignment_tab.py`、`app/relation_tab.py` 和 `app/supabase_api.py` 的实际结构做小范围手动修补，**不要覆盖整份旧 UI**。

