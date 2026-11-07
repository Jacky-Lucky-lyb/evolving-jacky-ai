"""Run: streamlit run app/review_ui.py --server.address 127.0.0.1"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
sys.path.insert(0,str(Path(__file__).parent))
from review_core import NODE_TYPES,NODE_SPACES,NODE_STATUSES,RELATION_TYPES,potential_duplicates,clean_node,clean_edge
from supabase_api import Api

st.set_page_config(page_title='Evolving Self · Review Center',page_icon='🧠',layout='wide')
st.title('Evolving Self AI · 知识审核中心')
st.caption('V0.2.2 本地原型 · 所有操作使用你的 Supabase Auth 身份 · 不调用模型 API')

if 'api' not in st.session_state:
    st.session_state.api=None

if st.session_state.api is None:
    with st.form('login'):
        url=st.text_input('Supabase Project URL',value=os.getenv('SUPABASE_URL',''))
        key=st.text_input('Publishable / anon Key',value=os.getenv('SUPABASE_PUBLISHABLE_KEY',''),type='password')
        email=st.text_input('测试用户邮箱')
        password=st.text_input('测试用户密码',type='password')
        submit=st.form_submit_button('登录并加载审核队列',type='primary')
    if submit:
        try:
            api=Api(url,key);api.login(email,password)
            st.session_state.api=api;st.rerun()
        except Exception as ex:st.error(str(ex))
    st.stop()
api=st.session_state.api
col1,col2=st.columns([4,1])
col1.success('已通过普通用户身份登录（不使用 service_role）')
if col2.button('退出登录'):
    st.session_state.api=None;st.rerun()

try:
    proposals=api.list('review_queue',{'select':'id,proposal_type,payload,status,source_ref,created_at','status':'eq.pending','order':'created_at.asc','limit':'100'})
    nodes=api.list('knowledge_nodes',{'select':'id,title,node_type,knowledge_space,status,metadata','order':'created_at.desc','limit':'500'})
    sources=api.list('sources',{'select':'id,title','order':'created_at.desc','limit':'500'})
except Exception as ex:
    st.error('读取失败：'+str(ex));st.stop()
source_names={s['id']:s['title'] for s in sources}

tab1,tab2,tab3,tab4=st.tabs(['候选节点审核','人工创建候选关系','当前图谱','自动关系发现'])
with tab1:
    node_proposals=[p for p in proposals if p['proposal_type']=='node']
    st.write(f'待审核节点：**{len(node_proposals)}**（只展示最新 100 条待审记录）')
    for p in node_proposals:
        payload=p.get('payload') or {}
        with st.expander(f"{payload.get('title','未命名')} · {p['id'][:8]}"):
            source_id=p.get('source_ref') or payload.get('source_id')
            st.caption('资料来源：'+source_names.get(source_id,source_id or '未知'))
            evidence=payload.get('evidence_quote','')
            st.write('原文证据：',evidence or '（未提供）')
            with st.form('review_'+p['id']):
                title=st.text_input('节点标题',value=payload.get('title',''),key='title_'+p['id'])
                type_default=payload.get('node_type','CONCEPT')
                ntype=st.selectbox('节点类型',NODE_TYPES,index=NODE_TYPES.index(type_default) if type_default in NODE_TYPES else 2,key='type_'+p['id'])
                space=st.selectbox('知识空间',NODE_SPACES,index=1,key='space_'+p['id'],help='导入资料默认 external；不能自动认定本人掌握')
                status_options=['external','hypothesized','observed','verified','disputed','obsolete']
                status=st.selectbox('知识状态',status_options,key='status_'+p['id'],help='选择与知识空间一致的状态：external 对应 external；hypothetical 对应 hypothesized')
                note=st.text_area('审核依据 / 说明',value=payload.get('rationale',''),key='note_'+p['id'])
                matches=potential_duplicates(title,nodes)
                if matches:
                    st.warning('可能重复：'+ '；'.join(f"{m['title']} ({score:.0%})" for score,m in matches))
                    st.caption('请先核对已有节点：本版不会自动合并。若重复请拒绝并保留理由。')
                action=st.radio('决定',['保持待审','批准新节点','拒绝','标记需要修改'],horizontal=True,key='action_'+p['id'])
                confirm=st.form_submit_button('保存此项审核')
            if confirm:
                try:
                    if action=='批准新节点':
                        if matches:raise ValueError('存在疑似重复节点，请先人工核查；当前不允许直接批准重复项')
                        data=clean_node(ntype,title,status,space,source_id,evidence,note)
                        api.create('knowledge_nodes',data)
                        new_status='approved'
                    elif action=='拒绝':new_status='rejected'
                    elif action=='标记需要修改':new_status='needs_revision'
                    else:new_status='pending'
                    if new_status!='pending':
                        api.update('review_queue',p['id'],{'status':new_status,'reviewed_at':datetime.now(timezone.utc).isoformat()}, {'status':'eq.pending'})
                        try:api.create('change_events',{'event_type':'review_node_'+new_status,'entity_id':data['id'] if action=='批准新节点' else str(p['id']), 'payload':{'proposal_id':str(p['id']),'title':title,'source_id':source_id}})
                        except Exception:st.warning('审核状态已保存，但审计事件写入失败，请记录此次操作并检查配置')
                    st.success('审核完成');st.rerun()
                except Exception as ex:st.error('未完成：'+str(ex))

with tab2:
    st.info('V0.2.2 当前提供人工提出关系候选；AI 关系自动发现与合并建议将在后续迭代加入。')
    if len(nodes)<2:st.warning('至少需要两个已批准的知识节点，才能创建关系')
    else:
        names={n['id']:f"{n['title']} · {n['id']}" for n in nodes}
        ids=list(names)
        with st.form('edge'):
            src=st.selectbox('起始节点',ids,format_func=lambda x:names[x])
            rtype=st.selectbox('关系类型',RELATION_TYPES)
            dst=st.selectbox('目标节点',ids,index=1,format_func=lambda x:names[x])
            source=st.selectbox('证据来源（可不选）',['']+list(source_names),format_func=lambda x:source_names.get(x,'暂未指定来源'))
            note=st.text_area('为什么成立？证据位置或说明')
            approved=st.checkbox('我已检查方向、语义和证据；确认将关系写入正式图谱')
            go=st.form_submit_button('批准并创建关系',type='primary',disabled=not approved)
        if go:
            try:
                if not note.strip():raise ValueError('请填写关系成立依据')
                edge=clean_edge(src,rtype,dst,source,note)
                api.create('knowledge_edges',edge)
                try:api.create('change_events',{'event_type':'review_edge_approved','entity_id':edge['id'],'payload':{'from':src,'to':dst,'relation':rtype}})
                except Exception:st.warning('关系写入成功，但审计事件写入失败')
                st.success('关系已创建：'+edge['id']);st.rerun()
            except Exception as ex:st.error('创建失败：'+str(ex))
with tab3:
    st.write('当前知识节点：',len(nodes))
    st.dataframe([{k:n.get(k) for k in ('id','title','node_type','knowledge_space','status')} for n in nodes],hide_index=True)
    try:
        edges=api.list('knowledge_edges',{'select':'id,from_node_id,relation_type,to_node_id,review_status','limit':'500'})
        st.write('当前知识关系：',len(edges))
        st.dataframe(edges,hide_index=True)
    except Exception as ex:st.warning('读取关系失败：'+str(ex))
st.caption('限制：当前不做自动 Git 同步、自动关系发现、批量事务审批；登录会话仅用于本地运行期间。')

with tab4:
    from relation_tab import render
    render(api,nodes,sources,proposals)
