"""Two-user RLS and cross-owner graph-edge smoke test for Evolving Self AI.

Only creates temporary knowledge_nodes records and one intentionally rejected edge.
Uses publishable/anon key and ordinary authenticated sessions, never service_role.
"""
import getpass
import sys
import uuid
from datetime import datetime, timezone

try:
    from supabase import create_client
except ImportError:
    sys.exit('Install dependency: python3 -m pip install supabase')

TABLE = 'knowledge_nodes'
EDGE_TABLE = 'knowledge_edges'


def login(url, key, label):
    c = create_client(url, key)
    print(f'\n{label} login (password hidden):')
    email = input('Email: ').strip()
    pw = getpass.getpass('Password: ')
    try:
        response = c.auth.sign_in_with_password({'email': email, 'password': pw})
    finally:
        del pw
    if not response.user or not response.session:
        raise RuntimeError(f'{label} has no authenticated session')
    return c, str(response.user.id)


def check(label, fn):
    try:
        ok = bool(fn())
        
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {label}")

        return ok
    except Exception as exc:
        print(f'[FAIL] {label}: {type(exc).__name__}: {str(exc)[:180]}')
        return False


def denied_or_empty(fn):
    try:
        response = fn()
        return not (response.data or [])
    except Exception:
        return True


def get_node(client, node_id):
    return client.table(TABLE).select('id,owner_id,title').eq('id', node_id).execute().data or []


def main():
    print('Evolving Self AI - Database RLS isolation smoke test')
    url = input('Project URL (https://xxxxx.supabase.co): ').strip().rstrip('/')
    key = getpass.getpass('Publishable / anon key (never service_role): ').strip()
    if not url.startswith('https://') or '.supabase.co' not in url:
        sys.exit('Invalid Supabase project URL.')
    if not key or key.startswith('sb_secret_') or 'service_role' in key.lower():
        sys.exit('Use publishable key or legacy anon key only.')
    try:
        a, aid = login(url, key, 'User A')
        b, bid = login(url, key, 'User B')
    except Exception as exc:
        sys.exit(f'Login failed; no data tests performed: {type(exc).__name__}: {str(exc)[:180]}')
    if aid == bid:
        sys.exit('Two distinct user accounts are required.')

    stamp = datetime.now(timezone.utc).strftime('%Y%m%d')
    suffix = str(uuid.uuid4().int % 1000000000).zfill(9)
    a_id = f'TST-{stamp}-{suffix}'
    b_id = f'TST-{stamp}-{str((int(suffix)+1) % 1000000000).zfill(9)}'
    edge_id = f'REL-{stamp}-{suffix}'
    title = f'RLS test A {suffix}'
    results = []
    created_a = created_b = False
    print('\nTesting with temporary nodes (no personal content)...')
    try:
        def create_a():
            nonlocal created_a
            r = a.table(TABLE).insert({'id': a_id, 'node_type': 'CONCEPT', 'title': title}).execute()
            created_a = bool(r.data)
            return created_a
        results.append(check('A creates own knowledge node', create_a))
        if not created_a:
            sys.exit('A node creation failed. Stop and inspect table grants / RLS.')
        results.append(check('A reads own node', lambda: len(get_node(a, a_id)) == 1))
        results.append(check('B cannot read A node', lambda: denied_or_empty(lambda: b.table(TABLE).select('id').eq('id', a_id).execute())))
        results.append(check('Anonymous cannot read A node', lambda: denied_or_empty(lambda: create_client(url, key).table(TABLE).select('id').eq('id', a_id).execute())))
        results.append(check('B cannot update A node', lambda: denied_or_empty(lambda: b.table(TABLE).update({'title': 'UNAUTHORIZED UPDATE'}).eq('id', a_id).execute()) and get_node(a, a_id)[0]['title'] == title))
        results.append(check('B cannot delete A node', lambda: denied_or_empty(lambda: b.table(TABLE).delete().eq('id', a_id).execute()) and len(get_node(a, a_id)) == 1))

        def create_b():
            nonlocal created_b
            r = b.table(TABLE).insert({'id': b_id, 'node_type': 'CONCEPT', 'title': 'RLS test B'}).execute()
            created_b = bool(r.data)
            return created_b
        results.append(check('B creates own knowledge node', create_b))
        if created_b:
            results.append(check('A cannot link to B node', lambda: denied_or_empty(lambda: a.table(EDGE_TABLE).insert({'id': edge_id, 'from_node_id': a_id, 'to_node_id': b_id, 'relation_type': 'PART_OF', 'review_status': 'pending'}).execute())))
            # Ensure no edge was created even if API returned oddly.
            results.append(check('No cross-owner edge persisted', lambda: denied_or_empty(lambda: a.table(EDGE_TABLE).select('id').eq('id', edge_id).execute())))
    finally:
        print('\nCleaning temporary records using their owners...')
        for label, client, node_id, created in [('A', a, a_id, created_a), ('B', b, b_id, created_b)]:
            if not created:
                continue
            try:
                client.table(TABLE).delete().eq('id', node_id).execute()
                leftover = get_node(client, node_id)
                if leftover:
                    print(f'[WARN] {label} temporary node still exists: {node_id}')
                else:
                    print(f'{label} temporary node removed')
            except Exception as exc:
                print(f'[WARN] {label} cleanup failed: {type(exc).__name__}: {str(exc)[:140]}')
    print(f'\nResult: {sum(results)}/{len(results)} checks passed')
    if not all(results):
        sys.exit(1)
    print('All smoke tests passed. This does not replace a security audit.')


if __name__ == '__main__':
    main()
