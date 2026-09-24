#!/usr/bin/env python3
# 回溯补采：为历史日期生成 {date}_sector_rps.json 快照，供模块五历史趋势表使用。
# 设计：TDX 一次性拉取足够长的近 600 根日K（覆盖所有历史报告日），再按各目标日期切片复算 RPS。
import os, json, glob, sys
import collect_sector_rps as C

DATA = os.path.join(C.BASE, "data")
COUNT = 600  # 近 600 交易日，覆盖最早一份 hithink 报告日之前足够窗口


def fetch_full_boards():
    api = C.connect_tdx()
    if not api:
        return None
    names = C.tdx_security_names(api)
    boards = []
    for code in range(C.TDX_CONCEPT_START, C.TDX_CONCEPT_END):
        try:
            bars = api.get_index_bars(4, C.TDX_MARKET, str(code), 0, COUNT)
        except Exception:
            bars = None
        if not bars or len(bars) < C.NEED_BARS:
            continue
        try:
            closes = [float(b["close"]) for b in bars]
            dts = [b["datetime"][:10] for b in bars]
            amts = [float(b["amount"]) for b in bars if b.get("amount")]
        except (ValueError, KeyError, TypeError):
            continue
        name = names.get(str(code), str(code))
        boards.append({"code": str(code), "name": name,
                       "closes": closes, "dates": dts, "amts": amts})
    api.disconnect()
    print(f"[backfill] 拉取完成：有效概念板块 {len(boards)} 个（近 {COUNT} 根）")
    return boards


def slice_to_date(boards, D):
    """切出截至日期 D 的板块快照列表（与 collect_se, rps.main 的 all_rets 同构）。"""
    sub = []
    for b in boards:
        idx = None
        for i, d in enumerate(b["dates"]):
            if d <= D:
                idx = i
            else:
                break
        if idx is None:
            continue
        c = b["closes"][:idx + 1]
        db = b["dates"][:idx + 1]
        ab = b["amts"][:idx + 1]
        if len(c) < C.NEED_BARS:
            continue
        rets = C.compute_returns(c)
        if not any(v is not None for v in rets.values()):
            continue
        avg_amt = (sum(ab[-20:]) / len(ab[-20:])) if ab else 0.0
        sub.append({"code": b["code"], "name": b["name"], "cat": "概念",
                    "rets": rets, "close": c[-1], "date": db[-1],
                    "dates": db, "closes": c, "amount": avg_amt})
    return sub


def build_snapshot(sub):
    if C.PRE_FILTER:
        kept = {t[1] for t in C.liquidity_prefilter(
            [("概念", b["code"], b["name"], b["amount"]) for b in sub])}
        sub = [b for b in sub if b["code"] in kept]
    rps = C.rps_from_returns(sub)
    passed = []
    for b in sub:
        r = rps.get(b["code"], {})
        vals = [r.get(n) for n in C.PERIODS]
        n_pass = sum(1 for v in vals if v is not None and v > C.THRESHOLD)
        if n_pass >= C.MIN_PASS:
            passed.append({
                "code": b["code"], "name": b["name"], "cat": b["cat"],
                "rps5": r.get(5), "rps10": r.get(10),
                "rps20": r.get(20), "rps50": r.get(50),
                "n_pass": n_pass,
                "close": round(b["close"], 2),
                "ret5": round(b["rets"][5] * 100, 2) if b["rets"][5] is not None else None,
                "ret10": round(b["rets"][10] * 100, 2) if b["rets"][10] is not None else None,
                "ret20": round(b["rets"][20] * 100, 2) if b["rets"][20] is not None else None,
                "ret50": round(b["rets"][50] * 100, 2) if b["rets"][50] is not None else None,
                "date": b["date"],
                "hist_dates": b.get("dates") or [],
                "hist_close": [round(x, 2) for x in (b.get("closes") or [])],
            })
    passed.sort(key=lambda x: (x["n_pass"], x["rps50"] or 0, x["rps20"] or 0), reverse=True)
    return {
        "ok": True,
        "source": "通达信 TDX（概念板块指数 881xxx，前复权；回溯补采）",
        "universe": getattr(C, "UNIVERSE", "concept"),
        "universe_label": "概念板块指数（回溯补采）",
        "date": sub[0]["date"] if sub else None,
        "periods": C.PERIODS,
        "threshold": C.THRESHOLD,
        "min_pass": C.MIN_PASS,
        "total_boards": len(sub),
        "valid_boards": len(sub),
        "n_passed": len(passed),
        "passed": passed,
    }


def main():
    boards = fetch_full_boards()
    if not boards:
        print("[backfill] TDX 拉取失败，退出")
        sys.exit(1)
    cache = C.load_name_cache()
    patch = C.load_name_patch()
    for b in boards:
        if b["name"] == b["code"]:
            if b["code"] in cache:
                b["name"] = cache[b["code"]]
            elif b["code"] in patch:
                b["name"] = patch[b["code"]]
    dates = []
    for f in sorted(glob.glob(os.path.join(DATA, "*_hithink.json"))):
        try:
            dt = json.load(open(f, encoding="utf-8")).get("date")
            if dt:
                dates.append(dt)
        except Exception:
            continue
    dates = sorted(set(dates))
    done = 0
    for D in dates:
        snap = os.path.join(DATA, f"{D}_sector_rps.json")
        if os.path.exists(snap):
            print(f"[backfill] 跳过已存在 {D}")
            continue
        sub = slice_to_date(boards, D)
        if not sub:
            print(f"[backfill] 跳过 {D}（无可用板块，可能早于数据窗口）")
            continue
        out = build_snapshot(sub)
        json.dump(out, open(snap, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[backfill] 写入 {D}：通过筛选 {out['n_passed']} 个")
        done += 1
    print(f"[backfill] 完成，新增 {done} 个快照")


if __name__ == "__main__":
    main()
