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


tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "候选节点审核",
    "人工创建候选关系",
    "当前图谱",
    "自动关系发现",
    "语义匹配/去重",
    "来源证据/安全复用"
])
with tab1:
    from guarded_node_tab import render as render_guarded_nodes
    render_guarded_nodes(api, proposals, nodes, sources)

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

with tab5:
    from alignment_tab import render as render_alignment
    render_alignment(api,nodes,sources,proposals)

with tab6:
    from evidence_merge_tab import render as render_evidence_merge

    render_evidence_merge(
        api,
        nodes,
        sources,
        proposals
    )

