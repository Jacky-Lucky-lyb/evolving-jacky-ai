"""V0.2.4: pure, conservative entity-resolution suggestions.

No API calls, database writes, automatic merges or ownership changes.
Use canonical titles, explicit abbreviations and known aliases first.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Mapping, Sequence

GENERIC = {'introduction','limitations','abstract','background','overview','conclusion','discussion','references','results','methodology','引言','概述','结论','局限性'}


def normalize(value: object) -> str:
    s = unicodedata.normalize('NFKC', str(value or '')).casefold()
    s = re.sub(r'[\u2010-\u2015_\-/]+', ' ', s)
    s = re.sub(r'[^\w\s\u4e00-\u9fff]', '', s, flags=re.UNICODE)
    return ' '.join(s.split())


def acronym(value: str) -> str | None:
    """Extract explicit acronyms, or initials from >=3-word phrases only.

    Never treat arbitrary single words as abbreviations.
    """
    text = str(value or '').strip()
    bracketed = re.search(r'\(([A-Z][A-Z0-9]{2,9})\)', text)
    if bracketed:
        return bracketed.group(1).casefold()
    if re.fullmatch(r'[A-Z][A-Z0-9]{2,9}', text):
        return text.casefold()
    clean = re.sub(r'\([^)]*\)', '', text)
    words = re.findall(r'[A-Za-z][A-Za-z0-9]*', clean)
    if len(words) >= 3 and all(len(w) > 1 for w in words):
        return ''.join(w[0] for w in words).casefold()
    return None


def aliases(node: Mapping) -> list[str]:
    md = node.get('metadata') or {}
    if not isinstance(md, dict):
        md = {}
    names = md.get('aliases') or []
    if not isinstance(names, list):
        names = []
    result = [str(node.get('title') or '')] + [str(a) for a in names if isinstance(a,str)]
    return [n for n in result if n.strip()]


def suggest_matches(candidate: Mapping, nodes: Sequence[Mapping], max_results=5) -> list[dict]:
    name = str(candidate.get('title') or '').strip()
    typ = candidate.get('node_type')
    space = candidate.get('knowledge_space', 'external')
    if not name or normalize(name) in GENERIC:
        return []
    key, abbr = normalize(name), acronym(name)
    matches = []
    for node in nodes:
        if typ and node.get('node_type') != typ:
            continue
        node_id = node.get('id')
        if not node_id:
            continue
        options = aliases(node)
        norm = [normalize(x) for x in options]
        is_exact = key in norm
        abbr_match = bool(abbr and any(acronym(x)==abbr for x in options))
        # Short abbreviations are only accepted if both sides explicitly encode an abbreviation.
        abbreviation_exact = bool(abbr and any(normalize(x)==abbr for x in options))
        if is_exact:
            score, reason = 1.0, 'same normalized name / alias'
        elif abbr_match or abbreviation_exact:
            score, reason = .98, 'matching explicit acronym'
        else:
            score = max((difflib.SequenceMatcher(None,key,txt).ratio() for txt in norm if txt),default=0)
            if score < .80:
                continue
            reason = 'similar wording; meaning must be checked'
        same_space = space == node.get('knowledge_space')
        matches.append({'node_id':node_id,'node_title':node.get('title',''),
                        'score':round(score,3),'reason':reason,
                        'same_knowledge_space':same_space,
                        'action':'review_reuse' if score>=.96 and same_space else 'manual_comparison'})
    return sorted(matches,key=lambda x:(-x['score'],x['node_title']))[:max_results]


def validate_evidence(candidate: Mapping) -> None:
    quote = str(candidate.get('evidence_quote') or '').strip()
    if len(quote) < 12:
        raise ValueError('Evidence quote must be at least 12 characters')
    if candidate.get('knowledge_space','external') != 'external':
        raise ValueError('This matching flow only imports external knowledge; personal claims need separate review')


def build_reuse_proposal(proposal: Mapping, target: Mapping, source_ref: str | None, note: str) -> dict:
    """Prepare a second-stage proposal; DOES NOT modify the existing node."""
    data = proposal.get('payload') or {}
    validate_evidence(data)
    if not source_ref:
        raise ValueError('Source ID is required to reuse an existing knowledge node')
    if not note.strip():
        raise ValueError('A reviewer explanation is required')
    if data.get('node_type') != target.get('node_type'):
        raise ValueError('Node types do not match')
    if target.get('knowledge_space') != 'external':
        raise ValueError('Cannot merge external material into a personal/hypothetical knowledge node')
    return {'proposal_type':'merge','source_ref':source_ref,'status':'pending',
            'payload':{'target_node_id':target['id'],'candidate_review_id':proposal['id'],
                       'candidate_title':data.get('title'), 'evidence_quote':data['evidence_quote'],
                       'rationale':note.strip()[:1000], 'source_id':source_ref,
                       'proposal_origin':'entity_alignment_v0.2.4'}}
