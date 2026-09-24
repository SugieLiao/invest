#!/usr/bin/env python3
"""测试均线占比API能返回多少天历史数据"""
import json, os, datetime, subprocess

BASE = "/Users/sugieliao/WorkBuddy/A股每日复盘"
DATA = os.path.join(BASE, "data")
TOKEN_FILE = os.path.join(DATA, ".jzxt_token")
HOST = "http://www.ghxb.site"
API = "/api/admin/daily/range"

def get_token():
    if os.path.exists(TOKEN_FILE):
        return open(TOKEN_FILE, encoding="utf-8").read().strip()
    return None

def ms(y, mo, d, h=0, mi=0, se=0):
    dt = datetime.datetime(y, mo, d, h, mi, se,
                           tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
    return int(dt.timestamp() * 1000)

def fetch(token, start_date, end_date):
    S = ms(start_date.year, start_date.month, start_date.day)
    E = ms(end_date.year, end_date.month, end_date.day, 23, 59, 59)
    url = (f"{HOST}{API}?from=dxb&marketType=sub&startTime={S}&endTime={E}")
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "60",
                            "-H", f"Authorization: Bearer {token}", url],
                           capture_output=True, text=True, timeout=70)
        if not r.stdout.strip():
            return None, "接口返回空"
        j = json.loads(r.stdout)
        if j.get("code") == "0000" and j.get("data"):
            return j["data"], None
        return None, f"接口异常 code={j.get('code')} msg={j.get('message')}"
    except Exception as e:
        return None, f"请求异常：{e}"

def main():
    token = get_token()
    if not token:
        print("缺少token")
        return
    
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    
    # 测试不同的时间窗口
    for days in [180, 250, 365, 500, 750, 1000]:
        start = now - datetime.timedelta(days=days)
        data, err = fetch(token, start, now)
        if err:
            print(f"窗口{days}天: 失败 - {err}")
        else:
            dates = data.get("dates") or []
            print(f"窗口{days}天: 成功返回{len(dates)}天, 最早={dates[0] if dates else 'N/A'}, 最新={dates[-1] if dates else 'N/A'}")
            if len(dates) >= 250:
                print(f"  ✓ 已达到250天目标！")
                break

if __name__ == "__main__":
    main()
