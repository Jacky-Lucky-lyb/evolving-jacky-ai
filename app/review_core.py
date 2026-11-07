"""Pure validation and matching for Evolving Self AI review workflow."""
import re
import secrets
from datetime import datetime, timezone

NODE_TYPES = ('PERSON','GOAL','CONCEPT','SKILL','PROJECT','EXPERIENCE','BELIEF','DECISION','SOURCE')
RELATION_TYPES = ('HAS_GOAL','KNOWS','HAS_SKILL','REQUIRES','PREREQUISITE_OF','APPLIES','PART_OF','DERIVED_FROM','SUPPORTS','CONTRADICTS','MOTIVATED_BY','REVISED_BY')
NODE_SPACES = ('current','external','hypothetical')
NODE_STATUSES = ('observed','verified','external','hypothesized','disputed','obsolete')

def make_id(prefix):
    return f'{prefix}-{datetime.now(timezone.utc):%Y%m%d}-{secrets.randbelow(10**12):012d}'

def canonical(s):
    return re.sub(r'\s+', ' ',str(s)).strip().casefold()

def potential_duplicates(title,nodes):
    """Deterministic candidate matches, not automatic merges."""
    import difflib
    label=canonical(title)
    return sorted([(difflib.SequenceMatcher(None,label,canonical(n.get('title',''))).ratio(),n)
                   for n in nodes if label and difflib.SequenceMatcher(None,label,canonical(n.get('title',''))).ratio()>=0.76],
                  key=lambda item:-item[0])[:5]

def clean_node(node_type,title,status,space,source_id,evidence,rationale):
    if node_type not in NODE_TYPES or space not in NODE_SPACES or status not in NODE_STATUSES:
        raise ValueError('Invalid node type/status/space')
    title=title.strip()
    if not title or len(title)>200:
        raise ValueError('Title must be 1–200 characters')
    if space == 'external' and status in ('verified','observed'):
        raise ValueError('External knowledge cannot be marked as verified personal knowledge')
    if space == 'hypothetical' and status != 'hypothesized':
        raise ValueError('Hypothetical knowledge must use hypothesized status')
    if status == 'verified' and node_type in ('SKILL','BELIEF','DECISION') and not evidence.strip():
        raise ValueError('Verified personal records require evidence')
    return {'id':make_id('KNW'), 'node_type':node_type,'title':title,
            'status':status,'knowledge_space':space,'privacy':'private',
            'metadata': {'source_id':source_id, 'evidence_quote':evidence[:1200], 'review_note':rationale[:1200], 'review_origin':'v0.2.2'}}

def clean_edge(from_id,relation,to_id,source_id=None,note=''):
    if relation not in RELATION_TYPES: raise ValueError('Unknown relation')
    if from_id == to_id: raise ValueError('Self-links are not allowed')
    if not from_id or not to_id: raise ValueError('Select two nodes')
    return {'id':make_id('REL'),'from_node_id':from_id,'relation_type':relation,
            'to_node_id':to_id,'evidence_source_id':source_id or None,
            'evidence_locator':note[:500] if note.strip() else None,
            'review_status':'approved','metadata': {'review_origin':'v0.2.2'}}
