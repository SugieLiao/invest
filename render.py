#!/usr/bin/env python3
# 读取 data/YYYY-MM-DD_hithink.json (+ 可选 westock.json) 与历史归档，渲染 A股每日复盘 HTML。
# 输出 /Users/sugieliao/WorkBuddy/A股每日复盘/A股复盘_YYYY-MM-DD.html，并更新 README 索引。
import json, os, sys, datetime, glob

BASE = "/Users/sugieliao/WorkBuddy/A股每日复盘"
DATA = os.path.join(BASE, "data")
VENDOR = os.path.join(BASE, "vendor", "chart.umd.min.js")
CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"
RED = "#d8392b"; GREEN = "#16a34a"; GREY = "#888"

HIST_INDUSTRY_FILE = os.path.join(DATA, "hist_industry_dist.json")
HIST_PCT_SECTORS_FILE = os.path.join(DATA, "hist_pct_sectors.json")

def load_hist_pct_sectors():
    """加载领涨/领跌板块历史趋势数据"""
    if os.path.exists(HIST_PCT_SECTORS_FILE):
        try:
            return json.load(open(HIST_PCT_SECTORS_FILE, encoding="utf-8"))
        except Exception:
            return {"dates": [], "top": {}, "bottom": {}}
    return {"dates": [], "top": {}, "bottom": {}}

def save_hist_pct_sectors(data):
    """保存领涨/领跌板块历史趋势数据"""
    with open(HIST_PCT_SECTORS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_hist_pct_sectors(date, pct_sec):
    """
    更新某天的领涨/领跌板块到历史数据。
    pct_sec: {"top": [{name, pct, ...}, ...], "bottom": [...]}
    """
    all_data = load_hist_pct_sectors()
    if date not in all_data["dates"]:
        all_data["dates"].append(date)
        all_data["dates"].sort()
    # 只保留名称和涨跌幅
    all_data["top"][date] = [{"name": s.get("name", ""), "pct": s.get("pct")} for s in pct_sec.get("top", [])]
    all_data["bottom"][date] = [{"name": s.get("name", ""), "pct": s.get("pct")} for s in pct_sec.get("bottom", [])]
    # 只保留最近120个交易日的数据
    if len(all_data["dates"]) > 120:
        old_dates = all_data["dates"][:-120]
        for d in old_dates:
            all_data["top"].pop(d, None)
            all_data["bottom"].pop(d, None)
        all_data["dates"] = all_data["dates"][-120:]
    save_hist_pct_sectors(all_data)

def get_hist_pct_sectors(days=20):
    """获取最近N天的领涨/领跌板块历史趋势，返回前端可用的格式"""
    all_data = load_hist_pct_sectors()
    dates = all_data["dates"][-days:]
    if not dates:
        return {"dates": [], "top_names": [], "top_pcts": [], "bottom_names": [], "bottom_pcts": []}
    # 领涨：行=排名(1-15)，列=日期，单元格=板块名称
    top_names = []
    top_pcts = []
    for rank in range(15):
        name_row = []
        pct_row = []
        for d in dates:
            day_list = all_data["top"].get(d, [])
            if rank < len(day_list):
                name_row.append(day_list[rank].get("name", ""))
                pct_row.append(day_list[rank].get("pct"))
            else:
                name_row.append(None)
                pct_row.append(None)
        top_names.append(name_row)
        top_pcts.append(pct_row)
    # 领跌：同样格式
    bottom_names = []
    bottom_pcts = []
    for rank in range(15):
        name_row = []
        pct_row = []
        for d in dates:
            day_list = all_data["bottom"].get(d, [])
            if rank < len(day_list):
                name_row.append(day_list[rank].get("name", ""))
                pct_row.append(day_list[rank].get("pct"))
            else:
                name_row.append(None)
                pct_row.append(None)
        bottom_names.append(name_row)
        bottom_pcts.append(pct_row)
    return {"dates": dates, "top_names": top_names, "top_pcts": top_pcts,
            "bottom_names": bottom_names, "bottom_pcts": bottom_pcts}

def load_hist_industry_all():
    """加载所有模块的历史行业分布数据"""
    if os.path.exists(HIST_INDUSTRY_FILE):
        try:
            return json.load(open(HIST_INDUSTRY_FILE, encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_hist_industry_all(data):
    """保存所有模块的历史行业分布数据"""
    with open(HIST_INDUSTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_hist_industry(date, module, industry_list):
    """
    更新某天某模块的行业分布到历史数据。
    industry_list: [{"industry": "化学制药", "count": 5}, ...] 按count降序排列
    """
    all_data = load_hist_industry_all()
    if module not in all_data:
        all_data[module] = {"dates": [], "data": {}}
    mod_data = all_data[module]
    if date not in mod_data["data"]:
        mod_data["dates"].append(date)
        mod_data["dates"].sort()
    mod_data["data"][date] = industry_list
    # 只保留最近120个交易日的数据
    if len(mod_data["dates"]) > 120:
        old_dates = mod_data["dates"][:-120]
        for d in old_dates:
            mod_data["data"].pop(d, None)
        mod_data["dates"] = mod_data["dates"][-120:]
    save_hist_industry_all(all_data)

def get_hist_industry(module, days=20, reverse_sort=True):
    """获取某模块最近N天的历史行业分布，返回前端可用的格式
    返回按天排名的行业数据：names[i][j]表示第j天排名第i的行业，values[i][j]表示对应数量
    reverse_sort=False 时按 count 升序（用于净赎回榜：最负=赎回最多排在最前）。
    """
    all_data = load_hist_industry_all()
    mod_data = all_data.get(module, {"dates": [], "data": {}})
    dates = mod_data["dates"][-days:]
    if not dates:
        return {"dates": [], "top_n": 10, "names": [], "values": []}
    # 每天取前10个行业，按出现次数排序
    top_n = 10
    names = [[] for _ in range(top_n)]  # names[i][j] = 第j天排名第i的行业
    values = [[] for _ in range(top_n)]
    for d in dates:
        day_items = mod_data["data"].get(d, [])
        # 按count排序（默认降序；净赎回等场景用升序让最负在前）
        sorted_items = sorted(day_items, key=lambda x: x.get("count", 0), reverse=reverse_sort)
        for i in range(top_n):
            if i < len(sorted_items):
                names[i].append(sorted_items[i].get("industry", ""))
                values[i].append(sorted_items[i].get("count", 0))
            else:
                names[i].append(None)
                values[i].append(None)
    return {"dates": dates, "top_n": top_n, "names": names, "values": values}

def load_chartjs():
    # 优先内联本地 vendor 副本，使报告完全离线自包含；缺失则退回 CDN。
    if os.path.exists(VENDOR):
        return open(VENDOR, encoding="utf-8").read()
    return None

def load(date):
    h = json.load(open(os.path.join(DATA, f"{date}_hithink.json"), encoding="utf-8"))
    # 个股新高/新低：优先通达信 tdx_screener（当日），回退 westock（T-1）
    h.setdefault("hl_source", ""); h.setdefault("hl_is_t1", False); h.setdefault("westock_source_date", None)
    tdx = os.path.join(DATA, f"{date}_tdxhl.json")
    used_tdx = False
    if os.path.exists(tdx):
        try:
            t = json.load(open(tdx, encoding="utf-8"))
            hn = t.get("high_new"); ln = t.get("low_new")
            h["high_new"] = hn.get("count") if isinstance(hn, dict) else hn
            h["low_new"] = ln.get("count") if isinstance(ln, dict) else ln
            h["hl_source"] = t.get("source", "通达信 tdx_screener（当日）")
            h["hl_is_t1"] = False
            h["tdx_hl"] = t
            used_tdx = True
        except Exception:
            pass
    if not used_tdx:
        w = os.path.join(DATA, f"{date}_westock.json")
        if os.path.exists(w):
            try:
                we = json.load(open(w, encoding="utf-8"))
                h["high_new"] = we.get("high_new", h.get("high_new"))
                h["low_new"] = we.get("low_new", h.get("low_new"))
                h["hl_source"] = "腾讯自选股 westock"
                h["hl_is_t1"] = True
                h["westock_source_date"] = we.get("source_date")
            except Exception:
                pass
    # 板块三 / 四 统一口径：同花顺 thsdk 90 行业（成交额 + 主力净流入）
    s = os.path.join(DATA, f"{date}_sectors_ths.json")
    if os.path.exists(s):
        try:
            ss = json.load(open(s, encoding="utf-8"))
            ts = ss.get("top_sectors", h.get("top_sectors"))
            h["top_sectors"] = ts if isinstance(ts, list) else []
            ns = ss.get("net_inflow_sectors", h.get("net_inflow_sectors"))
            if isinstance(ns, dict) and isinstance(ns.get("top"), list) and isinstance(ns.get("bottom"), list):
                h["net_inflow_sectors"] = ns
            else:
                h["net_inflow_sectors"] = {"top": [], "bottom": []}
            h["net_source"] = ss.get("source", h.get("net_source"))
            h["net_backup"] = False
            h["net_backup_source"] = None
            # 领涨/领跌板块前10（新模块三）
            ps = ss.get("pct_sectors")
            if isinstance(ps, dict) and isinstance(ps.get("top"), list) and isinstance(ps.get("bottom"), list):
                h["pct_sectors"] = ps
            else:
                h["pct_sectors"] = {"top": [], "bottom": []}
        except Exception:
            pass
    # 个股分类映射（行业 / 概念板块），用于新高新低、涨跌停清单 enrichment
    cf = os.path.join(DATA, "stock_classify.json")
    if os.path.exists(cf):
        try:
            h["stock_classify"] = json.load(open(cf, encoding="utf-8"))
        except Exception:
            h["stock_classify"] = {}
    else:
        h["stock_classify"] = {}
    return h

def history():
    # 长期成交额历史（东方财富指数合成，覆盖近2年），用于补全 hithink 之前的日期
    turnover_long = {}
    tp = os.path.join(DATA, "turnover_history.json")
    if os.path.exists(tp):
        try:
            tj = json.load(open(tp, encoding="utf-8"))
            turnover_long = dict(zip(tj.get("dates", []), tj.get("turnover_yi", [])))
        except Exception:
            pass
    dates, turnover, up, down, flat, lu, ld, hl_hn, hl_ln = [], [], [], [], [], [], [], [], []
    files = sorted(glob.glob(os.path.join(DATA, "*_hithink.json")))
    recs = {}
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
            recs[d["date"]] = d
        except Exception:
            continue
    # 日期并集：长期成交额历史 ∪ hithink 逐日采集
    for dt in sorted(set(list(turnover_long.keys()) + list(recs.keys()))):
        # 跳过周末：A股不开盘，若采集脚本误跑会生成无意义的重复数据点
        wd = datetime.datetime.strptime(dt, "%Y-%m-%d").weekday()
        if wd >= 5:
            continue
        d = recs.get(dt) or {}
        # 合并同日 新高/新低，使曲线可跨日累积：优先通达信 tdxhl，回退 westock(T-1)
        tf = os.path.join(DATA, f"{dt}_tdxhl.json")
        if os.path.exists(tf):
            try:
                t = json.load(open(tf, encoding="utf-8"))
                hn = t.get("high_new"); ln = t.get("low_new")
                if d.get("high_new") is None:
                    d["high_new"] = hn.get("count") if isinstance(hn, dict) else hn
                if d.get("low_new") is None:
                    d["low_new"] = ln.get("count") if isinstance(ln, dict) else ln
            except Exception:
                pass
        if d.get("high_new") is None:
            wf = os.path.join(DATA, f"{dt}_westock.json")
            if os.path.exists(wf):
                try:
                    we = json.load(open(wf, encoding="utf-8"))
                    if d.get("high_new") is None: d["high_new"] = we.get("high_new")
                    if d.get("low_new") is None: d["low_new"] = we.get("low_new")
                except Exception:
                    pass
        m = d.get("market") or {}
        # market 字段兜底（与上方 high_new/low_new 的 westock 链一致）：hithink 采集失败的历史日，
        # 逐个字段读 {dt}_westock.json 补，避免历史曲线出现 None 断点
        need = [k for k in ("total_turnover_yi", "up", "down", "flat", "limit_up", "limit_down")
                if m.get(k) is None]
        if need:
            wfm = os.path.join(DATA, f"{dt}_westock.json")
            if os.path.exists(wfm):
                try:
                    wem = json.load(open(wfm, encoding="utf-8"))
                    for k in need:
                        if wem.get(k) is not None:
                            m[k] = wem[k]
                except Exception:
                    pass
        # 成交额：优先 hithink/westock 实测值，缺失时回退长期指数合成历史
        turn_v = m.get("total_turnover_yi")
        if turn_v is None:
            turn_v = turnover_long.get(dt)
        dates.append(dt)
        turnover.append(turn_v)
        up.append(m.get("up")); down.append(m.get("down")); flat.append(m.get("flat"))
        lu.append(m.get("limit_up")); ld.append(m.get("limit_down"))
        hl_hn.append(d.get("high_new")); hl_ln.append(d.get("low_new"))
    return {"dates": dates, "turnover": turnover, "up": up, "down": down, "flat": flat,
            "lu": lu, "ld": ld, "hn": hl_hn, "ln": hl_ln}


def build_hist_tables(report_date, n_days=60):
    """聚合模块三/四/五/七的历史趋势表格数据。
    格式：行=排名，列=日期，单元格=名称（+数值）。便于看每天的TOP N是哪些、轮动情况。
    返回 {sec3, sec4, sec5, sec7}。"""
    # 1) 最近 n_days 个交易日（≤ report_date）
    all_dates = []
    for f in sorted(glob.glob(os.path.join(DATA, "*_hithink.json"))):
        try:
            dt = json.load(open(f, encoding="utf-8")).get("date")
            if dt and dt <= report_date:
                all_dates.append(dt)
        except Exception:
            continue
    all_dates = sorted(set(all_dates))
    dates = all_dates[-n_days:] if len(all_dates) > n_days else all_dates
    nd = len(dates)

    # 2) 预加载历史文件
    sec_cache, rps_cache = {}, {}
    for dt in dates:
        sf = os.path.join(DATA, f"{dt}_sectors_ths.json")
        if os.path.exists(sf):
            try: sec_cache[dt] = json.load(open(sf, encoding="utf-8"))
            except Exception: pass
        rf = os.path.join(DATA, f"{dt}_sector_rps.json")
        if os.path.exists(rf):
            try: rps_cache[dt] = json.load(open(rf, encoding="utf-8"))
            except Exception: pass
    # RPS 最新日期兜底：若当日无快照，用 sector_rps.json（覆盖式）补
    if report_date not in rps_cache:
        rp = os.path.join(DATA, "sector_rps.json")
        if os.path.exists(rp):
            try: rps_cache[report_date] = json.load(open(rp, encoding="utf-8"))
            except Exception: pass

    def _rank_matrix(items_getter, name_key, value_key, top_n):
        """通用：对每个日期取 items_getter(dt) 的前 top_n 个，返回 names[rank][day] + values[rank][day]。"""
        names = [[None] * nd for _ in range(top_n)]
        values = [[None] * nd for _ in range(top_n)]
        for j, dt in enumerate(dates):
            items = items_getter(dt) or []
            for i in range(min(top_n, len(items))):
                it = items[i]
                names[i][j] = it.get(name_key)
                values[i][j] = it.get(value_key)
        return names, values

    # 3) 模块三：每天成交 TOP10 板块（行=排名1-10，列=日期，单元格=板块名+成交额）
    s3_names, s3_values = _rank_matrix(
        lambda dt: (sec_cache.get(dt, {}) or {}).get("top_sectors", []),
        "name", "turnover_yi", 10)
    hist_sec3 = {"dates": dates, "top_n": 10, "names": s3_names, "values": s3_values}

    # 4) 模块四：每天主力净流入 TOP10 + 净流出 TOP10
    s4_in_names, s4_in_values = _rank_matrix(
        lambda dt: ((sec_cache.get(dt, {}) or {}).get("net_inflow_sectors", {}) or {}).get("top", []),
        "name", "zljlr_yi", 10)
    s4_out_names, s4_out_values = _rank_matrix(
        lambda dt: ((sec_cache.get(dt, {}) or {}).get("net_inflow_sectors", {}) or {}).get("bottom", []),
        "name", "zljlr_yi", 10)
    hist_sec4 = {"dates": dates, "top_n": 10,
                 "inflow_names": s4_in_names, "inflow_values": s4_in_values,
                 "outflow_names": s4_out_names, "outflow_values": s4_out_values}

    # 5) 模块五：每天 RPS 达标板块前20（按 n_pass 降序，collector 已排序）
    s5_names, s5_npass = _rank_matrix(
        lambda dt: (rps_cache.get(dt, {}) or {}).get("passed", []),
        "name", "n_pass", 20)
    hist_sec5 = {"dates": dates, "top_n": 20, "names": s5_names, "n_pass": s5_npass}

    # 6) 模块七：每天新高/新低个股前10（按涨跌幅排序，新高降序、新低升序）
    def _hl_stocks(dt, key):
        tf = os.path.join(DATA, f"{dt}_tdxhl.json")
        if os.path.exists(tf):
            try:
                t = json.load(open(tf, encoding="utf-8"))
                hn = t.get(key)
                if isinstance(hn, dict):
                    stocks = hn.get("stocks", []) or []
                    # 新高按 chg 降序，新低按 chg 升序
                    rev = (key == "high_new")
                    return sorted(stocks, key=lambda s: s.get("chg", 0) or 0, reverse=rev)
            except Exception:
                pass
        return []
    s7_hi_names, s7_hi_pct = _rank_matrix(
        lambda dt: _hl_stocks(dt, "high_new"), "name", "chg", 10)
    s7_lo_names, s7_lo_pct = _rank_matrix(
        lambda dt: _hl_stocks(dt, "low_new"), "name", "chg", 10)
    hist_sec7 = {"dates": dates, "top_n": 10,
                 "high_names": s7_hi_names, "high_pct": s7_hi_pct,
                 "low_names": s7_lo_names, "low_pct": s7_lo_pct}

    return {"sec3": hist_sec3, "sec4": hist_sec4, "sec5": hist_sec5, "sec7": hist_sec7}


def pct_color(v):
    if v is None: return ""
    return RED if v > 0 else (GREEN if v < 0 else "")

def fmt_pct(v):
    if v is None: return "—"
    return f"{v:+.2f}%"

def to_thscode(code):
    # 把通达信/tdx_screener 的纯数字代码规范成同花顺 thscode（含交易所后缀）
    if not code:
        return code
    if "." in str(code):
        return code
    c = str(code)
    if c.startswith("92"):
        return c + ".BJ"
    if c[0] == "6":
        return c + ".SH"
    if c[0] in ("0", "3"):
        return c + ".SZ"
    if c[0] in ("4", "8"):
        return c + ".BJ"
    return c + ".SH"

def lookup_cls(code, classify):
    c = to_thscode(code)
    return classify.get(c) or classify.get(str(code)) or {}

def cls_cells(code, classify, tdx_stock_ind=None):
    # 返回 (行业文本, 概念文本)
    cl = lookup_cls(code, classify)
    ind = "/".join(cl.get("industry", [])[:2])
    # 若stock_classify中无行业，回退到通达信研究行业三级分类（二级/三级）
    if not ind and tdx_stock_ind and code in tdx_stock_ind:
        ti = tdx_stock_ind[code]
        parts = [p for p in [ti.get("l2",""), ti.get("l3","")] if p]
        ind = "/".join(parts) if parts else ""
    if not ind:
        ind = "—"
    cons = cl.get("concept", [])
    if len(cons) > 3:
        cons_disp = "、".join(cons[:3]) + f" 等{len(cons)}个"
    else:
        cons_disp = "、".join(cons) or "—"
    return ind, cons_disp

def industry_distribution(stocks, classify, code_key="code", top_n=15, title="行业分布", l1_fetcher=None):
    """统计股票列表的一级行业分布，返回 (HTML标签云, 统计列表)
    统计列表格式: [{"industry": "化学制药", "count": 5}, ...] 按count降序
    l1_fetcher: 可选函数 code->一级行业名，优先于classify使用
    """
    from collections import Counter
    counter = Counter()
    for s in stocks:
        code = s.get(code_key, "")
        ind_name = ""
        # 优先使用股票自带的industry_l1字段
        if s.get("industry_l1") and s.get("industry_l1") != "—":
            ind_name = s["industry_l1"]
        # 然后使用l1_fetcher
        elif l1_fetcher:
            ind_name = l1_fetcher(code)
        # 最后回退到classify
        else:
            cl = lookup_cls(code, classify)
            industries = cl.get("industry", [])
            if industries:
                ind_name = industries[-1] if len(industries) >= 2 else industries[0]
        if ind_name:
            counter[ind_name] += 1
        else:
            counter["未分类"] += 1
    if not counter:
        return "", []
    items = counter.most_common(top_n)
    total = sum(counter.values())
    # 统计列表（用于保存历史）
    stats = [{"industry": name, "count": count} for name, count in counter.most_common()]
    # HTML标签云
    html = f'<div class="ind-dist"><span class="ind-dist-title">{title}（共{total}只）：</span>'
    for name, count in items:
        pct = count / total * 100
        html += f'<span class="ind-tag" title="{name}: {count}只 ({pct:.1f}%)">{name} <b>{count}</b></span>'
    if len(counter) > top_n:
        html += f'<span class="ind-tag-more">…等{len(counter)}个行业</span>'
    html += '</div>'
    return html, stats

def industry_distribution_l1(stocks, field="industry_l1", top_n=15, title="行业分布"):
    """统计股票列表的指定行业字段分布，返回 (HTML标签云, 统计列表)
    统计列表格式: [{"industry": "医药生物", "count": 8}, ...] 按count降序
    """
    from collections import Counter
    counter = Counter()
    for s in stocks:
        val = s.get(field, "") or "未分类"
        counter[val] += 1
    if not counter:
        return "", []
    items = counter.most_common(top_n)
    total = sum(counter.values())
    stats = [{"industry": name, "count": count} for name, count in counter.most_common()]
    html = f'<div class="ind-dist"><span class="ind-dist-title">{title}（共{total}只）：</span>'
    for name, count in items:
        pct = count / total * 100
        html += f'<span class="ind-tag" title="{name}: {count}只 ({pct:.1f}%)">{name} <b>{count}</b></span>'
    if len(counter) > top_n:
        html += f'<span class="ind-tag-more">…等{len(counter)}个行业</span>'
    html += '</div>'
    return html, stats

def jzxt_zone(v):
    # 均线占比区间（参考 极冰10/冰点25/中枢50/过热75/高潮90），返回 (区间名, 颜色)
    if v is None: return ("—", GREY)
    if v < 10: return ("极冰", "#00BFFF")
    if v < 25: return ("冰点", "#4169E1")
    if v < 50: return ("中枢下方", "#ca8a04")
    if v < 75: return ("中枢上方", "#ca8a04")
    if v < 90: return ("过热", "#d8392b")
    return ("高潮", "#d8392b")

def sa_attr(code, sector=False):
    """生成 hover 迷你K线的 data 属性"""
    if not code:
        return ""
    if sector or (isinstance(code, str) and code.startswith("88") and len(code) == 6):
        return ' class="sa-hover" data-code="' + code + '" data-hist-key="sec:' + code + '"'
    # 个股代码格式 300308.SZ / 600519.SH / 838171.BJ
    c = str(code)
    mkt = ""
    if c.endswith(".SZ"): mkt = "sz"; c = c[:-3]
    elif c.endswith(".SH"): mkt = "sh"; c = c[:-3]
    elif c.endswith(".BJ"): mkt = "bj"; c = c[:-3]
    elif c.endswith(".TI"): return ' class="sa-hover" data-hist-key="' + code + '"'  # 通达信指数用内置 hist
    # 纯6位数字代码，自动推断市场
    if not mkt and c.isdigit() and len(c) == 6:
        if c[0] in "6": mkt = "sh"
        elif c[0] in "03": mkt = "sz"
        elif c[:3] == "920": mkt = "bj"
        elif c[0] in "48": mkt = "bj"
        else: mkt = "sz"
    return ' class="sa-hover" data-code="' + c + '" data-mkt="' + mkt + '"'

def fetch_turnover_map(codes):
    """批量取个股成交额（亿），返回 {code: turnover_yi}。数据源：腾讯行情 qt.gtimg.cn。"""
    import urllib.request
    result = {}
    if not codes:
        return result
    codes = list(dict.fromkeys(c for c in codes if c))
    if not codes:
        return result
    def _prefix(c):
        if c[0] == '6': return 'sh'
        if c[0] in '03': return 'sz'
        if c[0] in '48': return 'bj'
        return 'sz'
    for i in range(0, len(codes), 40):
        batch = codes[i:i+40]
        q = ','.join(_prefix(c)+c for c in batch)
        try:
            req = urllib.request.Request(f"https://qt.gtimg.cn/q={q}", headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=15).read().decode("gbk", errors="ignore")
            for line in raw.strip().split(";"):
                if "=" not in line:
                    continue
                try:
                    p = line.split('"')[1].split("~")
                    if len(p) > 37 and p[37]:
                        result[p[2]] = round(float(p[37]) / 1e4, 1)
                except Exception:
                    pass
        except Exception:
            pass
    return result

def build_html(d, hist, midday=False, report_date=None):
    cj = load_chartjs()
    chartjs_tag = f"<script>{cj}</script>" if cj else f'<script src="{CDN}"></script>'
    # 报告日期（页面显示的日期）与数据日期（实际数据的日期）可以不同
    # 当数据回退到前一天时，报告日期=当天，数据日期=前一天，模块会显示红色感叹号
    data_date = d.get("date")
    if report_date is None:
        report_date = data_date
    m = d.get("market") or {}
    idx = d.get("indices") or []
    _sec = d.get("top_sectors")
    sec = _sec if isinstance(_sec, list) else []
    stk = (d.get("market") or {}).get("top_stocks") or []
    hn = d.get("high_new"); ln = d.get("low_new")
    ff = d.get("fund_flow") or {"top": [], "bottom": []}
    _net = d.get("net_inflow_sectors")
    net = _net if isinstance(_net, dict) and isinstance(_net.get("top"), list) and isinstance(_net.get("bottom"), list) else {"top": [], "bottom": []}
    # 领涨/领跌板块前10（新模块三）
    _pct = d.get("pct_sectors")
    pct_sec = _pct if isinstance(_pct, dict) else {"top": [], "bottom": []}
    net_backup = bool(d.get("net_backup"))
    net_backup_source = d.get("net_backup_source") or "未知备选源"
    net_src = d.get("net_source") or "同花顺 thsdk（游客模式）行业板块"
    net_top_n = len(net.get("top") or [])
    if net_backup:
        sec4_badge = (f"<p class='note' style='color:#b7791f'>⚠ 备选数据源：{net_backup_source}。"
                      f"东方财富 push2 限流时启用，板块口径为同花顺行业（与东方财富行业板块不同）。</p>")
        sec4_heading = f"五、主力净流入前 {net_top_n} 板块（行业 · {net_backup_source}·备选）"
    else:
        sec4_badge = ("<p class='note'>数据来源：同花顺 thsdk（游客模式）行业板块。"
                      "板块三、四、五均为同一套同花顺 90 行业口径，可直接对照同一行业的涨跌幅、成交额与主力净流入。</p>")
        sec4_heading = f"五、主力净流入前 {net_top_n} 板块（行业 · 同花顺 thsdk·当日）"
    hl_source = d.get("hl_source") or "未知"
    hl_is_t1 = d.get("hl_is_t1")
    if hl_is_t1:
        hl_note = f"数据来源：{hl_source}。实际数据日期：{d.get('westock_source_date') or '未知'}（该接口常滞后一日，为 T-1 数据）。"
    else:
        hl_note = f"数据来源：{hl_source}。当日数据（条件选股口径，前复权）。"
    # ── 非当日数据标记：计算各数据源实际数据日期，与报告日不同则在对应板块/图表/卡片打红色感叹号 ──
    # 板块三/四 同源于 同花顺 thsdk 行业板块
    ths_asof = None
    sp = os.path.join(DATA, f"{data_date}_sectors_ths.json")
    if os.path.exists(sp):
        try:
            ths_asof = json.load(open(sp, encoding="utf-8")).get("date")
        except Exception:
            ths_asof = None
    # 板块五 RPS 共振（东方财富）
    rps_asof = None
    rpp = os.path.join(DATA, "sector_rps.json")
    if os.path.exists(rpp):
        try:
            rps_asof = json.load(open(rpp, encoding="utf-8")).get("date")
        except Exception:
            rps_asof = None
    if hl_is_t1:
        ws = d.get("westock_source_date")
        hl_asof = ws if ws else (datetime.date.fromisoformat(report_date) - datetime.timedelta(days=1)).isoformat()
    else:
        hl_asof = report_date
    _hd = hist.get("dates") or []
    hist_last = _hd[-1] if _hd else None
    _id = idx[0]["hist_dates"] if idx else []
    idx_last = _id[-1] if _id else None
    def stale_attr(v):
        return f' data-stale="{v}"' if v and v != report_date else ""
    sector_stale = stale_attr(ths_asof)  # 三、四 板块（同花顺 thsdk）
    rps_stale = stale_attr(rps_asof)     # 六、RPS 共振（通达信 TDX 880 概念板块指数）
    hl_stale  = stale_attr(hl_asof)      # 八、个股新高/新低
    hist_stale = stale_attr(hist_last)  # 一、4 张历史曲线（成交额/涨跌/涨跌停/高低）
    idx_stale = stale_attr(idx_last)    # 二、指数走势曲线
    # ── 数据截止时间戳：数据内容本身截止的交易时点（收盘版=15:00 / 午间版=11:30），
    #    非采集动作发生时间。收盘版数据应为全天快照，午间版为上午快照。──
    cutoff_hhmm = "11:30" if midday else "15:00"
    cutoff_variant = "午间" if midday else "收盘"
    # 根据报告日期计算星期几（而非从数据文件读取，避免回退数据时星期几错位）
    _weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    try:
        report_weekday = _weekday_map[datetime.datetime.strptime(report_date, "%Y-%m-%d").weekday()]
    except Exception:
        report_weekday = d.get("weekday", "")
    cutoff_dt = f"{report_date} {cutoff_hhmm}"
    cutoff_attr = f' data-cutoff="{cutoff_dt}"'
    cutoff_banner = (f'<div class="cutoff-banner">数据截止时间：{cutoff_dt}'
                     f'（{cutoff_variant}版快照）</div>')
    # 全市场总成交额(亿) 作为「板块成交额占比%」的分母：板块成交额 / 全市场成交额
    total_amt = max(m.get("total_turnover_yi") or 0, 1)
    # 风格指数曲线数据：与宽基指数同一 60 日窗口对齐；历史覆盖 <60% 的指数（如同花顺
    # 仅部分交易日发布的指数）不纳入曲线，避免断线，其当日表现仍在上表展示。
    idx_dates = idx[0]["hist_dates"] if idx else []
    style_lines, style_dropped = [], []
    if idx_dates:
        for s in d.get("style_indices") or []:
            hd = s.get("hist_dates") or []
            hc = s.get("hist_close") or []
            if not hd or not hc:
                continue
            mv = dict(zip(hd, hc))
            data = [mv.get(dt) for dt in idx_dates]
            nn = sum(1 for v in data if v is not None)
            if nn / len(idx_dates) >= 0.6:
                style_lines.append({"name": s.get("name", "?"), "data": data})
            else:
                style_dropped.append(s.get("name", "?"))
    style_drop_note = ""
    if style_dropped:
        style_drop_note = (f"<p class='note' style='color:#888;background:#f6f8fa'>注："
                           f"{'、'.join(style_dropped)}（同花顺仅部分交易日发布、历史不连续）"
                           f"未纳入曲线，其当日表现见上方表格。</p>")
    payload = {
        "date": d["date"], "weekday": d.get("weekday", ""),
        "hist": hist,
        "idx_dates": idx[0]["hist_dates"] if idx else [],
        "idx_lines": [{"name": i["name"], "data": i["hist_close"]} for i in idx],
        "sec_bar": [{"name": s["name"], "v": s["turnover_yi"],
                     "pct": s.get("pct"),
                     "ratio": round(s["turnover_yi"] / total_amt * 100, 2)} for s in sec],
        "net_top": [{"name": x["name"], "v": x["zljlr_yi"], "pct": x.get("pct"),
                     "turnover": x.get("turnover_yi"),
                     "ratio": round((x.get("turnover_yi") or 0) / total_amt * 100, 2)} for x in net.get("top", [])],
        "net_bot": [{"name": x["name"], "v": x["zljlr_yi"], "pct": x.get("pct"),
                     "turnover": x.get("turnover_yi"),
                     "ratio": round((x.get("turnover_yi") or 0) / total_amt * 100, 2)} for x in net.get("bottom", [])],
        "style_indices": d.get("style_indices") or [],
        "style_dates": idx_dates,
        "style_lines": style_lines,
        "style_dropped": style_dropped,
        "top_sectors": sec,
        "net_inflow_sectors": net,
        "pct_sectors": pct_sec,
    }
    # 历史趋势表格数据（模块三/四/五/七），供前端折叠区展示
    hist_tables = build_hist_tables(report_date, n_days=60)
    payload["hist_tables"] = hist_tables
    # 行业分布历史趋势数据（模块六/七/八/九），供前端折叠区展示
    payload["hist_industry"] = {
        "limit_up": get_hist_industry("limit_up", days=20),
        "limit_down": get_hist_industry("limit_down", days=20),
        "top100": get_hist_industry("top100", days=20),
        "high_new": get_hist_industry("high_new", days=20),
        "low_new": get_hist_industry("low_new", days=20),
        "koudai": get_hist_industry("koudai", days=20),
        "score_strong": get_hist_industry("score_strong", days=20),
        "score_weak": get_hist_industry("score_weak", days=20),
        "etf_inflow": get_hist_industry("etf_inflow", days=20),
        "etf_outflow": get_hist_industry("etf_outflow", days=20, reverse_sort=False),
    }
    # 领涨/领跌板块历史趋势数据（新模块三），供前端折叠区展示
    payload["hist_pct_sectors"] = get_hist_pct_sectors(days=20)
    # 万得全A 日K（市值加权全A代理）
    wande = None
    wande_pct = None
    wp = os.path.join(DATA, "wande.json")
    if os.path.exists(wp):
        try:
            wj = json.load(open(wp, encoding="utf-8"))
            if wj.get("ok"):
                wande = wj
                # 计算当日涨跌幅：(今日收盘价 - 昨日收盘价) / 昨日收盘价 * 100
                closes = wj.get("close", [])
                if len(closes) >= 2 and closes[-2] != 0:
                    wande_pct = (closes[-1] - closes[-2]) / closes[-2] * 100
        except Exception:
            pass
    payload["wande"] = wande
    # 沪深两市融资余额（沪市上交所+深市深交所）
    margin = None
    margin_html = ""
    mp = os.path.join(DATA, "margin_balance.json")
    if os.path.exists(mp):
        try:
            mj = json.load(open(mp, encoding="utf-8"))
            if mj.get("dates") and mj.get("margin_balance"):
                margin = mj
        except Exception:
            pass
    if margin:
        m_dates = margin["dates"]
        m_vals = margin["margin_balance"]
        last_v = m_vals[-1]
        prev_v = m_vals[-2] if len(m_vals) >= 2 else last_v
        m_chg = last_v - prev_v
        m_chg_pct = (m_chg / prev_v * 100) if prev_v else 0
        m_color = RED if m_chg >= 0 else GREEN
        m_arrow = "▲" if m_chg >= 0 else "▼"
        # 两融交易占市场总成交比例 = 融资买入额 / 全市场成交额 × 100%
        margin_ratio = None
        turnover_map = dict(zip(hist.get("dates", []), hist.get("turnover", [])))
        m_buys = margin.get("margin_buy") or []
        if m_buys:
            r_dates, r_vals = [], []
            for i, ds in enumerate(m_dates):
                buy = m_buys[i] if i < len(m_buys) else None
                turn = turnover_map.get(ds)
                if buy is not None and turn:
                    r_dates.append(ds)
                    r_vals.append(round(buy / turn * 100, 2))
            if r_dates:
                margin_ratio = {"dates": r_dates, "ratio": r_vals}
                last_r = r_vals[-1]
                prev_r = r_vals[-2] if len(r_vals) >= 2 else last_r
                r_chg = last_r - prev_r
        rng = f"{m_dates[0]} → {m_dates[-1]}（{len(m_dates)} 个交易日）"
        margin_stale = stale_attr(m_dates[-1])  # 融资余额数据日期非报告日则标红色感叹号
        margin_html = (
            "<h4 style='margin-top:16px'>沪深两市融资余额（亿元）</h4>"
            f"<div class='kpis' style='margin-bottom:8px'>"
            f"<div class='kpi'><div class='lab'>最新余额（{m_dates[-1]}）</div>"
            f"<div class='val'>{last_v:,.2f}亿</div></div>"
            f"<div class='kpi'><div class='lab'>较前日</div>"
            f"<div class='val' style='color:{m_color};font-size:18px'>{m_arrow} {abs(m_chg):,.2f}亿 ({m_chg_pct:+.2f}%)</div></div>"
            f"</div>\n"
            f"<div style=\"position:relative\"><div class=\"chartLeg\" id=\"leg_cMargin\"></div><canvas id='cMargin'{margin_stale}></canvas></div>\n"
            "<p class='note'>数据来源：沪市（上交所）+ 深市（深交所）两市融资余额合计（akshare）。"
            "融资余额＝投资者融资买入后未偿还的金额，反映市场杠杆资金规模。范围：" + rng + "。</p>"
        )
        if margin_ratio:
            r_color = RED if r_chg >= 0 else GREEN
            r_arrow = "▲" if r_chg >= 0 else "▼"
            margin_html += (
                "<h4 style='margin-top:16px'>两融交易占市场总成交比例（%）</h4>"
                f"<div class='kpis' style='margin-bottom:8px'>"
                f"<div class='kpi'><div class='lab'>最新占比（{r_dates[-1]}）</div>"
                f"<div class='val'>{last_r:.2f}%</div></div>"
                f"<div class='kpi'><div class='lab'>较前日（百分点）</div>"
                f"<div class='val' style='color:{r_color};font-size:18px'>{r_arrow} {abs(r_chg):.2f}pct</div></div>"
                f"</div>\n"
                f"<div style=\"position:relative\"><div class=\"chartLeg\" id=\"leg_cMarginRatio\"></div><canvas id='cMarginRatio'{margin_stale}></canvas></div>\n"
                "<p class='note'>两融交易占比＝当日两市融资买入额 ÷ 全市场总成交额 × 100%，"
                "反映杠杆资金当日参与市场的活跃程度，占比越高代表融资盘交易越活跃。</p>"
            )
    else:
        margin_html = ("<p class='miss' style='margin-top:16px'>融资余额：数据暂不可达"
                       "（运行 collect_margin.py 采集后覆盖本占位）。</p>")
    payload["margin"] = margin
    payload["margin_ratio"] = margin_ratio
    # ETF 净申购 / 净赎回双榜（板块二「指数表现」子数据块）
    etf_flow = None
    etf_html = ""
    efp = os.path.join(DATA, f"{report_date}_etf_flow.json")
    if os.path.exists(efp):
        try:
            etf_flow = json.load(open(efp, encoding="utf-8"))
        except Exception:
            etf_flow = None
    if etf_flow and (etf_flow.get("inflow") or etf_flow.get("outflow")):
        def _etf_rows(lst, sign):
            out = ""
            def _vc(v):
                # 正值红色、负值绿色（A股红涨绿跌），0/缺失用次要灰
                if isinstance(v, (int, float)):
                    if v > 0: return RED
                    if v < 0: return GREEN
                return "#a0aec0"
            for k, r in enumerate(lst):
                wk, yr, tot = r.get("week"), r.get("year"), r.get("total")
                wkt = f"{wk:+.2f}" if isinstance(wk, (int, float)) else "—"
                yrt = f"{yr:+.2f}" if isinstance(yr, (int, float)) else "—"
                ttt = f"{tot:.2f}" if isinstance(tot, (int, float)) else "—"
                out += (f"<tr><td>{k+1}</td><td{sa_attr(r.get('code',''))}>{r.get('name','')}</td>"
                        f"<td class='num'>{r.get('code','')}</td>"
                        f"<td class='num' style='color:{_vc(wk)};font-weight:600'>{wkt}</td>"
                        f"<td class='num' style='color:{_vc(yr)}'>{yrt}</td>"
                        f"<td class='num'>{ttt}</td></tr>")
            return out or "<tr><td colspan=6 style='color:#888'>无数据</td></tr>"
        etf_inflow_rows = _etf_rows(etf_flow.get("inflow", []), "in")
        etf_outflow_rows = _etf_rows(etf_flow.get("outflow", []), "out")
        etf_wb = etf_flow.get("week_base", "") or "—"
        etf_yb = etf_flow.get("year_base", "") or "—"
        etf_dd = etf_flow.get("data_date") or etf_flow.get("date", "")
        etf_t1 = etf_flow.get("is_t1", False)
        etf_dd_lbl = (f"<span style='color:#fc8181'>⚠ 份额日期 {etf_dd}（T-1）</span> · "
                      if etf_t1 else f"份额日期 {etf_dd} · ")
        etf_html = (
            "<h4 style='margin-top:16px'>ETF 净申购 / 净赎回 TOP10（亿份）"
            f"<span style='font-size:12px;color:#888;font-weight:400;margin-left:8px'>"
            f"{etf_dd_lbl}本周基准 {etf_wb} · 本年基准 {etf_yb}</span></h4>"
            "<div class='grid2'>"
            "<div><h5 style='color:#d8392b;margin:4px 0'>净申购 TOP10</h5>"
            "<table class='etf-tb'><tr><th>#</th><th>名称</th><th>代码</th><th>本周</th><th>本年</th><th>总份额</th></tr>"
            + etf_inflow_rows + "</table></div>"
            "<div><h5 style='color:#16a34a;margin:4px 0'>净赎回 TOP10</h5>"
            "<table class='etf-tb'><tr><th>#</th><th>名称</th><th>代码</th><th>本周</th><th>本年</th><th>总份额</th></tr>"
            + etf_outflow_rows + "</table></div>"
            "</div>"
            "<p class='note'>数据来源：上交所 / 深交所每日公布的 ETF 份额（akshare）。"
            "本周净申赎＝当日总份额−上周五总份额（本周以来累计，周五即完整周度口径，复现 Wind ETF 净申赎榜）；"
            "本年净申赎＝当日−上年末(2025-12-31)；已剔除货币型 ETF。单位：亿份。</p>"
            "<div class='hist-section'><div class='hist-toggle' onclick='toggleHist(this)'>"
            "<span class='arrow'>▶</span> 历史趋势 · ETF净申购/净赎回（近20日）</div>"
            "<div class='hist-body' data-mod='ind_etf_both'></div></div>"
        )
        # 历史趋势（仅收盘版写入；午间版不写历史）
        if not midday:
            update_hist_industry(report_date, "etf_inflow",
                [{"industry": r.get("name", ""), "count": r.get("week")}
                 for r in etf_flow.get("inflow", []) if r.get("week") is not None])
            update_hist_industry(report_date, "etf_outflow",
                [{"industry": r.get("name", ""), "count": r.get("week")}
                 for r in etf_flow.get("outflow", []) if r.get("week") is not None])
    else:
        etf_html = ("<p class='miss' style='margin-top:16px'>ETF 净申购 / 净赎回：数据暂不可达"
                    "（运行 collect_etf_flow.py 采集后覆盖本占位）。</p>")
    payload["etf_flow"] = etf_flow
    # 均占系统 均线占比（市场宽度）日线
    jzxt = None
    jzxt_html = ""
    jp = os.path.join(DATA, "jzxt_history.json")
    if os.path.exists(jp):
        try:
            jj = json.load(open(jp, encoding="utf-8"))
            if jj.get("ok") and jj.get("dates"):
                jzxt = jj
        except Exception:
            pass
    if jzxt:
        series_def = [("cdx", "5日"), ("dx", "13日"), ("zx", "50日"), ("cx", "120日")]
        last_d = jzxt["dates"][-1]
        jzxt_stale = stale_attr(last_d)  # 均线占比数据日期非报告日则标红色感叹号
        rows = ""
        for key, name in series_def:
            arr = jzxt.get(key) or []
            v = arr[-1] if arr else None
            zn, zc = jzxt_zone(v)
            vtxt = f"{v:.2f}" if isinstance(v, (int, float)) else "—"
            rows += (f"<tr><td>{name}</td><td class='num' style='color:{zc};font-weight:600'>{vtxt}</td>"
                     f"<td style='color:{zc}'>{zn}</td></tr>")
        rng = f"{jzxt['dates'][0]} → {last_d}（{len(jzxt['dates'])} 个交易日）"
        jzxt_html = (
            "<h4 style='margin-top:16px'>均线占比（市场宽度 · 均占系统）</h4>"
            f"<table{jzxt_stale}><tr><th>周期</th><th>占比(%)</th><th>区间</th></tr>" + rows + "</table>\n"
            f"<div style=\"position:relative\"><div class=\"chartLeg\" id=\"leg_cJzxt\"></div><canvas id='cJzxt'{jzxt_stale}></canvas></div>\n"
            "<p class='note'>数据来源：均占系统 ghxb.site/jzxt（/api/admin/daily/range，Bearer 鉴权）。"
            "均线占比＝站上对应周期均线的个股比例(%)；参考区间 极冰10 / 冰点25 / 中枢50 / 过热75 / 高潮90。"
            "快线、慢线(kx/mx)当前无数据。范围：" + rng + "。</p>"
        )
    else:
        jzxt_html = ("<p class='miss' style='margin-top:16px'>均线占比（市场宽度）：数据源暂不可达"
                     "（token 缺失或接口异常），连上后由 collect_jzxt.py 取数并覆盖本占位。</p>")
    payload["jzxt"] = jzxt
    # TR情绪监测（通达信扩展数据 38/39/40：HTR10/HTR20/HTR40，市场宽度/情绪）
    tr = None
    tr_html = ""
    tp = os.path.join(DATA, "tr_emotion.json")
    if os.path.exists(tp):
        try:
            tj = json.load(open(tp, encoding="utf-8"))
            if tj.get("ok") and tj.get("dates"):
                tr = tj
                # 历史补发口径：只保留 report_date 及之前的数据，
                # 避免"重新抽数"补发历史日期时 TR 表格/曲线出现未来数据
                # （tr_emotion.json 是全局单一文件，始终滚动到最新）。
                di = len(tr["dates"])
                for i, dt in enumerate(tr["dates"]):
                    if dt > report_date:
                        di = i
                        break
                if di < len(tr["dates"]):
                    tr = dict(tr, dates=tr["dates"][:di],
                              **{k: tr[k][:di] for k in ("htr10", "htr20", "htr40") if k in tr})
                if not tr["dates"]:
                    tr = None
        except Exception:
            pass
    def tr_zone(v):
        # TR情绪区间：沸点87(超买) / 相变50(多空分界) / 冰点13(超卖)
        if v is None: return ("—", GREY)
        if v >= 87: return ("超买(沸点)", "#d8392b")
        if v >= 50: return ("偏强", "#ca8a04")
        if v >= 13: return ("偏弱", "#2b6cb0")
        return ("超卖(冰点)", "#4169E1")
    if tr:
        tr_series = [("htr10", "HTR10(短期)", "#ff6b6b"),
                      ("htr20", "HTR20(中期)", "#2b6cb0"),
                      ("htr40", "HTR40(长期)", "#9333ea")]
        last_d = tr["dates"][-1]
        rows = ""
        for key, name, color in tr_series:
            arr = tr.get(key) or []
            v = arr[-1] if arr else None
            zn, zc = tr_zone(v)
            vtxt = f"{v:.2f}" if isinstance(v, (int, float)) else "—"
            rows += (f"<tr><td><span style='display:inline-block;width:10px;height:10px;border-radius:50%;"
                     f"background:{color};margin-right:6px'></span>{name}</td>"
                     f"<td class='num' style='color:{zc};font-weight:600'>{vtxt}</td>"
                     f"<td style='color:{zc}'>{zn}</td></tr>")
        rng = f"{tr['dates'][0]} → {last_d}（{len(tr['dates'])} 个交易日）"
        tr_stale = stale_attr(last_d)  # TR情绪监测数据日期非报告日则标红色感叹号
        tr_html = (
            "<h4 style='margin-top:16px'>TR情绪监测（市场宽度 · 通达信扩展数据）</h4>"
            f"<table{tr_stale}><tr><th>指标</th><th>最新值(%)</th><th>区间</th></tr>" + rows + "</table>\n"
            f"<div style=\"position:relative\"><div class=\"chartLeg\" id=\"leg_cTr\"></div><canvas id='cTr'{tr_stale}></canvas></div>\n"
            "<p class='note'>数据来源：通达信扩展数据 38/39/40 号（TR占比 日线，基于平均股价指数880003）。"
            "TR＝个股收盘价突破N日TR波动上限的占比(%)，衡量市场广度情绪；"
            "参考线 沸点87(超买) / 相变50(多空分界) / 冰点13(超卖)。"
            "范围：" + rng + "。</p>"
        )
    else:
        tr_html = ("<p class='miss' style='margin-top:16px'>TR情绪监测：数据源暂不可达"
                   "（collect_tr_emotion.py 未运行或 VM 不可达），连上后覆盖本占位。</p>")
    payload["tr_emotion"] = tr
    # 板块 RPS 共振（通达信 TDX 880 概念板块指数，主源；同花顺 THS 兜底；5/10/20/50 日，至少3个>87）
    rps = None
    rps_html = ""
    rps_chart_cfg = None
    rp = os.path.join(DATA, "sector_rps.json")
    if os.path.exists(rp):
        try:
            rr = json.load(open(rp, encoding="utf-8"))
            if rr.get("ok") and rr.get("passed"):
                rps = rr
        except Exception:
            pass
    if rps:
        thr = rps["threshold"]; mp = rps["min_pass"]
        src = rps.get("source") or "通达信 TDX（概念板块指数 880xxx·本地概念清单，主源）"
        # 午间版不更新 RPS，沿用上一交易日收盘结果（sector_rps.json 为上一交易日）
        rps_midday_note = ("<p class='note' style='color:#b7791f'>⚠ 午间版不更新 RPS 数据，"
                           f"本区沿用上一交易日（{rps.get('date')}）收盘 RPS 共振结果。</p>"
                           ) if midday else ""
        def rps_cell(v):
            if v is None:
                return "<td class='num'>—</td>"
            col = "#d8392b" if v > thr else ("#999" if v < 50 else "#222")
            bold = "font-weight:600" if v > thr else ""
            return f"<td class='num' style='color:{col};{bold}'>{v:.2f}</td>"
        shown = rps["passed"][:40]
        rows = ""
        for p in shown:
            rows += (f"<tr><td{sa_attr(p.get('code') or '', sector=True)}>{p['name']}</td><td class='num'>{p['cat']}</td>"
                     + rps_cell(p["rps5"]) + rps_cell(p["rps10"]) + rps_cell(p["rps20"]) + rps_cell(p["rps50"])
                     + f"<td class='num' style='font-weight:600'>{p['n_pass']}</td></tr>")
        more = len(rps["passed"]) - len(shown)
        moretxt = (f"<tr><td colspan=7 style='color:#888;text-align:center'>… 其余 {more} 个（共 {len(rps['passed'])} 个通过筛选）</td></tr>"
                   if more > 0 else "")
        ulabel = rps.get("universe_label", "全市场板块")
        rng = f"{ulabel}有效板块 {rps['valid_boards']} 个，日期 {rps['date']}"
        rps_html = (
            f"<h4 style='margin-top:16px'>强势板块 · RPS 共振（{ulabel}）</h4>"
            + rps_midday_note +
            "<table><tr><th>板块</th><th>类别</th><th>RPS5</th><th>RPS10</th><th>RPS20</th><th>RPS50</th><th>达标周期</th></tr>"
            + rows + moretxt + "</table>\n"
            "<div class=\"chartLeg\" id=\"leg_cRps\"></div><canvas id='cRps'></canvas>\n"
            f"<p class='note'>筛选条件：5/10/20/50 日 RPS 中至少 {mp} 个 &gt; {thr}。"
            f"RPS＝板块N日涨幅在{ulabel}中的排名百分位（欧奈尔定义，前复权）。红字＝该周期 &gt; "
            f"{thr}（强势）。数据来源：{src}。{rng}。"
            f"｜ 操作：双击图表可放大；点击上方图例可高亮对应系列；悬停某一行可列出该板块全部 RPS 值。</p>"
        )
        # 横向分组条形图（前25个通过板块，最弱在下）
        top_rev = list(reversed(rps["passed"][:25]))
        names = [p["name"] for p in top_rev]
        def ds(k, color):
            return {"label": k, "data": [p[k] for p in top_rev], "backgroundColor": color}
        rps_chart_cfg = {
            "type": "bar",
            "data": {"labels": names, "datasets": [
                ds("rps5", "#2b6cb0"), ds("rps10", "#16a34a"),
                ds("rps20", "#ca8a04"), ds("rps50", "#d8392b")]},
            "options": {
                "indexAxis": "y", "responsive": True, "maintainAspectRatio": False,
                "layout": {"padding": {"right": 48, "top": 8}},
                "plugins": {"legend": {"labels": {"font": {"size": 11}}}},
                "scales": {
                    "x": {"min": 0, "max": 100, "grid": {"color": "#2a3040"},
                          "title": {"display": True, "text": "RPS", "font": {"size": 10}}},
                    "y": {"ticks": {"font": {"size": 12}, "autoSkip": False}}}
            }
        }
    else:
        rps_html = ("<p class='miss' style='margin-top:16px'>强势板块 RPS：数据源暂不可达"
                    "（collect_sector_rps.py 未运行或接口异常），连上后覆盖本占位。</p>")
    payload["rps"] = rps
    payload["rps_chart_cfg"] = rps_chart_cfg
    payload["rps_thr"] = rps["threshold"]
    only1 = len(hist["dates"]) <= 1

    # ---- 指数表 ----
    idx_rows = "".join(
        f"<tr><td{sa_attr(i.get('code') or '')}>{i['name']}</td><td class='num'>{i['close']}</td>"
        f"<td class='num' style='color:{pct_color(i['pct'])}'>{fmt_pct(i['pct'])}</td>"
        f"<td class='num'>{i['turnover_yi']}亿</td></tr>" for i in idx)
    # ---- 风格指数表（板块二子表：短线风格/情绪）----
    style = d.get("style_indices") or []
    style_rows = ""
    if style:
        for s in style:
            nm = s.get("name", "?")
            close = s.get("close")
            pct = s.get("pct")
            sa = sa_attr(s.get("code") or "")
            if pct is None:
                style_rows += f"<tr><td{sa}>{nm}</td><td class='num'>—</td><td class='num'>—</td></tr>"
            else:
                arr = "▲" if pct > 0 else ("▼" if pct < 0 else "—")
                style_rows += (f"<tr><td{sa}>{nm}</td><td class='num'>{close}</td>"
                               f"<td class='num' style='color:{pct_color(pct)};font-weight:600'>{arr}{fmt_pct(pct)}</td></tr>")
    else:
        style_rows = "<tr><td colspan=3 class='num'>风格指数数据暂缺</td></tr>"
    # ---- 板块表 ----
    # 板块三/四自带 hist 数据时，直接用自身 code（去 URFI 前缀）生成 hover 属性
    def _sec_hover(s):
        c = (s.get("code") or "").replace("URFI", "")
        return sa_attr(c, sector=True) if c else ""
    sec_rows = "".join(
        f"<tr><td>{k+1}</td><td{_sec_hover(s)}>{s['name']}</td><td class='num'>{s['turnover_yi']}亿</td>"
        f"<td class='num'>{s['turnover_yi']/total_amt*100:.2f}%</td>"
        f"<td class='num' style='color:{pct_color(s['pct'])}'>{fmt_pct(s['pct'])}</td></tr>"
        for k, s in enumerate(sec))
    # 领涨/领跌板块前10表格（新模块三）
    # 把今天的数据追加到每个板块的历史K线中（hist_dates只到昨天）
    for group in [pct_sec.get("top", []), pct_sec.get("bottom", [])]:
        for s in group:
            hd = s.get("hist_dates") or []
            hc = s.get("hist_close") or []
            pct = s.get("pct")
            if hd and hc and pct is not None and hd[-1] != report_date:
                today_close = hc[-1] * (1 + pct / 100)
                hd.append(report_date)
                hc.append(round(today_close, 2))
    def _pct_row(rank, s):
        return (f"<tr><td>{rank}</td><td{_sec_hover(s)}>{s['name']}</td>"
                f"<td class='num' style='color:{pct_color(s.get('pct'))};font-weight:600'>{fmt_pct(s.get('pct'))}</td>"
                f"<td class='num'>{s.get('turnover_yi', 0)}亿</td></tr>")
    pct_top_rows = "".join(_pct_row(k+1, s) for k, s in enumerate(pct_sec.get("top", [])))
    pct_bot_rows = "".join(_pct_row(k+1, s) for k, s in enumerate(pct_sec.get("bottom", [])))
    # ── 板块三：涨跌归因分析（读取 data/{date}_sector_analysis.json，不存在则不展示）──
    sector_analysis_html = ""
    sa_path = os.path.join(DATA, f"{report_date}_sector_analysis.json")
    if os.path.exists(sa_path):
        try:
            sa = json.load(open(sa_path, encoding="utf-8"))
            _gc = {"A": "#1a7f37", "B": "#0969da", "C": "#bf8700", "D": "#cf222e"}
            _gb = {"A": "#dafbe1", "B": "#ddf4ff", "C": "#fff8c5", "D": "#ffebe9"}
            def _dr(items, top=True):
                r = ""
                for it in items:
                    pct = it.get("pct", 0); ni = it.get("net_inflow_yi", 0)
                    dt = it.get("driver_type", "")
                    dtc = "#1a7f37" if dt == "主动领涨" else ("#bf8700" if dt in ("被动跟涨","事件驱动") else "#cf222e")
                    rsn = "".join(f"<li>{x}</li>" for x in it.get("reasons", []))
                    r += (f"<tr><td class='num' style='font-weight:600'>{it.get('sector','')}</td>"
                          f"<td class='num' style='color:{pct_color(pct)};font-weight:600'>{pct:+.2f}%</td>"
                          f"<td class='num'>{it.get('turnover_yi',0)}亿</td>"
                          f"<td class='num' style='color:{pct_color(ni)}'>{ni:+.2f}亿</td>"
                          f"<td style='white-space:nowrap'><span style='background:{_gb.get('B' if top else 'D','#f6f8fa')};color:{dtc};padding:1px 6px;border-radius:8px;font-size:11px;font-weight:600;white-space:nowrap'>{dt}</span></td>"
                          f"<td style='text-align:left;font-size:13px;line-height:1.6'><ul style='margin:0;padding-left:18px'>{rsn}</ul></td></tr>")
                return r
            _sa_top = _dr(sa.get("top_drivers", []), True)
            _sa_bot = _dr(sa.get("bottom_drivers", []), False)
            _sa_core = "".join(f"<li style='margin-bottom:6px;line-height:1.7'>{c}</li>" for c in sa.get("core_logic", []))
            _src = ""
            for s in sa.get("sources", []):
                g = s.get("grade", "?"); gc = _gc.get(g, "#666"); gb = _gb.get(g, "#f6f8fa")
                url = s.get("url", ""); title = s.get("title", "")
                th = f"<a href='{url}' target='_blank' style='color:#4a9eff;text-decoration:none'>{title}</a>" if url else title
                _src += (f"<tr><td style='white-space:nowrap;text-align:center'><span style='background:{gb};color:{gc};padding:1px 5px;border-radius:4px;font-weight:700;font-size:11px;white-space:nowrap'>{g}级</span></td>"
                          f"<td style='text-align:left;font-size:13px'>{th}<br><span style='color:#718096;font-size:12px'>{s.get('publisher','')} · {s.get('grade_desc','')}</span></td>"
                          f"<td style='text-align:left;font-size:12px;color:#a0aec0;line-height:1.5'>{s.get('used_for','')}</td></tr>")
            _gl = sa.get("grade_legend", {})
            _glh = "".join(f"<span style='margin-right:16px;font-size:12px'><span style='background:{_gb.get(k,'#f6f8fa')};color:{_gc.get(k,'#666')};padding:2px 6px;border-radius:4px;font-weight:700'>{k}级</span> {v}</span>" for k, v in _gl.items())
            sector_analysis_html = f"""
<div style="margin-top:18px;padding:16px 20px;background:#1a1f2e;border:1px solid #2a3348;border-radius:8px">
<h3 style="margin:0 0 10px 0;font-size:16px;color:#e2e8f0">📊 涨跌归因分析</h3>
<p style="margin:0 0 14px 0;font-size:13px;color:#a0aec0;line-height:1.7">{sa.get("market_context","")}</p>
<h4 style="margin:14px 0 6px 0;font-size:14px;color:#d8392b">领涨板块归因</h4>
<table style="width:100%;border-collapse:collapse;font-size:13px">
<tr style="background:#252d40"><th style="padding:6px 8px;text-align:left">板块</th><th>涨跌幅</th><th>成交额</th><th>主力净流入</th><th>驱动类型</th><th style="text-align:left">归因</th></tr>
{_sa_top}
</table>
<h4 style="margin:14px 0 6px 0;font-size:14px;color:#16a34a">领跌板块归因</h4>
<table style="width:100%;border-collapse:collapse;font-size:13px">
<tr style="background:#252d40"><th style="padding:6px 8px;text-align:left">板块</th><th>涨跌幅</th><th>成交额</th><th>主力净流入</th><th>驱动类型</th><th style="text-align:left">归因</th></tr>
{_sa_bot}
</table>
<h4 style="margin:14px 0 6px 0;font-size:14px;color:#e2e8f0">核心逻辑总结</h4>
<ol style="margin:0;padding-left:22px;font-size:13px;color:#c0cad8">{_sa_core}</ol>
<h4 style="margin:18px 0 6px 0;font-size:14px;color:#e2e8f0">信息来源与质量分级</h4>
<div style="margin-bottom:8px">{_glh}</div>
<table style="width:100%;border-collapse:collapse;font-size:13px">
<tr style="background:#252d40"><th style="padding:6px 8px;width:50px">质量</th><th style="text-align:left">来源</th><th style="text-align:left;width:40%">用于支撑的结论</th></tr>
{_src}
</table>
<p style="margin:10px 0 0 0;font-size:11px;color:#4a5568">说明：归因分析由人工结合当日市场热点与公开信息整理，信息来源按可信度分级（A权威/B较高/C中等/D较低），D级来源仅作辅助参考，核心结论均与A/B级来源交叉验证。</p>
</div>
"""
        except Exception as _e:
            sector_analysis_html = f"<p style='color:#cf222e;font-size:12px'>[归因分析加载失败：{_e}]</p>"
    # 保存领涨/领跌板块历史趋势数据（仅收盘版）
    if not midday:
        update_hist_pct_sectors(report_date, pct_sec)
    # ---- 成交量前100个股（51~100 折叠）----
    classify = d.get("stock_classify") or {}
    # 通达信研究行业三级分类（个股→一二三级行业），优先用于行业统计
    tdx_ind_path = os.path.join(DATA, "tdx_stock_industry.json")
    tdx_stock_ind = {}
    if os.path.exists(tdx_ind_path):
        try:
            tdx_stock_ind = json.load(open(tdx_ind_path, encoding="utf-8"))
        except Exception:
            pass
    def get_l1_industry(code):
        """优先从通达信研究行业分类获取一级行业，回退到stock_classify"""
        if code and code in tdx_stock_ind and tdx_stock_ind[code].get("l1"):
            return tdx_stock_ind[code]["l1"]
        cl = lookup_cls(code, classify)
        industries = cl.get("industry", [])
        if industries:
            return industries[-1] if len(industries) >= 2 else industries[0]
        return ""
    stk_top = stk[:50]
    stk_rest = stk[50:100]
    def _stk_row(rank, s, fold=False):
        ind, cons = cls_cells(s.get("code"), classify, tdx_stock_ind)
        l1 = get_l1_industry(s.get("code")) or "—"
        cls = " class='fold-row'" if fold else ""
        dsp = " style='display:none'" if fold else ""
        return (f"<tr{cls}{dsp}><td>{rank}</td><td{sa_attr(s.get('code') or '')}>{s['name']}</td><td class='num'>{s['code']}</td>"
                f"<td class='num'>{s['turnover_yi']}亿</td>"
                f"<td class='num' style='color:{pct_color(s['pct'])}'>{fmt_pct(s['pct'])}</td>"
                f"<td>{l1}</td><td>{ind}</td><td style='font-size:12px'>{cons}</td></tr>")
    stk_rows = "".join(_stk_row(k + 1, s) for k, s in enumerate(stk_top))
    stk_rows_rest = "".join(_stk_row(k + 51, s, fold=True) for k, s in enumerate(stk_rest))
    # 成交量前100行业分布统计
    stk_ind_dist, stk_ind_stats = industry_distribution(stk, classify, title="前100行业分布", l1_fetcher=get_l1_industry)
    # 保存到历史数据（仅收盘版）
    if not midday:
        update_hist_industry(report_date, "top100", stk_ind_stats)

    # ---- 新高 / 新低 个股清单（含行业 / 概念板块）----
    tdx_hl = d.get("tdx_hl") or {}
    def _hl_stocks(key):
        v = tdx_hl.get(key)
        if isinstance(v, dict):
            return v.get("stocks", []) or []
        return []
    hn_stocks = _hl_stocks("high_new")
    ln_stocks = _hl_stocks("low_new")
    # 个股成交额（腾讯行情实时取，板块九/十共用）
    turnover_map = {}
    try:
        _hl_codes = [s.get("code") for s in (hn_stocks + ln_stocks) if s.get("code")]
        turnover_map.update(fetch_turnover_map(_hl_codes))
    except Exception:
        pass
    def hl_rows(stocks):
        def _ind(s):
            try:
                return cls_cells(s.get("code"), classify, tdx_stock_ind)[0] or "zzz"
            except Exception:
                return "zzz"
        ordered = sorted(stocks, key=_ind)
        rows = ""
        for k, s in enumerate(ordered):
            ind, cons = cls_cells(s.get("code"), classify, tdx_stock_ind)
            l1 = get_l1_industry(s.get("code")) or "—"
            rows += (f"<tr><td>{k+1}</td><td{sa_attr(s.get('code') or '')}>{s.get('name','')}</td><td class='num'>{s.get('code','')}</td>"
                     f"<td class='num' style='color:{pct_color(s.get('chg'))}'>{fmt_pct(s.get('chg'))}</td>"
                     f"<td class='num'>{turnover_map.get(s.get('code',''), '—')}亿</td>"
                     f"<td>{l1}</td><td>{ind}</td><td style='font-size:12px'>{cons}</td></tr>")
        return rows or "<tr><td colspan=8 style='color:#888'>无数据</td></tr>"
    hn_rows = hl_rows(hn_stocks)
    ln_rows = hl_rows(ln_stocks)
    # 新高新低行业分布统计
    hn_ind_dist, hn_ind_stats = industry_distribution(hn_stocks, classify, title="新高行业分布", l1_fetcher=get_l1_industry)
    ln_ind_dist, ln_ind_stats = industry_distribution(ln_stocks, classify, title="新低行业分布", l1_fetcher=get_l1_industry)
    # 保存到历史数据（仅收盘版）
    if not midday:
        update_hist_industry(report_date, "high_new", hn_ind_stats)
        update_hist_industry(report_date, "low_new", ln_ind_stats)

    # ---- 涨停 / 跌停 个股清单（含行业 / 概念板块）----
    lu_list = m.get("limit_up_list") or []
    ld_list = m.get("limit_down_list") or []
    def lim_rows(stocks):
        def _ind(s):
            try:
                return cls_cells(s.get("code"), classify, tdx_stock_ind)[0] or "zzz"
            except Exception:
                return "zzz"
        ordered = sorted(stocks, key=_ind)
        rows = ""
        for k, s in enumerate(ordered):
            ind, cons = cls_cells(s.get("code"), classify, tdx_stock_ind)
            l1 = get_l1_industry(s.get("code")) or "—"
            rows += (f"<tr><td>{k+1}</td><td{sa_attr(s.get('code') or '')}>{s.get('name','')}</td><td class='num'>{s.get('code','')}</td>"
                     f"<td class='num' style='color:{pct_color(s.get('pct'))}'>{fmt_pct(s.get('pct'))}</td>"
                     f"<td class='num'>{s.get('turnover_yi',0)}亿</td>"
                     f"<td>{l1}</td><td>{ind}</td><td style='font-size:12px'>{cons}</td></tr>")
        return rows or "<tr><td colspan=8 style='color:#888'>无数据</td></tr>"
    lu_rows = lim_rows(lu_list)
    ld_rows = lim_rows(ld_list)
    # 涨停/跌停行业分布统计
    lu_ind_dist, lu_ind_stats = industry_distribution(lu_list, classify, title="涨停行业分布", l1_fetcher=get_l1_industry)
    ld_ind_dist, ld_ind_stats = industry_distribution(ld_list, classify, title="跌停行业分布", l1_fetcher=get_l1_industry)
    # 保存到历史数据（仅收盘版）
    if not midday:
        update_hist_industry(report_date, "limit_up", lu_ind_stats)
        update_hist_industry(report_date, "limit_down", ld_ind_stats)
    # ---- 口袋支点个股（本地自定义板块 + 通达信研究行业）----
    koudai_path = os.path.join(DATA, "koudai_industry.json")
    koudai_stocks = []
    kd_asof = ""
    if os.path.exists(koudai_path):
        try:
            koudai_data = json.load(open(koudai_path, encoding="utf-8"))
            koudai_stocks = koudai_data.get("stocks", [])
            kd_asof = koudai_data.get("date", "")
        except Exception:
            koudai_stocks = []
    # 按来源筛选：口袋、领先股、净利润断层，并按一级行业排序
    kd_only = sorted([s for s in koudai_stocks if '口袋' in s.get('source', '')], key=lambda x: x.get('industry_l1', '') or 'zzz')
    ld_only = sorted([s for s in koudai_stocks if '领先股' in s.get('source', '')], key=lambda x: x.get('industry_l1', '') or 'zzz')
    dc_only = sorted([s for s in koudai_stocks if '断层' in s.get('source', '')], key=lambda x: x.get('industry_l1', '') or 'zzz')
    # 板块十个股成交额（追加到 turnover_map）
    try:
        _kd_codes = [s.get("code") for s in koudai_stocks if s.get("code")]
        turnover_map.update(fetch_turnover_map(_kd_codes))
    except Exception:
        pass
    def gen_stock_rows(stocks, colspan=7):
        rows = ""
        for k, s in enumerate(stocks):
            l1 = s.get("industry_l1", "") or "—"
            l2 = s.get("industry_l2", "") or "—"
            l3 = s.get("industry_l3", "") or "—"
            rows += (f"<tr><td>{k+1}</td><td{sa_attr(s.get('code',''))}>{s.get('name','')}</td>"
                     f"<td class='num'>{s.get('code','')}</td>"
                     f"<td class='num'>{turnover_map.get(s.get('code',''), '—')}亿</td>"
                     f"<td>{l1}</td><td>{l2}</td><td>{l3}</td></tr>")
        return rows or f"<tr><td colspan={colspan} style='color:#888'>暂无数据</td></tr>"
    kd_stock_rows = gen_stock_rows(kd_only)
    leading_stock_rows = gen_stock_rows(ld_only)
    fault_stock_rows = gen_stock_rows(dc_only)
    kd_stale = stale_attr(kd_asof)
    # 各模块独立的数据截止时间（按实际数据日期显示，而非统一报告日期）
    def cutoff_for(date_str):
        if not date_str:
            return ""
        return f' data-cutoff="{date_str} {cutoff_hhmm}"'
    cutoff_market = cutoff_for(data_date)   # 模块一/二/七/八/十一（hithink数据）
    cutoff_sector = cutoff_for(ths_asof)     # 模块三/四/五（同花顺thsdk）
    cutoff_rps = cutoff_for(rps_asof)        # 模块六（RPS共振）
    cutoff_hl = cutoff_for(hl_asof)          # 模块九（新高新低）
    cutoff_kd = cutoff_for(kd_asof)          # 模块十（口袋+领先+断层）
    # hithink数据模块的红色感叹号（数据日期与报告日期不一致时）
    market_stale = stale_attr(data_date)
    # 行业分布统计（合并口袋+领先股+净利润断层，一级行业）
    kd_ind_dist, kd_ind_stats = industry_distribution_l1(koudai_stocks, field="industry_l1", title="一级行业分布（口袋+领先+断层合并）")
    # 保存到历史数据（仅收盘版）
    if not midday:
        update_hist_industry(report_date, "koudai", kd_ind_stats)
    # ---- 行业热度得分（分强势榜/弱势榜）----
    # 【重要】板块十一依赖以下所有板块的数据，任何板块数据修正后都必须重新render：
    #   强势榜：涨停(1分) + 成交量前100(2分) + 新高(2分) + 口袋+领先+断层(2分)
    #   弱势榜：跌停(1分) + 新低(2分)
    # 历史趋势仅收盘版更新，午间版不写入历史数据
    strong_score = {}
    weak_score = {}
    strong_stock_count = {}
    weak_stock_count = {}
    def add_score(code, weight, classify, score_dict, count_dict):
        if not code:
            return
        l1 = get_l1_industry(code) or "未分类"
        if not l1 or l1.strip() == "" or l1 == "—":
            l1 = "未分类"
        score_dict[l1] = score_dict.get(l1, 0) + weight
        count_dict[l1] = count_dict.get(l1, 0) + 1
    # 强势榜：涨停(1分)
    for s in lu_list:
        add_score(s.get("code"), 1, classify, strong_score, strong_stock_count)
    # 强势榜：成交量前100(2分)
    for s in stk[:100]:
        add_score(s.get("code"), 2, classify, strong_score, strong_stock_count)
    # 强势榜：新高(2分)
    for s in hn_stocks:
        add_score(s.get("code"), 2, classify, strong_score, strong_stock_count)
    # 强势榜：口袋+领先+断层(2分)
    for s in koudai_stocks:
        l1 = s.get("industry_l1", "") or "未分类"
        if l1 == "—":
            l1 = "未分类"
        strong_score[l1] = strong_score.get(l1, 0) + 2
        strong_stock_count[l1] = strong_stock_count.get(l1, 0) + 1
    # 弱势榜：跌停(1分)
    for s in ld_list:
        add_score(s.get("code"), 1, classify, weak_score, weak_stock_count)
    # 弱势榜：新低(2分)
    for s in ln_stocks:
        add_score(s.get("code"), 2, classify, weak_score, weak_stock_count)
    # 按得分排序
    sorted_strong = sorted(strong_score.items(), key=lambda x: x[1], reverse=True)
    sorted_weak = sorted(weak_score.items(), key=lambda x: x[1], reverse=True)
    # 生成HTML表格
    def gen_score_rows(sorted_list, count_dict):
        rows = ""
        for k, (ind, score) in enumerate(sorted_list):
            cnt = count_dict.get(ind, 0)
            rows += (f"<tr><td>{k+1}</td><td>{ind}</td>"
                     f"<td class='num' style='font-weight:600'>{score}</td>"
                     f"<td class='num'>{cnt}</td></tr>")
        return rows or "<tr><td colspan=4 style='color:#888'>暂无数据</td></tr>"
    strong_rows = gen_score_rows(sorted_strong[:15], strong_stock_count)
    weak_rows = gen_score_rows(sorted_weak[:15], weak_stock_count)
    # 保存到历史数据（仅收盘版）
    if not midday:
        strong_hist = [{"industry": ind, "count": score} for ind, score in sorted_strong]
        weak_hist = [{"industry": ind, "count": score} for ind, score in sorted_weak]
        update_hist_industry(report_date, "score_strong", strong_hist)
        update_hist_industry(report_date, "score_weak", weak_hist)
    # 所有历史数据更新完成后，重新读取最新数据构建payload（确保HTML嵌入的是更新后的数据）
    payload["hist_industry"] = {
        "limit_up": get_hist_industry("limit_up", days=20),
        "limit_down": get_hist_industry("limit_down", days=20),
        "top100": get_hist_industry("top100", days=20),
        "high_new": get_hist_industry("high_new", days=20),
        "low_new": get_hist_industry("low_new", days=20),
        "koudai": get_hist_industry("koudai", days=20),
        "score_strong": get_hist_industry("score_strong", days=20),
        "score_weak": get_hist_industry("score_weak", days=20),
        "etf_inflow": get_hist_industry("etf_inflow", days=20),
        "etf_outflow": get_hist_industry("etf_outflow", days=20, reverse_sort=False),
    }
    payload["hist_pct_sectors"] = get_hist_pct_sectors(days=20)
    # ---- 板块十二 主线回踩买点（仅通达信概念板块，5/20日涨幅 pytdx 现算）----
    ml_path = os.path.join(DATA, f"{report_date}_mainline.json")
    ml_fallback_date = ""
    if midday and not os.path.exists(ml_path):
        # 午间版：当天主线回踩数据尚未采集，回退最近8天内的收盘结果
        from datetime import datetime, timedelta
        try:
            rd = datetime.strptime(report_date, "%Y-%m-%d")
            for back in range(1, 9):
                cand = (rd - timedelta(days=back)).strftime("%Y-%m-%d")
                cpath = os.path.join(DATA, f"{cand}_mainline.json")
                if os.path.exists(cpath):
                    ml_path = cpath
                    ml_fallback_date = cand
                    break
        except Exception:
            pass
    ml = None
    if os.path.exists(ml_path):
        try:
            ml = json.load(open(ml_path, encoding="utf-8"))
        except Exception:
            ml = None
    ml_card = ""
    if ml:
        ml_asof = ml.get("date", "")
        cutoff_ml = cutoff_for(ml_asof)
        ml_stale = stale_attr(ml_asof)
        pool_size = ml.get("pool_size", 0)
        # 板块十二上榜概念板块的近60日K线（内嵌，供 hover 迷你K线；公网API取不到880板块）
        payload["mainline_kline"] = ml.get("kline", {}) or {}
        thr = ml.get("thresholds", {}) or {}
        pb_p20 = thr.get("pullback_p20", 5.0)
        dir_t2 = thr.get("dir_t2_top", 30)

        def _ml_pct_td(v):
            return f"<td class='num' style='color:{pct_color(v)}'>{fmt_pct(v)}</td>"

        def _ml_rows(rows, first, start=1):
            out = []
            for k, r in enumerate(rows, start):
                a, b = (r["p20"], r["p5"]) if first == "p20" else (r["p5"], r["p20"])
                pb = r.get("is_pullback")
                tr_style = " style='background:#33291a'" if pb else ""
                mark = " <span style='color:#e2b547;font-size:10px'>真回踩</span>" if pb else ""
                out.append(
                    f"<tr{tr_style}><td>{k}</td><td{sa_attr(r['code'], sector=True)}>{r['name']}{mark}</td>"
                    f"<td class='num'>{r['code']}</td>{_ml_pct_td(a)}{_ml_pct_td(b)}</tr>")
            return "".join(out)

        def _ml_table(rows, first):
            head = ("<tr><th>#</th><th>板块名</th><th>代码</th><th>20日涨幅</th><th>5日涨幅</th></tr>"
                    if first == "p20" else
                    "<tr><th>#</th><th>板块名</th><th>代码</th><th>5日涨幅</th><th>20日涨幅</th></tr>")
            top = "<table>" + head + _ml_rows(rows[:50], "p20" if first == "p20" else "p5", 1) + "</table>"
            if len(rows) > 50:
                rest = ("<table style='margin-top:6px'>" + head +
                        _ml_rows(rows[50:], "p20" if first == "p20" else "p5", 51) + "</table>")
                top += (f"<details style='margin-top:6px'><summary style='cursor:pointer;color:#4a9eff;"
                        f"font-size:12px;padding:4px 0'>展开第 51–{len(rows)} 名（点击折叠 / 展开）</summary>{rest}</details>")
            return top

        # ① 表1 大方向归集
        grp = ""
        for g in ml.get("t1_group", []):
            mem = "、".join(x["name"] for x in g["members"])
            grp += (f"<tr><td style='font-weight:600;white-space:nowrap'>{g['dir']}</td>"
                    f"<td class='num' style='font-weight:600'>{g['count']}</td>"
                    f"<td class='num'>{g['count']}%</td>"
                    f"<td class='num' style='color:{pct_color(g['avg20'])}'>{fmt_pct(g['avg20'])}</td>"
                    f"<td style='font-size:11px;color:#a0aec0;line-height:1.8'>{mem}</td></tr>")
        ml_grp = grp or "<tr><td colspan=5 style='color:#888'>无数据</td></tr>"
        # 三表
        ml_t1_html = _ml_table(ml.get("table1", []), "p20")
        ml_t2_html = _ml_table(ml.get("table2", []), "p5")
        ml_t3_html = _ml_table(ml.get("table3", []), "p5")
        # 今日方向判定
        sig_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
        sig_word = {"green": "双强主线", "yellow": "回踩等企稳", "red": "不独立成主线"}
        drows = ""
        for x in ml.get("direction", []):
            sg = x.get("signal", "")
            drows += (f"<tr><td style='text-align:center;white-space:nowrap'>{sig_emoji.get(sg,'')} "
                      f"<span style='font-size:10px;color:#a0aec0'>{sig_word.get(sg,'')}</span></td>"
                      f"<td style='font-weight:600;white-space:nowrap'>{x['dir']}</td>"
                      f"<td class='num'>{x['t1']}</td><td class='num'>{x['t2']}</td>"
                      f"<td style='font-size:12px;color:#c0cad8;line-height:1.6'>{x['note']}</td></tr>")
        ml_dir = drows or "<tr><td colspan=5 style='color:#888'>无数据</td></tr>"
        cfg_note = ""
        if ml.get("cfg_fallback_days"):
            cfg_note = f"（板块清单回退{ml['cfg_fallback_days']}天至 {ml.get('cfg_source_date')}，涨幅仍为当日实时）"
        ml_card = (
            f'<div class="card"{ml_stale}{cutoff_ml}><h2>十二、主线回踩买点（概念板块 · {pool_size} 个）</h2>'
            + (f"<p class='note' style='color:#b7791f'>⚠ 午间版不更新主线回踩数据，本区沿用 {ml_fallback_date} 收盘结果（当日收盘后自动更新）。</p>" if ml_fallback_date else "")
            + f"<p class='note'>仅用通达信概念板块（剔除风格属性后 {pool_size} 个{cfg_note}）。"
            f"表1=20日涨幅前100（主线池，20日稳≈主线）；表2=5日涨幅前100（短期动能，看谁最近在动）；"
            f"表3=表1前100内按5日涨幅升序（20日涨得多+5日走弱=主线回踩买点，"
            f"<span style='color:#e2b547'>金色底纹</span>=20日涨幅≥{pb_p20:.0f}%且5日为负的真回踩）；"
            f"方向判定=表1 TOP100 与表2 TOP{dir_t2} 重叠。涨幅由 pytdx 实时取板块指数日K现算，红涨绿跌。</p>"
            f"<h4 style='margin-top:14px'>① 表1 大方向归集（方向堆越厚 = 主线越真）</h4>"
            f"<table><tr><th>大方向</th><th>板块数</th><th>占比</th><th>20日均值</th><th>板块成员（按20日涨幅降序）</th></tr>{ml_grp}</table>"
            f"<h4 style='margin-top:16px'>② 表1：20日涨幅前100（主线池）</h4>{ml_t1_html}"
            f"<h4 style='margin-top:16px'>③ 表2：5日涨幅前100（短期动能池）</h4>{ml_t2_html}"
            f"<h4 style='margin-top:16px'>④ 表3：表1前100内 · 5日涨幅升序（回踩买点池）</h4>{ml_t3_html}"
            f"<h4 style='margin-top:16px'>⑤ 今日方向判定（表1 TOP100 ＋ 表2 TOP{dir_t2} 重叠）</h4>"
            f"<table><tr><th>信号</th><th>方向</th><th>表1板块数</th><th>表2板块数</th><th>说明</th></tr>{ml_dir}</table>"
            f"</div>")
    # ---- 主力净流入板块（东方财富·当日）----
    def _net_amt_cell(x):
        tv = x.get("turnover_yi")
        if tv is None:
            return "<td class='num'>—</td>", "<td class='num'>—</td>"
        return (f"<td class='num'>{tv}亿</td>",
                f"<td class='num'>{tv/total_amt*100:.2f}%</td>")
    net_top_rows = "".join(
        (lambda c: f"<tr><td>{k+1}</td><td{_sec_hover(x)}>{x['name']}</td>"
         f"<td class='num' style='color:{RED}'>+{x['zljlr_yi']:.2f}亿</td>"
         f"<td class='num' style='color:{pct_color(x.get('pct'))}'>{fmt_pct(x.get('pct'))}</td>"
         f"{c[0]}{c[1]}</tr>")(_net_amt_cell(x))
        for k, x in enumerate(net.get("top", [])))
    net_bot_rows = "".join(
        (lambda c: f"<tr><td>{k+1}</td><td{_sec_hover(x)}>{x['name']}</td>"
         f"<td class='num' style='color:{GREEN}'>{x['zljlr_yi']:.2f}亿</td>"
         f"<td class='num' style='color:{pct_color(x.get('pct'))}'>{fmt_pct(x.get('pct'))}</td>"
         f"{c[0]}{c[1]}</tr>")(_net_amt_cell(x))
        for k, x in enumerate(net.get("bottom", [])))

    # ── 板块五：当日资金行为分析（综合板块二ETF申赎+板块四成交额+板块五主力净流入）──
    capital_flow_html = ""
    try:
        _mkt = m if isinstance(m, dict) else {}
        _total_amt = float(_mkt.get("total_turnover_yi") or 0)
        _up = int(_mkt.get("up") or 0)
        _down = int(_mkt.get("down") or 0)
        _lu = int(float(_mkt.get("limit_up") or 0))
        _ld = int(float(_mkt.get("limit_down") or 0))
        _net_top = net.get("top", []) or []
        _net_bot = net.get("bottom", []) or []
        _turnover_top = sec if isinstance(sec, list) else []
        _inflow_sum = sum(float(x.get("zljlr_yi") or 0) for x in _net_top)
        _outflow_sum = sum(float(x.get("zljlr_yi") or 0) for x in _net_bot)
        _turnover_top10_sum = sum(float(x.get("turnover_yi") or 0) for x in _turnover_top)
        _tech_names = {"半导体","通信设备","元件","光学光电子","消费电子","电子化学品","其他电子","计算机设备","软件开发","IT服务"}
        _tech_turnover = sum(float(x.get("turnover_yi") or 0) for x in _turnover_top if x.get("name") in _tech_names)
        _tech_inflow = sum(float(x.get("zljlr_yi") or 0) for x in _net_top if x.get("name") in _tech_names)
        _inflow_outflow_ratio = _inflow_sum / abs(_outflow_sum) if _outflow_sum != 0 else 0
        # ETF数据
        _etf_path = os.path.join(DATA, f"{report_date}_etf_flow.json")
        _etf_data = None
        _etf_is_t1 = False
        _etf_date = ""
        if os.path.exists(_etf_path):
            try:
                _etf_data = json.load(open(_etf_path, encoding="utf-8"))
                _etf_is_t1 = bool(_etf_data.get("is_t1"))
                _etf_date = _etf_data.get("data_date") or ""
            except Exception:
                pass
        # ETF净申购/赎回TOP5
        _etf_inflow_rows = ""
        _etf_outflow_rows = ""
        if _etf_data:
            for i, e in enumerate((_etf_data.get("inflow") or [])[:5]):
                _etf_inflow_rows += f"<tr><td>{i+1}</td><td style='text-align:left'>{e.get('name','')}</td><td class='num' style='color:#16a34a'>+{e.get('week',0):.2f}亿</td><td class='num'>{e.get('total',0):.1f}亿</td></tr>"
            for i, e in enumerate((_etf_data.get("outflow") or [])[:5]):
                _etf_outflow_rows += f"<tr><td>{i+1}</td><td style='text-align:left'>{e.get('name','')}</td><td class='num' style='color:#d8392b'>{e.get('week',0):.2f}亿</td><td class='num'>{e.get('total',0):.1f}亿</td></tr>"
        _etf_note = f"<span style='color:#bf8700;font-size:11px'>（T-1数据 {_etf_date}，沪市份额接口异常）</span>" if _etf_is_t1 else ""
        # 资金换仓方向
        _buy_dirs = "、".join(x["name"] for x in _net_top[:3])
        _sell_dirs = "、".join(x["name"] for x in _net_bot[:3])
        # 半导体/通信ETF赎回 vs 主力净流入背离
        _etf_semiconductor_redeem = any("半导" in e.get("name","") or "科创" in e.get("name","") for e in (_etf_data.get("outflow") or [])) if _etf_data else False
        _main_semiconductor_inflow = any("半导" in x.get("name","") for x in _net_top[:2]) if _net_top else False
        _divergence_note = ""
        if _etf_semiconductor_redeem and _main_semiconductor_inflow:
            _divergence_note = ("<p style='margin:8px 0 0 0;font-size:12px;color:#4a9eff;line-height:1.6'>"
                                 "⚠ <b>资金背离信号</b>：ETF层面半导体/通信被净赎回（散户通过ETF获利了结），"
                                 "但主力资金大幅净流入半导体（大单直接买入个股），呈现「散户卖ETF、主力买个股」的背离格局。</p>")
        capital_flow_html = f"""
<div style="margin-top:18px;padding:16px 20px;background:#1a1f2e;border:1px solid #2a3348;border-radius:8px">
<h3 style="margin:0 0 12px 0;font-size:16px;color:#e2e8f0">💰 当日资金行为分析</h3>
<div class="kpis" style="margin-bottom:14px">
<div class="kpi"><div class="lab">全市场成交额</div><div class="val" style="color:#4a9eff">{_total_amt/10000:.2f}万亿</div></div>
<div class="kpi"><div class="lab">上涨/下跌</div><div class="val" style="color:#d8392b">{_up}<span style="color:#718096;font-size:14px"> / </span><span style="color:#16a34a">{_down}</span></div></div>
<div class="kpi"><div class="lab">涨停/跌停</div><div class="val" style="color:#d8392b">{_lu}<span style="color:#718096;font-size:14px"> / </span><span style="color:#16a34a">{_ld}</span></div></div>
<div class="kpi"><div class="lab">主力净流入/流出比</div><div class="val" style="color:#16a34a">{_inflow_outflow_ratio:.2f}</div></div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:14px">
<div>
<h4 style="margin:0 0 8px 0;font-size:13px;color:#e2e8f0">📊 量能集中度（板块四·成交额）</h4>
<ul style="margin:0;padding-left:18px;font-size:12px;color:#a0aec0;line-height:1.8">
<li>成交额TOP10合计 <b style="color:#e2e8f0">{_turnover_top10_sum:.0f}亿</b>，占全市场 <b style="color:#4a9eff">{_turnover_top10_sum/_total_amt*100:.1f}%</b></li>
<li>科技板块（半导/通信/元件/光学/消费电子）占TOP10 <b style="color:#4a9eff">{_tech_turnover/_turnover_top10_sum*100:.1f}%</b></li>
<li>半导体单板块 <b style="color:#e2e8f0">{_turnover_top[0]['turnover_yi'] if _turnover_top else 0:.0f}亿</b>，占全市场 <b style="color:#4a9eff">{(_turnover_top[0]['turnover_yi'] if _turnover_top else 0)/_total_amt*100:.1f}%</b></li>
</ul>
</div>
<div>
<h4 style="margin:0 0 8px 0;font-size:13px;color:#e2e8f0">💹 主力资金流向（板块五）</h4>
<ul style="margin:0;padding-left:18px;font-size:12px;color:#a0aec0;line-height:1.8">
<li>净流入TOP10合计 <b style="color:#16a34a">+{_inflow_sum:.1f}亿</b>，净流出TOP10合计 <b style="color:#d8392b">{_outflow_sum:.1f}亿</b></li>
<li>科技板块占净流入TOP10 <b style="color:#16a34a">{_tech_inflow/_inflow_sum*100:.1f}%</b></li>
<li>半导体单板块净流入 <b style="color:#16a34a">+{_net_top[0]['zljlr_yi'] if _net_top else 0:.1f}亿</b>，占净流入TOP10 <b style="color:#4a9eff">{(_net_top[0]['zljlr_yi'] if _net_top else 0)/_inflow_sum*100:.1f}%</b></li>
</ul>
</div>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:14px">
<div>
<h4 style="margin:0 0 8px 0;font-size:13px;color:#e2e8f0">📈 ETF净申购TOP5 {_etf_note}</h4>
<table style="width:100%;border-collapse:collapse;font-size:12px">
<tr style="background:#252d40"><th style="padding:4px 6px">#</th><th style="text-align:left">ETF</th><th>周净申购</th><th>累计份额</th></tr>
{_etf_inflow_rows or "<tr><td colspan=4 class='num'>数据缺失</td></tr>"}
</table>
</div>
<div>
<h4 style="margin:0 0 8px 0;font-size:13px;color:#e2e8f0">📉 ETF净赎回TOP5 {_etf_note}</h4>
<table style="width:100%;border-collapse:collapse;font-size:12px">
<tr style="background:#252d40"><th style="padding:4px 6px">#</th><th style="text-align:left">ETF</th><th>周净赎回</th><th>累计份额</th></tr>
{_etf_outflow_rows or "<tr><td colspan=4 class='num'>数据缺失</td></tr>"}
</table>
</div>
</div>
{_divergence_note}
<h4 style="margin:14px 0 6px 0;font-size:13px;color:#e2e8f0">📝 资金行为总结</h4>
<ol style="margin:0;padding-left:22px;font-size:12px;color:#c0cad8;line-height:1.8">
<li><b>资金高度集中于科技成长</b>：成交额TOP10中科技板块占近8成，主力净流入TOP10中科技板块占近7成，半导体单板块独占净流入近半，资金抱团科技主线极为明显。</li>
<li><b>典型「卖防御买成长」换仓</b>：主力大幅买入{_buy_dirs}，同时卖出{_sell_dirs}，净流入/流出比达{_inflow_outflow_ratio:.1f}，风险偏好显著回升。</li>
<li><b>量价配合健康</b>：全市场成交{_total_amt/10000:.2f}万亿放量，上涨{_up}家远多于下跌{_down}家，涨停{_lu}家/跌停仅{_ld}家，普涨格局下资金进攻意愿强。</li>
<li><b>ETF与主力资金背离需关注</b>：散户通过ETF赎回半导体/通信获利，但主力大单直接买入个股，短期分歧后若主力持续流入则行情延续，若主力也转为流出则需警惕回调。</li>
</ol>
<p style="margin:10px 0 0 0;font-size:11px;color:#4a5568">数据来源：板块四成交额+板块五主力净流入（同花顺thsdk当日）+ 板块二ETF净申赎（上交所/深交所，T-1标注见上）。仅客观复盘，不构成投资建议。</p>
</div>
"""
    except Exception as _e:
        capital_flow_html = f"<p style='color:#d8392b;font-size:12px'>[资金行为分析加载失败：{_e}]</p>"

    if only1:
        note = "<p class='note'>⚠️ 曲线为自建归档逐日累积，当前仅首日数据；随每日自动化运行，曲线将自动变长。</p>"
    else:
        note = ("<p class='note'>曲线为自建归档逐日累积（近 60 交易日）。"
                "历史点：涨跌家数/涨停跌停/创250日新高新低来自腾讯自选股 westock，"
                "全市场成交额来自东方财富妙想，指数收盘来自 westock K线；"
                "历史点新高/新低为创250日口径，末点（当日）为创一年口径（近似一致）；"
                "末点（当日）与报告其余部分同源（同花顺/通达信）。</p>")

    if wande:
        wande_stale = stale_attr(wande["dates"][-1])  # 平均股价数据日期非报告日则标红色感叹号
        wande_html = ("<h4>平均股价(880003) 日K · 等权全A代理（通达信）</h4>"
                      f"<div style=\"position:relative\"><canvas id='cWande'{wande_stale}></canvas></div>")
    else:
        wande_html = ("<p class='miss'>平均股价(880003) 日K：数据源暂不可达"
                      "（通达信行情服务器当前不可达，连上后由 collect_wande.py 经 pytdx 取数并覆盖本占位）。"
                      "说明：平均股价=全市场个股价格的等权平均，是「全A等权」的贴近代理。</p>")

    hn_disp = f"{hn} 只" if isinstance(hn, int) else "数据缺失"
    ln_disp = f"{ln} 只" if isinstance(ln, int) else "数据缺失"

    LEGEND_JS = r"""
// ---- 自定义图例 + 点击高亮对应曲线 ----
function chartColor(ds){
  var c = ds.borderColor;
  if(c===undefined || (typeof c==='string' && c.indexOf('rgba(0,0,0,0)')>=0)) c = ds.backgroundColor;
  return c;
}
function hexToRgba(c,a){
  if(typeof c!=='string') return c;
  var h=c.replace('#','');
  if(h.length===3) h=h.split('').map(function(x){return x+x;}).join('');
  if(h.length===6){var r=parseInt(h.substr(0,2),16),g=parseInt(h.substr(2,2),16),b=parseInt(h.substr(4,2),16);return 'rgba('+r+','+g+','+b+','+a+')';}
  return c;
}
function darken(c,f){
  if(typeof c!=='string'||c.charAt(0)!=='#') return c;
  var h=c.replace('#',''); if(h.length===3) h=h.split('').map(function(x){return x+x;}).join('');
  if(h.length!==6) return c;
  var r=parseInt(h.substr(0,2),16),g=parseInt(h.substr(2,2),16),b=parseInt(h.substr(4,2),16);
  r=Math.max(0,Math.round(r*f));g=Math.max(0,Math.round(g*f));b=Math.max(0,Math.round(b*f));
  return 'rgb('+r+','+g+','+b+')';
}
// RPS 自定义外部 tooltip：紧凑显示全部 4 个 RPS，值>87 红色
function rpsExternalTooltip(context){
  var t=context.tooltip;
  var el=document.getElementById('rpsTip');
  if(!el){
    el=document.createElement('div');
    el.id='rpsTip';
    el.style.cssText='position:absolute;pointer-events:none;background:rgba(255,255,255,.97);border:1px solid #e1e4e8;border-radius:8px;box-shadow:0 4px 14px rgba(0,0,0,.12);padding:8px 10px;font-size:13px;color:#1f2329;z-index:9999;max-width:260px;line-height:1.55;font-family:-apple-system,BlinkMacSystemFont,sans-serif';
    document.body.appendChild(el);
  }
  if(!t||t.opacity===0){ el.style.opacity=0; return; }
  var items=t.dataPoints;
  if(!items||!items.length){ el.style.opacity=0; return; }
  var board=items[0].label;
  var thr=87;
  var order=['rps50','rps20','rps10','rps5'];
  var map={};
  items.forEach(function(it){ map[it.dataset.label]=it.parsed.x; });
  var html='<div style="font-weight:600;margin-bottom:4px">'+board+'</div>';
  order.forEach(function(k){
    if(map[k]===undefined) return;
    var v=Number(map[k]);
    var col=v>thr?'#d8392b':'#1f2329';
    html+='<div style="color:'+col+'">■ '+k+': '+v.toFixed(2)+'</div>';
  });
  el.innerHTML=html;
  var ch=context.chart;
  var cv=ch.canvas;
  var rect=cv.getBoundingClientRect();
  el.style.opacity=1;
  // 优先用鼠标实际位置，回退到 caret 位置
  var mx = (ch._mouseX != null) ? ch._mouseX : (rect.left + t.caretX);
  var my = (ch._mouseY != null) ? ch._mouseY : (rect.top + t.caretY);
  var tipW = el.offsetWidth || 200;
  var tipH = el.offsetHeight || 100;
  var vw = window.innerWidth;
  var vh = window.innerHeight;
  // 默认在鼠标右下方15px
  var left = mx + 15 + window.pageXOffset;
  var top = my + 15 + window.pageYOffset;
  // 超出右边界则放到鼠标左侧
  if(mx + 15 + tipW > vw) left = mx - tipW - 15 + window.pageXOffset;
  // 超出下边界则放到鼠标上方
  if(my + 15 + tipH > vh) top = my - tipH - 15 + window.pageYOffset;
  el.style.left=left+'px';
  el.style.top=top+'px';
}
function setHighlight(id, idx){
  var ch=INSTANCES[id]; if(!ch) return;
  var same = ch._hlIdx===idx;
  ch._hlIdx = same?null:idx;
  ch.data.datasets.forEach(function(ds,i){
    if(ds.__ob===undefined) ds.__ob={bc:ds.borderColor,bg:ds.backgroundColor,bw:ds.borderWidth,pr:ds.pointRadius};
    var ob=ds.__ob;
    if(ch._hlIdx===null){
      ds.borderColor=ob.bc; ds.backgroundColor=ob.bg; ds.borderWidth=ob.bw; ds.pointRadius=ob.pr;
    } else if(i===ch._hlIdx){
      // 选中系列：保留原色，并加一条更深的描边 + 加粗，使其明显“跳”出来
      ds.borderColor = (ob.bc!==undefined && ob.bc!==null) ? ob.bc : darken(ob.bg, 0.5);
      ds.backgroundColor = ob.bg;
      ds.borderWidth = (typeof ob.bw==='number'?ob.bw:1) + 2.5;
      ds.pointRadius = (typeof ob.pr==='number'?ob.pr:2) + 2;
    } else {
      ds.borderColor=hexToRgba(ob.bc,0.10);
      ds.backgroundColor=hexToRgba(ob.bg,0.10);
      ds.borderWidth=1; ds.pointRadius=0;
    }
  });
  ch.update();
  var box=document.getElementById('leg_'+id);
  if(box) box.querySelectorAll('.chip').forEach(function(c){
    c.classList.toggle('active', !same && (+c.dataset.idx)===idx);
  });
}
function toggleDatasetHidden(id, idx){
  // 双击图例标签：隐藏/显示对应曲线
  var ch=INSTANCES[id]; if(!ch) return;
  var ds=ch.data.datasets[idx];
  if(!ds) return;
  ds.hidden = !ds.hidden;
  ch.update();
  var box=document.getElementById('leg_'+id);
  if(box){
    var chip=box.querySelector('.chip[data-idx="'+idx+'"]');
    if(chip) chip.classList.toggle('hidden', ds.hidden);
  }
}
function buildLegends(){
  var ids=['cTurn','cUp','cLim','cHL','cIdx','cStyle','cSec','cNet','cMargin','cMarginRatio','cJzxt','cTr','cRps'];
  ids.forEach(function(id){
    var ch=INSTANCES[id]; var box=document.getElementById('leg_'+id);
    if(!ch||!box) return;
    ch.data.datasets.forEach(function(ds,i){
      var col=chartColor(ds);
      if(col===undefined) return;
      if(typeof col==='string' && col.indexOf('rgba(0,0,0,0)')>=0) return;
      var chip=document.createElement('span');
      chip.className='chip'; chip.dataset.idx=i;
      var dot=document.createElement('span'); dot.className='dot'; dot.style.background=col;
      var txt=document.createElement('span'); txt.textContent=ds.label||('系列'+(i+1));
      chip.appendChild(dot); chip.appendChild(txt);
      chip.addEventListener('click',(function(i){return function(){setHighlight(id,i);};})(i));
      chip.addEventListener('dblclick',(function(i){return function(e){e.stopPropagation();toggleDatasetHidden(id,i);};})(i));
      box.appendChild(chip);
    });
  });
}
// ---- RPS 图表：悬停某一行列出该板块全部 RPS 值 ----
if(D.rps_chart_cfg){
  var rch=INSTANCES['cRps'];
  if(rch){
    // 横向条形图(indexAxis:y)用 index+axis:y，按鼠标所在行触发整行所有系列；
    // 值取 parsed.x（X轴=RPS数值），parsed.y 是行号索引。
    rch.options.interaction={mode:'index', axis:'y', intersect:false};
    rch.options.plugins.tooltip.enabled=false;
    rch.options.plugins.tooltip.mode='index';
    rch.options.plugins.tooltip.axis='y';
    rch.options.plugins.tooltip.intersect=false;
    rch.options.plugins.tooltip.external=rpsExternalTooltip;
    rch.update();
  }
}
buildLegends();
"""

    # 顶部分页导航（内嵌到 ctrl-bar 同一行左侧）
    if midday:
        nav_href, nav_label = "../", "查看收盘版"
    else:
        nav_href, nav_label = "noon/", "查看午间版"
    # 跨应用顶部导航栏（统一由 https://liaohao.cc/shared/nav.js 提供，深浅色随页面主题自适应）
    nav_html = '<script src="/shared/nav.js" defer></script>'

    # stock-a 控制按钮：通达信量化（保留不动）+ 重新抽数（同行右侧，无色描边）
    # 导航链接 + 控制按钮合为一行：左=导航链接，右=操作按钮
    ctrl_bar = ("""<div class="ctrl-bar">
<a class="navlink" href="{nav_href}">{nav_label}</a>
<span style="flex:1"></span>
<button id="tdxBtn" class="re-btn" onclick="copyAndOpenDoubao(this,'重新跑一次所有Task。')">📊 通达信量化</button>
<button id="reBtn" class="re-btn" onclick="copyAndOpenDoubao(this,'重新跑一次抽数。当前如果没收盘，就跑午间版。如果收盘了，就跑复盘版。')">🔄 重新抽数</button>
<span class="ctrl-status" id="saStatus"></span>
</div>
<style>
.ctrl-bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:8px 0 12px}
/* 导航文字链接 */
.navlink{display:inline-flex;align-items:center;gap:6px;text-decoration:none;color:#4a9eff;font-size:14px;font-weight:600;padding:6px 2px;transition:.15s}
.navlink:hover{color:#7bb8ff;text-decoration:underline}
/* 无色描边按钮 */
.re-btn{border:1.5px solid #4a5568;border-radius:10px;padding:9px 18px;font-size:14px;font-weight:600;color:#e2e8f0;cursor:pointer;background:transparent;transition:all .15s;white-space:nowrap}
.re-btn:hover{border-color:#4a9eff;color:#7bb8ff;background:rgba(74,158,255,.1)}
.re-btn:active{transform:scale(.97)}
.re-btn:disabled{opacity:.5;cursor:wait}
.ctrl-status{font-size:13px;color:#888;min-height:18px}
.ctrl-status.ok{color:#48c779;font-weight:600}
.ctrl-status.err{color:#f56565;font-weight:600}
.ctrl-status.busy{color:#ff8a3d}
{SA_CSS}
</style>
<script>
function saSet(t,m){document.querySelectorAll('.ctrl-status').forEach(function(e){e.textContent=m||'';e.className='ctrl-status '+(t||'')})}
function lastTradingDate(){
  var d=new Date();var dow=d.getDay();
  if(dow===0) d.setDate(d.getDate()-2);      /* Sun → Fri */
  else if(dow===6) d.setDate(d.getDate()-1);  /* Sat → Fri */
  var off=d.getTimezoneOffset()*60000;
  return new Date(d.getTime()-off).toISOString().slice(0,10);
}
function saTrigger(cmd, el, opts){
  opts=opts||{};
  var btns = el ? [el] : document.querySelectorAll('.re-btn');
  btns.forEach(function(b){b.disabled=true});
  saSet('busy','正在提交…');
  var tries=0;
  function done(ok,msg){saSet(ok?'ok':'err',msg);btns.forEach(function(b){b.disabled=false})}
  function attempt(){
    tries++;
    var url=location.origin+'/api/trigger?cmd='+encodeURIComponent(cmd);
    if(cmd==='reextract') url+='&type='+encodeURIComponent(PAGE_MODE);
    if(opts.date) url+='&date='+encodeURIComponent(opts.date);
    fetch(url,{method:'POST'})
      .then(function(r){return r.json()})
      .then(function(d){
        var label=(cmd==='tdx'?'通达信量化 Task1-5':'重新抽数'+(opts.date?'（'+opts.date+'）':''));
        if(d&&d.ok) done(true,'✅ 已提交：'+label+'。完成后邮件通知 hao.liao01@qq.com');
        else if(tries<3) setTimeout(attempt,800);
        else done(false,'❌ 提交失败：'+(d&&d.error||'未知错误，请稍后重试'));
      })
      .catch(function(e){ if(tries<3) setTimeout(attempt,800); else done(false,'❌ 网络错误：'+e.message) });
  }
  attempt();
}
function localToday(){var d=new Date();var off=d.getTimezoneOffset()*60000;return new Date(d.getTime()-off).toISOString().slice(0,10)}
function copyAndOpenDoubao(el,text){
  function done(){
    var orig=el.innerHTML;
    el.innerHTML='✅ 已复制，正在打开豆包…';
    el.disabled=true;
    setTimeout(function(){ window.location.href='doubao://'; }, 300);
    setTimeout(function(){ el.innerHTML=orig; el.disabled=false; }, 2500);
  }
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(done).catch(function(){ fallbackCopy(text,done); });
  } else { fallbackCopy(text,done); }
}
function fallbackCopy(text,cb){
  var ta=document.createElement('textarea');
  ta.value=text;ta.style.position='fixed';ta.style.opacity='0';
  document.body.appendChild(ta);ta.select();
  try{document.execCommand('copy');}catch(e){}
  document.body.removeChild(ta);cb();
}
{SA_JS}
</script>""")
    # ---- 红绿灯（抽数状态指示）：黄=进行中 绿=成功 红=有错 灰=离线/待机 ----
    sa_css = """
.sa-light{display:inline-flex;align-items:center;gap:7px;font-size:13px;font-weight:600;padding:4px 12px;border:1px solid #3a4560;border-radius:20px;background:#1e2536;cursor:default;white-space:nowrap;user-select:none;vertical-align:middle;margin-left:10px;color:#a0aec0}
.sa-dot{width:11px;height:11px;border-radius:50%;background:#cbd5e0;display:inline-block;flex:none;transition:background .3s,box-shadow .3s}
.sa-light.running .sa-dot{background:#f6c343;box-shadow:0 0 8px rgba(246,195,67,.85);animation:saBlink 1.2s infinite}
.sa-light.ok .sa-dot{background:#48c779;box-shadow:0 0 8px rgba(72,199,121,.7)}
.sa-light.err .sa-dot{background:#f56565;box-shadow:0 0 8px rgba(245,101,101,.7)}
.sa-light.off .sa-dot{background:#a0aec0}
@keyframes saBlink{0%,100%{opacity:1}50%{opacity:.4}}
/* hover 迷你K线弹窗 */
.sa-hover{cursor:help;text-decoration:underline dotted #aaa;text-underline-offset:3px}
.sa-hover:hover{background:#252d40;border-radius:4px}
#saKlineTip{position:fixed;pointer-events:none;z-index:99999;display:none;width:420px;height:340px;background:#151a28;border:1px solid #3a4560;border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.5);padding:10px 10px 6px;overflow:hidden}
#saKlineLbl{text-align:center;font-size:12px;font-weight:600;color:#e0e6ed;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#saKlineCv{width:100%;height:230px;display:block}
#saKlineFoot{text-align:center;font-size:10px;color:#718096;margin-top:2px}"""
    sa_js = """
function renderLight(d){
  var box=document.getElementById('saLight'),dot=document.getElementById('saDot'),txt=document.getElementById('saTxt');
  if(!box||!dot||!txt) return;
  function set(cls,text,title){box.className='sa-light '+(cls||'off');txt.textContent=text;if(title)box.title=title;else box.removeAttribute('title')}
  // 静态部署页：隧道未运行时显示快照就绪，避免被误解为数据离线
  var pageDate=(typeof REPORT_DATE!=='undefined'?REPORT_DATE:'')||'';
  var pageMode=(typeof PAGE_MODE!=='undefined'?PAGE_MODE:'')||'';
  var cutoffText=pageDate+(pageMode==='midday'?' 11:30':(pageMode==='close'?' 15:00':''));
  if(!d||!d.ok){set('ok','快照已就绪','数据截止：'+cutoffText+'；实时抽数服务未连接');return}
  var st=d.state,last=d.last;
  if(st==='running'){
    var rn=d.running||{},src=rn.note||'';
    var label=(rn.cmd==='tdx')?'通达信刷新':(rn.cmd==='external'?'定时自动化':'抽数');
    set('running',label+'进行中'+(src?'（'+src+'）':''),'开始于 '+(rn.started||'?'));
  }else if(st==='done_ok'){
    var warns=(last&&last.warns||[]);
    var title='最近完成：'+(last&&last.finished||'?')+'（耗时 '+(last&&last.elapsed_s!=null?last.elapsed_s+'s':'?')+'）'+(warns.length?'\\n提示：'+warns.join('；'):'');
    set('ok','抽数成功',title);
  }else if(st==='done_error'){
    var issues=(last&&last.issues||[]),err=last&&last.error||'';
    var isQ=issues.length>0&&!(last&&last.rc);
    var msg=isQ?'完成但有缺口':'抽数失败';
    var title='最近完成：'+(last&&last.finished||'?');
    if((last&&last.rc)!=null)title+='（rc='+last.rc+'，耗时 '+(last&&last.elapsed_s!=null?last.elapsed_s+'s':'?')+'）';
    if(issues.length)title+='\\n缺口：'+issues.join('；');
    if(err)title+='\\n错误：'+err;
    set('err',msg,title);
  }else{
    set('off','待机','暂无抽数记录');
  }
}
function pollStatus(){
  fetch(location.origin+'/api/status?ts='+Date.now())
    .then(function(r){return r.json()})
    .then(function(d){renderLight(d)})
    .catch(function(){renderLight(null)})
    .then(function(){setTimeout(pollStatus,30000)});
}
pollStatus();

/* ---- hover 迷你K线弹窗 ---- */
var saTip=null,saTimer=null,saCurReq=0;
function initSaHover(){
  if(saTip)return;
  saTip=document.createElement('div');saTip.id='saKlineTip';
  var lbl=document.createElement('div');lbl.id='saKlineLbl';
  var cv=document.createElement('canvas');cv.id='saKlineCv';
  var ft=document.createElement('div');ft.id='saKlineFoot';
  saTip.appendChild(lbl);saTip.appendChild(cv);saTip.appendChild(ft);
  document.body.appendChild(saTip);
  document.querySelectorAll('.sa-hover').forEach(function(td){
    td.addEventListener('mouseenter',function(e){clearTimeout(saTimer);saTimer=setTimeout(function(){showKlineTip(td,e)},300)});
    td.addEventListener('mouseleave',function(){clearTimeout(saTimer);hideKlineTip()});
    td.addEventListener('mousemove',function(e){posTip(e)});
  });
}
function showKlineTip(td,e){
  var code=td.getAttribute('data-code')||'';
  var mkt=td.getAttribute('data-mkt')||'';
  var isSector=td.getAttribute('data-sector')==='1';
  var histKey=td.getAttribute('data-hist-key')||'';
  var name=td.textContent.trim();
  var lbl=document.getElementById('saKlineLbl');
  lbl.textContent=name+' 加载中…';
  posTip(e);saTip.style.display='block';
  /* 优先用页面已嵌入的历史数据（指数、板块） */
  if(histKey){
    var found=null;
    if(histKey.indexOf('sec:')===0){
      var sc=histKey.slice(4);
      (D.rps&&D.rps.passed||[]).forEach(function(x){if(x.code===sc)found=x});
      if(!found&&(D.top_sectors||[]))D.top_sectors.forEach(function(x){if((x.code||'').replace('URFI','')===sc)found=x});
      if(!found&&D.net_inflow_sectors){
        var ni=D.net_inflow_sectors;
        (ni.top||[]).forEach(function(x){if((x.code||'').replace('URFI','')===sc)found=x});
        if(!found)(ni.bottom||[]).forEach(function(x){if((x.code||'').replace('URFI','')===sc)found=x});
      }
      if(!found&&D.pct_sectors){
        var ps=D.pct_sectors;
        (ps.top||[]).forEach(function(x){if((x.code||'').replace('URFI','')===sc)found=x});
        if(!found)(ps.bottom||[]).forEach(function(x){if((x.code||'').replace('URFI','')===sc)found=x});
      }
      if(!found&&D.mainline_kline&&D.mainline_kline[sc]){var _mk=D.mainline_kline[sc];found={hist_dates:_mk.dates,hist_close:_mk.close};}
    }else{
      (D.indices||[]).forEach(function(x){if(x.code===histKey)found=x});
      if(!found&&(D.style_indices||[]))D.style_indices.forEach(function(x){if(x.code===histKey)found=x});
    }
    if(found&&found.hist_dates&&found.hist_close){
      drawMiniKline(found.hist_dates,found.hist_close,null,null,null,name,'页面嵌入数据');
      return;
    }
  }
  /* 否则 fetch API */
  var myReq=++saCurReq;
  var url=location.origin+'/api/kline?lmt=150';
  if(isSector){url+='&secid='+encodeURIComponent(code)}
  else{url+='&code='+encodeURIComponent(code);if(mkt)url+='&mkt='+mkt}
  fetch(url).then(function(r){return r.json()}).then(function(d){
    if(myReq!==saCurReq)return;
    if(!d.ok){lbl.textContent=name+'：'+(d.error||'获取失败');return}
    drawMiniKline(d.dates,d.close,d.open,d.high,d.low,name,d.name||'');
  }).catch(function(){if(myReq===saCurReq)lbl.textContent=name+'：网络错误'});
}
function drawMiniKline(dates,close,open,high,low,name,foot){
  var cv=document.getElementById('saKlineCv');
  var lbl=document.getElementById('saKlineLbl');
  var ft=document.getElementById('saKlineFoot');
  lbl.textContent=name;
  var n=dates.length;if(!n){lbl.textContent=name+'：无K线数据';return}
  var dpr=window.devicePixelRatio||1;
  var w=cv.clientWidth||360,h=cv.clientHeight||230;
  cv.width=w*dpr;cv.height=h*dpr;
  var ctx=cv.getContext('2d');ctx.scale(dpr,dpr);
  ctx.clearRect(0,0,w,h);
  /* 计算价格范围 */
  var hasOHLC=open&&open.length===n;
  var mn=Infinity,mx=-Infinity;
  for(var i=0;i<n;i++){
    var lo=hasOHLC?Math.min(open[i],close[i],high[i],low[i]):close[i];
    var hi=hasOHLC?Math.max(open[i],close[i],high[i],low[i]):close[i];
    if(lo<mn)mn=lo;if(hi>mx)mx=hi;
  }
  if(mn===mx){mn-=1;mx+=1}
  var rng=mx-mn;mn-=rng*0.08;mx+=rng*0.08;
  var pad=12,pw=w-pad*2,ph=h-pad*2;
  var cw=hasOHLC?Math.max(2,(n>1?pw/(n-1):0)*0.55):0;
  var x0=pad+cw/2,xEnd=w-pad-cw/2;
  var xStep=n>1?(xEnd-x0)/(n-1):0;
  var yOf=function(v){return pad+ph-(v-mn)/(mx-mn)*ph};
  /* 网格线 */
  ctx.strokeStyle='#f0f0f0';ctx.lineWidth=1;
  for(var g=0;g<=4;g++){var y=pad+g*ph/4;ctx.beginPath();ctx.moveTo(x0,y);ctx.lineTo(x0+pw,y);ctx.stroke()}
  /* K线或折线 */
  var RED='#d8392b',GREEN='#16a34a';
  if(hasOHLC){
    for(var i=0;i<n;i++){
      var x=x0+i*xStep;
      var yO=yOf(open[i]),yC=yOf(close[i]),yH=yOf(high[i]),yL=yOf(low[i]);
      var up=close[i]>=open[i];
      ctx.strokeStyle=up?RED:GREEN;ctx.fillStyle=up?RED:GREEN;
      ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,yH);ctx.lineTo(x,yL);ctx.stroke();
      var top=Math.min(yO,yC),bh=Math.max(1,Math.abs(yC-yO));
      ctx.fillRect(x-cw/2,top,cw,bh);
    }
  }else{
    ctx.strokeStyle='#2b6cb0';ctx.lineWidth=1.5;ctx.beginPath();
    for(var i=0;i<n;i++){var x=x0+i*xStep,y=yOf(close[i]);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}
    ctx.stroke();
  }
  /* 末点标签 */
  var lastV=close[n-1];
  ctx.fillStyle='#1f2329';ctx.font='9px sans-serif';ctx.textAlign='right';
  ctx.fillText(lastV.toFixed(2),w-pad,pad+14);
  ctx.textAlign='left';
  ctx.fillText(dates[0],pad,h-pad-4);
  ctx.textAlign='right';ctx.fillText(dates[n-1],w-pad,h-pad-4);
  ft.textContent=foot||('近'+n+'个交易日');
}
function posTip(e){
  if(!saTip)return;
  var tw=420,th=340,off=14;
  var x=e.clientX+off,y=e.clientY-th-18;
  if(x+tw>window.innerWidth)x=e.clientX-tw-off;
  if(x<4)x=4;if(y<4)y=4;if(y+th>window.innerHeight)y=window.innerHeight-th-4;
  saTip.style.left=x+'px';saTip.style.top=y+'px';
}
function hideKlineTip(){if(saTip)saTip.style.display='none'}
if(document.readyState!=='loading')initSaHover();
else document.addEventListener('DOMContentLoaded',initSaHover);"""
    ctrl_bar = ctrl_bar.replace("{nav_href}", nav_href).replace("{nav_label}", nav_label)
    ctrl_bar = ctrl_bar.replace("{SA_CSS}", sa_css).replace("{SA_JS}", sa_js)
    pm = "midday" if midday else "close"
    title_label = "午间版复盘" if midday else "收盘版复盘"
    page_cfg = f"<script>var REPORT_DATE='{report_date}';var PAGE_MODE='{pm}';</script>"

    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_label} {report_date}（{report_weekday}）</title>
{chartjs_tag}
<style>
*{{box-sizing:border-box}} body{{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;
background:#0a0e1a;color:#e0e6ed;margin:0;padding:24px}}
.wrap{{max-width:1080px;margin:0 auto}}
h1{{font-size:24px;margin:0 0 4px;color:#fff}} .sub{{color:#718096;font-size:13px;margin-bottom:20px}}
.card{{background:#151a28;border:1px solid #252d40;border-radius:12px;padding:18px 20px;margin-bottom:18px;box-shadow:0 2px 8px rgba(0,0,0,.3)}}
.card h2{{font-size:18px;margin:0 0 14px;border-left:4px solid #4a9eff;padding-left:10px;color:#e0e6ed}}
.kpis{{display:flex;flex-wrap:wrap;gap:14px;margin-bottom:14px}}
.kpi{{flex:1;min-width:150px;background:#1e2536;border:1px solid #2a3348;border-radius:10px;padding:12px 14px}}
.kpi .lab{{font-size:12px;color:#718096}} .kpi .val{{font-size:22px;font-weight:700;margin-top:4px}}
canvas{{height:300px!important;max-height:300px;width:100%!important}}
#cRps{{height:1000px!important;max-height:1000px!important}}
body{{overflow-x:hidden}}
.grid2{{display:grid;grid-template-columns:1fr;gap:16px}}
@media(min-width:900px){{ .grid2{{grid-template-columns:1fr 1fr}} }}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{padding:7px 10px;border-bottom:1px solid #252d40;text-align:left;color:#e0e6ed}}
th{{background:#1e2536;color:#a0aec0;font-weight:600}} td.num{{text-align:right;font-variant-numeric:tabular-nums}}
table.sortable th{{cursor:pointer;user-select:none;position:relative;white-space:nowrap}}
table.sortable th:hover{{background:#2a3348}}
table.sortable th .arr{{color:#2b6cb0;font-size:10px;margin-left:4px}}
h4{{margin:6px 0;color:#e0e6ed}}
.note{{color:#e2b547;font-size:12px;background:#2d2316;border:1px solid #4a3a1a;padding:8px 10px;border-radius:6px}}
.miss{{color:#718096;font-style:italic}}
#zoomModal{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.78);z-index:999;align-items:center;justify-content:center;flex-direction:column}}
#zoomBody{{width:90vw;height:82vh;background:#151a28;border-radius:12px;padding:18px;box-sizing:border-box}}
#zoomBody canvas{{max-height:none!important;width:100%!important;height:100%!important}}
#zoomHint{{color:#fff;font-size:12px;margin-top:10px}}
#idxTip{{position:fixed;z-index:1000;display:none;pointer-events:none;background:rgba(21,26,40,.97);border:1px solid #3a4560;border-radius:8px;padding:8px 10px;font-size:12px;box-shadow:0 4px 14px rgba(0,0,0,.4);min-width:150px;max-width:240px;color:#e0e6ed}}
#idxTip .t-date{{font-weight:700;color:#a0aec0;margin-bottom:6px;border-bottom:1px solid #2a3348;padding-bottom:4px}}
#idxTip .t-row{{display:flex;justify-content:space-between;gap:14px;line-height:1.7}}
#idxTip .t-row b{{font-variant-numeric:tabular-nums}}
.chartLeg{{display:flex;flex-wrap:wrap;gap:6px;margin:2px 0 8px}}
.chartLeg .chip{{display:inline-flex;align-items:center;gap:5px;font-size:11px;line-height:1;padding:4px 9px;border:1px solid #3a4560;border-radius:14px;cursor:pointer;user-select:none;background:#1e2536;transition:.15s;color:#a0aec0}}
.chartLeg .chip:hover{{border-color:#4a9eff;color:#4a9eff}}
.chartLeg .chip.active{{background:#4a9eff;color:#fff;border-color:#4a9eff;box-shadow:0 1px 4px rgba(74,158,255,.4)}}
.chartLeg .chip.hidden{{opacity:0.35;text-decoration:line-through;background:#252d40}}
.chartLeg .chip .dot{{width:9px;height:9px;border-radius:50%;display:inline-block}}
/* TR情绪监测 时间范围切换按钮 */
.tr-range-btns{{display:flex;gap:6px;margin:4px 0 8px}}
.tr-range-btn{{font-size:12px;padding:4px 12px;border:1px solid #3a4560;border-radius:14px;background:#1e2536;color:#a0aec0;cursor:pointer;user-select:none;transition:.15s}}
.tr-range-btn:hover{{border-color:#4a9eff;color:#4a9eff}}
.tr-range-btn.active{{background:#4a9eff;color:#fff;border-color:#4a9eff;box-shadow:0 1px 4px rgba(74,158,255,.4)}}
/* 平均股价K线 时间范围切换按钮 */
.range-btns{{display:inline-flex;gap:6px;margin-left:12px;vertical-align:middle}}
.range-btn{{font-size:12px;padding:3px 10px;border:1px solid #3a4560;border-radius:12px;background:#1e2536;color:#a0aec0;cursor:pointer;user-select:none;transition:.15s}}
.range-btn:hover{{border-color:#4a9eff;color:#4a9eff}}
.range-btn.active{{background:#4a9eff;color:#fff;border-color:#4a9eff}}
/* 非当日数据红色感叹号标记 */
.stale-badge{{position:absolute;top:5px;right:6px;width:18px;height:18px;line-height:18px;text-align:center;border-radius:50%;background:#d8392b;color:#fff;font-weight:700;font-size:12px;cursor:help;z-index:5;box-shadow:0 1px 3px rgba(216,57,43,.4)}}
.stale-badge::after{{content:attr(data-tip);position:absolute;left:50%;top:140%;transform:translateX(-50%);white-space:nowrap;background:#d8392b;color:#fff;font-size:12px;font-weight:400;padding:4px 9px;border-radius:5px;opacity:0;pointer-events:none;transition:opacity .15s;z-index:50;box-shadow:0 2px 8px rgba(0,0,0,.2)}}
.stale-badge:hover::after{{opacity:1}}
/* 数据截止时间戳 */
.cutoff-banner{{position:relative;display:inline-block;background:#1a2540;color:#4a9eff;border:1px solid #2a3d66;border-radius:8px;padding:6px 12px;font-size:13px;font-weight:600;margin:0 0 14px}}
.cutoff-badge{{display:block;width:fit-content;max-width:100%;margin:2px 0 6px auto;font-size:11px;color:#a0aec0;background:#1e2536;border:1px solid #2a3348;border-radius:10px;padding:2px 8px;z-index:4}}
/* ── 历史趋势折叠区 ── */
.hist-section{{margin-top:16px;border-top:1px dashed #2a3348;padding-top:12px}}
.hist-toggle{{display:inline-flex;align-items:center;gap:6px;cursor:pointer;color:#4a9eff;font-size:13px;font-weight:600;user-select:none}}
.hist-toggle:hover{{color:#7bb8ff}}
.hist-toggle .arrow{{transition:transform .2s;display:inline-block}}
.hist-toggle.open .arrow{{transform:rotate(90deg)}}
.hist-body{{display:none;margin-top:10px;overflow-x:auto}}
.hist-body.open{{display:block}}
.hist-range-btns{{display:flex;gap:6px;margin-bottom:8px}}
.hist-range-btn{{font-size:11px;padding:3px 10px;border:1px solid #4a5568;border-radius:12px;background:#252d40;color:#e0e6ed;cursor:pointer;user-select:none;transition:.15s}}
.hist-range-btn:hover{{border-color:#7bb8ff;color:#7bb8ff;background:#2a3348}}
.hist-range-btn.active{{background:#4a9eff;color:#fff;border-color:#4a9eff}}
.hist-table{{font-size:12px;white-space:nowrap;border-collapse:collapse}}
.hist-table th{{background:#1e2536;color:#a0aec0;font-weight:600;padding:5px 6px;border-bottom:1px solid #252d40;text-align:center}}
.hist-table th:first-child{{text-align:left;position:sticky;left:0;background:#1e2536;z-index:2;white-space:nowrap}}
.hist-table td{{padding:4px 6px;border-bottom:1px solid #252d40;text-align:center;font-variant-numeric:tabular-nums;color:#e0e6ed}}
.hist-table td:first-child{{text-align:left;font-weight:600;position:sticky;left:0;background:#151a28;z-index:1;white-space:nowrap}}
.heat-cell{{border-radius:3px;min-width:44px}}
.hist-cell{{cursor:pointer;transition:box-shadow .1s}}
.hist-highlight{{box-shadow:inset 0 0 0 2px #2b6cb0;font-weight:700;position:relative;z-index:1}}
.hist-hint{{font-size:11px;color:#999;margin-bottom:6px}}
.heat-na{{color:#4a5568;background:#1a1f2e}}
.hl7-expand{{cursor:pointer;color:#7bb8ff;font-size:11px}}
.hl7-stocks{{display:none;font-size:11px;color:#666;padding:4px 0;text-align:left;white-space:normal;line-height:1.6}}
.hl7-stocks.open{{display:block}}
.hl7-stocks .tag{{display:inline-block;margin:1px 3px;padding:1px 6px;border-radius:3px;background:#252d40;color:#a0aec0}}
/* 行业分布标签云 */
.ind-dist{{margin:10px 0 14px;line-height:2}}
.ind-dist-title{{font-size:13px;font-weight:600;color:#a0aec0;margin-right:8px}}
.ind-tag{{display:inline-block;margin:2px 4px 2px 0;padding:3px 10px;border-radius:14px;background:#1e2536;border:1px solid #3a4560;font-size:12px;color:#a0aec0;cursor:default;transition:.15s}}
.ind-tag:hover{{background:#2a3348;border-color:#7bb8ff;color:#7bb8ff}}
.ind-tag b{{color:#7bb8ff;font-weight:700;margin-left:2px}}
.ind-tag-more{{display:inline-block;margin:2px 4px;padding:3px 8px;font-size:12px;color:#888}}
/* 时间范围拖动条 */
.range-slider-wrap{{margin:10px 0 6px;padding:0 4px}}
.range-slider-labels{{display:flex;justify-content:space-between;font-size:11px;color:#718096;margin-bottom:4px;padding:0 2px}}
.range-slider-quick{{display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap}}
.range-slider-quick button{{padding:3px 10px;font-size:11px;background:#1e2538;border:1px solid #3a4560;border-radius:4px;color:#94a3b8;cursor:pointer;transition:all .2s}}
.range-slider-quick button:hover{{background:#2a3550;border-color:#4a9eff;color:#cbd5e1}}
.range-slider-quick button.active{{background:#2563eb;border-color:#3b82f6;color:#fff}}
.range-slider{{position:relative;height:40px;border:1px solid #3a4560;border-radius:8px;background:#151a28;overflow:hidden}}
.range-slider .mini-chart{{position:absolute;top:0;left:0;width:100%;height:100%;z-index:1}}
.range-slider .mini-chart svg{{width:100%;height:100%;display:block}}
.range-slider .mask-left{{position:absolute;top:0;left:0;height:100%;background:rgba(10,14,24,.55);z-index:2;pointer-events:none}}
.range-slider .mask-right{{position:absolute;top:0;right:0;height:100%;background:rgba(10,14,24,.55);z-index:2;pointer-events:none}}
.range-slider .sel-box{{position:absolute;top:0;height:100%;z-index:2;pointer-events:none;background:rgba(74,158,255,.18);border:1px solid #6db5ff;box-shadow:inset 0 0 10px rgba(74,158,255,.2);box-sizing:border-box}}
.range-slider input[type=range]{{position:absolute;width:100%;height:40px;top:0;left:0;background:none;pointer-events:none;-webkit-appearance:none;appearance:none;z-index:3;margin:0;padding:0}}
.range-slider input[type=range]::-webkit-slider-runnable-track{{width:100%;height:100%;background:transparent;border:none;margin:0;padding:0}}
.range-slider input.rs-min{{z-index:5}}
.range-slider input[type=range]::-webkit-slider-thumb{{-webkit-appearance:none;appearance:none;box-sizing:border-box;width:7px;height:28px;margin:6px 0;border-radius:3px;background:linear-gradient(to right,rgba(255,255,255,.95),rgba(255,255,255,.95)) center/1px 10px no-repeat,linear-gradient(180deg,#7cb8ff 0%,#4a9eff 50%,#3b82f6 100%);cursor:pointer;pointer-events:auto;box-shadow:0 0 8px rgba(74,158,255,.7),0 2px 4px rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.3)}}
.range-slider input.rs-min::-webkit-slider-thumb{{transform:translateX(-50%)}}
.range-slider input.rs-max::-webkit-slider-thumb{{transform:translateX(50%)}}
.range-slider input[type=range]::-webkit-slider-thumb:hover{{background:linear-gradient(to right,rgba(255,255,255,1),rgba(255,255,255,1)) center/1px 10px no-repeat,linear-gradient(180deg,#a5d0ff 0%,#7bb8ff 50%,#60a5fa 100%);box-shadow:0 0 12px rgba(74,158,255,.9),0 2px 6px rgba(0,0,0,.4)}}
.range-slider input[type=range]::-moz-range-thumb{{width:7px;height:28px;margin:6px 0;border-radius:3px;background:linear-gradient(to right,rgba(255,255,255,.95),rgba(255,255,255,.95)) center/1px 10px no-repeat,linear-gradient(180deg,#7cb8ff 0%,#4a9eff 50%,#3b82f6 100%);cursor:pointer;pointer-events:auto;box-shadow:0 0 8px rgba(74,158,255,.7);border:1px solid rgba(255,255,255,.3)}}
body[data-pagemode="midday"] .hide-midday{{display:none!important}}
</style></head><body data-pagemode="{{pm}}"><div class="wrap">
{nav_html}
<h1>{title_label} {report_date}（{report_weekday}）<span class="sa-light off" id="saLight" title=""><span class="sa-dot" id="saDot"></span><span class="sa-txt" id="saTxt">状态加载中…</span></span></h1>
<div class="sub">数据来源：同花顺 hithink-finance（市场宽度/等权/指数/板块成交额/个股）＋ 通达信 TDX（板块 RPS 共振·概念板块指数 880xxx 本地概念清单，同花顺兜底）＋ 东方财富（主力净流入前10板块·当日）＋ 通达信 tdx_screener（个股新高/新低·当日，westock 兜底）· 仅客观复盘，不构成投资建议</div>
{cutoff_banner}
{page_cfg}
{ctrl_bar}
<div class="card"{market_stale}{cutoff_market}><h2>一、市场表现</h2>
<div class="kpis">
<div class="kpi"><div class="lab">全A等权涨跌幅</div><div class="val" style="color:{pct_color(wande_pct if wande_pct is not None else m.get('equal_weight_pct'))}">{fmt_pct(wande_pct if wande_pct is not None else m.get('equal_weight_pct'))}</div></div>
<div class="kpi"><div class="lab">涨跌幅中位数</div><div class="val" style="color:{pct_color(m.get('median_pct'))}">{fmt_pct(m.get('median_pct'))}</div></div>
<div class="kpi"><div class="lab">全市场总成交额</div><div class="val">{m.get('total_turnover_yi')}亿</div></div>
<div class="kpi"><div class="lab">上涨 / 下跌 / 平</div><div class="val" style="font-size:18px"><span style="color:{RED}">{int(float(m.get('up') or 0))}</span> / <span style="color:{GREEN}">{int(float(m.get('down') or 0))}</span> / <span style="color:#1f2329">{int(float(m.get('flat') or 0))}</span></div></div>
<div class="kpi"><div class="lab">涨停 / 跌停</div><div class="val" style="font-size:18px;color:{RED}">{int(float(m.get('limit_up') or 0))} <span style="color:#888">/</span> <span style="color:{GREEN}">{int(float(m.get('limit_down') or 0))}</span></div></div>
</div>
<div class="grid2">
<div><h4>全市场总成交额（亿元）</h4><div class="chartLeg" id="leg_cTurn"></div><canvas id="cTurn"{hist_stale}></canvas></div>
<div><h4>涨跌家数</h4><div class="chartLeg" id="leg_cUp"></div><canvas id="cUp"{hist_stale}></canvas></div>
</div>
<div class="grid2" style="margin-top:12px">
<div><h4>涨停 / 跌停家数</h4><div class="chartLeg" id="leg_cLim"></div><canvas id="cLim"{hist_stale}></canvas></div>
<div><h4>个股创新高 / 新低家数</h4><div class="chartLeg" id="leg_cHL"></div><canvas id="cHL"{hist_stale}></canvas></div>
</div>
<div style="margin-top:14px">{wande_html}</div>
{margin_html}
{jzxt_html}
{tr_html}
{note}
</div>

<div class="card"{market_stale}{cutoff_market}><h2>二、指数表现</h2>
<h4>宽基指数</h4>
<table><tr><th>指数</th><th>收盘</th><th>涨跌幅</th><th>成交额</th></tr>{idx_rows}</table>
<h4 style="margin-top:14px">宽基指数 · 近两年收盘走势（归一化 · 窗口首日=100）</h4>
<p class='note' style="color:#888">拖动下方滑块选择日期范围，自动以所选窗口首日为基准 100 比较强弱。</p>
<div class="chartLeg" id="leg_cIdx"></div><canvas id="cIdx"{idx_stale}></canvas>
<hr style="margin:20px 0 6px;border:none;border-top:1px solid #e5e8ec">
<h4 style="margin-top:8px">风格指数（短线风格 / 情绪）</h4>
<table><tr><th>风格</th><th>收盘</th><th>涨跌幅</th></tr>{style_rows}</table>
<p class='note'>风格指数数据来源：同花顺 hithink 特色指数（tszs，与上方宽基指数同源）；北证50 来自腾讯行情（hithink 指数接口不支持北交所）。「昨日涨停 / 昨日成交前10 / 创历史新高 / 近期创一年新高」为同花顺编制的风格指数：成分股为上一交易日对应股票（涨停股 / 成交额前十 / 创历史新高 / 近期创一年新高），指数反映其今日整体表现。</p>
<h4 style="margin-top:14px">风格指数 · 近两年收盘走势（归一化 · 窗口首日=100）</h4>
<p class='note'>风格指数点位差异大，拖动下方滑块选择日期范围，自动以所选窗口首日收盘为基准 100，直接比较各风格在该区间的相对强弱；鼠标悬停可查看各指数当日数值（按强弱降序排列）。历史收盘：同花顺特色指数走 hithink 历史接口（与宽基指数同源），北证50 走新浪日线。</p>
<div class="chartLeg" id="leg_cStyle"></div><canvas id="cStyle"{idx_stale}></canvas>
{style_drop_note}
{etf_html}
</div>

<div class="card"{sector_stale}{cutoff_sector}><h2>三、领涨 / 领跌板块前 10（行业 · 同花顺 thsdk·按涨跌幅）</h2>
<div class='grid2'>
<div><h4 style="color:{RED}">领涨 TOP15</h4><table><tr><th>#</th><th>板块</th><th>涨跌幅</th><th>成交额</th></tr>{pct_top_rows}</table></div>
<div><h4 style="color:{GREEN}">领跌 TOP15</h4><table><tr><th>#</th><th>板块</th><th>涨跌幅</th><th>成交额</th></tr>{pct_bot_rows}</table></div>
</div>
<p class='note'>按涨跌幅排序，数据来源：同花顺 thsdk（游客模式）行业板块，与后续成交额、主力净流入模块为同一套 90 行业口径。</p>
{sector_analysis_html}
<div class="hist-section"><div class="hist-toggle" onclick="toggleHist(this)"><span class="arrow">▶</span> 历史趋势 · 领涨/领跌板块（近20日）</div><div class="hist-body" data-mod="sec3_pct"></div></div>
</div>

<div class="card"{sector_stale}{cutoff_sector}><h2>四、成交量排名前 10 板块（行业 · 同花顺 thsdk·按真实成交额）</h2>
<table><tr><th>#</th><th>板块</th><th>成交额</th><th>成交额占比%</th><th>涨跌幅</th></tr>{sec_rows}</table>
<h4 style="margin-top:14px">前 10 板块：成交额（亿元 · 柱）与 成交额占比%（% · 线）</h4><div class="chartLeg" id="leg_cSec"></div><canvas id="cSec"></canvas>
<p class='note'>按真实成交额排序，数据来源：同花顺 thsdk（游客模式）行业板块，与第五节「主力净流入」为同一套 90 行业口径，可直接对照同一行业的成交额与资金流向。</p>
<div class="hist-section"><div class="hist-toggle" onclick="toggleHist(this)"><span class="arrow">▶</span> 历史趋势 · 板块成交额（近20日）</div><div class="hist-body" data-mod="sec3"></div></div>
</div>

<div class="card"{sector_stale}{cutoff_sector}><h2>{sec4_heading}</h2>
{sec4_badge}
<div class='grid2'>
<div><h4>主力净流入 TOP{net_top_n}</h4><table><tr><th>#</th><th>行业</th><th>净额</th><th>涨跌幅</th><th>成交额</th><th>成交额占比%</th></tr>{net_top_rows or "<tr><td colspan=4>数据缺失</td></tr>"}</table></div>
<div><h4>主力净流出 TOP{net_top_n}</h4><table><tr><th>#</th><th>行业</th><th>净额</th><th>涨跌幅</th><th>成交额</th><th>成交额占比%</th></tr>{net_bot_rows or "<tr><td colspan=4>数据缺失</td></tr>"}</table></div>
</div>
<h4 style="margin-top:14px">主力净流入前 {net_top_n} 板块（亿元）</h4><div class="chartLeg" id="leg_cNet"></div><canvas id="cNet"></canvas>
<p class='note'>按主力净流入排序，数据来源：{net_src}（与第四节成交额同为同花顺 90 行业口径，可直接对照）。本节即「资金流向」模块。</p>
{capital_flow_html}
<div class="hist-section"><div class="hist-toggle" onclick="toggleHist(this)"><span class="arrow">▶</span> 历史趋势 · 主力净流入（近20日）</div><div class="hist-body" data-mod="sec4"></div></div>
</div>

<div class="card"{rps_stale}{cutoff_rps}><h2>六、强势板块 · RPS 共振（RPS≥87）</h2>
{rps_html}
<div class="hist-section"><div class="hist-toggle" onclick="toggleHist(this)"><span class="arrow">▶</span> 历史趋势 · RPS 达标数（近20日）</div><div class="hist-body" data-mod="sec5"></div></div>
</div>

<div class="card"{market_stale}{cutoff_market}><h2>七、涨停 / 跌停个股</h2>
<div class="kpis">
<div class="kpi"><div class="lab">涨停</div><div class="val" style="color:{RED}">{int(float(m.get('limit_up') or 0))}</div></div>
<div class="kpi"><div class="lab">跌停</div><div class="val" style="color:{GREEN}">{int(float(m.get('limit_down') or 0))}</div></div>
</div>
{lu_ind_dist}
{ld_ind_dist}
<h4 style="margin-top:14px">涨停（{len(lu_list)} 只 · 含行业 / 概念板块，按行业排序）</h4>
<table><tr><th>#</th><th>名称</th><th>代码</th><th>涨跌幅</th><th>成交额</th><th>一级行业</th><th>行业</th><th>概念板块</th></tr>{lu_rows}</table>
<h4 style="margin-top:14px">跌停（{len(ld_list)} 只 · 含行业 / 概念板块，按行业排序）</h4>
<table><tr><th>#</th><th>名称</th><th>代码</th><th>涨跌幅</th><th>成交额</th><th>一级行业</th><th>行业</th><th>概念板块</th></tr>{ld_rows}</table>
<p class='note'>涨停 / 跌停口径：当日涨跌幅 ≥9.9% / ≤−9.9%（同花顺快照，已含科创 / 创业 / 北交所不同涨跌幅限制的股票）。行业 / 概念板块来自同花顺分类映射，未匹配到的显示「—」。</p>
<div class="hist-section"><div class="hist-toggle" onclick="toggleHist(this)"><span class="arrow">▶</span> 历史趋势 · 涨停/跌停行业分布（近20日）</div><div class="hist-body" data-mod="ind_limit_both"></div></div>
</div>

<div class="card"{market_stale}{cutoff_market}><h2>八、成交量排名前 100 个股</h2>
{stk_ind_dist}
<table id="stkVolTable"><tr><th>#</th><th>名称</th><th>代码</th><th>成交额</th><th>涨跌幅</th><th>一级行业</th><th>行业</th><th>概念板块</th></tr>{stk_rows}{stk_rows_rest}</table>
<p style="margin-top:10px"><span id="foldToggle" style="cursor:pointer;color:#2b6cb0;font-size:13px">展开 第 51–100 名（点击折叠 / 展开）</span></p>
<p class='note'>按当日真实成交额降序，取前 100；51–100 默认折叠，点击展开。点击表头可排序（含折叠行一并参与排序）。数据来源：同花顺 hithink-finance。</p>
<div class="hist-section"><div class="hist-toggle" onclick="toggleHist(this)"><span class="arrow">▶</span> 历史趋势 · 前100行业分布（近20日）</div><div class="hist-body" data-mod="ind_top100"></div></div>
</div>

<div class="card hide-midday"{hl_stale}{cutoff_hl}><h2>九、个股新高 / 新低</h2>
<div class="kpis">
<div class="kpi"><div class="lab">创一年新高</div><div class="val" style="color:{RED}">{hn_disp}</div></div>
<div class="kpi"><div class="lab">创一年新低</div><div class="val" style="color:{GREEN}">{ln_disp}</div></div>
</div>
{hn_ind_dist}
{ln_ind_dist}
<p class='note'>{hl_note}</p>
<h4 style="margin-top:14px">创一年新高（{len(hn_stocks)} 只 · 含行业 / 概念板块，按行业排序）</h4>
<table><tr><th>#</th><th>名称</th><th>代码</th><th>涨跌幅</th><th>成交额</th><th>一级行业</th><th>行业</th><th>概念板块</th></tr>{hn_rows}</table>
<h4 style="margin-top:14px">创一年新低（{len(ln_stocks)} 只 · 含行业 / 概念板块，按行业排序）</h4>
<table><tr><th>#</th><th>名称</th><th>代码</th><th>涨跌幅</th><th>成交额</th><th>一级行业</th><th>行业</th><th>概念板块</th></tr>{ln_rows}</table>
<div class="hist-section"><div class="hist-toggle" onclick="toggleHist(this)"><span class="arrow">▶</span> 历史趋势 · 新高/新低行业分布（近20日）</div><div class="hist-body" data-mod="ind_high_low_both"></div></div>
</div>

<div class="card hide-midday"{kd_stale}{cutoff_kd}><h2>十、口袋 &amp; 领先 &amp; 断层</h2>
<p class='note'>自定义板块「口袋」（{len(kd_only)} 只）+「领先股」（{len(ld_only)} 只）+「净利润断层」（{len(dc_only)} 只），行业分类来自通达信研究行业三级分类（本地文件），统计按一级行业合并。</p>
{kd_ind_dist}
<h4 style="margin-top:14px">口袋支点个股（{len(kd_only)} 只）</h4>
<table><tr><th>#</th><th>名称</th><th>代码</th><th>成交额</th><th>一级行业</th><th>二级行业</th><th>三级行业</th></tr>{kd_stock_rows}</table>
<h4 style="margin-top:14px">领先股个股（{len(ld_only)} 只）</h4>
<table><tr><th>#</th><th>名称</th><th>代码</th><th>成交额</th><th>一级行业</th><th>二级行业</th><th>三级行业</th></tr>{leading_stock_rows}</table>
<h4 style="margin-top:14px">净利润断层个股（{len(dc_only)} 只）</h4>
<table><tr><th>#</th><th>名称</th><th>代码</th><th>成交额</th><th>一级行业</th><th>二级行业</th><th>三级行业</th></tr>{fault_stock_rows}</table>
<div class="hist-section"><div class="hist-toggle" onclick="toggleHist(this)"><span class="arrow">▶</span> 历史趋势 · 口袋+领先+断层一级行业分布（近20日）</div><div class="hist-body" data-mod="ind_koudai"></div></div>
</div>

<div class="card"{market_stale}{cutoff_market}><h2>十一、行业热度得分</h2>
<p class='note'>强势榜：涨停(1分) + 成交量前100(2分) + 新高(2分) + 口袋+领先+断层(2分)；弱势榜：跌停(1分) + 新低(2分)。按一级行业汇总得分，降序排列。</p>
<div class="grid2">
<div>
<h4 style="margin:0 0 8px;color:#d8392b">强势榜</h4>
<table><tr><th>#</th><th>一级行业</th><th>得分</th><th>个股数</th></tr>{strong_rows}</table>
</div>
<div>
<h4 style="margin:0 0 8px;color:#16a34a">弱势榜</h4>
<table><tr><th>#</th><th>一级行业</th><th>得分</th><th>个股数</th></tr>{weak_rows}</table>
</div>
</div>
<div class="hist-section"><div class="hist-toggle" onclick="toggleHist(this)"><span class="arrow">▶</span> 历史趋势 · 强势/弱势行业得分（近20日）</div><div class="hist-body" data-mod="ind_score_both"></div></div>
</div>

{ml_card}

</div>

<div id="zoomModal"><div id="zoomBody"></div><div id="zoomHint">点击空白处或按 Esc 关闭</div></div>
<div id="idxTip"></div>

<script>
const D = {json.dumps(payload, ensure_ascii=False)};
const RED='{RED}', GREEN='{GREEN}', GREY='{GREY}';
/* ===== 折线末端最新值标注（全局注册，所有 Chart 生效；纯柱图不标，混合图只标折线）===== */
function __endFmt(n,d){{
  if(d&&typeof d.endFmt==='function'){{try{{var t=d.endFmt(n);if(t!=null)return t;}}catch(e){{}}}}
  // 整数（涨跌停/新高新低/家数等）直接显示整数，避免 65.00
  if(Math.abs(n-Math.round(n))<0.005) return Math.round(n).toLocaleString();
  var a=Math.abs(n);
  if(a>=1000) return Math.round(n).toLocaleString();
  if(a>=100) return n.toFixed(1);
  return n.toFixed(2);
}}
const endValuePlugin={{
  id:'endValue',
  _lineDs(chart){{
    const ct=chart.config.type||'line', out=[];
    (chart.data.datasets||[]).forEach((d,di)=>{{ const dt=d.type||ct; if(dt!=='bar'&&d.hidden!==true) out.push([d,di]); }});
    return out;
  }},
  _lastValid(d){{
    const a=d.data||[];
    for(let k=a.length-1;k>=0;k--){{const x=a[k]; if(x!=null && !(typeof x==='number'&&isNaN(x))) return [k,x];}}
    return null;
  }},
  afterDatasetsDraw(chart){{
    try{{
      const ctx=chart.ctx, lds=this._lineDs(chart);
      if(!lds.length)return;
      ctx.save();ctx.font='bold 10px -apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif';
      ctx.textAlign='right';ctx.textBaseline='middle';
      const ca=chart.chartArea||{{}};
      const topLimit=(ca.top!=null?ca.top:0)+2;
      const bottomLimit=(ca.bottom!=null?ca.bottom:chart.height)-2;
      const leftEdge=(ca.right!=null?ca.right:chart.width-60)+6;
      const maxRight=(chart.width||ca.right+80)-4;
      // 第一遍：收集所有末端标签位置
      const labels=[];
      lds.forEach(([d,di])=>{{
        const lv=this._lastValid(d); if(!lv)return;
        const i=lv[0],raw=lv[1];
        const meta=chart.getDatasetMeta(di); if(!meta||meta.hidden||!meta.data[i])return;
        let val=(raw&&typeof raw==='object')?(raw.y!=null?raw.y:(raw.close!=null?raw.close:null)):raw;
        val=Number(val); if(isNaN(val))return;
        const txt=__endFmt(val,d);
        let col=d.endColor||d.borderColor;
        if(!col||col==='transparent'||/0,\s*0,\s*0,\s*0/.test(String(col)))col='#e6edf7';
        const px=meta.data[i].x, py=meta.data[i].y, w=ctx.measureText(txt).width;
        let tx=leftEdge+w;
        if(tx>maxRight) tx=maxRight;
        // 垂直：优先点上方，超上边界则放下方
        let labelY=py-0.5;
        if(py-7<topLimit){{ labelY=py+10; }}
        labels.push({{tx,labelY,txt,col,w,val}});
      }});
      // 边界clamp
      labels.forEach(l=>{{
        if(l.labelY<topLimit+7) l.labelY=topLimit+7;
        if(l.labelY>bottomLimit-7) l.labelY=bottomLimit-7;
      }});
      // 防重叠：按数值降序（数值大的标签在上），从下往上推，重叠时上方标签上移14px
      // （从上往下推会在底部边界clamp时失效：下方标签下移后又被clamp回原位，导致完全重叠）
      labels.sort((a,b)=>b.val-a.val);
      for(let k=labels.length-2;k>=0;k--){{
        if(labels[k].labelY+14 > labels[k+1].labelY){{
          labels[k].labelY=labels[k+1].labelY-14;
          if(labels[k].labelY<topLimit+7) labels[k].labelY=topLimit+7;
        }}
      }}
      // 第二遍：绘制
      labels.forEach(l=>{{
        const bx=l.tx-l.w-3, bw=l.w+6, bh=14, rr=3, by=l.labelY-7;
        ctx.beginPath();
        ctx.moveTo(bx+rr,by);ctx.arcTo(bx+bw,by,bx+bw,by+bh,rr);ctx.arcTo(bx+bw,by+bh,bx,by+bh,rr);
        ctx.arcTo(bx,by+bh,bx,by,rr);ctx.arcTo(bx,by,bx+bw,by,rr);ctx.closePath();
        ctx.fillStyle='rgba(12,17,30,.82)';ctx.fill();
        ctx.fillStyle=l.col;ctx.fillText(l.txt,l.tx,l.labelY);
      }});
      ctx.restore();
    }}catch(e){{}}
  }}
}};
if(typeof Chart!=='undefined')Chart.register(endValuePlugin);
/* RPS横向条形图：每根柱子右端标数值 */
const rpsBarLabelPlugin={{
  id:'rpsBarLabel',
  afterDatasetsDraw(chart){{
    try{{
      if(chart.config.type!=='bar')return;
      const ctx=chart.ctx;
      ctx.save();
      ctx.font='bold 10px -apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif';
      ctx.textAlign='left';ctx.textBaseline='middle';
      chart.data.datasets.forEach((ds,di)=>{{
        const meta=chart.getDatasetMeta(di);
        if(!meta||meta.hidden)return;
        const col=ds.backgroundColor||'#e6edf7';
        meta.data.forEach((el,i)=>{{
          const v=ds.data[i];
          if(v==null||isNaN(Number(v)))return;
          ctx.fillStyle=col;
          ctx.fillText(Number(v).toFixed(1), el.x+4, el.y);
        }});
      }});
      ctx.restore();
    }}catch(e){{}}
  }}
}};
const verticalLinePlugin = {{
  id:'verticalLine',
  afterDraw(chart){{
    const isH = chart.options && chart.options.indexAxis === 'y';
    const ctx = chart.ctx;
    ctx.save();
    ctx.lineWidth = 1.5; ctx.strokeStyle = 'rgba(0,0,0,.4)';
    ctx.setLineDash([4,3]);
    if(isH){{
      let y = null;
      const tt = chart.tooltip;
      if(tt && tt.getActiveElements && tt.getActiveElements().length) y = tt.getActiveElements()[0].element.y;
      else if(chart._hy != null) y = chart._hy;
      if(y == null){{ ctx.restore(); return; }}
      ctx.beginPath();
      ctx.moveTo(chart.chartArea.left, y); ctx.lineTo(chart.chartArea.right, y);
      ctx.stroke();
    }} else {{
      let x = null;
      if(chart._hx != null) x = chart._hx;
      else {{ const tt = chart.tooltip; if(tt && tt.getActiveElements && tt.getActiveElements().length) x = tt.getActiveElements()[0].element.x; }}
      if(x == null){{ ctx.restore(); return; }}
      ctx.beginPath();
      ctx.moveTo(x, chart.chartArea.top); ctx.lineTo(x, chart.chartArea.bottom);
      ctx.stroke();
    }}
    ctx.restore();
  }}
}};
const ZONES=[{{name:'极冰',value:10,color:'#00BFFF'}},{{name:'冰点',value:25,color:'#4169E1'}},{{name:'中枢',value:50,color:'#FFB7C5'}},{{name:'过热',value:75,color:'#FFD700'}},{{name:'高潮',value:90,color:'#ff0000'}}];
const zonePlugin={{id:'zones',afterDraw(chart){{const ys=chart.scales.y;if(!ys)return;const ctx=chart.ctx;ctx.save();ctx.font='11px sans-serif';ZONES.forEach(z=>{{const y=ys.getPixelForValue(z.value);ctx.beginPath();ctx.moveTo(chart.chartArea.left,y);ctx.lineTo(chart.chartArea.right,y);ctx.lineWidth=1;ctx.setLineDash([5,4]);ctx.strokeStyle=z.color;ctx.stroke();ctx.setLineDash([]);ctx.fillStyle=z.color;ctx.fillText(z.name,chart.chartArea.left+4,y-3);}});ctx.restore();}}}};
const TR_ZONES=[{{name:'沸点87',value:87,color:'#d8392b'}},{{name:'相变50',value:50,color:'#ca8a04'}},{{name:'冰点13',value:13,color:'#4169E1'}}];
const trZonePlugin={{id:'trZones',afterDraw(chart){{const ys=chart.scales.y;if(!ys)return;const ctx=chart.ctx;ctx.save();ctx.font='11px sans-serif';TR_ZONES.forEach(z=>{{const y=ys.getPixelForValue(z.value);ctx.beginPath();ctx.moveTo(chart.chartArea.left,y);ctx.lineTo(chart.chartArea.right,y);ctx.lineWidth=1;ctx.setLineDash([5,4]);ctx.strokeStyle=z.color;ctx.stroke();ctx.setLineDash([]);ctx.fillStyle=z.color;ctx.fillText(z.name,chart.chartArea.left+4,y-3);}});ctx.restore();}}}};
const WANDE = (D.wande && D.wande.ok) ? D.wande : null;
let wandeCurData = WANDE; // 当前显示的K线数据（可被切换范围更新）
const candlePlugin = {{
  id:'candle',
  afterDraw(chart){{
    if(!wandeCurData) return;
    const xs=chart.scales.x, ys=chart.scales.y;
    const n=wandeCurData.close.length;
    if(!n) return;
    const step = n>1 ? Math.abs(xs.getPixelForValue(1)-xs.getPixelForValue(0)) : 10;
    const w = Math.max(1.5, step*0.6);
    const ctx=chart.ctx;
    for(let i=0;i<n;i++){{
      const x=xs.getPixelForValue(i);
      const yO=ys.getPixelForValue(wandeCurData.open[i]);
      const yC=ys.getPixelForValue(wandeCurData.close[i]);
      const yH=ys.getPixelForValue(wandeCurData.high[i]);
      const yL=ys.getPixelForValue(wandeCurData.low[i]);
      const up = wandeCurData.close[i] >= wandeCurData.open[i];
      ctx.strokeStyle = up ? RED : GREEN;
      ctx.fillStyle = up ? RED : GREEN;
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x,yH); ctx.lineTo(x,yL); ctx.stroke();
      const top=Math.min(yO,yC), hgt=Math.max(1,Math.abs(yC-yO));
      ctx.fillRect(x-w/2, top, w, hgt);
    }}
  }}
}};
const INSTANCES = {{}};
function cloneCfg(config){{
  // 克隆「干净、可序列化」的配置，专供大图放大使用。
  // chart.config 是 Chart.js 的 Config 包装对象（内含 chart 自引用），JSON 序列化会抛循环引用错误，
  // 因此必须在创建图表时单独存一份纯数据副本。
  try {{ return {{type:config.type, data:JSON.parse(JSON.stringify(config.data)), options:JSON.parse(JSON.stringify(config.options||{{}}))}}; }} catch(e){{ return null; }}
}}
function attachHover(ch, cv, onMove){{
  let rafId = null;
  const isH = ch.options && ch.options.indexAxis === 'y';
  cv.addEventListener('mousemove', (e)=>{{
    ch._mouseX = e.clientX;
    ch._mouseY = e.clientY;
    const rect = cv.getBoundingClientRect();
    const labels = (ch.data && ch.data.labels) || [];
    const mx = e.clientX - rect.left;
    if(isH){{
      // 横向图：横线对齐到最近 data point（保持原行为，不影响 RPS 原生 tooltip 对齐）
      const ys = ch.scales.y; if(!ys) return;
      let v = null, idx = null;
      const points = ch.getElementsAtEventForMode(e, 'index', {{intersect:false}}, true);
      if(points && points.length){{ idx = points[0].index; v = points[0].element.y; }}
      if(v !== ch._hy){{
        ch._hy = v;
        if(rafId) cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(()=>{{ ch.update('none'); rafId=null; }});
      }}
      if(onMove) onMove((idx!=null && idx>=0 && idx<labels.length)?idx:null, e);
    }} else {{
      // 纵向图：竖线精确跟随鼠标 X（CSS 像素，与 Chart.js 内部一致，不受 dpr 影响）；移出绘图区则隐藏
      const xs = ch.scales.x; if(!xs) return;
      const left = ch.chartArea.left, right = ch.chartArea.right;
      let x = null, idx = null;
      if(mx >= left && mx <= right){{
        x = mx;
        const points = ch.getElementsAtEventForMode(e, 'index', {{intersect:false}}, true);
        if(points && points.length){{ idx = points[0].index; }}
      }}
      if(x !== ch._hx){{
        ch._hx = x;
        if(rafId) cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(()=>{{ ch.update('none'); rafId=null; }});
      }}
      if(onMove) onMove((idx!=null && idx>=0 && idx<labels.length)?idx:null, e);
    }}
  }});
  cv.addEventListener('mouseleave', ()=>{{
    if(isH){{
      if(ch._hy!==null){{ ch._hy=null; if(rafId) cancelAnimationFrame(rafId);
        const _te = ch.options.plugins.tooltip.enabled; ch.update('none'); ch.options.plugins.tooltip.enabled=_te; }}
    }} else {{
      if(ch._hx!==null){{ ch._hx=null; if(rafId) cancelAnimationFrame(rafId);
        const _te = ch.options.plugins.tooltip.enabled; ch.update('none'); ch.options.plugins.tooltip.enabled=_te; }}
    }}
    if(onMove) onMove(null, null);
  }});
}}
function makeChart(id, config, onMove){{
  config.options = config.options || {{}};
  config.options.interaction = {{mode:'index', intersect:false}};
  config.options.plugins = config.options.plugins || {{}};
  config.options.plugins.verticalLine = true;
  // 关闭原生图例（改用上方可点击高亮的自定义图例 chip）
  config.options.plugins.legend = Object.assign({{}}, config.options.plugins.legend||{{}}, {{display:false}});
  config.options.plugins.tooltip = Object.assign({{
    enabled:true, titleFont:{{size:13,weight:'bold'}}, bodyFont:{{size:12}},
    padding:10, filter:(item)=> item.parsed !== null && item.parsed !== undefined
  }}, config.options.plugins.tooltip||{{}});
  config.plugins = (config.plugins||[]).concat([verticalLinePlugin]);
  // 折线/含折线的混合图：右侧预留空白，让末端数值标签落在曲线之外、不遮挡曲线
  const _eds=(config.data&&config.data.datasets)||[];
  const _hasLine = config.type==='line' || _eds.some(d=>d&&d.type==='line');
  if(_hasLine){{
    config.options.layout=config.options.layout||{{}};
    config.options.layout.padding=Object.assign({{right:64,top:18}}, config.options.layout.padding||{{}});
  }}
  const ch = new Chart(document.getElementById(id), config);
  INSTANCES[id] = ch;
  // 保存干净可序列化配置用于大图放大（见 cloneCfg 说明）
  ch.__zoomCfg = cloneCfg(config);
  ch.__needsCandle = (id==='cWande');
  ch.__needsZone = (id==='cJzxt');
  ch.__needsTrZone = (id==='cTr');
  const cv = document.getElementById(id);
  cv.style.cursor='zoom-in';
  cv.addEventListener('dblclick', ()=>openZoom(id));
  attachHover(ch, cv, onMove);
  return ch;
}}
function lineCfg(labels, datasets, opts){{ return {{type:'line', data:{{labels,datasets}}, options:Object.assign({{responsive:true,elements:{{point:{{hitRadius:8}}}},plugins:{{legend:{{labels:{{font:{{size:11}},color:'#a0aec0'}}}}}},scales:{{x:{{ticks:{{maxTicksLimit:12,font:{{size:10}},color:'#718096'}},grid:{{display:false}}}},y:{{ticks:{{font:{{size:10}},color:'#718096'}},grid:{{color:'#252d40'}}}}}}}}, opts||{{}})}}; }}
function barCfg(labels, label, data, color, rot){{ return {{type:'bar', data:{{labels,datasets:[{{label,data,backgroundColor:color, barPercentage:0.2, categoryPercentage:0.5}}]}}, options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{font:{{size:10}},maxRotation:rot||0,color:'#718096'}}}},y:{{ticks:{{font:{{size:10}},color:'#718096'}},grid:{{color:'#252d40'}}}}}}}}}}; }}
/* 时间范围拖动条 */
function attachRangeSlider(chartId, origLabels, origDataArrays, onUpdate, defaultDays, maxDays, showQuickBtns, miniColor){{
  miniColor = miniColor || '#60a5fa';
  try {{
    const canvas = document.getElementById(chartId);
    if(!canvas || !canvas.parentNode) {{ console.log('attachRangeSlider: canvas not found for', chartId); return; }}
    // 限制最大显示范围
    let labels = origLabels;
    let dataArrays = origDataArrays;
    if(maxDays && origLabels.length > maxDays){{
      const startIdx = origLabels.length - maxDays;
      labels = origLabels.slice(startIdx);
      dataArrays = origDataArrays.map(arr => arr.slice(startIdx));
    }}
    const wrap = document.createElement('div');
    wrap.className = 'range-slider-wrap';
    const quickBtnsHtml = showQuickBtns === false ? '' : '<div class="range-slider-quick"><button data-days="60">60天</button><button data-days="120">近半年</button><button data-days="250">近一年</button><button data-days="500">近两年</button></div>';
    wrap.innerHTML = '<div class="range-slider-labels"><span class="rs-start"></span><span class="rs-end"></span></div>' + quickBtnsHtml + '<div class="range-slider"><div class="mini-chart"></div><div class="mask-left"></div><div class="sel-box"></div><div class="mask-right"></div><input type="range" class="rs-min" min="0" max="100" value="0"><input type="range" class="rs-max" min="0" max="100" value="100"></div>';
    if(canvas.nextSibling) {{
      canvas.parentNode.insertBefore(wrap, canvas.nextSibling);
    }} else {{
      canvas.parentNode.appendChild(wrap);
    }}
    const minInput = wrap.querySelector('.rs-min');
    const maxInput = wrap.querySelector('.rs-max');
    const sliderEl = wrap.querySelector('.range-slider');
    const miniChart = wrap.querySelector('.mini-chart');
    const maskLeft = wrap.querySelector('.mask-left');
    const maskRight = wrap.querySelector('.mask-right');
    const selBox = wrap.querySelector('.sel-box');
    const startLabel = wrap.querySelector('.rs-start');
    const endLabel = wrap.querySelector('.rs-end');
    
    // 绘制曲线缩影（用第一条数据）
    const miniData = dataArrays[0] || [];
    if(miniData.length > 1){{
      const validVals = miniData.filter(v => v !== null && v !== undefined && !isNaN(v));
      if(validVals.length > 0){{
        const minVal = Math.min(...validVals);
        const maxVal = Math.max(...validVals);
        const range = maxVal - minVal || 1;
        const w = 1000, h = 100;
        const pointArr = miniData.map((v, i) => {{
          if(v === null || v === undefined || isNaN(v)) return null;
          const x = (i / (miniData.length - 1)) * w;
          const y = h - ((v - minVal) / range) * (h - 10) - 5;
          return {{x, y}};
        }}).filter(p => p !== null);
        const points = pointArr.map(p => p.x + ',' + p.y).join(' ');
        // 填充路径：曲线 + 底部闭合
        const firstP = pointArr[0], lastP = pointArr[pointArr.length - 1];
        const fillPath = 'M' + firstP.x + ',' + firstP.y + ' L' + pointArr.map(p => p.x + ',' + p.y).join(' L') + ' L' + lastP.x + ',' + h + ' L' + firstP.x + ',' + h + ' Z';
        const gradId = 'miniGrad_' + chartId;
        miniChart.innerHTML = '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none">' +
          '<defs><linearGradient id="' + gradId + '" x1="0" y1="0" x2="0" y2="1">' +
          '<stop offset="0%" stop-color="' + miniColor + '" stop-opacity="0.4"/>' +
          '<stop offset="100%" stop-color="' + miniColor + '" stop-opacity="0.05"/>' +
          '</linearGradient></defs>' +
          '<path d="' + fillPath + '" fill="url(#' + gradId + ')"/>' +
          '<polyline points="' + points + '" fill="none" stroke="' + miniColor + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>' +
          '</svg>';
      }}
    }}
    // 设置默认显示范围
    if(defaultDays && labels.length > defaultDays){{
      const defaultStart = Math.round((1 - defaultDays / labels.length) * 100);
      minInput.value = defaultStart;
    }}
    function update(){{
      let minVal = parseInt(minInput.value);
      let maxVal = parseInt(maxInput.value);
      if(minVal > maxVal - 2){{ minVal = maxVal - 2; maxVal = minVal + 2; }}
      // 用像素精确定位，使取值线与滑动按钮中心竖线对齐
      const W = sliderEl.clientWidth;
      const tw = 7; // thumb宽度（box-sizing:border-box，含border）
      // webkit中thumb原生左边缘=p/100*(W-tw)；min用translateX(-50%)、max用translateX(+50%)
      const minX = (minVal / 100) * (W - tw);              // min thumb中心
      const maxX = (maxVal / 100) * (W - tw) + tw;         // max thumb中心
      maskLeft.style.width = minX + 'px';
      maskRight.style.width = (W - maxX) + 'px';
      selBox.style.left = minX + 'px';
      selBox.style.width = (maxX - minX) + 'px';
      const total = labels.length;
      const startIdx = Math.floor(minVal / 100 * total);
      const endIdx = Math.min(total, Math.ceil(maxVal / 100 * total));
      startLabel.textContent = labels[startIdx];
      endLabel.textContent = labels[endIdx - 1];
      const ch = INSTANCES[chartId];
      if(ch){{
        ch.data.labels = labels.slice(startIdx, endIdx);
        ch.data.datasets.forEach((ds, i)=>{{ ds.data = dataArrays[i].slice(startIdx, endIdx); }});
        ch.update();
      }}
      if(onUpdate) onUpdate(startIdx, endIdx);
    }}
    minInput.addEventListener('input', update);
    maxInput.addEventListener('input', update);
    window.addEventListener('resize', update);
    // 快捷日期按钮
    const quickBtns = wrap.querySelectorAll('.range-slider-quick button');
    quickBtns.forEach(btn => {{
      btn.addEventListener('click', function() {{
        const days = parseInt(this.dataset.days);
        if(labels.length > days) {{
          const startPct = Math.round((1 - days / labels.length) * 100);
          minInput.value = startPct;
          maxInput.value = 100;
        }} else {{
          minInput.value = 0;
          maxInput.value = 100;
        }}
        quickBtns.forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        update();
      }});
    }});
    update();
    console.log('attachRangeSlider: created for', chartId, 'with', labels.length, 'points (orig:', origLabels.length, ', defaultDays:', defaultDays, ', maxDays:', maxDays, ')');
  }} catch(e) {{
    console.error('attachRangeSlider error for', chartId, ':', e);
  }}
}}

const H=D.hist;
makeChart('cTurn', lineCfg(H.dates, [{{label:'总成交额(亿)',data:H.turnover,borderColor:'#60a5fa',backgroundColor:'rgba(96,165,250,.15)',fill:true,pointRadius:1,tension:.25,borderWidth:1.5}}]));
attachRangeSlider('cTurn', H.dates, [H.turnover], null, 60, 500);
// 裁剪掉数据数组前面全为 null 的前缀：成交额已用长期历史补全（491天），
// 但涨跌家数/涨跌停/新高新低只有 hithink 采集期（近期）有值，不裁剪会被挤到图表最右侧
function trimNullPrefix(labels, arrays){{
  let start = labels.length;
  arrays.forEach(a=>{{ for(let i=0;i<a.length;i++){{ if(a[i]!==null && a[i]!==undefined){{ start=Math.min(start,i); break; }} }} }});
  return {{labels: labels.slice(start), arrays: arrays.map(a=>a.slice(start))}};
}}
const upT = trimNullPrefix(H.dates, [H.up, H.down]);
makeChart('cUp', lineCfg(upT.labels, [
  {{label:'上涨',data:upT.arrays[0],borderColor:RED,backgroundColor:RED,fill:false,pointRadius:1,tension:.25,borderWidth:1}},
  {{label:'下跌',data:upT.arrays[1],borderColor:GREEN,backgroundColor:GREEN,fill:false,pointRadius:1,tension:.25,borderWidth:1}}]));
const limT = trimNullPrefix(H.dates, [H.lu, H.ld]);
makeChart('cLim', lineCfg(limT.labels, [
  {{label:'涨停',data:limT.arrays[0],borderColor:RED,fill:false,pointRadius:1,tension:.25,borderWidth:1}},
  {{label:'跌停',data:limT.arrays[1],borderColor:GREEN,fill:false,pointRadius:1,tension:.25,borderWidth:1}}]));
const hlT = trimNullPrefix(H.dates, [H.hn, H.ln]);
const hlDs=[];
if(hlT.arrays[0].some(x=>x!==null)) hlDs.push({{label:'新高',data:hlT.arrays[0],borderColor:RED,fill:false,pointRadius:1,tension:.25,borderWidth:1}});
if(hlT.arrays[1].some(x=>x!==null)) hlDs.push({{label:'新低',data:hlT.arrays[1],borderColor:GREEN,fill:false,pointRadius:1,tension:.25,borderWidth:1}});
if(hlDs.length) makeChart('cHL', lineCfg(hlT.labels, hlDs));
else document.getElementById('cHL').parentElement.innerHTML='<p class="miss">新高/新低：暂无历史数据</p>';
const idxColors=['#2b6cb0','#d8392b','#16a34a','#9333ea','#0891b2','#ca8a04','#db2777','#475569'];
// 重要指数：一律归一化（首日=100），消除点位绝对值差异，便于比强弱
const idxRaw = D.idx_lines.map(l=>l.data.slice());
const idxNorm = idxRaw.map(arr=>{{ const b=arr[0]; return arr.map(v=> v==null?null:+(v/b*100).toFixed(2)); }});
makeChart('cIdx', lineCfg(D.idx_dates, D.idx_lines.map((l,i)=>({{
  label:l.name, data:idxNorm[i], borderColor:idxColors[i%8], fill:false, pointRadius:0, tension:.2, borderWidth:1.5
}}))), renderIdxTip);
INSTANCES['cIdx'].options.scales.y.title={{display:true,text:'归一化（窗口首日=100）',font:{{size:10}}}};
INSTANCES['cIdx'].options.plugins.tooltip.enabled=false;  // 用自定义 #idxTip 代替原生 tooltip
// 滑动范围变化时：按窗口内第一天重新归一化（窗口起点=100）
function idxRenorm(startIdx,endIdx){{
  const ch=INSTANCES['cIdx']; if(!ch) return;
  ch.data.datasets.forEach((ds,i)=>{{
    const win=idxRaw[i].slice(startIdx,endIdx);
    const base=win.find(v=>v!==null&&v!==undefined&&!isNaN(v));
    ds.data=base?win.map(v=>(v===null||v===undefined||isNaN(v))?null:+(v/base*100).toFixed(2)):[];
  }});
  ch.update();
}}
attachRangeSlider('cIdx', D.idx_dates, idxRaw, idxRenorm, 250, 500, true, '#60a5fa');
// 鼠标悬停时渲染各指数当日数值，按强弱（值）降序排列
function renderIdxTip(idx, e){{
  const tip=document.getElementById('idxTip');
  if(idx==null || idx<0){{ tip.style.display='none'; return; }}
  const ch=INSTANCES['cIdx']; if(!ch) return;
  const rows=ch.data.datasets
    .map(d=>({{name:d.label, val:d.data[idx]}}))
    .filter(r=>r.val!==null && r.val!==undefined)
    .sort((a,b)=>b.val-a.val);
  const date=D.idx_dates[idx];
  tip.innerHTML='<div class="t-date">'+date+'</div>'+rows.map(r=>'<div class="t-row"><span>'+r.name+'</span><b>'+Number(r.val).toFixed(2)+'</b></div>').join('');
  tip.style.display='block';
  const cv=ch.canvas, rect=cv.getBoundingClientRect();
  const v=ch._hx;
  let lx=(v!=null?rect.left+v:e.clientX)+14, ly=e.clientY+14;
  const w=tip.offsetWidth||160;
  if(lx+w>window.innerWidth) lx=(v!=null?rect.left+v:e.clientX)-w-14;
  if(ly+tip.offsetHeight>window.innerHeight) ly=e.clientY-tip.offsetHeight-14;
  tip.style.left=lx+'px';
  tip.style.top=ly+'px';
}}
// 风格指数曲线（归一化 · 首日=100）：数据由后端按宽基指数同一 60 日窗口对齐（D.style_lines）
if(D.style_lines && D.style_lines.length){{
  const sRaw=D.style_lines.map(l=>l.data.slice());
  const sNorm=sRaw.map(arr=>{{ const b=arr.find(v=>v!==null); return b?arr.map(v=>v==null?null:+(v/b*100).toFixed(2)):[]; }});
  const styleColors=['#2b6cb0','#d8392b','#16a34a','#9333ea','#0891b2','#ca8a04','#db2777','#475569'];
  const sch=makeChart('cStyle', lineCfg(D.style_dates, D.style_lines.map((l,i)=>({{
    label:l.name, data:sNorm[i], borderColor:styleColors[i%styleColors.length], fill:false, pointRadius:0, tension:.2, borderWidth:1.5
  }}))), renderStyleTip);
  sch._sd=D.style_dates;  // 供自定义 tooltip 取日期
  sch.options.scales.y.title={{display:true,text:'归一化（窗口首日=100）',font:{{size:10}}}};
  sch.options.plugins.tooltip.enabled=false;  // 用自定义 #idxTip 代替原生 tooltip
  // 滑动范围变化时：按窗口内第一天重新归一化（窗口起点=100），再比较各指数强弱
  function styleRenorm(startIdx,endIdx){{
    const ch=INSTANCES['cStyle']; if(!ch) return;
    ch.data.datasets.forEach((ds,i)=>{{
      const win=sRaw[i].slice(startIdx,endIdx);
      const base=win.find(v=>v!==null&&v!==undefined&&!isNaN(v));
      ds.data=base?win.map(v=>(v===null||v===undefined||isNaN(v))?null:+(v/base*100).toFixed(2)):[];
    }});
    ch.update();
  }}
  attachRangeSlider('cStyle', D.style_dates, sRaw, styleRenorm, 250, 500, true, '#2b6cb0');
}} else {{
  document.getElementById('cStyle').parentElement.innerHTML='<p class="miss">风格指数曲线：暂无历史数据（本次采集后自动累积）</p>';
}}
function renderStyleTip(idx, e){{
  const tip=document.getElementById('idxTip');
  if(idx==null || idx<0){{ tip.style.display='none'; return; }}
  const ch=INSTANCES['cStyle']; if(!ch) return;
  const rows=ch.data.datasets
    .map(d=>({{name:d.label, val:d.data[idx]}}))
    .filter(r=>r.val!==null && r.val!==undefined)
    .sort((a,b)=>b.val-a.val);
  const date=(ch._sd||[])[idx];
  tip.innerHTML='<div class="t-date">'+date+'</div>'+rows.map(r=>'<div class="t-row"><span>'+r.name+'</span><b>'+Number(r.val).toFixed(2)+'</b></div>').join('');
  tip.style.display='block';
  const cv=ch.canvas, rect=cv.getBoundingClientRect();
  const v=ch._hx;
  let lx=(v!=null?rect.left+v:e.clientX)+14, ly=e.clientY+14;
  const w=tip.offsetWidth||160;
  if(lx+w>window.innerWidth) lx=(v!=null?rect.left+v:e.clientX)-w-14;
  if(ly+tip.offsetHeight>window.innerHeight) ly=e.clientY-tip.offsetHeight-14;
  tip.style.left=lx+'px';
  tip.style.top=ly+'px';
}}
makeChart('cSec', {{
  type:'bar',
  data:{{labels:D.sec_bar.map(s=>s.name), datasets:[
    {{type:'bar', label:'成交额(亿)', data:D.sec_bar.map(s=>s.v), backgroundColor:'#2b6cb0', yAxisID:'y', barPercentage:0.2, categoryPercentage:0.5}},
    {{type:'line', label:'成交额占比%', data:D.sec_bar.map(s=>s.ratio), borderColor:'#d8392b', backgroundColor:'#d8392b', yAxisID:'y1', pointRadius:3, borderWidth:2, tension:.25}}
  ]}},
  options:{{responsive:true, plugins:{{legend:{{display:false}}}}, scales:{{
    x:{{ticks:{{font:{{size:10}},maxRotation:60}}}},
    y:{{position:'left', grid:{{color:'#252d40'}}, title:{{display:true,text:'成交额(亿)',font:{{size:10}}}}}},
    y1:{{position:'right', grid:{{drawOnChartArea:false}}, title:{{display:true,text:'成交额占比%',font:{{size:10}}}}, ticks:{{font:{{size:10}}}}}}
  }}}}
}});
makeChart('cNet', barCfg(D.net_top.map(s=>s.name),'主力净流入(亿)',D.net_top.map(s=>s.v),'#d8392b',60));

// 万得全A(881001) 日K（市值加权全A代理，非等权）
function getWandeSliceByIdx(startIdx, endIdx){{
  if(!WANDE) return null;
  const pct = [];
  for(let i = startIdx; i < endIdx; i++){{
    if(i > 0 && WANDE.close[i-1] !== 0){{
      pct.push((WANDE.close[i] - WANDE.close[i-1]) / WANDE.close[i-1] * 100);
    }} else {{
      pct.push(null);
    }}
  }}
  return {{
    dates: WANDE.dates.slice(startIdx, endIdx),
    open: WANDE.open.slice(startIdx, endIdx),
    close: WANDE.close.slice(startIdx, endIdx),
    high: WANDE.high.slice(startIdx, endIdx),
    low: WANDE.low.slice(startIdx, endIdx),
    pct: pct
  }};
}}
if(WANDE){{
  let wandeCur = getWandeSliceByIdx(0, WANDE.dates.length);
  wandeCurData = wandeCur;
  const wcfg={{type:'line',
    data:{{labels:wandeCur.dates, datasets:[{{data:wandeCur.close, pointRadius:0, borderColor:'rgba(0,0,0,0)', showLine:false}}]}},
    options:{{responsive:true, maintainAspectRatio:false,
      interaction:{{mode:'index', intersect:false}},
      layout:{{padding:{{right:64,top:18}}}},
      plugins:{{legend:{{display:false}}, verticalLine:true,
        tooltip:{{enabled:true, titleFont:{{size:13,weight:'bold'}}, bodyFont:{{size:12}}, padding:10,
          callbacks:{{label:(c)=>{{
            const p = wandeCur.pct[c.dataIndex];
            const pStr = p !== null ? ((p > 0 ? '+' : '') + p.toFixed(2) + '%') : '-';
            return ['开 '+wandeCur.open[c.dataIndex].toFixed(2),'收 '+wandeCur.close[c.dataIndex].toFixed(2),'涨跌幅 '+pStr,'高 '+wandeCur.high[c.dataIndex].toFixed(2),'低 '+wandeCur.low[c.dataIndex].toFixed(2)];
          }}}}}}}},
      scales:{{x:{{offset:true,ticks:{{maxTicksLimit:12,font:{{size:10}}}},grid:{{display:false}}}},y:{{ticks:{{font:{{size:10}}}},grid:{{color:'#252d40'}}}}}}
    }},
    plugins:[verticalLinePlugin, candlePlugin]
  }};
  const wch=new Chart(document.getElementById('cWande'), wcfg);
  INSTANCES['cWande']=wch;
  wch.__zoomCfg = cloneCfg(wcfg);
  wch.__needsCandle = true;
  const wcv=document.getElementById('cWande');
  wcv.style.cursor='zoom-in';
  wcv.addEventListener('dblclick', ()=>openZoom('cWande'));
  attachHover(wch, wcv);
  // 时间范围拖动条
  attachRangeSlider('cWande', WANDE.dates, [WANDE.close], function(startIdx, endIdx){{
    wandeCur = getWandeSliceByIdx(startIdx, endIdx);
    wandeCurData = wandeCur;
  }}, 250, 600);
}}
// 沪深两市融资余额（亿元）
const mg = D.margin;
if(mg && mg.dates && mg.dates.length){{
  const mgCfg={{type:'line',data:{{labels:mg.dates,datasets:[{{label:'融资余额(亿)',data:mg.margin_balance,borderColor:'#a78bfa',backgroundColor:'rgba(167,139,250,.15)',fill:true,pointRadius:0,tension:.25,borderWidth:1.8}}]}},options:{{responsive:true,plugins:{{legend:{{labels:{{font:{{size:11}}}}}},tooltip:{{enabled:true,callbacks:{{label:(c)=>'融资余额: '+Number(c.parsed.y).toLocaleString()+' 亿'}}}}}},scales:{{x:{{ticks:{{maxTicksLimit:12,font:{{size:10}}}},grid:{{display:false}}}},y:{{ticks:{{font:{{size:10}},callback:(v)=>v>=10000?(v/10000).toFixed(1)+'万':v}},grid:{{color:'#252d40'}},title:{{display:true,text:'亿元',font:{{size:10}}}}}}}}}}}};
  makeChart('cMargin', mgCfg);
  attachRangeSlider('cMargin', mg.dates, [mg.margin_balance], null, 120, 250, true, '#a78bfa');
}}
// 两融交易占市场总成交比例（%）
const mr = D.margin_ratio;
if(mr && mr.dates && mr.dates.length){{
  const mrCfg={{type:'line',data:{{labels:mr.dates,datasets:[{{label:'两融交易占比(%)',data:mr.ratio,borderColor:'#c084fc',backgroundColor:'rgba(192,132,252,.15)',fill:true,pointRadius:0,tension:.25,borderWidth:1.8}}]}},options:{{responsive:true,plugins:{{legend:{{labels:{{font:{{size:11}}}}}},tooltip:{{enabled:true,callbacks:{{label:(c)=>'两融交易占比: '+Number(c.parsed.y).toFixed(2)+'%'}}}}}},scales:{{x:{{ticks:{{maxTicksLimit:12,font:{{size:10}}}},grid:{{display:false}}}},y:{{ticks:{{font:{{size:10}},callback:(v)=>v+'%'}},grid:{{color:'#252d40'}},title:{{display:true,text:'%',font:{{size:10}}}}}}}}}}}};
  makeChart('cMarginRatio', mrCfg);
  attachRangeSlider('cMarginRatio', mr.dates, [mr.ratio], null, 120, 250, true, '#c084fc');
}}
// 均占系统 均线占比（市场宽度）日线
const jz=D.jzxt;
if(jz && jz.dates && jz.dates.length){{
  const jzSeries=[['cdx','5日','#ff0000'],['dx','13日','#4169E1'],['zx','50日','#ff8c00'],['cx','120日','#8B008B']];
  const jzDs=jzSeries.filter(s=>(jz[s[0]]||[]).length).map(s=>({{label:s[1],data:jz[s[0]],borderColor:s[2],backgroundColor:s[2],fill:false,pointRadius:0,tension:.2,borderWidth:1.5}}));
  const jzCfg={{type:'line',data:{{labels:jz.dates,datasets:jzDs}},options:{{responsive:true,plugins:{{legend:{{labels:{{font:{{size:11}}}}}},tooltip:{{enabled:true,callbacks:{{label:(c)=>c.dataset.label+': '+Number(c.parsed.y).toFixed(2)+'%'}}}}}},scales:{{x:{{ticks:{{maxTicksLimit:12,font:{{size:10}}}},grid:{{display:false}}}},y:{{min:0,max:100,ticks:{{font:{{size:10}}}},grid:{{color:'#252d40'}},title:{{display:true,text:'占比 %',font:{{size:10}}}}}}}}}},plugins:[zonePlugin]}};
  makeChart('cJzxt', jzCfg);
  const jzOrigData = jzSeries.filter(s=>(jz[s[0]]||[]).length).map(s=>jz[s[0]]);
  attachRangeSlider('cJzxt', jz.dates, jzOrigData, null, 120, 250);
}}
// TR情绪监测（通达信扩展数据 38/39/40：HTR10/HTR20/HTR40）
const trFull = D.tr_emotion;
if(trFull && trFull.dates && trFull.dates.length){{
  const TR_RANGES = {{'120':120,'half':180,'year':365,'2year':730}};
  function trSlice(range){{
    const days = TR_RANGES[range] || 180;
    const lastDate = new Date(trFull.dates[trFull.dates.length-1]);
    const cutoff = new Date(lastDate);
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString().slice(0,10);
    let si = trFull.dates.findIndex(d => d >= cutoffStr);
    return si < 0 ? 0 : si;
  }}
  let trStart = 0;
  const trSeries=[['htr10','HTR10(短期)','#ff6b6b'],['htr20','HTR20(中期)','#2b6cb0'],['htr40','HTR40(长期)','#9333ea']];
  function trDs(start){{
    return trSeries.map(s=>({{label:s[1],data:(trFull[s[0]]||[]).slice(start),borderColor:s[2],backgroundColor:s[2],fill:false,pointRadius:0,tension:.2,borderWidth:1.5}}));
  }}
  const trCfg={{type:'line',data:{{labels:trFull.dates,datasets:trDs(0)}},options:{{responsive:true,plugins:{{legend:{{labels:{{font:{{size:11}}}}}},tooltip:{{enabled:true,callbacks:{{label:(c)=>c.dataset.label+': '+Number(c.parsed.y).toFixed(2)+'%'}}}}}},scales:{{x:{{ticks:{{maxTicksLimit:12,font:{{size:10}}}},grid:{{display:false}}}},y:{{min:0,max:100,ticks:{{font:{{size:10}}}},grid:{{color:'#252d40'}},title:{{display:true,text:'TR占比 %',font:{{size:10}}}}}}}}}},plugins:[trZonePlugin]}};
  makeChart('cTr', trCfg);
  const trOrigData = trSeries.map(s=>trFull[s[0]]||[]);
  attachRangeSlider('cTr', trFull.dates, trOrigData, null, 120, 250);
}}
// 板块 RPS 共振（东方财富·全市场板块）：横向分组条形图
if(D.rps_chart_cfg){{
  D.rps_chart_cfg.plugins=(D.rps_chart_cfg.plugins||[]).concat([rpsBarLabelPlugin]);
  makeChart('cRps', D.rps_chart_cfg);
}}

{LEGEND_JS}

// ---- 真正用数据重新渲染的大图（新建 Canvas + Chart 实例）----
var __zoomInst = null;   // 当前放大态的 Chart 实例
var __zoomId   = null;   // 当前放大态的原始图表 id

function openZoom(id){{
  var m=document.getElementById('zoomModal');
  if(m.style.display==='flex') return;
  var ch=INSTANCES[id]; if(!ch) return;

  // 用创建时保存的「干净可序列化」配置（ch.__zoomCfg）作为大图数据源。
  // 切勿使用 ch.config：它是 Chart.js 的 Config 包装对象，内含 chart 自引用，
  // JSON.stringify 会抛“循环引用”错误，导致大图打不开。
  var box=document.getElementById('zoomBody');
  var cfg=null;
  if(ch.__zoomCfg){{ try{{ cfg=JSON.parse(JSON.stringify(ch.__zoomCfg)); }}catch(e){{cfg=null;}} }}
  if(!cfg){{ try{{ cfg=JSON.parse(JSON.stringify((ch.config&&ch.config._config)||ch.config)); }}catch(e){{cfg=null;}} }}
  if(!cfg){{ m.style.display='flex'; box.innerHTML='<p style="color:#f00;padding:20px">该图表暂不支持放大</p>'; return; }}

  // 重建插件（JSON 序列化会丢失插件函数对象，这里按原图需要重新挂回）
  cfg.plugins = [verticalLinePlugin];
  if(ch.__needsCandle) cfg.plugins.push(candlePlugin);
  if(ch.__needsZone) cfg.plugins.push(zonePlugin);
  if(ch.__needsTrZone) cfg.plugins.push(trZonePlugin);
  cfg.options = cfg.options || {{}};
  cfg.options.maintainAspectRatio = false;  // 大图填满弹窗，避免 letterbox

  // 在弹窗中创建全新高分辨率 canvas
  var box=document.getElementById('zoomBody');
  box.innerHTML = '';
  var ncv = document.createElement('canvas');
  ncv.id='zoomCanvas';
  ncv.style.width='92vw';
  ncv.style.height='82vh';
  box.appendChild(ncv);

  m.style.display='flex';
  var tip=document.getElementById('idxTip'); if(tip) tip.style.display='none';

  // 用同一份配置新建 Chart 实例（高分辨率渲染）
  try {{
    __zoomInst = new Chart(ncv, cfg);
    INSTANCES['__zoom__'] = __zoomInst;   // 注册到全局映射，使 setHighlight 可用
    __zoomId = id;

    // ---- 补回 JSON 丢失的函数回调 ----
    // RPS 横向条形图：改用 index 模式 + 自定义外部 tooltip
    if(id==='cRps'){{
      __zoomInst.options.interaction={{mode:'index', intersect:false}};
      __zoomInst.options.plugins.tooltip.enabled=false;
      __zoomInst.options.plugins.tooltip.mode='index';
      __zoomInst.options.plugins.tooltip.intersect=false;
      __zoomInst.options.plugins.tooltip.external=rpsExternalTooltip;
      __zoomInst.update();
    }}
    // 指数图：关闭原生 tooltip（用自定义 idxTip，但大图中暂不跟随鼠标）
    if(id==='cIdx'){{
      __zoomInst.options.scales.y.title={{display:true,text:'归一化（首日=100）',font:{{size:10}}}};
      __zoomInst.options.plugins.tooltip.enabled=false;
      __zoomInst.update();
    }}
    // 风格指数图：同上（归一化曲线，大图不挂自定义 tooltip）
    if(id==='cStyle'){{
      __zoomInst.options.scales.y.title={{display:true,text:'归一化（首日=100）',font:{{size:10}}}};
      __zoomInst.options.plugins.tooltip.enabled=false;
      __zoomInst.update();
    }}

    // 继承原图的高亮状态
    if(ch._hlIdx!==null && ch._hlIdx!==undefined){{
      setHighlight('__zoom__', ch._hlIdx);
    }}
  }} catch(e){{ console.error('[zoom] 新建图表失败', e); box.innerHTML='<p style="color:#f00">图表放大失败：'+e.message+'</p>'; }}
}}
function closeZoom(){{
  // 销毁放大态 Chart 实例（释放 canvas / 事件 / 内存）
  if(__zoomInst){{
    try {{ __zoomInst.destroy(); }} catch(e){{}}
    delete INSTANCES['__zoom__'];
    __zoomInst = null;
    __zoomId = null;
  }}
  var box=document.getElementById('zoomBody');
  box.innerHTML='';
  var m=document.getElementById('zoomModal');
  m.style.display='none';
  var tip=document.getElementById('idxTip'); if(tip) tip.style.display='none';
}}
document.getElementById('zoomModal').addEventListener('click',(e)=>{{ if(e.target.id==='zoomModal') closeZoom(); }});
document.addEventListener('keydown',(e)=>{{ if(e.key==='Escape') closeZoom(); }});

// ---- 表头点击排序（所有数据表通用）----
function parseCell(txt){{
  txt=(txt||'').trim();
  if(txt===''||txt==='—'||txt==='-') return {{num:false, raw:txt}};
  var s=txt.replace(/[^0-9.-]/g,'');
  var n=parseFloat(s);
  if(s!=='' && !isNaN(n) && isFinite(n)) return {{num:true, val:n, raw:txt}};
  return {{num:false, raw:txt}};
}}
function sortTable(t, ci, dir){{
  var rows=[], skips=[];
  t.querySelectorAll('tr').forEach(function(tr){{
    if(tr.querySelector(':scope > th')) return;            // 跳过表头行
    var cells=tr.children;
    if(!cells.length || cells.length<=ci) return;
    if(cells[ci].getAttribute('colspan')){{ skips.push(tr); return; }}  // 跳过合计/占位行
    rows.push(tr);
  }});
  rows.sort(function(a,b){{
    var av=parseCell(a.children[ci].textContent), bv=parseCell(b.children[ci].textContent);
    if(av.num&&bv.num) return (av.val-bv.val)*dir;
    return av.raw.localeCompare(bv.raw,'zh')*dir;
  }});
  // 仅当首列表头为 #（序号列）时，按新顺序重排序号
  var firstTh=t.querySelector('th');
  var renum = firstTh && firstTh.textContent.trim()==='#';
  rows.forEach(function(r, idx){{ t.appendChild(r); if(renum){{ r.children[0].textContent = (idx+1); }} }});
  skips.forEach(function(r){{ t.appendChild(r); }});
  // 排序后，把折叠行（如成交量 51–100）全部显示出来
  var fr=t.querySelectorAll('tr.fold-row');
  if(fr.length && typeof foldState!=='undefined'){{ foldState.open=true; if(foldState.apply) foldState.apply(); }}
}}
function makeTablesSortable(){{
  document.querySelectorAll('table').forEach(function(t){{
    var ths=t.querySelectorAll('th');
    if(!ths.length) return;
    t.classList.add('sortable');
    var state={{col:null, dir:1}};
    ths.forEach(function(th, ci){{
      var arr=document.createElement('span'); arr.className='arr'; th.appendChild(arr);
      th.addEventListener('click', function(){{
        if(state.col===ci){{ state.dir=-state.dir; }} else {{ state.col=ci; state.dir=1; }}
        sortTable(t, ci, state.dir);
        ths.forEach(function(o){{ var a=o.querySelector('.arr'); if(a) a.textContent=''; }});
        arr.textContent = state.dir>0 ? '▲' : '▼';
      }});
    }});
  }});
}}
makeTablesSortable();
// 成交量表的折叠/展开（51–100 名），折叠行仍参与排序；排序后自动展开
var foldState={{open:false}};
function setupFold(){{
  var t=document.getElementById('stkVolTable'); if(!t) return;
  var btn=document.getElementById('foldToggle'); if(!btn) return;
  var rows=t.querySelectorAll('tr.fold-row');
  foldState.apply=function(){{
    rows.forEach(function(r){{ r.style.display = foldState.open ? '' : 'none'; }});
    btn.textContent = foldState.open ? '折叠 第 51–100 名（点击折叠 / 展开）' : '展开 第 51–100 名（点击折叠 / 展开）';
  }};
  btn.addEventListener('click', function(){{ foldState.open=!foldState.open; foldState.apply(); }});
}}
setupFold();
// ── 历史趋势表格（模块三/四/五/七）──
var HT = D.hist_tables || {{}};
function toggleHist(el){{
  var body = el.nextElementSibling;
  var open = el.classList.toggle('open');
  body.classList.toggle('open', open);
  if(open && !body.dataset.rendered){{ renderHistBody(body); body.dataset.rendered='1'; }}
}}
function histRangeBtns(cur){{
  return '<div class="hist-range-btns">'+[10,20,60].map(function(n){{
    return '<button class="hist-range-btn'+(n===cur?' active':'')+'" data-range="'+n+'">近'+n+'日</button>';
  }}).join('')+'</div>';
}}
function cellBg(v,type){{
  if(v===null||v===undefined) return 'background:#1a1f2e;color:#4a5568';
  if(type==='turnover') return 'background:rgba(43,108,176,0.2);color:#7bb8ff';
  if(type==='inflow') return 'background:rgba(216,57,43,0.15);color:#fc8181';
  if(type==='outflow') return 'background:rgba(22,163,74,0.15);color:#68d391';
  if(type==='rps'){{
    var rc=['#1a1f2e','#744210','#9b2c2c','#c53030','#742a2a'];
    var idx=Math.max(0,Math.min(4,Math.round(v)));
    return 'background:'+rc[idx]+';color:'+(idx>=2?'#fed7d7':'#e0e6ed');
  }}
  if(type==='high') return 'background:rgba(216,57,43,0.12);color:#fc8181';
  if(type==='low') return 'background:rgba(22,163,74,0.12);color:#68d391';
  return '';
}}
function renderRankTable(names,values,dates,offset,topN,type,valFmt){{
  var html='<table class="hist-table"><thead><tr><th>#</th>';
  dates.forEach(function(d){{ html+='<th>'+d.slice(5)+'</th>'; }});
  html+='</tr></thead><tbody>';
  for(var i=0;i<topN;i++){{
    html+='<tr><td style="color:#999;font-weight:600">'+(i+1)+'</td>';
    for(var j=0;j<dates.length;j++){{
      var di=offset+j;
      var name=names[i]?names[i][di]:null;
      var val=values[i]?values[i][di]:null;
      if(name===null||name===undefined){{
        html+='<td class="heat-cell" style="background:#1a1f2e;color:#4a5568">—</td>';
      }} else {{
        var bg=cellBg(val,type);
        var vtxt=valFmt?valFmt(val):(val!==null&&val!==undefined?val:'');
        html+='<td class="heat-cell hist-cell" data-name="'+name+'" style="'+bg+'" title="'+name+(vtxt?(' ('+vtxt+')'):'')+'" onclick="toggleHistHighlight(this)">'+name+'</td>';
      }}
    }}
    html+='</tr>';
  }}
  html+='</tbody></table>';
  return html;
}}
function renderHistBody(body){{
  var mod = body.dataset.mod;
  var data = HT[mod];
  if(mod.indexOf('ind_')!==0 && mod!=='sec3_pct' && (!data||!data.dates||!data.dates.length)){{ body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>'; return; }}
  function render(n){{
    var html = histRangeBtns(n);
    if(mod.indexOf('ind_')!==0 && mod!=='sec3_pct'){{
      var dates = data.dates.slice(-n);
      var offset = data.dates.length - dates.length;
    }}
    if(mod==='sec3'){{
      html += renderRankTable(data.names,data.values,dates,offset,data.top_n,'turnover',
        function(v){{return v!==null&&v!==undefined?v.toFixed(0)+'亿':'';}});
    }} else if(mod==='sec4'){{
      html += '<h5 style="margin:8px 0 4px;color:#d8392b">主力净流入 TOP10</h5>';
      html += renderRankTable(data.inflow_names,data.inflow_values,dates,offset,data.top_n,'inflow',
        function(v){{return v!==null&&v!==undefined?(v>0?'+':'')+v.toFixed(1)+'亿':'';}});
      html += '<h5 style="margin:12px 0 4px;color:#16a34a">主力净流出 TOP10</h5>';
      html += renderRankTable(data.outflow_names,data.outflow_values,dates,offset,data.top_n,'outflow',
        function(v){{return v!==null&&v!==undefined?v.toFixed(1)+'亿':'';}});
    }} else if(mod==='sec5'){{
      html += renderRankTable(data.names,data.n_pass,dates,offset,data.top_n,'rps',
        function(v){{return v!==null&&v!==undefined?v+'/4':'';}});
    }} else if(mod==='sec7'){{
      html += '<h5 style="margin:8px 0 4px;color:#d8392b">创一年新高个股 TOP10</h5>';
      html += renderRankTable(data.high_names,data.high_pct,dates,offset,data.top_n,'high',
        function(v){{return v!==null&&v!==undefined?(v>0?'+':'')+v.toFixed(2)+'%':'';}});
      html += '<h5 style="margin:12px 0 4px;color:#16a34a">创一年新低个股 TOP10</h5>';
      html += renderRankTable(data.low_names,data.low_pct,dates,offset,data.top_n,'low',
        function(v){{return v!==null&&v!==undefined?v.toFixed(2)+'%':'';}});
    }} else if(mod==='sec3_pct'){{
      // 领涨/领跌板块历史趋势
      var pctData = D.hist_pct_sectors || {{}};
      if(!pctData.dates || !pctData.dates.length){{ body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>'; return; }}
      function renderPct(n){{
        var dts = pctData.dates.slice(-n);
        var off = pctData.dates.length - dts.length;
        var html2 = histRangeBtns(n);
        html2 += '<h5 style="margin:8px 0 4px;color:#d8392b">领涨板块 TOP15</h5>';
        html2 += renderRankTable(pctData.top_names,pctData.top_pcts,dts,off,15,'high',
          function(v){{return v!==null&&v!==undefined?(v>0?'+':'')+v.toFixed(2)+'%':'';}});
        html2 += '<h5 style="margin:12px 0 4px;color:#16a34a">领跌板块 TOP15</h5>';
        html2 += renderRankTable(pctData.bottom_names,pctData.bottom_pcts,dts,off,15,'low',
          function(v){{return v!==null&&v!==undefined?v.toFixed(2)+'%':'';}});
        body.innerHTML = html2;
        alignHistTables(body);
        body.querySelectorAll('.hist-range-btn').forEach(function(btn){{
          btn.addEventListener('click',function(){{ renderPct(parseInt(this.dataset.range)); }});
        }});
      }}
      renderPct(20);
      return;
    }} else if(mod==='ind_limit_both'){{
      // 涨停/跌停行业分布合并展示
      var upData = (D.hist_industry || {{}})['limit_up'];
      var downData = (D.hist_industry || {{}})['limit_down'];
      if((!upData || !upData.dates || !upData.dates.length) && (!downData || !downData.dates || !downData.dates.length)){{
        body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>'; return;
      }}
      function renderBoth(n){{
        var html2 = histRangeBtns(n);
        function renderIndTable(indData, title, color, bgType){{
          if(!indData || !indData.dates || !indData.dates.length) return '';
          var dts = indData.dates.slice(-n);
          var off = indData.dates.length - dts.length;
          var nms = indData.names.map(function(row){{ return row.slice(off); }});
          var vls = indData.values.map(function(row){{ return row.slice(off); }});
          return '<h5 style="margin:8px 0 4px;color:'+color+'">'+title+'</h5>' +
            renderRankTable(nms, vls, dts, 0, indData.top_n || 10, bgType,
              function(v){{return v!==null&&v!==undefined?v+'只':'';}});
        }}
        html2 += renderIndTable(upData, '涨停行业分布', '#d8392b', 'high');
        html2 += renderIndTable(downData, '跌停行业分布', '#16a34a', 'low');
        body.innerHTML = html2;
        alignHistTables(body);
        body.querySelectorAll('.hist-range-btn').forEach(function(btn){{
          btn.addEventListener('click',function(){{ renderBoth(parseInt(this.dataset.range)); }});
        }});
      }}
      renderBoth(20);
      return;
    }} else if(mod==='ind_high_low_both'){{
      // 新高/新低行业分布合并展示
      var highData = (D.hist_industry || {{}})['high_new'];
      var lowData = (D.hist_industry || {{}})['low_new'];
      if((!highData || !highData.dates || !highData.dates.length) && (!lowData || !lowData.dates || !lowData.dates.length)){{
        body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>'; return;
      }}
      function renderHLBoth(n){{
        var html2 = histRangeBtns(n);
        function renderIndTable(indData, title, color, bgType){{
          if(!indData || !indData.dates || !indData.dates.length) return '';
          var dts = indData.dates.slice(-n);
          var off = indData.dates.length - dts.length;
          var nms = indData.names.map(function(row){{ return row.slice(off); }});
          var vls = indData.values.map(function(row){{ return row.slice(off); }});
          return '<h5 style="margin:8px 0 4px;color:'+color+'">'+title+'</h5>' +
            renderRankTable(nms, vls, dts, 0, indData.top_n || 10, bgType,
              function(v){{return v!==null&&v!==undefined?v+'只':'';}});
        }}
        html2 += renderIndTable(highData, '新高行业分布', '#d8392b', 'high');
        html2 += renderIndTable(lowData, '新低行业分布', '#16a34a', 'low');
        body.innerHTML = html2;
        alignHistTables(body);
        body.querySelectorAll('.hist-range-btn').forEach(function(btn){{
          btn.addEventListener('click',function(){{ renderHLBoth(parseInt(this.dataset.range)); }});
        }});
      }}
      renderHLBoth(20);
      return;
    }} else if(mod==='ind_etf_both'){{
      // ETF 净申购/净赎回历史双榜
      var etfIn = (D.hist_industry || {{}})['etf_inflow'];
      var etfOut = (D.hist_industry || {{}})['etf_outflow'];
      if((!etfIn || !etfIn.dates || !etfIn.dates.length) && (!etfOut || !etfOut.dates || !etfOut.dates.length)){{
        body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>'; return;
      }}
      function renderEtfBoth(n){{
        var html2 = histRangeBtns(n);
        function renderEtfTable(indData, title, color, bgType){{
          if(!indData || !indData.dates || !indData.dates.length) return '';
          var dts = indData.dates.slice(-n);
          var off = indData.dates.length - dts.length;
          var nms = indData.names.map(function(row){{ return row.slice(off); }});
          var vls = indData.values.map(function(row){{ return row.slice(off); }});
          return '<h5 style="margin:8px 0 4px;color:'+color+'">'+title+'</h5>' +
            renderRankTable(nms, vls, dts, 0, indData.top_n || 10, bgType,
              function(v){{return v!==null&&v!==undefined?(v>0?'+':'')+v.toFixed(2)+'亿份':'';}});
        }}
        html2 += renderEtfTable(etfIn, 'ETF 净申购 TOP10（本周净申赎·亿份）', '#d8392b', 'high');
        html2 += renderEtfTable(etfOut, 'ETF 净赎回 TOP10（本周净申赎·亿份）', '#16a34a', 'low');
        body.innerHTML = html2;
        alignHistTables(body);
        body.querySelectorAll('.hist-range-btn').forEach(function(btn){{
          btn.addEventListener('click',function(){{ renderEtfBoth(parseInt(this.dataset.range)); }});
        }});
      }}
      renderEtfBoth(20);
      return;
    }} else if(mod==='ind_score_both'){{
      // 强势/弱势行业得分合并展示
      var strongData = (D.hist_industry || {{}})['score_strong'];
      var weakData = (D.hist_industry || {{}})['score_weak'];
      if((!strongData || !strongData.dates || !strongData.dates.length) && (!weakData || !weakData.dates || !weakData.dates.length)){{
        body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>'; return;
      }}
      function renderScoreBoth(n){{
        var html2 = histRangeBtns(n);
        function renderIndTable(indData, title, color, bgType){{
          if(!indData || !indData.dates || !indData.dates.length) return '';
          var dts = indData.dates.slice(-n);
          var off = indData.dates.length - dts.length;
          var nms = indData.names.map(function(row){{ return row.slice(off); }});
          var vls = indData.values.map(function(row){{ return row.slice(off); }});
          return '<h5 style="margin:8px 0 4px;color:'+color+'">'+title+'</h5>' +
            renderRankTable(nms, vls, dts, 0, indData.top_n || 10, bgType,
              function(v){{return v!==null&&v!==undefined?v+'分':'';}});
        }}
        html2 += renderIndTable(strongData, '强势行业得分', '#d8392b', 'high');
        html2 += renderIndTable(weakData, '弱势行业得分', '#16a34a', 'low');
        body.innerHTML = html2;
        alignHistTables(body);
        body.querySelectorAll('.hist-range-btn').forEach(function(btn){{
          btn.addEventListener('click',function(){{ renderScoreBoth(parseInt(this.dataset.range)); }});
        }});
      }}
      renderScoreBoth(20);
      return;
    }} else if(mod.indexOf('ind_')===0){{
      // 行业分布历史趋势表
      var indMod = mod.replace('ind_','');
      var indData = (D.hist_industry || {{}})[indMod];
      if(!indData || !indData.dates || !indData.dates.length){{
        body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>';
        return;
      }}
      function renderInd(n){{
        var dates2 = indData.dates.slice(-n);
        var offset2 = indData.dates.length - dates2.length;
        // 新数据结构：names[i][j] 和 values[i][j] 已是 行(排名)x列(日期) 格式
        var names2 = indData.names.map(function(row){{ return row.slice(offset2); }});
        var values2 = indData.values.map(function(row){{ return row.slice(offset2); }});
        var html2 = histRangeBtns(n);
        html2 += renderRankTable(names2, values2, dates2, 0, indData.top_n || 10, 'turnover',
          function(v){{return v!==null&&v!==undefined?v+'只':'';}});
        body.innerHTML = html2;
        alignHistTables(body);
        body.querySelectorAll('.hist-range-btn').forEach(function(btn){{
          btn.addEventListener('click',function(){{ renderInd(parseInt(this.dataset.range)); }});
        }});
      }}
      renderInd(20);
      return;
    }}
    body.innerHTML = html;
    alignHistTables(body);
    body.querySelectorAll('.hist-range-btn').forEach(function(btn){{
      btn.addEventListener('click',function(){{ render(parseInt(this.dataset.range)); }});
    }});
  }}
  render(20);
}}
function alignHistTables(body){{
  var tables = body.querySelectorAll('.hist-table');
  if(tables.length < 2) return;
  setTimeout(function(){{
    // 先清除所有固定宽度，让浏览器自然布局
    tables.forEach(function(t){{
      t.style.tableLayout = 'auto';
      t.style.width = 'auto';
      var cells = t.querySelectorAll('th, td');
      cells.forEach(function(c){{ c.style.width=''; c.style.minWidth=''; c.style.maxWidth=''; }});
    }});
    // 测量每一列的最大宽度
    var maxCols = 0;
    tables.forEach(function(t){{ var c=t.querySelectorAll('thead th').length; if(c>maxCols) maxCols=c; }});
    var colW = [];
    for(var i=0;i<maxCols;i++) colW.push(0);
    tables.forEach(function(t){{
      var ths = t.querySelectorAll('thead th');
      for(var i=0;i<ths.length;i++){{ var w=ths[i].offsetWidth; if(w>colW[i]) colW[i]=w; }}
    }});
    // 统一设置每一列宽度（用colgroup确保整列一致）
    tables.forEach(function(t){{
      var cols = t.querySelectorAll('colgroup col');
      if(cols.length === 0){{
        // 没有colgroup则用th设置
        var ths = t.querySelectorAll('thead th');
        for(var i=0;i<ths.length;i++){{ if(colW[i]>0){{ ths[i].style.width=colW[i]+'px'; ths[i].style.minWidth=colW[i]+'px'; }} }}
      }} else {{
        for(var i=0;i<cols.length && i<colW.length;i++){{ if(colW[i]>0) cols[i].style.width=colW[i]+'px'; }}
        t.style.tableLayout='fixed';
      }}
    }});
  }}, 20);
}}
function toggleHistHighlight(cell){{
  var body=cell.closest('.hist-body');
  var name=cell.dataset.name;
  var already=cell.classList.contains('hist-highlight');
  body.querySelectorAll('.hist-highlight').forEach(function(c){{c.classList.remove('hist-highlight');}});
  if(!already){{
    body.querySelectorAll('.hist-cell[data-name="'+name.replace(/"/g,'\\"')+'"]').forEach(function(c){{c.classList.add('hist-highlight');}});
  }}
}}
// 非当日数据：在标记的元素（表格/图表/卡片）上显示红色感叹号，hover 显示数据截至日期
// 非交易日（周末）：A股不开盘，数据本就该截止到最近交易日，不标红
function markStale(elm, date){{
  if(!elm) return;
  // 周末为非交易日，没有更新的数据可得，一律不标红（交易日由数据自然决定是否过期）
  var dow = new Date().getDay();
  if(dow === 0 || dow === 6) return;
  var host = (elm.tagName==='CANVAS') ? elm.parentElement : elm;
  if(!host) return;
  if(getComputedStyle(host).position==='static') host.style.position='relative';
  var b=document.createElement('span');
  b.className='stale-badge';
  b.setAttribute('data-tip','当前数据截至 '+date);
  b.textContent='!';
  host.appendChild(b);
}}
document.querySelectorAll('[data-stale]').forEach(function(box){{
  var date=box.getAttribute('data-stale');
  if(box.classList.contains('card') || box.classList.contains('section')){{
    // 子元素自身带 data-stale（如融资/均线占比/TR/平均股价等独立数据源）时以其自身日期为准，不重复打卡片日期
    box.querySelectorAll('table,canvas').forEach(function(c){{ if(c.hasAttribute('data-stale'))return; markStale(c, date); }});
  }} else {{
    markStale(box, date);
  }}
}});
// 数据截止时间戳：在每个数据块（表格/图表）右下角标注「数据截至 YYYY-MM-DD HH:MM」
// 若 data-cutoff 在卡片上，则遍历卡片内所有 table/canvas，在每个数据块上单独标注
function addCutoffBadge(elm, dateStr){{
  if(!elm || !elm.parentNode) return;
  // 标签放在数据块（表格/图表）上方右侧，不叠在表头里
  var b=document.createElement('div');
  b.className='cutoff-badge';
  b.textContent='数据截至 '+dateStr;
  elm.parentNode.insertBefore(b, elm);
}}
document.querySelectorAll('[data-cutoff]').forEach(function(box){{
  var dateStr = box.getAttribute('data-cutoff');
  if(box.classList.contains('card') || box.classList.contains('section')){{
    box.querySelectorAll('table,canvas').forEach(function(c){{
      // 子元素有独立 data-stale（如均线占比/TR/融资/平均股价等）时，用其自身数据日期，不用卡片统一日期
      var d = c.hasAttribute('data-stale') ? c.getAttribute('data-stale') : dateStr;
      addCutoffBadge(c, d);
    }});
  }} else {{
    addCutoffBadge(box, dateStr);
  }}
}});
</script>
</body></html>"""
    # ── 动态化（Path A）：把"数据"拆成 bundle JSON，页面运行时 fetch 后渲染 ──
    # body_html = .wrap 内部全部内容（标题/截止戳/控制条/八张卡片）；图表脚本在静态外壳里。
    body_html = html.split('<div class="wrap">', 1)[1].split('<div id="zoomModal">', 1)[0]
    meta = {
        "date": report_date,
        "weekday": d.get("weekday", ""),
        "midday": midday,
        "pagemode": "midday" if midday else "close",
        "report_date": report_date,
        "cutoff_hhmm": cutoff_hhmm,
        "cutoff_variant": cutoff_variant,
        "cutoff_dt": cutoff_dt,
    }
    bundle = {"meta": meta, "payload": payload, "body_html": body_html}
    return html, bundle

def main():
    args = sys.argv[1:]
    midday = "--midday" in args
    if midday:
        args.remove("--midday")
    # --data-date: 指定数据日期（回退到前一天数据时使用）
    # 报告日期=命令行传入的日期，数据日期=--data-date指定的日期
    data_date = None
    for i, a in enumerate(args):
        if a.startswith("--data-date="):
            data_date = a.split("=", 1)[1]
            args.pop(i)
            break
        elif a == "--data-date" and i + 1 < len(args):
            data_date = args[i + 1]
            args.pop(i + 1)
            args.pop(i)
            break
    date = args[0] if args else datetime.date.today().strftime("%Y-%m-%d")
    if data_date is None:
        data_date = date
    d = load(data_date)
    hist = history()
    page_label = "A股午间复盘" if midday else "A股收盘复盘"
    base_name = "A股午盘" if midday else "A股复盘"
    html, bundle = build_html(d, hist, midday=midday, report_date=date)
    html = html.replace("A股收盘复盘", page_label)
    if midday:
        bundle["body_html"] = bundle["body_html"].replace("A股收盘复盘", page_label)
    out = os.path.join(BASE, f"{base_name}_{date}.html")
    open(out, "w", encoding="utf-8").write(html)
    # ── 动态化：写出 bundle（数据）+ manifest（指向最新 bundle）──
    # 文件名带 variant，避免收盘/午间同日期时 bundle 互相覆盖（曾导致午间页误加载收盘数据）
    variant = "midday" if midday else "close"
    bundle_name = f"{date}_{variant}_bundle.json"
    bundle_path = os.path.join(DATA, bundle_name)
    json.dump(bundle, open(bundle_path, "w", encoding="utf-8"), ensure_ascii=False)
    manifest = {"variant": variant, "date": date, "bundle": f"data/{bundle_name}",
                "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    json.dump(manifest, open(os.path.join(DATA, f"manifest_{variant}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    if not midday:
        # 主线索引仅收盘版维护；午间版走独立目录，不污染主线
        rd = os.path.join(BASE, "README.md")
        line = f"- [{date}]({base_name}_{date}.html)"
        txt = open(rd, encoding="utf-8").read()
        if line not in txt:
            if "## 已生成复盘" in txt:
                txt = txt.rstrip() + "\n" + line + "\n"
            else:
                txt += f"\n## 已生成复盘\n{line}\n"
            open(rd, "w", encoding="utf-8").write(txt)
    print(f"已生成[{'午间' if midday else '收盘'}]", out, "| 历史归档点数:", len(hist["dates"]))

if __name__ == "__main__":
    main()
