#!/usr/bin/env python3
"""补采历史数据：板块三领涨领跌、全市场总成交额、均线占比"""
import json
import os
import glob
from datetime import datetime

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def backfill_pct_sectors():
    """从sectors_ths.json补采领涨/领跌板块历史数据"""
    hist_file = os.path.join(DATA, "hist_pct_sectors.json")
    if os.path.exists(hist_file):
        all_data = json.load(open(hist_file, encoding="utf-8"))
    else:
        all_data = {"dates": [], "top": {}, "bottom": {}}
    
    files = sorted(glob.glob(os.path.join(DATA, "*_sectors_ths.json")))
    added = 0
    for f in files:
        try:
            data = json.load(open(f, encoding="utf-8"))
            dt = data.get("date")
            if not dt:
                continue
            pct = data.get("pct_sectors", {})
            top = pct.get("top", [])
            bottom = pct.get("bottom", [])
            if not top and not bottom:
                continue
            
            if dt not in all_data["dates"]:
                all_data["dates"].append(dt)
                all_data["dates"].sort()
            
            all_data["top"][dt] = [{"name": s.get("name", ""), "pct": s.get("pct")} for s in top[:15]]
            all_data["bottom"][dt] = [{"name": s.get("name", ""), "pct": s.get("pct")} for s in bottom[:15]]
            added += 1
            print(f"  补采 {dt}: 领涨{len(top)}个, 领跌{len(bottom)}个")
        except Exception as e:
            print(f"  处理 {f} 失败: {e}")
    
    # 只保留最近120天
    if len(all_data["dates"]) > 120:
        keep = set(all_data["dates"][-120:])
        all_data["dates"] = [d for d in all_data["dates"] if d in keep]
        all_data["top"] = {d: v for d, v in all_data["top"].items() if d in keep}
        all_data["bottom"] = {d: v for d, v in all_data["bottom"].items() if d in keep}
    
    with open(hist_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"板块三补采完成: 新增{added}天, 总计{len(all_data['dates'])}天")
    return len(all_data["dates"])

def check_turnover_data():
    """检查全市场总成交额数据"""
    files = sorted(glob.glob(os.path.join(DATA, "*_hithink.json")))
    dates = []
    for f in files:
        try:
            data = json.load(open(f, encoding="utf-8"))
            dt = data.get("date")
            if dt:
                dates.append(dt)
        except:
            pass
    print(f"全市场总成交额: {len(dates)}天, 最早={dates[0] if dates else 'N/A'}, 最新={dates[-1] if dates else 'N/A'}")
    return len(dates)

def check_jzxt_data():
    """检查均线占比数据"""
    jzxt_file = os.path.join(DATA, "jzxt_history.json")
    if os.path.exists(jzxt_file):
        data = json.load(open(jzxt_file, encoding="utf-8"))
        dates = data.get("dates", [])
        print(f"均线占比: {len(dates)}天, 最早={dates[0] if dates else 'N/A'}, 最新={dates[-1] if dates else 'N/A'}")
        return len(dates)
    return 0

if __name__ == "__main__":
    print("=" * 50)
    print("开始补采历史数据")
    print("=" * 50)
    
    print("\n1. 补采板块三（领涨/领跌板块）历史数据:")
    pct_days = backfill_pct_sectors()
    
    print("\n2. 全市场总成交额数据现状:")
    turnover_days = check_turnover_data()
    
    print("\n3. 均线占比数据现状:")
    jzxt_days = check_jzxt_data()
    
    print("\n" + "=" * 50)
    print("补采完成")
    print(f"  板块三: {pct_days}天")
    print(f"  全市场总成交额: {turnover_days}天 (hithink数据从2026-05-19开始，无法补采更早)")
    print(f"  均线占比: {jzxt_days}天 (需从ghxb.site补采更早数据)")
    print("=" * 50)
