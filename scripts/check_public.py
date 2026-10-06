"""Fail closed on invalid UTF-8, private paths, likely credentials or binary files."""
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf8').split('\0')
    forbidden=[re.compile(r'(?i)(?:C:[/\\]Users[/\\]|personal-alexandria-transcripts|MSI-DONDI)'),
        re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
        re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{24,}|AKIA[A-Z0-9]{16})\b'),
        re.compile(r'(?i)(?:password|api_key|access_token)\s*[:=]\s*[\x22\x27][^\x22\x27\s]{8,}[\x22\x27]')]
    problems=[]
    for path in filter(None,paths):
        if path.startswith('.state/') or Path(path).name=='.env':problems.append((path,'PRIVATE_PATH'));continue
        try:text=(ROOT/path).read_bytes().decode('utf8')
        except UnicodeDecodeError:problems.append((path,'NOT_UTF8'));continue
        if '\0' in text:problems.append((path,'BINARY_CONTENT'))
        # Pattern definitions are code, not discovered secrets. No values are printed.
        if path=='scripts/check_public.py':continue
        if any(pattern.search(text) for pattern in forbidden):problems.append((path,'PUBLIC_BOUNDARY_PATTERN'))
    for path,code in problems:print(code+': '+path)
    print('Public UTF-8 boundary: '+('FAIL' if problems else 'PASS'))
    return 1 if problems else 0


if __name__=='__main__':raise SystemExit(main())
