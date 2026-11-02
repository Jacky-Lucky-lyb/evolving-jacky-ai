#!/usr/bin/env python3
"""协议 v0.1 静态校验。安装依赖：pip install pyyaml。示例：python validate_graph.py --examples"""
from pathlib import Path
import argparse,json,re,sys,yaml
ROOT=Path(__file__).resolve().parents[1]
SCHEMA=yaml.safe_load((ROOT/'schemas'/'node_schema.yaml').read_text(encoding='utf-8'))
RS=yaml.safe_load((ROOT/'schemas'/'relation_schema.yaml').read_text(encoding='utf-8'))

def load_frontmatter(file):
    data=file.read_text(encoding='utf-8')
    if not data.startswith('---\n'): return None
    m=re.search(r'^---\s*$',data[4:],re.M)
    if m is None: return None
    return yaml.safe_load(data[4:4+m.start()])

def validate(paths,relfile):
    errors=[];nodes={}
    for file in paths:
        try: d=load_frontmatter(file)
        except Exception as e:errors.append(f'{file}: YAML 错误 {e}');continue
        if d is None:continue
        if not isinstance(d,dict):errors.append(f'{file}: frontmatter 必须为对象');continue
        missing=set(SCHEMA['required'])-set(d)
        if missing:errors.append(f'{file}: 缺失字段 {sorted(missing)}');continue
        nid=d['id'];typ=d['type']
        if typ not in SCHEMA['node_types']:errors.append(f'{file}: 未知节点类型 {typ}');continue
        prefix=SCHEMA['node_types'][typ]['prefix']
        if not isinstance(nid,str) or not re.fullmatch(re.escape(prefix)+r'-\d{8}-\d{3}',nid):errors.append(f'{file}: ID 与类型前缀不匹配 {nid}')
        if nid in nodes:errors.append(f'{file}: 重复 ID {nid}')
        nodes[nid]=d
        for key in ('status','knowledge_space','privacy'):
            if d[key] not in SCHEMA[key]:errors.append(f'{file}: {key} 非法值 {d[key]}')
        if d['status']=='hypothesized' and d['knowledge_space']!='hypothetical':errors.append(f'{file}: hypothesized 必须位于 hypothetical')
        if d['knowledge_space']=='current' and d['status'] in ('external','hypothesized'):errors.append(f'{file}: current 不接受 external/hypothesized')
        if not isinstance(d['source_ids'],list):errors.append(f'{file}: source_ids 必须为数组')
        if 'learning_status' in d and d['learning_status'] not in SCHEMA['learning_status']:errors.append(f'{file}: learning_status 非法')
    for nid,d in nodes.items():
        for sid in d.get('source_ids',[]):
            if sid not in nodes:errors.append(f'{nid}: 缺失来源节点 {sid}')
            elif nodes[sid]['type']!='SOURCE':errors.append(f'{nid}: source_ids 只能指向 SOURCE')
    try:rels=json.loads(relfile.read_text(encoding='utf-8'))
    except Exception as e:errors.append(f'{relfile}: JSON 错误 {e}');rels=[]
    seen=set();edge_ids=set()
    for i,r in enumerate(rels):
        label=f'{relfile} 第{i+1}条关系'
        if not isinstance(r,dict):errors.append(label+': 必须是对象');continue
        missing=set(RS['required'])-set(r)
        if missing:errors.append(label+f': 缺少 {sorted(missing)}');continue
        if r['id'] in edge_ids:errors.append(label+': 关系 ID 重复')
        edge_ids.add(r['id'])
        if not isinstance(r['id'],str) or not re.fullmatch(r'REL-\d{8}-\d{3}',r['id']):errors.append(label+': 关系 ID 格式非法')
        a,b,k=r['from'],r['to'],r['relation']
        if a not in nodes or b not in nodes:errors.append(label+': 关系端点不存在');continue
        if k not in RS['relations']:errors.append(label+f': 关系类型未定义 {k}');continue
        rule=RS['relations'][k]
        if nodes[a]['type'] not in rule['source_types'] or nodes[b]['type'] not in rule['target_types']:errors.append(label+': 起点/终点类型非法')
        if r['review_status'] not in RS['review_status']:errors.append(label+': 审核状态非法')
        if r['review_status']=='rejected':errors.append(label+': 已拒绝关系不得写入关系数据')
        if relfile.name=='relations.json' and r['review_status']!='approved':errors.append(label+': 正式关系必须是 approved')
        triple=(a,k,b)
        if triple in seen:errors.append(label+': 重复三元组，应合并证据')
        seen.add(triple)
        evidence=r['evidence']
        if not isinstance(evidence,list) or not evidence:errors.append(label+': 缺失证据列表');continue
        for ev in evidence:
            if not isinstance(ev,dict) or not ev.get('source_id') or not ev.get('locator'):errors.append(label+': 证据必须包含 source_id 与 locator');continue
            if ev['source_id'] not in nodes or nodes[ev['source_id']]['type']!='SOURCE':errors.append(label+': 证据来源不存在或不是 SOURCE')
    return errors,len(nodes),len(rels)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--examples',action='store_true');args=parser.parse_args()
    if args.examples:paths=list((ROOT/'examples').glob('*.md'));rel=ROOT/'examples'/'example_relations.json'
    else:paths=[p for p in ROOT.rglob('*.md') if 'examples' not in p.relative_to(ROOT).parts];rel=ROOT/'relations.json'
    errors,n,e=validate(paths,rel)
    print(f'扫描节点 {n} / 关系 {e} / 错误 {len(errors)}')
    if errors:
        for x in errors:print('✗',x)
        sys.exit(1)
    print('✓ 结构校验通过（不代表来源内容真实性已人工核验）')
