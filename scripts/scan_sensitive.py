import re, sys, pathlib
PATTERNS = [r'浙江移动', r'zhejiang', r'移动公司', r'10\.\d+\.\d+\.\d+', r'192\.168\.', r'sk-[A-Za-z0-9]{16,}', r'[\w.]+@(?!example)[\w.]+\.(com|cn|net)']
ROOTS = ['dist', 'content', 'src']
hits = []
for r in ROOTS:
    for f in pathlib.Path(r).rglob('*'):
        if 'pagefind' in str(f) or 'node_modules' in str(f): continue
        if f.is_file() and f.suffix in ('.html', '.md', '.js', '.css', '.json'):
            try: t = f.read_text(encoding='utf-8', errors='ignore')
            except Exception: continue
            for pat in PATTERNS:
                for m in re.finditer(pat, t):
                    hits.append((str(f), pat, m.group(0)[:40]))
if hits:
    print('敏感词命中', len(hits))
    for h in hits[:20]: print(' ', h)
    sys.exit(1)
print('敏感词扫描：0 命中')
