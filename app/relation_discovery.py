"""Conservative relationship suggestions; proposals never directly create graph edges."""
import json
import re
from difflib import SequenceMatcher
from review_core import RELATION_TYPES

MAX_CANDIDATES = 20

def textnorm(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip().casefold()

def related_node_pairs(nodes, max_pairs=100):
    """Prioritize topic proximity; never claim a relation based only on similarity."""
    scored=[]
    for i,a in enumerate(nodes):
        for b in nodes[i+1:]:
            na=textnorm(a.get('title'));nb=textnorm(b.get('title'))
            if not na or not nb or na==nb:continue
            score=SequenceMatcher(None,na,nb).ratio()
            tokens_a=set(re.findall(r'\w+',na));tokens_b=set(re.findall(r'\w+',nb))
            overlap=len(tokens_a & tokens_b)/max(1,len(tokens_a | tokens_b))
            same_source=bool((a.get('metadata') or {}).get('source_id') and (a.get('metadata') or {}).get('source_id')==(b.get('metadata') or {}).get('source_id'))
            rank=score*.45+overlap*.35+(0.2 if same_source else 0)
            if rank>=.13:scored.append((rank,a,b))
    scored.sort(key=lambda x:-x[0])
    return [(a,b) for _,a,b in scored[:max_pairs]]

def explicit_candidates(nodes, source_text):
    """Generate candidates only for explicit short English definitional patterns.
    Most articles/languages produce zero suggestions; that is intentional.
    """
    if len(source_text)>100_000:source_text=source_text[:100_000]
    sentences=re.split(r'(?<=[.!?\n])\s+',source_text)
    names=[(n,textnorm(n.get('title'))) for n in nodes if n.get('title')]
    found=[];seen=set()
    patterns=[(re.compile(r'\b(is a (?:kind|type|form) of|is part of)\b',re.I),'PART_OF'),
              (re.compile(r'\b(requires|depends on)\b',re.I),'REQUIRES'),
              (re.compile(r'\b(uses|applies)\b',re.I),'APPLIES')]
    for sentence in sentences:
        s=textnorm(sentence)
        if not 12<=len(s)<=500:continue
        for pat,relation in patterns:
            for m in pat.finditer(s):
                left=s[:m.start()];right=s[m.end():]
                srcs=[n for n,name in names if len(name)>=3 and re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',left)]
                dsts=[n for n,name in names if len(name)>=3 and re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',right)]
                if len(srcs)!=1 or len(dsts)!=1:continue
                a,b=srcs[0],dsts[0]
                if a['id']==b['id']:continue
                key=(a['id'],relation,b['id'])
                if key in seen:continue
                seen.add(key)
                found.append({'from_node_id':a['id'],'relation_type':relation,'to_node_id':b['id'],
                              'evidence_quote':sentence.strip()[:500],
                              'rationale':'Rule-matched explicit wording; confirm meaning and context manually',
                              'method':'rule'})
                if len(found)>=MAX_CANDIDATES:return found
    return found

def validate_suggestions(raw,nodes,existing_edges=()):
    valid_ids={n['id'] for n in nodes}
    existing={(e['from_node_id'],e['relation_type'],e['to_node_id']) for e in existing_edges}
    output=[];seen=set()
    for row in raw:
        if not isinstance(row,dict):continue
        a=row.get('from_node_id');b=row.get('to_node_id');t=row.get('relation_type')
        evidence=str(row.get('evidence_quote') or '').strip()
        if a not in valid_ids or b not in valid_ids or a==b or t not in RELATION_TYPES:continue
        key=(a,t,b)
        if key in seen or key in existing:continue
        if len(evidence)<8:continue
        seen.add(key)
        output.append({'from_node_id':a,'relation_type':t,'to_node_id':b,
                       'evidence_quote':evidence[:500],
                       'rationale':str(row.get('rationale') or '')[:600],
                       'method':str(row.get('method') or 'ai')[:30]})
        if len(output)>=MAX_CANDIDATES:break
    return output

def ai_candidates(nodes,source_text,api_key,model='gpt-4.1-mini'):
    """Optional external API; user must consent to sharing source text with provider."""
    if not api_key or not api_key.startswith('sk-'):raise ValueError('Missing valid API key')
    import urllib.request,urllib.error
    schema_nodes=[{'id':n['id'],'title':n['title'],'type':n.get('node_type')} for n in nodes[:80]]
    prompt=("You propose candidate directed knowledge-graph edges. Only use node IDs provided. "
            "Use only these edge types: "+', '.join(RELATION_TYPES)+'. '
            "Only propose a relationship directly supported by a verbatim quote in the supplied source text. "
            "Never infer from topic similarity or co-occurrence. Never claim a person's knowledge or beliefs from external documents. "
            "When evidence is absent, return an empty array. Return only JSON object {'suggestions': "
            "[{'from_node_id':'...', 'relation_type':'...', 'to_node_id':'...', 'evidence_quote':'...', 'rationale':'...'}]}. "
            "Nodes: "+json.dumps(schema_nodes,ensure_ascii=False)+"\nSource:\n"+source_text[:12000])
    body=json.dumps({'model':model,'input':prompt,'max_output_tokens':1400},ensure_ascii=False).encode()
    request=urllib.request.Request('https://api.openai.com/v1/responses',data=body,
          headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=65) as response:result=json.load(response)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'AI request failed HTTP {e.code}; inspect API billing/model access') from e
    output=''.join(content.get('text','') for part in result.get('output',[]) for content in part.get('content',[]) if content.get('type')=='output_text')
    if output.startswith('```'):
        output=re.sub(r'^```(?:json)?\s*|\s*```$','',output.strip())
    try:parsed=json.loads(output)
    except json.JSONDecodeError as e:raise RuntimeError('Model did not return valid JSON; no changes made') from e
    return parsed.get('suggestions',[]) if isinstance(parsed,dict) else []
