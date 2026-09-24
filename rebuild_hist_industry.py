#!/usr/bin/env python3
"""用更新后的 stock_classify.json 重新计算所有历史日期的行业分布，更新 hist_industry_dist.json"""
import json, os, glob, sys
from collections import Counter

BASE = "/Users/sugieliao/WorkBuddy/A股每日复盘"
DATA = os.path.join(BASE, "data")
HIST_FILE = os.path.join(DATA, "hist_industry_dist.json")

def to_thscode(code):
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

def calc_industry_dist(stocks, classify, code_key="code"):
    """计算股票列表的行业分布，返回 [{"industry": "xxx", "count": N}, ...] 按count降序"""
    counter = Counter()
    for s in stocks:
        code = s.get(code_key, "")
        thscode = to_thscode(code)
        cl = classify.get(thscode) or classify.get(str(code)) or {}
        industries = cl.get("industry", [])
        if industries:
            counter[industries[0]] += 1
        else:
            counter["未分类"] += 1
    if not counter:
        return []
    return [{"industry": name, "count": count} for name, count in counter.most_common()]

def main():
    # 加载更新后的行业字典
    classify = json.load(open(os.path.join(DATA, "stock_classify.json"), encoding="utf-8"))
    print(f"行业字典股票数: {len(classify)}")
    
    # 加载现有历史数据
    if os.path.exists(HIST_FILE):
        all_data = json.load(open(HIST_FILE, encoding="utf-8"))
        print(f"现有历史数据模块: {list(all_data.keys())}")
    else:
        all_data = {}
    
    # 遍历所有历史日期的 hithink.json
    hithink_files = sorted(glob.glob(os.path.join(DATA, "*_hithink.json")))
    print(f"\n历史 hithink 文件数: {len(hithink_files)}")
    
    for f in hithink_files:
        try:
            d = json.load(open(f, encoding="utf-8"))
            date = d.get("date", "")
            if not date:
                continue
            m = d.get("market", {})
            
            # 涨停个股行业分布
            lu_list = m.get("limit_up_list", [])
            if lu_list:
                lu_dist = calc_industry_dist(lu_list, classify)
                update_module(all_data, "limit_up", date, lu_dist)
            
            # 跌停个股行业分布
            ld_list = m.get("limit_down_list", [])
            if ld_list:
                ld_dist = calc_industry_dist(ld_list, classify)
                update_module(all_data, "limit_down", date, ld_dist)
            
            # 成交量前100行业分布
            top100 = m.get("top_stocks", [])
            if top100:
                top100_dist = calc_industry_dist(top100, classify)
                update_module(all_data, "top100", date, top100_dist)
            
            print(f"  {date}: 涨停{len(lu_list)}只 跌停{len(ld_list)}只 前100{len(top100)}只")
        except Exception as e:
            print(f"  处理 {f} 失败: {e}")
    
    # 遍历所有历史日期的 tdxhl.json
    tdxhl_files = sorted(glob.glob(os.path.join(DATA, "*_tdxhl.json")))
    print(f"\n历史 tdxhl 文件数: {len(tdxhl_files)}")
    
    for f in tdxhl_files:
        try:
            d = json.load(open(f, encoding="utf-8"))
            # tdxhl.json 可能没有 date 字段，从文件名提取
            basename = os.path.basename(f)
            date = basename.replace("_tdxhl.json", "")
            
            # 新高个股行业分布
            hn = d.get("high_new", {})
            hn_stocks = hn.get("stocks", []) if isinstance(hn, dict) else []
            if hn_stocks:
                hn_dist = calc_industry_dist(hn_stocks, classify)
                update_module(all_data, "high_new", date, hn_dist)
            
            # 新低个股行业分布
            ln = d.get("low_new", {})
            ln_stocks = ln.get("stocks", []) if isinstance(ln, dict) else []
            if ln_stocks:
                ln_dist = calc_industry_dist(ln_stocks, classify)
                update_module(all_data, "low_new", date, ln_dist)
            
            print(f"  {date}: 新高{len(hn_stocks)}只 新低{len(ln_stocks)}只")
        except Exception as e:
            print(f"  处理 {f} 失败: {e}")
    
    # 保存更新后的历史数据
    json.dump(all_data, open(HIST_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n完成！历史数据已更新到 {HIST_FILE}")
    for module, data in all_data.items():
        if isinstance(data, dict) and "dates" in data:
            print(f"  {module}: {len(data['dates'])} 个交易日")

def update_module(all_data, module, date, industry_list):
    """更新某天某模块的行业分布到历史数据"""
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

if __name__ == "__main__":
    main()
