#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_turnover_history.py — 全市场成交额长期历史采集

用途：hithink 只从 2026-05 起逐日采集，全市场成交额曲线/两融占比需要更长历史。
用东方财富指数日K补全：全市场成交额 ≈ 上证指数(1.000001) + 深证综指(0.399106)，
与 hithink 的 total_turnover_yi 口径差异仅北交所（约0.7%），可忽略。

输出：data/turnover_history.json
  {"dates": [...], "turnover_yi": [成交额(亿元), ...], "source": "..."}
"""
import json, os, subprocess, datetime, sys

BASE = "/Users/sugieliao/WorkBuddy/A股每日复盘"
DATA = os.path.join(BASE, "data")
OUT = os.path.join(DATA, "turnover_history.json")

# 指数成分：secid -> 名称
INDEXES = [("1.000001", "上证指数"), ("0.399106", "深证综指")]


def fetch_index_amount(secid, beg, end):
    """返回 {date: 成交额(亿元)}"""
    url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}"
           f"&fields1=f1,f2,f3&fields2=f51,f57&klt=101&fqt=1&beg={beg}&end={end}")
    out = subprocess.run(
        ["curl", "-s", "--max-time", "25", url, "-H", "User-Agent: Mozilla/5.0"],
        capture_output=True, text=True, timeout=30
    ).stdout
    d = json.loads(out)
    result = {}
    for line in d.get("data", {}).get("klines", []):
        parts = line.split(",")
        ds = parts[0]
        amount_yi = float(parts[1]) / 1e8  # 元 -> 亿元
        result[ds] = result.get(ds, 0) + amount_yi
    return result


def main():
    os.makedirs(DATA, exist_ok=True)
    # 默认取近 2 年（约500交易日），覆盖所有图表的最长滑动范围
    n_years = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    end = datetime.date.today()
    beg = end - datetime.timedelta(days=365 * n_years + 10)
    beg_s, end_s = beg.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    total = {}
    for secid, name in INDEXES:
        m = fetch_index_amount(secid, beg_s, end_s)
        print(f"[INFO] {name}({secid}) 获取 {len(m)} 天")
        for ds, v in m.items():
            total[ds] = total.get(ds, 0) + v

    dates = sorted(total)
    values = [round(total[ds], 2) for ds in dates]
    result = {
        "dates": dates,
        "turnover_yi": values,
        "source": "东方财富指数日K：上证指数+深证综指成交额合计（近似全市场，缺北交所约0.7%）",
        "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    json.dump(result, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"[DONE] 已保存 {OUT} | {len(dates)} 天 | {dates[0]} ~ {dates[-1]}")


if __name__ == "__main__":
    main()
