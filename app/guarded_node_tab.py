"""Node review for Migration 0006. All decisions are atomic, authenticated RPC calls."""
import streamlit as st
from review_core import NODE_TYPES, potential_duplicates


def render(api, proposals, nodes, sources):
    source_names = {s['id']: s.get('title',s['id']) for s in sources}
    node_proposals = [p for p in proposals if p.get('proposal_type') == 'node']
    merge_candidates = {str(p.get('payload',{}).get('candidate_review_id'))
                        for p in proposals if p.get('proposal_type') == 'merge' and p.get('status') == 'pending'}
    active_nodes = [n for n in nodes if n.get('status') != 'obsolete']
    st.write(f'待审核节点：**{len(node_proposals)}**')
    for p in node_proposals:
        payload = p.get('payload') or {}
        rid = str(p['id'])
        with st.expander(f"{payload.get('title','未命名')} · {rid[:8]}"):
            sid = p.get('source_ref') or payload.get('source_id')
            st.caption('资料来源：'+source_names.get(sid,sid or '未知'))
            st.write('原文证据：', payload.get('evidence_quote') or '（无）')
            blocked = rid in merge_candidates
            if blocked:
                st.warning('存在待审复用建议：必须先去「来源证据/安全复用」批准，或在「语义匹配/去重」拒绝复用建议。')
            with st.form('node_guard_'+rid):
                title = st.text_input('节点标题',value=payload.get('title',''))
                dtype = payload.get('node_type','CONCEPT')
                node_type = st.selectbox('节点类型',NODE_TYPES,index=NODE_TYPES.index(dtype) if dtype in NODE_TYPES else 2)
                st.caption('此版本自动接入仅允许外部知识：external；不会自动宣称你已掌握。')
                note = st.text_area('审核意见',value=payload.get('rationale',''))
                matches = potential_duplicates(title,active_nodes)
                if matches:
                    st.warning('可能重复：'+ '；'.join(f"{n['title']} ({score:.0%})" for score,n in matches))
                action=st.radio('处理方式',['保持待审','批准新节点','拒绝','标记需要修改'],horizontal=True)
                submit=st.form_submit_button('保存审核',disabled=blocked)
            if submit:
                try:
                    if action == '保持待审':
                        st.info('未进行修改');continue
                    if action == '批准新节点' and matches:
                        raise ValueError('疑似重复节点：请先检查复用匹配，不要直接批准新建。')
                    result=api.rpc('review_node_proposal',{
                        'p_review_id':rid,
                        'p_action':{'批准新节点':'approve','拒绝':'reject','标记需要修改':'needs_revision'}[action],
                        'p_title':title,'p_node_type':node_type,
                        'p_space':'external','p_status':'external','p_note':note})
                    st.success('数据库原子审核完成：'+str(result));st.rerun()
                except Exception as exc:
                    st.error('审批失败（未部分创建节点）：'+str(exc))
