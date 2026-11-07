在现有 `app/supabase_api.py` 的 `Api` 类内新增以下方法（与 `list`、`create` 同一级缩进）：

```python
    def rpc(self, function_name, payload):
        if function_name != 'approve_node_reuse':
            raise ValueError('RPC function is not approved for this client')
        return self._req('/rest/v1/rpc/' + function_name, 'POST', payload)
```

在现有 `app/review_ui.py` 中，将：

```python
tab1,tab2,tab3,tab4,tab5=st.tabs([...])
```

替换为（原五个标签名称保持原样）：

```python
tab1,tab2,tab3,tab4,tab5,tab6=st.tabs(['候选节点审核','人工创建候选关系','当前图谱','自动关系发现','语义匹配/去重','来源证据/安全复用'])
```

文件末尾新增：

```python
with tab6:
    from evidence_merge_tab import render as render_evidence_merge
    render_evidence_merge(api, nodes, sources, proposals)
```

**不要覆盖你现有的 `review_ui.py`。** 上述增量改动可保留 V0.2.4 已正常工作的全部标签。
