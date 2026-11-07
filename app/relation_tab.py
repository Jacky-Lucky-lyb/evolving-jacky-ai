"""V0.2.2 relationship suggestion/review UI. Import from review_ui."""
import json
from datetime import datetime,timezone
import streamlit as st
from relation_discovery import explicit_candidates,ai_candidates,validate_suggestions
from review_core import RELATION_TYPES,clean_edge

def render(api,nodes,sources,proposals):
    st.subheader('关系自动发现与审核')
    st.caption('仅生成候选关系；AI 不会直接创建正式知识关系。源文本仅由你粘贴在这里，不会自动检索私人资料。')
    try:
        existing=api.list('knowledge_edges',{'select':'id,from_node_id,relation_type,to_node_id','limit':'1000'})
    except Exception as ex:
        st.error('关系表读取失败：'+str(ex));return
    label={n['id']:n['title'] for n in nodes}
    pending_edges=[p for p in proposals if p.get('proposal_type')=='edge']
    if pending_edges:
        st.write('待审核关系：',len(pending_edges))
    for p in pending_edges:
        data=p.get('payload') or {}
        frm=data.get('from_node_id');to=data.get('to_node_id');rel=data.get('relation_type')
        with st.expander(f"{label.get(frm,frm)} → {rel} → {label.get(to,to)}"):
            st.caption('证据：'+str(data.get('evidence_quote') or '缺失'))
            st.write('建议理由：',data.get('rationale') or '未提供')
            with st.form('approve_edge_'+p['id']):
                rtype=st.selectbox('关系类型',RELATION_TYPES,index=RELATION_TYPES.index(rel) if rel in RELATION_TYPES else 0)
                note=st.text_area('证据位置 / 审核说明',value=data.get('evidence_quote') or '')
                action=st.radio('决定',['保持待审','批准关系','拒绝'],horizontal=True)
                submitted=st.form_submit_button('保存审核')
            if submitted:
                try:
                    if action=='批准关系':
                        if frm not in label or to not in label:raise ValueError('关联节点不存在，请先处理节点')
                        if not note.strip():raise ValueError('必须填写依据')
                        if (frm,rtype,to) in {(e['from_node_id'],e['relation_type'],e['to_node_id']) for e in existing}:
                            raise ValueError('正式图谱已经存在同一关系')
                        edge=clean_edge(frm,rtype,to,p.get('source_ref'),note)
                        api.create('knowledge_edges',edge)
                        status='approved'
                    elif action=='拒绝':status='rejected'
                    else:status='pending'
                    if status!='pending':
                        updated=api.update('review_queue',p['id'],{'status':status,'reviewed_at':datetime.now(timezone.utc).isoformat()}, {'status':'eq.pending'})
                        if not updated:st.warning('关系可能已保存，但审核状态未确认；请刷新并检查，勿重复批准')
                    st.success('操作完成');st.rerun()
                except Exception as ex:st.error(str(ex))
    st.divider()
    st.subheader('发现新关系')
    st.write('当前有',len(nodes),'个节点。为控制成本与隐私，本版仅将已批准的节点标题用于候选分析。')
    source_choices={'（无关联来源）':None,**{s['title']+' · '+s['id']:s['id'] for s in sources}}
    source_label=st.selectbox('证据来源（请尽量选择）',list(source_choices))
    source_ref=source_choices[source_label]
    input_text=st.text_area('粘贴带有明确关系描述的原文（不建议粘贴隐私资料）',height=160,placeholder='Example: RAG uses embeddings. A project requires Python.')
    mode=st.radio('提议方式',['保守规则模式（无需 API）','AI 语义分析（需要 API Key）'],horizontal=True)
    api_key=''
    if mode.startswith('AI'):
        st.warning('调用外部模型会向 API 服务发送粘贴的文本和节点名称。仅在了解数据处理条款并同意后使用。')
        api_key=st.text_input('OpenAI API Key（本次会话使用，不保存至 Git）',type='password')
    if st.button('分析并生成候选关系',disabled=len(nodes)<2 or not input_text.strip()):
        try:
            if mode.startswith('AI'):
                raw=ai_candidates(nodes,input_text,api_key)
            else:raw=explicit_candidates(nodes,input_text)
            valid=validate_suggestions(raw,nodes,existing)
            # Avoid proposing edges that are already pending.
            pending={(p['payload'].get('from_node_id'),p['payload'].get('relation_type'),p['payload'].get('to_node_id')) for p in pending_edges}
            valid=[r for r in valid if (r['from_node_id'],r['relation_type'],r['to_node_id']) not in pending]
            st.session_state['candidate_edges']=valid
            st.success(f'得到 {len(valid)} 条候选关系。没有充分证据时返回 0 条是正常的。')
        except Exception as e:st.error('分析失败：'+str(e))
    for idx,edge in enumerate(st.session_state.get('candidate_edges',[])):
        with st.container(border=True):
            st.write(f"**{label.get(edge['from_node_id'])} → {edge['relation_type']} → {label.get(edge['to_node_id'])}**")
            st.caption(edge['evidence_quote'])
            st.write(edge.get('rationale',''))
            if st.button('加入待审核队列',key=f'queue_edge_{idx}'):
                try:
                    payload={**edge,'source_id':source_ref,'proposal_origin':'relation_discovery_v0.2.2'}
                    api.create('review_queue',{'proposal_type':'edge','payload':payload,'source_ref':source_ref,'status':'pending'})
                    st.success('已保存为候选关系，尚未写入正式图谱')
                    st.session_state['candidate_edges']=[x for j,x in enumerate(st.session_state['candidate_edges']) if j!=idx]
                    st.rerun()
                except Exception as ex:st.error('保存候选失败：'+str(ex))
