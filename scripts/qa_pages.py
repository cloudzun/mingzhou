"""逐页 QA：本地 dist 或线上站点，一页不落。"""
import re
import sys
import pathlib
import urllib.request

LOCAL = len(sys.argv) > 1 and sys.argv[1] == "local"
DIST = pathlib.Path("dist")
HOST = "https://www.cloudzun.com/mingzhou"

routes = [
    "/", "/handbook/00/", "/handbook/01/", "/handbook/02/", "/handbook/03/",
    "/demo/fruitlab/", "/wizard/rag/", "/wizard/sql/", "/wizard/contract/",
    "/wizard/fruitlab/", "/wizard/project/", "/kit/", "/search/", "/print/", "/v1.0/",
]

def fetch(route):
    if LOCAL:
        p = DIST / route.strip("/") / "index.html" if route != "/" else DIST / "index.html"
        if not p.exists():
            return None, ""
        return 200, p.read_text(encoding="utf-8", errors="ignore")
    try:
        with urllib.request.urlopen(HOST + route, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except Exception as e:
        return None, str(e)

rows, bad = [], 0
for route in routes:
    code, html = fetch(route)
    issues = []
    if code != 200:
        issues.append(f"HTTP {code}")
    else:
        if "sidenav" not in html and route != "/print/":
            issues.append("无侧栏")
        if "# 实验手册 ·" in html:
            issues.append("漏出H1")
        if "demo/fruitlab.html" in html and "/mingzhou/demo/fruitlab.html" not in html:
            issues.append("iframe 路径缺 BASE")
        if route == "/handbook/01/" and "svg" not in html:
            issues.append("无图")
        # 图的锚点挂在外层 <figure id="fig-N-x"> 上（不是 svg 上，否则与 mermaid 自带 id 撞车）
        if route in ("/handbook/01/", "/handbook/02/", "/handbook/03/", "/print/"):
            if not re.search(r'id="fig-\d+-\d+"', html):
                issues.append("图缺 id 锚点")
        if "@@BASE@@" in html or "@@FIG_" in html:
            issues.append("占位符未替换")
    rows.append((route, code, "OK" if not issues else "; ".join(issues)))
    bad += 1 if issues else 0

print(f"{'路由':<24}{'状态':<6}结果")
for r, c, s in rows:
    print(f"{r:<24}{str(c):<6}{s}")
print(f"\n共 {len(rows)} 页，异常 {bad} 页")
sys.exit(1 if bad else 0)
