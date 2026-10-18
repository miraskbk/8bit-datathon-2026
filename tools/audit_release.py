"""Check tracked release files without printing secret values or private content."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path
from zipfile import ZipFile

PATTERNS = [
    rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    rb'gh[pousr]_[A-Za-z0-9]{20,}', rb'github_pat_[A-Za-z0-9_]{20,}',
    rb'AKIA[A-Z0-9]{16}', rb'sk-[A-Za-z0-9_-]{24,}',
    rb'/Users/[A-Za-z0-9_.-]+/',
]
PRIVATE_PARTS = {'runtime', 'local-evaluation', 'open', 'data', 'models', '.hf-cache'}
PRIVATE_SUFFIXES = {'.mov', '.mp4', '.avi', '.mkv', '.docx', '.xlsx', '.pem', '.key'}


def main():
    root = Path(__file__).resolve().parents[1]
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    issues = []
    checked = 0
    for name in filter(None, names):
        p = root / name
        if not p.exists():
            continue  # A tracked deletion pending the release commit.
        checked += 1
        if p.is_symlink() or set(p.relative_to(root).parts) & PRIVATE_PARTS or p.suffix.lower() in PRIVATE_SUFFIXES:
            issues.append(name)
        if p.name.startswith('.env') and p.name != '.env.example':
            issues.append(name)
        if p.suffix == '.pptx':
            with ZipFile(p) as archive:
                content = b'\n'.join(archive.read(n) for n in archive.namelist() if n.endswith(('.xml', '.rels')))
        else:
            content = p.read_bytes()
        if any(re.search(pattern, content) for pattern in PATTERNS):
            issues.append(name)
    if issues:
        raise SystemExit('Release audit failed for paths: ' + ', '.join(sorted(set(issues))))
    print(f'Release audit passed for {checked} tracked files. No private content was printed.')


if __name__ == '__main__':
    main()
