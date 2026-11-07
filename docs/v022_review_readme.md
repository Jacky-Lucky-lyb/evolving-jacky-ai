# Evolving Self AI V0.2.2：本地审核中心（第一版）

## 安装

将压缩包内 `app/`、`tests/test_review_core.py` 和本文件放在公开仓库根目录下；保留之前 V0.2.1 的文件。不要用压缩包覆盖根目录 README。

```bash
python3 -m pip install streamlit
python3 -m unittest discover -s tests -p test_review_core.py -v
python3 -m streamlit run app/review_ui.py --server.address 127.0.0.1
```

浏览器打开终端显示的 `http://127.0.0.1:8501`。登录时填写 Supabase Project URL、Publishable Key、你此前创建的 Supabase Auth 用户邮箱和密码。仅在你信任的本地电脑运行；不要公开部署这个 Demo。不要使用 `service_role`、`sb_secret_` 或个人 GitHub Token。

## 当前功能

- 查看该用户 `review_queue` 中 status 为 `pending` 的节点候选，以及来源与证据。
- 编辑标题、类型、知识空间、知识状态、审核备注，并批准为新节点或拒绝、标记为需要修改。
- 对近似标题做提醒（阈值 0.76）；疑似重复节点将阻止直接新增，避免盲目制造重复数据。
- 从已有节点中选择两端和关系类型，并要求人工确认后才写入 `knowledge_edges`。
- 查看现有 `knowledge_nodes` 与 `knowledge_edges`；记录基础 `change_events`。

## 重要限制

1. **目前没有 LLM 关系发现**。这是审核界面和手动关系建立原型，V0.2.2 的候选关系自动生成仍待实现。
2. 本版各数据库写入是顺序 REST 操作，**不具备跨表事务原子性**。若知识节点写入成功但审核状态更新失败，需人工检查；不要盲目重复审批。
3. 不会进行 Git 同步。数据库已审核状态与私有 Markdown 快照同步将在后续版本实现。
4. 对来源的追踪以 metadata 记录为主，尚不提供证据页码原文自动定位。
5. 默认 `external` + `external`；不能因为上传材料就把知识标记为自己已掌握。如需标为 current/verified，请确保确实有实际学习或实践证据。
6. 只显示前 100 条待审、500 个节点/关系。不是完整检索系统。
7. 本地网页有 Streamlit 会话状态，不是互联网部署版本；会话过期可退出并重新登录。
8. 不要把包含真实用户知识、个人凭据的截图、配置文件提交到公开 GitHub 仓库。

## 重要注意：正式知识 ID 与协议

采用 `KNW-YYYYMMDD-随机数字` 和 `REL-YYYYMMDD-随机数字`，与现有数据库校验兼容。节点类型严格限定为初始九类，关系严格限定为初始十二类。

## 可选后续工作

- 引入 AI 候选关系提取、合并与正式审核队列；补充支持关系证据定位。
- 在 Supabase 使用经权限校验的 RPC 完成多表原子审批、审计事件和幂等锁。
- 给 `change_events` 强化服务端可信性，并实现私有 vault Git 同步队列与失败重试。
