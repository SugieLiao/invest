#!/usr/bin/env python3
"""用更新后的 stock_classify.json 重新关联 koudai_industry.json 中所有个股的行业信息"""
import json, os

DATA = "/Users/sugieliao/WorkBuddy/A股每日复盘/data"

def to_thscode(code):
    """将纯数字代码转换为带后缀的 thscode"""
    code = str(code).split(".")[0]  # 去掉已有后缀
    if code.startswith(("60", "68", "90", "11", "13", "5")):
        return code + ".SH"
    elif code.startswith(("8", "4", "92")):
        return code + ".BJ"
    else:
        return code + ".SZ"

def main():
    # 加载行业字典
    classify = json.load(open(os.path.join(DATA, "stock_classify.json"), encoding="utf-8"))
    print(f"行业字典股票数: {len(classify)}")
    
    # 加载口袋+领先股数据
    koudai = json.load(open(os.path.join(DATA, "koudai_industry.json"), encoding="utf-8"))
    stocks = koudai.get("stocks", [])
    print(f"口袋+领先股股票数: {len(stocks)}")
    
    updated = 0
    not_found = []
    
    for s in stocks:
        code = s.get("code", "")
        thscode = to_thscode(code)
        
        # 在行业字典中查找
        cl = classify.get(thscode) or classify.get(code) or {}
        industries = cl.get("industry", [])
        
        if industries:
            # stock_classify.json 中 industry 数组是 [三级行业, 二级行业] 顺序
            industry_l3 = industries[0] if len(industries) > 0 else ""
            industry_l2 = industries[1] if len(industries) > 1 else industry_l3
            # 一级行业保留原值（stock_classify.json 中无标准一级行业）
            industry_l1 = s.get("industry_l1", "") or industry_l2
            
            old_l1 = s.get("industry_l1", "")
            old_l2 = s.get("industry_l2", "")
            old_l3 = s.get("industry_l3", "")
            
            if old_l2 != industry_l2 or old_l3 != industry_l3:
                s["industry_l1"] = industry_l1
                s["industry_l2"] = industry_l2
                s["industry_l3"] = industry_l3
                s["industry"] = industry_l3  # 主行业字段用三级
                s["industry_path"] = " > ".join([x for x in [industry_l1, industry_l2, industry_l3] if x])
                updated += 1
                print(f"  {code} {s.get('name','')}: {old_l1}/{old_l2}/{old_l3} → {industry_l1}/{industry_l2}/{industry_l3}")
        else:
            not_found.append(code)
    
    # 保存更新后的数据
    koudai["stocks"] = stocks
    json.dump(koudai, open(os.path.join(DATA, "koudai_industry.json"), "w", encoding="utf-8"), 
              ensure_ascii=False, indent=2)
    
    print(f"\n完成！更新 {updated} 只股票的行业信息")
    if not_found:
        print(f"未找到行业信息的股票 ({len(not_found)}只): {not_found}")

if __name__ == "__main__":
    main()
