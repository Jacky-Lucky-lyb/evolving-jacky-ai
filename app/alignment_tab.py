"""Streamlit tab for safe, explicit duplicate suggestions and a reuse review queue.

Uses existing Supabase review_queue rows. V0.2.4 stages a merge proposal;
source-to-node linking awaits the transactional v0.2.5 migration.
"""
from __future__ import annotations
from datetime import datetime,timezone
import streamlit as st
from entity_alignment import suggest_matches, build_reuse_proposal


def render(api, nodes, sources, proposals):
    st.subheader('语义匹配与重复节点检查 · V0.2.4')
    st.caption('仅提出复用已有节点的候选建议，不会直接合并或改变已有知识。')
    st.info('当前为离线匹配（无需 API）：名称、别名、明确缩写及相似度。跨语言和复杂语义匹配需后续接入模型并人工复核。')
    if len(nodes)>=500:
        st.warning('已读取的节点达到页面上限 500，匹配结果可能不完整；请勿据此认定没有重复。')
    pending_nodes=[p for p in proposals if p.get('proposal_type')=='node']
    pending_merges=[p for p in proposals if p.get('proposal_type')=='merge']
    known_pending={str(m.get('payload',{}).get('candidate_review_id')) for m in pending_merges}
    sources_set={s['id'] for s in sources}
    st.write(f'待检查节点：**{len(pending_nodes)}** · 待复核复用建议：**{len(pending_merges)}**')
    for p in pending_nodes:
        payload=p.get('payload') or {}
        title=payload.get('title','(untitled)')
        with st.expander(f'新候选：{title}'):
            items=suggest_matches(payload,nodes)
            if not items:
                st.write('没有找到明显匹配。注意：结果仅限于已加载的节点和当前名称规则。')
                continue
            st.dataframe([{'已有节点':x['node_title'],'相似度':x['score'],'原因':x['reason'],
                           '知识空间一致':x['same_knowledge_space'],'建议':x['action']} for x in items],hide_index=True)
            if str(p['id']) in known_pending:
                st.info('这条候选已有待审核的复用建议，请先处理该建议。')
                continue
            options=[x for x in items if x['action']=='review_reuse']
            if not options:
                st.warning('没有可以直接进入复用审核的匹配；需要人工比较语义与知识空间。')
                continue
            with st.form('reuse_'+str(p['id'])):
                chosen=st.selectbox('推荐复用的已有节点',options,
                                    format_func=lambda x:f"{x['node_title']} · {x['node_id']} ({x['reason']})")
                note=st.text_area('为什么认为是同一概念？（必填）',value=f"候选 {title} 与已有 {chosen['node_title']} 可能表示同一概念；需要二次审核。")
                submit=st.form_submit_button('提交二次审核（不会修改正式节点）')
            if submit:
                try:
                    src=p.get('source_ref') or payload.get('source_id')
                    if src not in sources_set: raise ValueError('来源记录未找到，请先检查 sources 表')
                    target=next(n for n in nodes if n['id']==chosen['node_id'])
                    merge=build_reuse_proposal(p,target,src,note)
                    api.create('review_queue',merge)
                    st.success('已新增 merge 类型待审核记录，原候选节点仍然保持 pending。')
                    st.rerun()
                except Exception as ex: st.error('提交失败：'+str(ex))
    st.divider()
    st.subheader('待审核的复用建议')
    for m in pending_merges:
        payload=m.get('payload') or {}
        tid=payload.get('target_node_id')
        target=next((n for n in nodes if n['id']==tid),None)
        with st.expander(f"{payload.get('candidate_title')} → {target['title'] if target else tid}"):
            st.write('原文证据：',payload.get('evidence_quote',''))
            st.write('审核意见：',payload.get('rationale',''))
            st.caption('V0.2.4 不执行跨表合并或自动更新证据，正式复用审批需待 v0.2.5 的原子写入实现。')
            if st.button('拒绝这项复用建议',key='reject_merge_'+str(m['id'])):
                try:
                    updated=api.update('review_queue',m['id'],{'status':'rejected','reviewed_at':datetime.now(timezone.utc).isoformat()}, {'status':'eq.pending'})
                    if not updated: raise RuntimeError('审核记录未更新；请刷新')
                    st.rerun()
                except Exception as ex: st.error(str(ex))
    st.caption('请勿将手工录入的个人掌握状态与 external 资料合并。')
