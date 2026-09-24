#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_margin.py — 沪深两市融资余额、融资买入额历史数据采集

数据源（均为 akshare 批量接口，一次取全历史，无需逐日请求）：
  - 沪市：macro_china_market_margin_sh（上交所）
  - 深市：macro_china_market_margin_sz（深交所）

输出：data/margin_balance.json
  {
    "dates": ["2025-08-01", ...],
    "margin_balance": [融资余额合计, ...],   # 亿元
    "margin_buy": [融资买入额合计, ...]       # 亿元
  }

用法：
  python3 collect_margin.py              # 全量采集（取最近250个交易日）
  python3 collect_margin.py --increment  # 增量更新（效果同全量，批量接口很快）
"""
import json, os, sys, datetime

BASE = "/Users/sugieliao/WorkBuddy/A股每日复盘"
DATA = os.path.join(BASE, "data")
OUT = os.path.join(DATA, "margin_balance.json")


def fetch_market_margin():
    """获取沪深两市融资余额、融资买入额，按日期合并（单位：亿元）"""
    import akshare as ak
    merged = {}
    for market_name, func in [("沪市", ak.macro_china_market_margin_sh),
                              ("深市", ak.macro_china_market_margin_sz)]:
        try:
            df = func()
            cnt = 0
            for _, row in df.iterrows():
                ds = str(row["日期"])[:10]
                bal = row["融资余额"]
                buy = row["融资买入额"]
                if ds not in merged:
                    merged[ds] = {"balance": 0.0, "buy": 0.0}
                try:
                    merged[ds]["balance"] += float(bal) / 1e8 if bal == bal else 0  # 元->亿
                except (TypeError, ValueError):
                    pass
                try:
                    merged[ds]["buy"] += float(buy) / 1e8 if buy == buy else 0
                except (TypeError, ValueError):
                    pass
                cnt += 1
            print(f"[INFO] {market_name}获取 {cnt} 行")
        except Exception as e:
            print(f"[WARN] {market_name}融资数据获取失败: {e}", file=sys.stderr)
    return merged


def main():
    os.makedirs(DATA, exist_ok=True)
    merged = fetch_market_margin()
    if not merged:
        print("[ERROR] 未获取到任何融资数据", file=sys.stderr)
        sys.exit(1)

    # 只保留最近约 400 个自然日（覆盖250交易日+缓冲），按日期排序
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=420)
    all_dates = sorted(ds for ds in merged if ds >= cutoff.strftime("%Y-%m-%d"))

    dates, balances, buys = [], [], []
    for ds in all_dates:
        v = merged[ds]
        if v["balance"] <= 0:
            continue
        dates.append(ds)
        balances.append(round(v["balance"], 2))
        buys.append(round(v["buy"], 2))

    result = {
        "dates": dates,
        "margin_balance": balances,
        "margin_buy": buys,
        "source": "沪市(上交所) + 深市(深交所) akshare批量接口 融资余额/融资买入额合计",
        "unit": "亿元",
        "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    json.dump(result, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"[DONE] 已保存 {OUT} | {len(dates)} 天 | "
          f"最新: {dates[-1]} 余额={balances[-1]}亿 买入={buys[-1]}亿")


if __name__ == "__main__":
    main()
