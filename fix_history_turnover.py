#!/usr/bin/env python3
"""修复历史成交额数据：用东方财富指数K线（上证+深证综指+北证50）替换hithink个股求和的成交额"""
import json, os, glob, time, subprocess, sys

DATA = "/Users/sugieliao/WorkBuddy/A股每日复盘/data"

def fetch_kline(secid, beg, end):
    """获取指数日K线，返回 {date: turnover_yi}"""
    url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=0&beg={beg}&end={end}"
    for attempt in range(5):
        try:
            out = subprocess.run(["curl", "-s", "--max-time", "30",
                                  "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                  "-H", "Referer: https://quote.eastmoney.com/",
                                  "-H", "Accept: */*",
                                  "-H", "Accept-Language: zh-CN,zh;q=0.9",
                                  url],
                                 capture_output=True, text=True, timeout=35).stdout
            if not out or not out.strip().startswith("{"):
                print(f"  空响应，重试 {attempt+1}/5", file=sys.stderr)
                time.sleep(3)
                continue
            d = json.loads(out)
            klines = d.get("data", {}).get("klines", [])
            if not klines:
                print(f"  无K线数据，重试 {attempt+1}/5", file=sys.stderr)
                time.sleep(3)
                continue
            result = {}
            for k in klines:
                parts = k.split(",")
                dt = parts[0]
                turnover = float(parts[6]) / 1e8  # 元→亿
                result[dt] = turnover
            return result
        except Exception as e:
            print(f"  重试 {attempt+1}/5: {e}", file=sys.stderr)
            time.sleep(3)
    return {}

def main():
    files = sorted(glob.glob(os.path.join(DATA, "*_hithink.json")))
    if not files:
        print("没有找到hithink文件")
        return
    
    dates = []
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
            dates.append(d["date"])
        except Exception:
            continue
    
    if not dates:
        print("没有有效日期")
        return
    
    beg = dates[0].replace("-", "")
    end = dates[-1].replace("-", "")
    print(f"修复范围: {dates[0]} ~ {dates[-1]}，共 {len(dates)} 天")
    
    print("获取上证指数K线...")
    sh = fetch_kline("1.000001", beg, end)
    print(f"  获取到 {len(sh)} 天")
    time.sleep(2)
    
    print("获取深证综指K线...")
    sz = fetch_kline("0.399106", beg, end)
    print(f"  获取到 {len(sz)} 天")
    time.sleep(2)
    
    print("获取北证50K线...")
    bj = fetch_kline("0.899050", beg, end)
    print(f"  获取到 {len(bj)} 天")
    
    updated = 0
    for dt in dates:
        total = sh.get(dt, 0) + sz.get(dt, 0) + bj.get(dt, 0)
        if total <= 0:
            print(f"  {dt}: 无数据，跳过")
            continue
        
        f = os.path.join(DATA, f"{dt}_hithink.json")
        try:
            d = json.load(open(f, encoding="utf-8"))
            old = d.get("market", {}).get("total_turnover_yi")
            if old != round(total, 1):
                d["market"]["total_turnover_yi"] = round(total, 1)
                json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                print(f"  {dt}: {old} → {total:.1f} 亿 (已更新)")
                updated += 1
            else:
                print(f"  {dt}: {total:.1f} 亿 (无需更新)")
        except Exception as e:
            print(f"  {dt}: 更新失败 - {e}")
    
    print(f"\n完成！共更新 {updated} 天的成交额数据")

if __name__ == "__main__":
    main()
