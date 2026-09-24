#!/usr/bin/env python3
# 取 全A宽基指数 近 ~600 交易日日K（OHLC），写 data/wande.json。
# 2026-09-10 起：通达信 pytdx 公共节点全部假活，切换腾讯财经 HTTP 数据源。
#   - 原通达信 880003「平均股价」为等权口径；腾讯无对应自制指数，
#     改用「中证全指 sh000985」（市值加权、与平均股价走势高度相关）作可视化代理。
# 接口：https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000985,day,,,600,qfq
#   返回 data.sh000985.day = [[date, open, close, high, low, volume], ...]
import json, os, sys, datetime, time, urllib.request

BASE = "/Users/sugieliao/WorkBuddy/A股每日复盘"
DATA = os.path.join(BASE, "data")
SECID = "sh000985"          # 中证全指（替代通达信平均股价880003）
NAME = "中证全指"
LIMIT = 600                 # 保留最近交易日数（支持500天切换）
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


def write_fail(date, reason):
    out = {"ok": False, "code": SECID, "name": NAME,
           "reason": reason, "updated": date}
    json.dump(out, open(os.path.join(DATA, "wande.json"), "w"), ensure_ascii=False, indent=2)
    print(f"[wande] 取数失败（{reason}），已写 ok:false 占位；下次运行自动重试。")


def fetch_tencent_index(code, limit):
    url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?"
           f"param={code},day,,,{limit},qfq")
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            d = json.load(urllib.request.urlopen(req, timeout=15))
            k = (d.get("data") or {}).get(code) or {}
            arr = k.get("day") or k.get("qfqday") or []
            if arr:
                return arr
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"腾讯指数日K失败: {last}")


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().strftime("%Y-%m-%d")
    try:
        arr = fetch_tencent_index(SECID, LIMIT)
    except Exception as e:
        write_fail(date, str(e))
        return
    dates, o, c, h, l = [], [], [], [], []
    for r in arr:
        dt = r[0]
        if not dt:
            continue
        dates.append(dt)
        try:
            o.append(float(r[1])); c.append(float(r[2]))
            h.append(float(r[3])); l.append(float(r[4]))
        except (ValueError, IndexError, TypeError):
            continue
    if len(dates) < 2:
        write_fail(date, "腾讯日K 解析失败")
        return
    idx0 = max(0, len(dates) - LIMIT)
    out = {
        "ok": True, "code": SECID, "name": NAME,
        "source": "腾讯财经 中证全指(sh000985) 指数日K（市值加权，替代通达信平均股价880003）",
        "updated": date,
        "dates": dates[idx0:], "open": o[idx0:], "close": c[idx0:],
        "high": h[idx0:], "low": l[idx0:],
    }
    json.dump(out, open(os.path.join(DATA, "wande.json"), "w"), ensure_ascii=False, indent=2)
    print(f"[wande] 已写 {len(out['dates'])} 个交易日 {NAME}({SECID}) 日K，"
          f"末日 {out['dates'][-1]} 收盘 {out['close'][-1]}")


if __name__ == "__main__":
    main()
