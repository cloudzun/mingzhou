"""逐页 QA：三种模式，一页不落。

用法：
  python scripts/qa_pages.py                  # 线上 HTTP 冒烟（默认）
  python scripts/qa_pages.py local            # 本地 dist 文件冒烟（不起服务）
  python scripts/qa_pages.py browser          # 线上真浏览器验收（控制台/404/交互）
  python scripts/qa_pages.py browser http://127.0.0.1:4321/mingzhou   # 本地真浏览器

两种冒烟模式只回答"文件在不在、关键字符串在不在"，发现不了 BASE 写错、资源 404、
控制台报错、iframe 白屏——历史上 15/15 全绿但线上白屏就是这么来的。发版前跑 browser 模式。
"""
import re
import sys
import pathlib
import urllib.request

LOCAL = len(sys.argv) > 1 and sys.argv[1] == "local"
BROWSER = len(sys.argv) > 1 and sys.argv[1] == "browser"
BASE = (sys.argv[2] if len(sys.argv) > 2 else "https://www.cloudzun.com/mingzhou").rstrip("/")
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


def smoke():
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
    return rows, bad


def browser():
    from playwright.sync_api import sync_playwright

    rows, bad = [], 0
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context()
        for route in routes:
            page = ctx.new_page()
            errs, http_bad = [], []
            page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
            page.on("response", lambda r: http_bad.append(f"{r.status} {r.url}") if r.status >= 400 else None)
            issues = []
            try:
                page.goto(BASE + route, wait_until="load", timeout=30000)
                page.wait_for_timeout(700)
            except Exception as e:
                rows.append((route, "-", f"打不开: {str(e)[:80]}"))
                bad += 1
                page.close()
                continue

            if errs:
                issues.append(f"控制台 {len(errs)} 错误: {errs[0][:70]}")
            if http_bad:
                issues.append(f"资源错误: {http_bad[0][:70]}")

            body = page.inner_text("body")
            if "@@" in body:
                issues.append("占位符未替换")
            if "undefined" in body:
                issues.append("正文含 undefined")

            # 正文页只允许一个 h1（页面标题）。iframe 外壳页（演示 + 三个案例向导）没有 h1，
            # 打印页每篇一个 h1，都不在这条检查里。
            if route != "/print/" and page.locator("iframe").count() == 0:
                h1 = page.locator("h1").count()
                if h1 != 1:
                    issues.append(f"h1 数量={h1}")

            if route == "/demo/fruitlab/":
                n = page.evaluate(
                    "() => { const f = document.querySelector('iframe');"
                    " if (!f || !f.contentDocument) return 0;"
                    " return f.contentDocument.body.innerText.trim().length; }"
                )
                if n < 200:
                    issues.append(f"iframe 空/白屏（{n} 字）")

            if route in ("/handbook/01/", "/handbook/02/", "/handbook/03/", "/print/"):
                if page.locator("figure[id^='fig-']").count() == 0:
                    issues.append("图未渲染")

            if route in ("/handbook/00/", "/handbook/01/", "/handbook/02/", "/handbook/03/"):
                if page.locator(".prose table").count() == 0:
                    issues.append("正文表格未渲染")

            if route == "/print/":
                # 部分/附录已从 h1 降为 h2，分页靠 print.astro 里按锚点前缀的 CSS 补回来
                heads = page.evaluate(
                    "() => ['第一部分','第二部分','第三部分','附录'].map(p =>"
                    " document.querySelectorAll('.prose h2[id^=\"h-' + p + '\"]').length)"
                )
                if heads[:3] != [1, 1, 1] or heads[3] < 4:
                    issues.append(f"打印视图分页标题数异常（{heads}，前三项应为 1/1/1，附录≥4）")
                pb = page.evaluate(
                    "() => { const h = document.querySelector('.prose h2[id^=\"h-第一部分\"]');"
                    ' return h ? getComputedStyle(h).pageBreakBefore : ""; }'
                )
                if pb != "always":
                    issues.append(f"部分标题未分页（{pb}）")
                if page.locator("h1").count() != 4:
                    issues.append(f"打印视图篇标题数={page.locator('h1').count()}（应为 4）")

            if route == "/search/":
                box = page.locator(".pagefind-ui__search-input")
                if box.count() == 0:
                    issues.append("找不到搜索框")
                else:
                    # Pagefind UI 是运行时初始化的：初始化可能把输入框节点换掉，
                    # 太早 fill 会落空（本地快、线上慢，本地过线上挂过一次）。
                    page.wait_for_timeout(900)
                    links = page.locator(".pagefind-ui__result-link")
                    for attempt in range(2):
                        box.first.fill("判定单元")
                        try:
                            page.wait_for_selector(".pagefind-ui__result", timeout=6000)
                            break
                        except Exception:
                            page.evaluate(
                                "() => { const i = document.querySelector('.pagefind-ui__search-input');"
                                " if (i) { i.value = '判定单元'; i.dispatchEvent(new Event('input', { bubbles: true })); } }"
                            )
                            page.wait_for_timeout(2500)
                    if links.count() == 0:
                        # 线上索引是构建期产物 + 运行时 fetch，偶发慢一拍；再给一次机会，避免假红
                        page.wait_for_timeout(3000)
                    if links.count() == 0:
                        issues.append("搜索结果为空")
                    else:
                        href = links.first.get_attribute("href") or ""
                        if "/mingzhou/" not in href and not href.startswith("/"):
                            issues.append(f"结果链接异常: {href[:60]}")

            rows.append((route, "200", "OK" if not issues else "; ".join(issues)))
            bad += 1 if issues else 0
            page.close()
        b.close()
    return rows, bad


rows, bad = browser() if BROWSER else smoke()
mode = "browser" if BROWSER else ("local" if LOCAL else "online")
print(f"模式：{mode} ｜ 基址：{BASE}")
print(f"{'路由':<24}{'状态':<6}结果")
for r, c, s in rows:
    print(f"{r:<24}{str(c):<6}{s}")
print(f"\n共 {len(rows)} 页，异常 {bad} 页")
sys.exit(1 if bad else 0)
