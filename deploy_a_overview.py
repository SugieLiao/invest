#!/usr/bin/env python3
"""deploy_a_overview.py — 把一份「A股盘面全景分析」HTML 部署到 liaohao.cc/a-overview/。

用法：
  python3 deploy_a_overview.py <报告.html> [label]
    label 例：0945 / 1030 / 1130 / 1330 / 1430（盘中各时点）
              1500 或 close —— 收盘版：进入历史归档（线上 history/ 永久保留 + 本地 a_overview_history/）

行为：
  1) 准备 /tmp/cfpub/a-overview/（与 stock-a/ 子树互不干扰，deploy_cf.py 全量增量发布）：
     - echarts.min.js  ← BASE/web/echarts.min.js（自托管，国内访问稳）
     - index.html      ← 报告正文（CDN 引用改写为 ./echarts.min.js），即最新一期
     - overview_<date>_<label>.html ← 归档副本（保留近 12 份，更早的删除；收盘版不在此列）
  2) 收盘版（label=1500/close）额外：
     - history/overview_<date>_close.html ← 线上永久历史归档（不删除）
     - history/index.html                  ← 历史索引页（按日期倒序，供回顾）
     - BASE/a_overview_history/overview_<date>_close.html ← 本地永久副本
  3) 读取 BASE/secrets.env 的 CF_TOKEN / CF_ACCOUNT，调用 deploy_cf.py 发布。
  4) 输出最终 URL。

退出码非 0 即失败（供自动化调用方判断后决定是否发通知）。
"""
import os, re, sys, glob, shutil, subprocess, datetime, html as html_mod

BASE = os.path.dirname(os.path.abspath(__file__))
PUB = "/tmp/cfpub"
DEST = os.path.join(PUB, "a-overview")
HIST = os.path.join(DEST, "history")
LOCAL_HIST = os.path.join(BASE, "a_overview_history")
KEEP_ARCHIVES = 12
CLOSE_LABELS = {"1500", "close"}

NAV_TAG = '<script src="/shared/nav.js" defer></script>'
_LEGACY_NAV = re.compile(r'<nav\b[^>]*class="topnav"[^>]*>.*?</nav>', re.S | re.I)
_LEGACY_NAV2 = re.compile(r'<div\b[^>]*class="topnav"[^>]*>.*?</div\s*>', re.S | re.I)
# 只剥离 .topnav 的单条 CSS 规则；绝不可删整块 <style>（页面主体样式与其同处一块）
_LEGACY_STYLE_RULE = re.compile(r'\.topnav[^{}]*\{[^{}]*\}', re.I)


def inject_nav(html):
    """注入统一的跨应用菜单栏：移除页面自带旧导航，插入 /shared/nav.js（幂等）。

    不同 App 页面深浅色不同，nav.js 会按页面背景自动切换深浅主题，
    历史归档页（history/ 子目录）统一用相对上级再回站的绝对路径 src="/shared/nav.js"。
    """
    html = _LEGACY_NAV.sub("", html)
    html = _LEGACY_NAV2.sub("", html)
    html = _LEGACY_STYLE_RULE.sub("", html)
    if "/shared/nav.js" in html:
        return html
    if "</head>" in html:
        return html.replace("</head>", NAV_TAG + "</head>", 1)
    return NAV_TAG + html


def build_history_index():
    """根据 history/ 下已有归档生成索引页 history/index.html（按日期倒序）。"""
    items = []
    for p in glob.glob(os.path.join(HIST, "overview_*.html")):
        name = os.path.basename(p)
        m = re.match(r"overview_(\d{4})(\d{2})(\d{2})_close\.html", name)
        if not m:
            continue
        d = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        # 从报告文件里抓标题（第一个 <h1>）
        title = ""
        try:
            txt = open(p, encoding="utf-8").read(60000)
            t = re.search(r"<h1>(.*?)</h1>", txt, re.S)
            if t:
                title = re.sub(r"<[^>]+>", "", t.group(1)).strip()[:60]
        except OSError:
            pass
        items.append((d, name, title or f"A股盘面全景分析（收盘）"))
    items.sort(reverse=True)
    rows = "\n".join(
        f'<tr><td>{d}</td><td><a href="{html_mod.escape(n)}">{html_mod.escape(t)}</a></td></tr>'
        for d, n, t in items
    )
    page = inject_nav(f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A股盘中全景 · 收盘历史归档</title>
<style>
body{{font-family:"PingFang SC","Microsoft YaHei",sans-serif;background:#f6f7f9;color:#2c3e50;padding:24px;line-height:1.7}}
.wrap{{max-width:860px;margin:0 auto}}
.topnav{{background:#fff;border:1px solid #e3e6ea;border-radius:10px;padding:10px 16px;margin-bottom:20px;display:flex;gap:8px;align-items:center;font-size:14px;flex-wrap:wrap;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
.topnav .brand{{font-weight:700;color:#1a5276;text-decoration:none;margin-right:12px}}
.topnav .grp{{color:#95a5a6;font-size:12px;margin-right:4px}}
.topnav a{{color:#2c3e50;text-decoration:none;padding:3px 10px;border-radius:5px}}
.topnav a:hover{{background:#eef3f8}}
.topnav a.cur{{background:#1a5276;color:#fff}}
h1{{font-size:22px;margin-bottom:6px}}
.sub{{color:#7f8c8d;font-size:13px;margin-bottom:16px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e3e6ea;border-radius:10px;overflow:hidden;font-size:14px}}
th{{background:#f0f3f6;text-align:left;padding:10px 14px}}
td{{padding:9px 14px;border-bottom:1px solid #eef1f4}}
a{{color:#1a5276}}
</style></head><body><div class="wrap">
<nav class="topnav"><a class="brand cur" href="/a-overview/">A股盘中全景</a><span class="grp">A股复盘：</span><a href="/stock-a/">收盘版</a><a href="/stock-a/noon/">午间版</a><span class="grp" style="margin-left:12px">本站：</span><a href="/a-overview/">最新一期</a><a class="cur" href="/a-overview/history/">历史归档</a></nav>
<h1>A股盘中全景 · 收盘历史归档</h1>
<div class="sub">每个交易日 15:00 收盘版全景分析的永久历史记录，供日后回顾。共 {len(items)} 期。</div>
<table><tr><th style="width:120px">日期</th><th>当日全景标题</th></tr>
{rows if rows else '<tr><td colspan="2" style="color:#95a5a6">暂无归档</td></tr>'}
</table>
<p style="font-size:12px;color:#95a5a6;margin-top:14px">免责声明：归档内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。</p>
</div></body></html>""")
    with open(os.path.join(HIST, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    return len(items)

def main():
    if len(sys.argv) < 2:
        print("用法: deploy_a_overview.py <报告.html> [label]"); sys.exit(2)
    src = os.path.abspath(sys.argv[1])
    if not os.path.isfile(src):
        print(f"找不到报告文件: {src}"); sys.exit(2)
    label = (sys.argv[2] if len(sys.argv) > 2 else datetime.datetime.now().strftime("%H%M")).lower()
    is_close = label in CLOSE_LABELS

    # 1) 目标目录
    os.makedirs(DEST, exist_ok=True)
    if is_close:
        os.makedirs(HIST, exist_ok=True)
        os.makedirs(LOCAL_HIST, exist_ok=True)

    # 2) 自托管 echarts（幂等：仅本地缺失或大小异常时复制）
    echarts_src = os.path.join(BASE, "web", "echarts.min.js")
    echarts_dst = os.path.join(DEST, "echarts.min.js")
    if os.path.isfile(echarts_src) and os.path.getsize(echarts_src) > 500_000:
        if not os.path.isfile(echarts_dst) or os.path.getsize(echarts_dst) != os.path.getsize(echarts_src):
            shutil.copy(echarts_src, echarts_dst)
    else:
        print("⚠ 本地 echarts.min.js 缺失或过小，报告需自备图表库")

    # 3) 读取报告并改写 CDN 引用为本地
    html = open(src, encoding="utf-8").read()
    html = re.sub(
        r'<script src="https://cdn\.jsdelivr\.net/npm/echarts[^"]*"></script>',
        '<script src="./echarts.min.js"></script>',
        html,
    )
    # 历史归档页位于 history/ 子目录，echarts 相对路径需要回上一级
    html_hist = html.replace('<script src="./echarts.min.js"></script>',
                             '<script src="../echarts.min.js"></script>')

    # 4.5) 统一顶部菜单栏（移除旧导航 + 注入 /shared/nav.js）
    html = inject_nav(html)
    html_hist = inject_nav(html_hist)

    date = datetime.datetime.now().strftime("%Y%m%d")

    # 4) index.html（最新一期，所有时点都更新）
    with open(os.path.join(DEST, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    if is_close:
        # 收盘版 → 永久历史归档（线上 + 本地）+ 索引页
        hist_name = f"overview_{date}_close.html"
        with open(os.path.join(HIST, hist_name), "w", encoding="utf-8") as f:
            f.write(html_hist)
        shutil.copy(src, os.path.join(LOCAL_HIST, hist_name))
        n = build_history_index()
        print(f"[a-overview] 收盘版已永久归档：线上 history/{hist_name} + 本地 a_overview_history/（共 {n} 期）")
    else:
        # 盘中版 → 滚动归档（保留近 12 份）
        archive = os.path.join(DEST, f"overview_{date}_{label}.html")
        shutil.copy(os.path.join(DEST, "index.html"), archive)
        olds = sorted(glob.glob(os.path.join(DEST, "overview_*.html")))
        for p in olds[:-KEEP_ARCHIVES]:
            try: os.remove(p)
            except OSError: pass
        print(f"[a-overview] index.html + 归档 {os.path.basename(archive)} 就绪（归档共 {min(len(olds)+1, KEEP_ARCHIVES)} 份）")

    # 5) 读取 secrets.env → 环境变量 → 调 deploy_cf.py
    env = dict(os.environ)
    sec = os.path.join(BASE, "secrets.env")
    for line in open(sec, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    if not env.get("CF_TOKEN") or not env.get("CF_ACCOUNT"):
        print("缺少 CF_TOKEN / CF_ACCOUNT（secrets.env）"); sys.exit(1)
    env["CF_PUB_DIR"] = PUB

    r = subprocess.run([sys.executable, os.path.join(BASE, "deploy_cf.py")],
                       env=env, capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print("deploy_cf.py 失败:", r.stderr); sys.exit(1)

    print(f"== 完成 == https://liaohao.cc/a-overview/" + ("history/" if is_close else ""))

if __name__ == "__main__":
    main()
