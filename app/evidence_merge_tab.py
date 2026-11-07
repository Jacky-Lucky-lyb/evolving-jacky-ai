"""V0.2.5: review pending merge proposals using one atomic PostgREST RPC."""
from __future__ import annotations
import streamlit as st

def render(api, nodes, sources, proposals):
    st.subheader('多来源证据与安全复用 · V0.2.5')
    st.caption('只有通过复用审核，才能为已有节点新增证据；不改变原节点的知识掌握状态。')
    by_id = {n['id']: n for n in nodes}
    source_names = {s['id']: s['title'] for s in sources}
    merges = [p for p in proposals if p.get('proposal_type') == 'merge']
    st.write(f'待审核复用建议：**{len(merges)}**')
    for m in merges:
        payload = m.get('payload') or {}
        target = by_id.get(payload.get('target_node_id'))
        label = f"{payload.get('candidate_title','未命名')} → {target['title'] if target else '未找到目标'}"
        with st.expander(label):
            st.write('来源：',source_names.get(m.get('source_ref'),m.get('source_ref','未知')))
            st.write('引用：',payload.get('evidence_quote',''))
            st.write('匹配理由：',payload.get('rationale',''))
            if not target:
                st.error('目标节点未加载。请检查节点是否存在及当前页面 500 条上限。')
                continue
            st.warning('复用会批准原候选，并为已有节点新增来源证据；不会改变节点名称、知识空间或掌握状态。')
            confirm=st.checkbox('我已核对同一概念、原始引用和资料来源',key='merge_ok_'+str(m['id']))
            if st.button('批准复用并原子保存',key='approve_merge_'+str(m['id']),disabled=not confirm):
                try:
                    result=api.rpc('approve_node_reuse',{'p_merge_id':str(m['id'])})
                    st.success('事务成功：'+str(result))
                    st.rerun()
                except Exception as exc:
                    st.error('未完成审批；数据库事务应已回滚，请核对后再试：'+str(exc))
    st.divider()
    st.subheader('现有节点的来源证据')
    if not nodes:
        st.info('暂无节点');return
    chosen=st.selectbox('选择知识节点',nodes,format_func=lambda n:f"{n['title']} · {n['id']}",key='evidence_node')
    if st.button('加载来源证据',key='load_evidence'):
        try:
            evidence=api.list('knowledge_node_evidence',{'select':'id,source_id,evidence_quote,evidence_locator,created_at',
                      'node_id':'eq.'+chosen['id'],'order':'created_at.desc','limit':'100'})
            if evidence:
                for item in evidence: item['source_title']=source_names.get(item.get('source_id'),item.get('source_id'))
                st.dataframe(evidence,hide_index=True)
            else: st.info('暂无已记录的复用证据。历史节点的旧证据暂未回填。')
        except Exception as exc: st.error('读取失败：'+str(exc))
    st.caption('Git 版本同步尚未执行。批准后仅创建 queued 状态的 sync_jobs，不能视为已提交 GitHub。')
