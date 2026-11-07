#!/usr/bin/env python3
"""Add-on CLI. Reuses v0.2.1 upload function and storage path; never approves nodes."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from semantic_extraction import preview
from model_providers import load_config, make_provider


def main(argv=None):
    parser=argparse.ArgumentParser(description='Evidence-checked AI node suggestions. Preview by default.')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file')
    group.add_argument('--text')
    parser.add_argument('--mode',choices=('preview','upload'),default='preview')
    parser.add_argument('--provider', choices=('deepseek','openai','custom'), default='deepseek')
    parser.add_argument('--model', default=None, help='Override the selected provider model')
    parser.add_argument('--max-chunks',type=int,default=6)
    args=parser.parse_args(argv)
    try:
        from ingest_knowledge import load_text, stage
        text,raw,filename,mime=load_text(args.file,args.text)
        config=load_config(args.provider, args.model)
        print(f'Using provider={config.name}, model={config.model}; input will be sent to that provider.', file=sys.stderr)
        result=preview(text,make_provider(config),args.max_chunks)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if args.mode=='preview':
            print('PREVIEW ONLY: no database/storage changes.')
            return 0
        if not result['candidates']:
            print('No acceptable evidence-backed candidates. Upload cancelled to avoid empty staging.')
            return 0
        url=os.environ.get('SUPABASE_URL','').strip()
        key=os.environ.get('SUPABASE_PUBLISHABLE_KEY','').strip()
        if not(url.startswith('https://') and key):
            raise ValueError('Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY')
        email=os.environ.get('SUPABASE_EMAIL','').strip() or input('Supabase Auth email: ').strip()
        stage(text,raw,filename,mime,filename,result['candidates'],url,key,email)
        print('All candidates are pending; no personal knowledge claims have been approved.')
        return 0
    except (ValueError,RuntimeError,OSError,ImportError,KeyError) as exc:
        print('ERROR:',str(exc),file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
