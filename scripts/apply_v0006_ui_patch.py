"""Run from repository root: python3 scripts/apply_v0006_ui_patch.py --check (or --apply)
Requires app/guarded_node_tab.py from this package. Keeps backup copies on apply.
"""
import argparse
from pathlib import Path
import re
import shutil


def patch_review(source):
    if 'from guarded_node_tab import render as render_guarded_nodes' in source:
        return source
    start = source.find('with tab1:')
    end = source.find('\nwith tab2:',start)
    if start < 0 or end < 0: raise ValueError('review_ui.py tab1/tab2 pattern not found; do not auto-patch')
    replacement = ('with tab1:\n'
                   '    from guarded_node_tab import render as render_guarded_nodes\n'
                   '    render_guarded_nodes(api, proposals, nodes, sources)\n')
    return source[:start]+replacement+source[end:]


def patch_alignment(source):
    old="updated=api.update('review_queue',m['id'],{'status':'rejected','reviewed_at':datetime.now(timezone.utc).isoformat()}, {'status':'eq.pending'})\n                    if not updated: raise RuntimeError('审核记录未更新；请刷新')"
    new="api.rpc('reject_merge_proposal', {'p_merge_id':str(m['id'])})"
    if new in source:return source
    if old not in source: raise ValueError('alignment_tab.py reject handler differs; manual review required')
    return source.replace(old,new)


def patch_api(source):
    # Replace existing whitelisted rpc, preserving the original method shape and indentation.
    old='if function_name != "approve_node_reuse":'
    new='if function_name not in ("approve_node_reuse", "review_node_proposal", "reject_merge_proposal", "review_edge_proposal"):'
    if new in source:return source
    if old not in source:raise ValueError('Api.rpc whitelist differs or is missing; edit manually')
    return source.replace(old,new)


def patch_relation(source):
    if "api.rpc('review_edge_proposal'" in source:return source
    start=source.find("                    if action=='批准关系':")
    end=source.find("                    st.success('操作完成');st.rerun()",start)
    if start < 0 or end < 0: raise ValueError('relation_tab.py review handler differs; manual review required')
    replacement=("                    if action!='保持待审':\n"
       "                        if action=='批准关系' and not note.strip():raise ValueError('必须填写依据')\n"
       "                        api.rpc('review_edge_proposal', {\n"
       "                            'p_review_id':str(p['id']),\n"
       "                            'p_action':'approve' if action=='批准关系' else 'reject',\n"
       "                            'p_relation_type':rtype,'p_note':note})\n")
    return source[:start]+replacement+source[end:]


def main():
    a=argparse.ArgumentParser();a.add_argument('--check',action='store_true');a.add_argument('--apply',action='store_true');args=a.parse_args()
    if args.check == args.apply: a.error('choose --check OR --apply')
    root=Path.cwd();spec=[('app/review_ui.py',patch_review),('app/alignment_tab.py',patch_alignment),('app/relation_tab.py',patch_relation),('app/supabase_api.py',patch_api)]
    outputs=[]
    for rel,fn in spec:
        p=root/rel
        if not p.exists():raise SystemExit(f'NOT FOUND: {p}')
        raw=p.read_text(encoding='utf-8');patched=fn(raw)
        compile(patched,rel,'exec')
        outputs.append((p,raw,patched))
        print(f"{'WILL CHANGE' if raw != patched else 'ALREADY OK'}: {rel}")
    if args.apply:
        for p,raw,patched in outputs:
            if raw!=patched:
                backup=p.with_suffix(p.suffix+'.pre0006.bak')
                if backup.exists():raise SystemExit(f'Backup already exists: {backup}. Move it first.')
                shutil.copy2(p,backup);p.write_text(patched,encoding='utf-8')
        print('Patched and saved. Backup *.pre0006.bak files created (do not commit backups).')
    else:print('Check-only: no files modified.')

if __name__=='__main__':main()
