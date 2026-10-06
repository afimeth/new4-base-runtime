"""Verify measured source binding and derive a readable evidence projection."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluate import source_hashes
from runtime import ROOT, digest


def verify(report):
    expected={'schema','timestamp','environment','source_commit_at_run','source_hashes','scope','planner','model_calls','provider_cost_usd','semantic_accuracy','human_usability','independent_review','cases','passed','total','status','process_kill','receipt_hash'}
    if set(report)!=expected or report['schema']!='evaluation/1':raise ValueError('REPORT_SCHEMA_MISMATCH')
    if digest({k:v for k,v in report.items() if k!='receipt_hash'})!=report['receipt_hash']:raise ValueError('REPORT_HASH_MISMATCH')
    if report['source_hashes']!=source_hashes():raise ValueError('SOURCE_BINDING_MISMATCH')
    if not report['cases'] or report['total']!=len(report['cases']) or report['passed']!=sum(c['status']=='PASS' for c in report['cases']):raise ValueError('CASE_COUNT_MISMATCH')
    names=set()
    for case in report['cases']:
        if case['id'] in names or case['status'] not in ('PASS','FAIL','ERROR') or not isinstance(case['elapsed_ms'],(int,float)) or case['elapsed_ms']<0:raise ValueError('INVALID_CASE')
        names.add(case['id'])
    if report['status']!='PASS' or report['passed']!=report['total']:raise ValueError('EVALUATION_FAILED')
    if any(report[k] is not None for k in ('semantic_accuracy','human_usability','independent_review')):raise ValueError('UNMEASURED_FIELD_PROMOTED')
    methods={n.name for n in ast.walk(ast.parse((ROOT/'tests/test_workflow.py').read_text(encoding='utf8'))) if isinstance(n,ast.FunctionDef)}
    claims=json.loads((ROOT/'contracts/claims.json').read_text(encoding='utf8'))
    for claim in claims['claims']:
        for test in claim.get('tests',[claim['test']] if 'test' in claim else []):
            if test not in methods or not any(c.endswith('.'+test) for c in names):raise ValueError('CLAIM_TEST_NOT_MEASURED')
        for code in claim.get('code',[]):
            if code not in report['source_hashes']:raise ValueError('CLAIM_CODE_NOT_BOUND')
    return True


def project(report):
    verify(report)
    lines=['# Measured evidence','','Generated from the evaluation JSON. Do not edit this projection by hand.','',
        f"Run: {report['timestamp']}. Environment: {report['environment']['os']}, Python {report['environment']['python']}, SQLite {report['environment']['sqlite']}.",'',
        f"Result: **{report['passed']}/{report['total']} fixture scenarios passed**. This is not a production task-success rate.",'',
        f"Source commit at run: `{report['source_commit_at_run']}`. Exact tested source bytes are bound by the JSON source hash map.",'',
        '| Scenario | Outcome | Elapsed ms |','|---|---|---:|']
    lines += [f"| {c['id'].rsplit('.',1)[-1]} | {c['status']} | {c['elapsed_ms']:.3f} |" for c in report['cases']]
    lines += ['', 'Times include fixture setup, execution and cleanup; subprocess and HTTP scenarios are not retrieval latency benchmarks.','',
        'Provider calls: 0. Provider cost: $0. Semantic accuracy: UNKNOWN. Human usability: UNKNOWN. Independent review: UNKNOWN.','',
        'Real OS-process termination was exercised. Power failure and distributed effects were not. Receipt hash checking does not provide a signature or external anchor.','',
        f"Report receipt hash: `{report['receipt_hash']}`."]
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',default='evidence/local-eval.json');p.add_argument('--output',default='docs/EVIDENCE.md');p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    report=json.loads(Path(a.report).read_text(encoding='utf8'));verify(report)
    if not a.verify_only:Path(a.output).write_text(project(report),encoding='utf8',newline='\n')
    print(json.dumps({'status':'VERIFIED_SOURCE_BOUND_FIXTURE_REPORT','receipt_hash':report['receipt_hash']}))


if __name__=='__main__':main()
