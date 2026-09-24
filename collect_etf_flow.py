#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_etf_flow.py — ETF 净申购 / 净赎回榜单采集（复现 Wind「ETF 净申赎」口径）

核心口径（已与 Wind 分享表逐只校验、20/20 分毫不差）：
  本周净申赎(亿份) = 当日总份额 − 本周基准日(上周五，即本周一之前最近交易日)总份额
  本年净申赎(亿份) = 当日总份额 − 上年度末(2025-12-31)总份额
  最新总份额(亿份) = 当日交易所公布值
  净申购 TOP10 = 本周净申赎降序前 10；净赎回 TOP10 = 升序前 10。

数据源（全部免费、官方、可脚本化）：
  - 沪市 ETF（51/56/58 开头）：上交所 ak.fund_etf_scale_sse(date)，支持任意历史日期
  - 深市 ETF（15/16 开头）：深交所日频接口
        http://www.szse.cn/api/report/ShowReport （注意：本机 https 被阻断，必须用 http）
        CATALOGID=scsj_fund_jjgm，支持日期区间（单次≤6个月）
  - 货币型 ETF（现金管理工具，份额巨大且与热点无关）按名称排除，与 Wind 热点榜口径一致。

输出：
  data/etf_share_snap.json   每日全市场 ETF 份额快照（累积，长期保存）
  data/{date}_etf_flow.json  当日净申购/净赎回双榜（render.py 板块二读取）

用法：
  python collect_etf_flow.py                  # 日常：补齐近 12 天快照 + 采集今天 + 出榜
  python collect_etf_flow.py 2026-08-28       # 指定日期
  python collect_etf_flow.py --backfill 60    # 回填 60 自然日（供近 20 交易日历史趋势）后出今天榜
"""
import os, sys, io, json, time, glob, datetime, warnings
warnings.simplefilter("ignore")

BASE = "/Users/sugieliao/WorkBuddy/A股每日复盘"
DATA = os.path.join(BASE, "data")
SNAP_FILE = os.path.join(DATA, "etf_share_snap.json")
HIST_INDUSTRY_FILE = os.path.join(DATA, "hist_industry_dist.json")
YEAR_END = "2025-12-31"          # 本年净申赎基准
WEEK_LOOKBACK_DAYS = 12          # 日常运行自动补齐的自然日窗口（保证覆盖上周五）

# 货币型 / 现金管理类 ETF 名称关键词（排除，不参与热点排名）
MONEY_KW = ("货币", "现金", "活期", "快线", "保证金", "添富快线", "理财金", "日盈", "日添利")


# ---------------- 快照库读写 ----------------
def load_snap():
    if os.path.exists(SNAP_FILE):
        try:
            return json.load(open(SNAP_FILE, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_snap(snap):
    snap = dict(sorted(snap.items()))
    json.dump(snap, open(SNAP_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def is_money(name):
    return any(k in str(name) for k in MONEY_KW)


# ---------------- 沪市（上交所） ----------------
def fetch_sh(date_str):
    """返回 {code: {name, share(亿份), mkt:'SH'}}；失败返回 None"""
    import akshare as ak
    ymd = date_str.replace("-", "")
    df = ak.fund_etf_scale_sse(date=ymd)
    # 当日份额尚未公布时接口可能返回空表/缺列结构，优雅视为无数据（由调用方回退 T-1）
    need = {"基金代码", "基金简称", "基金份额"}
    if df is None or len(df) == 0 or not need.issubset(set(df.columns)):
        return None
    out = {}
    for _, r in df.iterrows():
        code = str(r["基金代码"]).zfill(6)
        # 用接口返回的统计日期校验，避免非交易日落到最近交易日造成错配
        stat = str(r.get("统计日期", ""))[:10]
        if stat and stat != date_str:
            continue
        try:
            share = float(r["基金份额"]) / 1e8
        except (TypeError, ValueError):
            continue
        if share <= 0:
            continue
        out[code] = {"name": str(r["基金简称"]), "share": round(share, 4), "mkt": "SH"}
    return out or None


# ---------------- 深市（深交所，必须 http） ----------------
def fetch_sz(start_str, end_str, max_retry=3):
    """返回 {date: {code: {name, share, mkt:'SZ'}}}；失败返回 {}"""
    import requests, pandas as pd
    hdr = {"Referer": "https://www.szse.cn/market/fund/volume/etf/index.html",
           "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"}
    params = {"SHOWTYPE": "xlsx", "CATALOGID": "scsj_fund_jjgm", "TABKEY": "tab1",
              "txtStart": start_str, "txtEnd": end_str, "jjlb": "ETF",
              "random": str(time.time() % 1)}
    last_err = None
    for i in range(max_retry):
        try:
            r = requests.get("http://www.szse.cn/api/report/ShowReport",
                             params=params, headers=hdr, timeout=25)
            r.raise_for_status()
            if len(r.content) < 500:
                last_err = "响应过小"
                time.sleep(2); continue
            df = pd.read_excel(io.BytesIO(r.content), engine="openpyxl").dropna(how="all")
            col = "基金规模(份)" if "基金规模(份)" in df.columns else "基金份额"
            out = {}
            for _, x in df.iterrows():
                d = str(x["日期"])[:10]; c = str(x["基金代码"]).zfill(6)
                try:
                    share = float(x[col]) / 1e8
                except (TypeError, ValueError):
                    continue
                if share <= 0:
                    continue
                out.setdefault(d, {})[c] = {"name": str(x["基金简称"]),
                                            "share": round(share, 4), "mkt": "SZ"}
            return out
        except Exception as e:
            last_err = repr(e)[:100]; time.sleep(2)
    print(f"[WARN] 深市 {start_str}~{end_str} 获取失败: {last_err}", file=sys.stderr)
    return {}


# ---------------- 快照采集 / 回填 ----------------
def daterange(start, end):
    d = start
    while d <= end:
        if d.weekday() < 5:  # 周一~周五才请求
            yield d
        d += datetime.timedelta(days=1)


def collect_range(start_date, end_date, snap, verbose=True):
    """采集 [start,end] 区间快照，合并进 snap。沪市逐日、深市整区间。"""
    # 深市一次取整区间（≤6 个月）
    sz_all = fetch_sz(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    for d, mp in sz_all.items():
        snap.setdefault(d, {}).update(mp)
    if verbose:
        print(f"[sz ] {start_date}~{end_date} 深市覆盖 {len(sz_all)} 个交易日")
    # 沪市逐日
    sh_ok = 0
    for d in daterange(start_date, end_date):
        ds = d.strftime("%Y-%m-%d")
        if ds in snap and _has_sh(snap[ds]):
            sh_ok += 1; continue
        try:
            sh = fetch_sh(ds)
        except Exception as e:
            if verbose: print(f"[sh ] {ds} 失败: {repr(e)[:80]}", file=sys.stderr)
            sh = None
        if sh:
            snap.setdefault(ds, {}).update(sh); sh_ok += 1
        time.sleep(0.35)
    if verbose:
        print(f"[sh ] 沪市区间内有效交易日 {sh_ok} 天")
    return snap


def _has_sh(day_map):
    return any(v.get("mkt") == "SH" for v in day_map.values())


def ensure_year_base(snap):
    """确保有上年度末(2025-12-31 附近)快照，用于本年净申赎基准。"""
    have = [d for d in snap if "2025-12-29" <= d <= "2026-01-05"]
    if have:
        return
    print("[init] 采集上年末基准快照(2025-12-29~2026-01-05)…")
    collect_range(datetime.date(2025, 12, 29), datetime.date(2026, 1, 5), snap)


# ---------------- 榜单计算 ----------------
def week_base_date(snap, date_str):
    """本周基准日 = date 所在周周一之前、最近的一个有快照的交易日（通常是上周五）。"""
    d = datetime.date.fromisoformat(date_str)
    monday = d - datetime.timedelta(days=d.weekday())          # 本周一
    candidates = [x for x in snap if x < monday.isoformat()]
    return max(candidates) if candidates else None


def year_base_date(snap):
    cands = [x for x in snap if x <= YEAR_END]
    return max(cands) if cands else None


def build_rank(date_str, snap, top_n=10):
    if date_str not in snap:
        return None
    latest = snap[date_str]
    wb = week_base_date(snap, date_str)
    yb = year_base_date(snap)
    week_map = snap.get(wb, {}) if wb else {}
    year_map = snap.get(yb, {}) if yb else {}
    rows = []
    for code, info in latest.items():
        name = info["name"]
        if is_money(name):
            continue
        total = info["share"]
        prev_w = week_map.get(code, {}).get("share")
        prev_y = year_map.get(code, {}).get("share")
        week = round(total - prev_w, 2) if prev_w is not None else None
        year = round(total - prev_y, 2) if prev_y is not None else None
        rows.append({"code": code, "name": name, "mkt": info.get("mkt", ""),
                     "week": week, "year": year, "total": round(total, 2)})
    valid_week = [r for r in rows if r["week"] is not None]
    inflow = sorted(valid_week, key=lambda x: x["week"], reverse=True)[:top_n]
    outflow = sorted(valid_week, key=lambda x: x["week"])[:top_n]
    return {"date": date_str, "week_base": wb, "year_base": yb,
            "total_etf": len(rows), "inflow": inflow, "outflow": outflow,
            "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


# ---------------- 历史趋势重建（幂等，不联网） ----------------
def rebuild_hist(snap, keep=120):
    """基于快照库为每个交易日重建 ETF 净申购/净赎回历史，写入 hist_industry_dist.json。
    与 render.py 的 update_hist_industry 结构一致：{module:{dates:[],data:{date:[{industry,count}]}}。
    净赎回榜按 week 升序（最负=赎回最多在前），count 保留带符号原值。"""
    hist = {}
    if os.path.exists(HIST_INDUSTRY_FILE):
        try:
            hist = json.load(open(HIST_INDUSTRY_FILE, encoding="utf-8"))
        except Exception:
            hist = {}
    in_mod = hist.setdefault("etf_inflow", {"dates": [], "data": {}})
    out_mod = hist.setdefault("etf_outflow", {"dates": [], "data": {}})
    for mod in (in_mod, out_mod):
        mod["dates"] = []; mod["data"] = {}
    all_dates = sorted(snap.keys())
    for d in all_dates:
        rank = build_rank(d, snap)
        if not rank:
            continue
        in_mod["dates"].append(d)
        out_mod["dates"].append(d)
        in_mod["data"][d] = [{"industry": r["name"], "count": r["week"]}
                             for r in rank["inflow"] if r["week"] is not None]
        # outflow 在 build_rank 里已按 week 升序（赎回最多在前）
        out_mod["data"][d] = [{"industry": r["name"], "count": r["week"]}
                              for r in rank["outflow"] if r["week"] is not None]
    for mod in (in_mod, out_mod):
        if len(mod["dates"]) > keep:
            for old in mod["dates"][:-keep]:
                mod["data"].pop(old, None)
            mod["dates"] = mod["dates"][-keep:]
    json.dump(hist, open(HIST_INDUSTRY_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    return len(in_mod["dates"])


# ---------------- 主流程 ----------------
def main():
    os.makedirs(DATA, exist_ok=True)
    args = sys.argv[1:]
    backfill_days = 0
    if "--backfill" in args:
        i = args.index("--backfill"); backfill_days = int(args[i+1]); del args[i:i+2]
    # 午间版：不写历史趋势（只有收盘版数据计入历史）
    no_hist = ("--midday" in args) or ("--no-hist" in args)
    for f in ("--midday", "--no-hist"):
        while f in args: args.remove(f)
    pos = [a for a in args if not a.startswith("--")]
    today = datetime.date.today()
    date_str = pos[0] if pos else today.strftime("%Y-%m-%d")
    target = datetime.date.fromisoformat(date_str)

    snap = load_snap()

    # 1) 回填 / 日常补齐窗口
    if backfill_days > 0:
        start = target - datetime.timedelta(days=backfill_days)
    else:
        start = target - datetime.timedelta(days=WEEK_LOOKBACK_DAYS)
    collect_range(start, target, snap)
    ensure_year_base(snap)
    save_snap(snap)

    # 2) 计算榜单：优先当日快照；当日尚未公布（如午间）则回退到最近的已公布交易日
    eff_date = date_str
    if eff_date not in snap:
        prior = sorted(d for d in snap if d <= date_str)
        if prior:
            eff_date = prior[-1]
            print(f"[fallback] {date_str} 当日ETF份额尚未公布，回退到最近交易日 {eff_date}")
    rank = build_rank(eff_date, snap)
    if not rank:
        print(f"[ERROR] {date_str}（实际 {eff_date}）无快照，无法出榜", file=sys.stderr); sys.exit(1)
    rank["report_date"] = date_str
    rank["data_date"] = eff_date
    rank["is_t1"] = (eff_date != date_str)
    out = os.path.join(DATA, f"{date_str}_etf_flow.json")
    json.dump(rank, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # 历史趋势：仅收盘版重建（午间 --midday/--no-hist 不写历史）
    n_hist = rebuild_hist(snap) if not no_hist else 0
    print(f"[DONE] 已保存 {out}（数据日期 {eff_date}{'·T-1回退' if rank['is_t1'] else ''}）")
    print(f"  周基准={rank['week_base']} 年基准={rank['year_base']} 参与ETF={rank['total_etf']}"
          + (f" | 历史趋势 {n_hist} 个交易日" if not no_hist else " | 午间版不写历史"))
    print("  净申购TOP5: " + " | ".join(f"{r['name']}{r['week']:+.2f}" for r in rank['inflow'][:5]))
    print("  净赎回TOP5: " + " | ".join(f"{r['name']}{r['week']:+.2f}" for r in rank['outflow'][:5]))


if __name__ == "__main__":
    main()
