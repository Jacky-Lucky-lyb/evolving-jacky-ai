"""Non-destructive, two-user Supabase Storage isolation smoke test.

Run with only project URL and publishable/anon key. Passwords are prompted
privately at runtime and are never written to disk.
"""
import os
import sys
import uuid
import getpass

try:
    from supabase import create_client
except ImportError:
    sys.exit('Missing dependency: run python3 -m pip install -r requirements.txt')

BUCKET = 'knowledge-sources'
PAYLOAD = b'Evolving Self AI test only. No personal content.\n'


def check(label, operation, should_succeed=True, validator=None):
    try:
        result = operation()
        if not should_succeed:
            print(f'[FAIL] {label}: operation did not raise an error (verify result manually: {str(result)[:120]})')
            return False
        if validator and not validator(result):
            print(f'[FAIL] {label}: unexpected result')
            return False
        print(f'[PASS] {label}')
        return True
    except Exception as exc:
        if should_succeed:
            print(f'[FAIL] {label}: {type(exc).__name__}: {str(exc)[:180]}')
            return False
        print(f'[PASS] {label}: request denied ({type(exc).__name__})')
        return True


def login(url, key, label):
    client = create_client(url, key)
    print(f'\n{label} login (credentials remain local):')
    email = input('Email: ').strip()
    password = getpass.getpass('Password: ')
    try:
        response = client.auth.sign_in_with_password({'email': email, 'password': password})
    finally:
        del password
    if not response.user or not response.session:
        raise RuntimeError(f'{label} has no authenticated session; check email confirmation')
    print(f'{label} authenticated (user UUID suffix: ...{str(response.user.id)[-6:]})')
    return client, str(response.user.id)


def main():
    print('Evolving Self AI - Storage isolation test (temporary text file only)')
    url = input('Supabase Project URL (https://xxxxx.supabase.co): ').strip().rstrip('/')
    key = getpass.getpass('Publishable/anon key (NOT service_role / secret key): ').strip()
    if not url.startswith('https://') or '.supabase.co' not in url:
        sys.exit('Invalid Project URL.')
    if not key or 'service_role' in key.lower() or key.startswith('sb_secret_'):
        sys.exit('Use only publishable or legacy anon key. Never use service_role/secret.')

    try:
        a, a_id = login(url, key, 'User A')
        b, b_id = login(url, key, 'User B')
    except Exception as exc:
        sys.exit(f'Login failed; no file tests were run: {type(exc).__name__}: {str(exc)[:200]}')
    if a_id == b_id:
        sys.exit('Both logins are the same user; use two different Auth accounts.')

    suffix = uuid.uuid4().hex
    a_path = f'{a_id}/security-tests/{suffix}.txt'
    b_path = f'{b_id}/security-tests/{suffix}.txt'
    print('\nRunning temporary object tests...')
    results = []
    created = False
    def own_upload():
        nonlocal created
        r = a.storage.from_(BUCKET).upload(a_path, PAYLOAD, {'content-type':'text/plain', 'upsert':'false'})
        created = True
        return r
    results.append(check('A uploads in A folder', own_upload))
    if not created:
        sys.exit('Cannot continue safely: own upload failed. Check RLS and login.')

    try:
        results.append(check('A downloads own file', lambda: a.storage.from_(BUCKET).download(a_path), validator=lambda x: x == PAYLOAD))
        results.append(check('B cannot download A file', lambda: b.storage.from_(BUCKET).download(a_path), should_succeed=False))
        results.append(check('A cannot upload into B folder', lambda: a.storage.from_(BUCKET).upload(b_path, PAYLOAD, {'content-type':'text/plain', 'upsert':'false'}), should_succeed=False))
        # Unauthorized remove may return an empty result without raising. Confirm original still exists instead.
        try:
            b.storage.from_(BUCKET).remove([a_path])
        except Exception:
            pass
        results.append(check('B cannot delete A file', lambda: a.storage.from_(BUCKET).download(a_path), validator=lambda x: x == PAYLOAD))
        anon_client = create_client(url, key)
        results.append(check('Anonymous cannot download A file', lambda: anon_client.storage.from_(BUCKET).download(a_path), should_succeed=False))
    finally:
        print('\nCleaning up temporary file using A account...')
        try:
            a.storage.from_(BUCKET).remove([a_path])
            print('Cleanup requested. Check Storage if any test failed.')
        except Exception as exc:
            print(f'Cleanup warning: {type(exc).__name__}: {str(exc)[:120]}')
            print('Manually remove security-tests object through authorized client if needed.')

    print(f'\nResult: {sum(results)}/{len(results)} checks passed.')
    if not all(results):
        sys.exit(1)
    print('All smoke tests passed; does not replace an independent security audit.')


if __name__ == '__main__':
    main()
