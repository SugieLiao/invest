#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
collect_mainline.py — 板块十二「主线回踩买点」数据采集。

只用通达信「概念板块」（tdxzs3.cfg 中 880 类型=4，共269个，剔除8个风格属性后约261个）。
板块清单来自最近通达信备份（清单变化极慢，允许回退最近8天）；
5日/20日涨幅由 pytdx 直连通达信行情服务器取板块指数日K现算（行情是运行当时的实时值，
因此本模块数据日期=运行当日，与备份清单日期无关）。

产出 data/{date}_mainline.json：
  table1   主线池     20日涨幅降序 TOP100
  t1_group 表1大方向归集（11方向，按板块厚度降序）
  table2   短期动能池 5日涨幅降序 TOP100
  table3   回踩买点池 表1前100集合内按5日涨幅升序（is_pullback=True 为"20日强势+5日走弱"真回踩）
  direction 今日方向判定（表1 TOP100 + 表2 TOP30 重叠，🟢🟡🔴信号灯）

用法：
  python3 collect_mainline.py [YYYY-MM-DD] [--midday]
"""
import os, sys, json, time, datetime, collections

BASE = "/Users/sugieliao/WorkBuddy/A股每日复盘"
DATA = os.path.join(BASE, "data")
BACKUP_ROOT = "/Users/sugieliao/Documents/01 通达信/通达信自定义数据备份"
MOOTDX_CFG = os.path.expanduser("~/.mootdx/config.json")
# 兜底旧节点（mootdx 配置缺失时用）
_FALLBACK_HOSTS = [("115.238.90.165", 7709), ("119.147.212.81", 7709), ("124.74.236.94", 7709),
                   ("180.153.39.20", 7709), ("218.108.98.18", 7709)]


def load_hosts():
    """从 mootdx bestip 配置读取 HQ 节点池（含 BESTIP 优先），缺失则用兜底旧节点。"""
    try:
        cfg = json.load(open(MOOTDX_CFG, encoding="utf-8"))
        hosts = []
        best = (cfg.get("BESTIP", {}) or {}).get("HQ")
        if best and len(best) == 2:
            hosts.append((best[0], int(best[1])))
        for _name, h, p in (cfg.get("SERVER", {}) or {}).get("HQ", []):
            t = (h, int(p))
            if t not in hosts:
                hosts.append(t)
        if hosts:
            return hosts
    except Exception as e:
        print(f"[hosts] 读取 mootdx 配置失败({e})，用兜底节点", flush=True)
    return list(_FALLBACK_HOSTS)


HOSTS = load_hosts()
TOPN = 100           # 三表各取前100
DIR_TOP30 = 30       # 方向判定时表2只取 TOP30
PULLBACK_P20 = 5.0   # 表3"真回踩"：20日涨幅≥5%
KLINE_N = 60         # 每个上榜板块内嵌近60日日K，供页面 hover 迷你K线（公网API取不到880板块）
# 概念板块中需剔除的风格属性板块（非主题概念）
DROP_STYLE = {"含H股", "含B股", "含可转债", "含GDR", "通达信88", "ST板块", "次新股", "稀缺资源"}

# ── 11 大方向关键词（顺序=多命中时的优先级，与用户截图一致）──
DIRS = collections.OrderedDict()
DIRS["半导体&电子"] = ["半导体","芯片","光刻","封装","EDA","存储","PCB","消费电子","元器件","电子","MLCC","LED","OLED","MicroLED","MiniLED","显示","折叠屏","混合现实","虚拟现实","石墨烯","玻璃基板","无线耳机","智能穿戴","毫米波","摄像头","触控","碳化硅","第三代半","汽车芯片","MCU","电子纸","苹果","华为海思","超清视频","胎压","外骨骼"]
DIRS["AI"] = ["人工智能","AIGC","多模态","智能体","DeepSeek","ChatGPT","智谱","AI","大模型","类脑","人脑","生成式","AI营销","AI手机","AI眼镜"]
DIRS["算力&数字基建"] = ["算力","CPO","光通信","铜缆","数据中心","液冷","服务器","5G","6G","通信","光模块","光器件","边缘计算","国资云","云计算","高速连接","华为算力","东数西算","网络设备","IDC","星闪"]
DIRS["数字经济"] = ["信创","国产软件","操作系统","鸿蒙","数据要素","物联网","工业互联","软件","大数据","网络安全","信息安全","互联网","区块链","数字货币","数据确权","数字水印","数字孪生","智慧","知识付费","知识产权","远程办公","IT","财税","Web3","NFT","量子","抖音","腾讯","阿里","百度","小米","小红书","网红","跨境电商","电商","虚拟","元宇宙","游戏","短剧","IP经济","安防","电子身份","在线","职业教育","云游戏","智能家居","智能交通","工业软件","ETC"]
DIRS["新能源"] = ["光伏","HJT","钙钛矿","锂电","固态电池","储能","风电","氢","充电桩","电池","POE","换电","高压快充","超级电容","盐湖提锂","新能源","钠电","TOPCon","BIPV","BC电池","热泵","光热","钒电池","燃料电池","复合铜箔","动力电池"]
DIRS["汽车&机器人"] = ["汽车","整车","无人驾驶","人形机器人","减速器","低空经济","机器人","一体压铸","车联网","飞行汽车","机器视觉","3D打印","工业母机","华为汽车","新能源车","汽车热管理","汽车拆解","汽车电子"]
DIRS["军工"] = ["国防军工","军贸","大飞机","无人机","卫星导航","商业航天","军工","航天","航空","军民融合","船舶","军工信息"]
DIRS["医药"] = ["创新药","生物制药","CXO","医美","减肥药","医疗器械","医药","中药","中成药","生物","医疗","疫苗","制药","健康","肝炎","维生素","免疫","基因","民营医院","家庭医生","辅助生殖","血氧","口罩","幽门","医废","NMN","代糖","工业大麻","养老","婴童","虫害","合成生物","DRG","仿制药","食品安全","智能医疗","草甘膦"]
DIRS["消费"] = ["白酒","食品","免税","预制菜","旅游","酒店","家电","零售","百货","影视","传媒","纺织","服装","服饰","家居","农业","养殖","猪肉","种业","种植","渔","林","农产品","乳","饮料","美容","宠物","文娱","教育","培训","饲料","酿酒","啤酒","黄酒","商业","超市","连锁","批发","商贸","商品城","出版","广告","文教","休闲","体育","博彩","赛马","彩票","人造肉","鸡肉","水产","粮食","供销社","乡村振兴","土地流转","烟草","物业","装修装饰","租购","消费","风沙治理","新零售","C2M","冷链","预制"]
DIRS["金融"] = ["银行","证券","保险","多元金融","金融","创投","期货","跨境支付","CIPS","互联金融","中特估"]
DIRS["周期&资源&基建"] = ["石油","煤炭","焦","有色","黄金","化工","钢铁","钢","水泥","地产","房产","工程","电力","水力","火力","发电","燃气","供气","供热","水务","建筑","建材","铜","铝","铅锌","小金属","金属","稀土","磁","矿","交通","运输","港口","航运","水运","空运","路桥","机场","公路","铁路","物流","仓储","环保","固废","环境","垃圾","园林","基建","公用","园区","城镇","地下管网","水利","一带一路","雄安","自贸","粤港澳","海峡","海南","中俄","海洋","可燃冰","页岩气","天然气","油气","核电","核能","核聚","可控核","特高压","智能电网","虚拟电厂","超临界","地热","新材料","材料","塑料","橡胶","化纤","化肥","农药","涂料","染料","陶瓷","玻璃","聚氨酯","PVDF","PEEK","氟","磷","镍","钴","钛","超导","工业气体","降解","PPP","综合","装配式","绿色建筑","新型城镇","培育钻石","碳中","节能","生物质能","风沙","碳纤维","高铁"]
DIR_ORDER = list(DIRS.keys())


def classify_dir(name):
    for g, kws in DIRS.items():
        if any(k in name for k in kws):
            return g
    return "其他"


def find_cfg(target_date):
    """在最近8天备份里找 tdxzs3.cfg，返回(cfg路径, 清单日期)。"""
    for i in range(8):
        d = (datetime.datetime.strptime(target_date, "%Y-%m-%d") - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        cfg = os.path.join(BACKUP_ROOT, f"TdxBak_{d.replace('-','')}", "T0002", "hq_cache", "tdxzs3.cfg")
        if os.path.exists(cfg):
            return cfg, d, i
    return None, None, None


def load_concepts(cfg_path):
    """解析 tdxzs3.cfg（GBK，每行 名称|代码|类型|...），取 880 类型=4 概念板块并剔除风格属性。"""
    blocks = collections.OrderedDict()
    raw_n = 0
    for line in open(cfg_path, encoding="gbk", errors="ignore"):
        p = line.strip().split("|")
        if len(p) >= 3 and p[1].startswith("880") and p[2] == "4":
            raw_n += 1
            if p[0] in DROP_STYLE:
                continue
            blocks[p[1]] = p[0]
    return blocks, raw_n


# 通达信概念名称 → 腾讯概念名称 手工映射（自动匹配失败的约18个，人工核对后填入）
MANUAL_MAP = {
    "核电核能": "核电概念", "卫星导航": "卫星互联网", "车联网": "车联网(车路协同)",
    "财税数字化": "财税改革", "安防服务": "安防概念", "互联金融": "互联网金融",
    "先进封装": "先进封装(Chiplet)", "复合铜箔": "复合集流体(PET铜箔)",
    "短剧游戏": "短剧/互动游戏", "多模态AI": "Gemini多模态", "飞行汽车": "飞行汽车(eVTOL)",
    "HJT电池": "HJT/HIT电池", "代糖概念": "代糖(甜味剂)", "网红经济": "网红直播",
    "量子科技": "量子计算", "仿制药": "仿制药一致性评价", "存储芯片": "存储器",
}


def _strip_suf(n):
    for s in ("概念", "板块"):
        if n.endswith(s):
            n = n[:-len(s)]
    return n.strip()


def select_tdx_concepts(tx_rows, date):
    """按通达信261概念白名单，在腾讯全量概念里映射过滤。
    tx_rows: 腾讯全量 [{code,name,p5,p20,dates,close}]
    返回 (selected, tdx_total, missed)：
      selected 板块 name 用通达信名称（方向归集关键词匹配），code 用腾讯代码（取数/tooltip）。"""
    cfg_path, cfg_date, back = find_cfg(date)
    if not cfg_path:
        # 清单取不到就退回腾讯全量（不阻断）
        print("[warn] 未找到 tdxzs3.cfg，退回腾讯全量", flush=True)
        return tx_rows, len(tx_rows), []
    tdx_blocks, _ = load_concepts(cfg_path)
    tdx_names = list(tdx_blocks.values())
    tx_by_name = {r["name"]: r for r in tx_rows}

    selected, hit = [], set()
    for tdx_name in tdx_names:
        tx = None
        if tdx_name in tx_by_name:                       # 1 精确同名
            tx = tx_by_name[tdx_name]
        elif tdx_name in MANUAL_MAP and MANUAL_MAP[tdx_name] in tx_by_name:  # 2 手工映射
            tx = tx_by_name[MANUAL_MAP[tdx_name]]
        else:                                             # 3 去后缀同名
            sn = _strip_suf(tdx_name)
            for tn, r in tx_by_name.items():
                if _strip_suf(tn) == sn:
                    tx = r; break
        if tx is None:                                    # 4 双向包含兜底
            sn = _strip_suf(tdx_name)
            cands = [r for tn, r in tx_by_name.items()
                     if sn and (sn in tn or tn in sn) and abs(len(sn) - len(tn)) <= 4]
            if cands:
                tx = cands[0]
        if tx:
            selected.append({**tx, "name": tdx_name})    # 名称用通达信，代码用腾讯
            hit.add(tdx_name)
    missed = [n for n in tdx_names if n not in hit]
    return selected, len(tdx_names), missed


# ── 东方财富概念板块数据源（兜底：通达信 pytdx 节点不可用时启用）──
EM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/center/boardlist.html",
}
# 东财概念板块中需剔除的非主题/辅助分类
EM_DROP = {"昨日首板", "昨日连板", "昨日涨停", "科创板做市商", "金融地产风格", "昨日触板",
           "昨日炸板", "昨日涨停表现", "昨日跌停", "昨日连板含ST", "昨日首板含ST"}


def _em_get(url, tries=4):
    import urllib.request
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=EM_HEADERS)
            return json.load(urllib.request.urlopen(req, timeout=15))
        except Exception as e:
            last = e
            time.sleep(2.0 * (i + 1))  # 退避：2s,4s,6s,8s
    raise RuntimeError(f"东财请求失败: {last}")


def fetch_concepts_tencent():
    """腾讯财经概念板块：翻页拉全概念榜，接口直接带 5日/20日涨幅。
    返回 rows=[{code,name,p5,p20,dates,close}]。dates/close 留空（迷你K线后续补）。"""
    rows, failed = [], []
    total = 0
    for p in range(1, 12):
        url = (f"https://proxy.finance.qq.com/ifzqgtimg/appstock/app/mktHs/rank"
               f"?l=100&p={p}&t=02/averatio&o=0")
        d = _em_get(url)
        items = d.get("data") or []
        if not items:
            break
        for x in items:
            try:
                rows.append({"code": x["bd_code"], "name": x["bd_name"],
                             "p5": round(float(x.get("bd_zdf5") or 0), 2),
                             "p20": round(float(x.get("bd_zdf20") or 0), 2),
                             "dates": [], "close": []})
            except Exception:
                failed.append(x.get("bd_code"))
        total += len(items)
        print(f"  腾讯概念板块第{p}页: +{len(items)}，累计{total}", flush=True)
        if len(items) < 100:
            break
        time.sleep(0.3)
    return rows, failed


def build_groups(t1):
    """表1 TOP100 按11大方向归集，按板块厚度降序。"""
    g = collections.defaultdict(list)
    for r in t1:
        g[classify_dir(r["name"])].append(r)
    out = []
    for direction, rs in g.items():
        rs = sorted(rs, key=lambda x: -x["p20"])
        out.append({
            "dir": direction,
            "count": len(rs),
            "avg20": round(sum(x["p20"] for x in rs) / len(rs), 2),
            "members": [{"name": x["name"], "code": x["code"], "p20": x["p20"], "p5": x["p5"]} for x in rs],
        })
    out.sort(key=lambda x: (-x["count"], -x["avg20"]))
    return out


def build_direction(t1, t2):
    """今日方向判定：表1 TOP100 + 表2 TOP30 重叠。"""
    t2top = t2[:DIR_TOP30]
    c1, m1, c2, m2 = collections.Counter(), collections.defaultdict(list), collections.Counter(), collections.defaultdict(list)
    for r in t1:
        d = classify_dir(r["name"]); c1[d] += 1; m1[d].append(r["name"])
    for r in t2top:
        d = classify_dir(r["name"]); c2[d] += 1; m2[d].append(r["name"])
    res = []
    for d in DIR_ORDER + ["其他"]:
        a, b = c1.get(d, 0), c2.get(d, 0)
        if a == 0 and b == 0:
            continue
        if a == 0:
            signal, note = "red", f"20日主线无，仅5日异动（{'、'.join(m2[d][:6])}），观察能否走成主线"
        elif a <= 1:
            signal, note = "red", f"20日仅{a}个、5日{b}个，板块太薄，不独立成主线"
        elif b <= 1:
            signal, note = "yellow", f"20日仍在主线（{'、'.join(m1[d][:6])}），但5日TOP{DIR_TOP30}仅{b}个，短期回踩/歇火，等企稳"
        else:
            signal, note = "green", f"20日在榜{a}个且5日TOP{DIR_TOP30}有{b}个，双强主线；短期活跃：{'、'.join(m2[d][:6])}"
        res.append({"signal": signal, "dir": d, "t1": a, "t2": b, "note": note,
                    "t1_members": m1[d], "t2_members": m2[d]})
    order = {"green": 0, "yellow": 1, "red": 2}
    res.sort(key=lambda x: (order[x["signal"]], -x["t1"], -x["t2"]))
    return res


def main():
    args = sys.argv[1:]
    midday = "--midday" in args
    if midday:
        args.remove("--midday")
    date = args[0] if args else datetime.date.today().strftime("%Y-%m-%d")

    # 板块名单：腾讯概念榜全量 → 按通达信261概念白名单映射过滤（通达信pytdx/东财当日不可用）
    rows_raw, failed = fetch_concepts_tencent()
    rows, tdx_n, missed = select_tdx_concepts(rows_raw, date)
    raw_n = len(rows)
    cfg_date, back = date, 0
    print(f"[src] 通达信261口径→腾讯映射：命中 {len(rows)}/{tdx_n}，未匹配 {len(missed)}；腾讯全量 {len(rows_raw)}", flush=True)
    if missed:
        print(f"[warn] 未匹配(腾讯无对应，已丢弃)：{missed}", flush=True)
    if len(rows) < 150:
        print("[error] 映射后板块数过少（<150），终止", flush=True)
        sys.exit(1)
    print(f"[fetch] 成功 {len(rows)}，失败 {len(failed)}" + (f"：{failed[:8]}" if failed else ""), flush=True)

    rowmap = {r["code"]: r for r in rows}
    t1_full = sorted(rows, key=lambda x: -x["p20"])[:TOPN]
    t2_full = sorted(rows, key=lambda x: -x["p5"])[:TOPN]
    t1set = {r["code"] for r in t1_full}
    # 上榜板块（表1∪表2，表3是表1子集）的近60日K线，内嵌供页面 hover 迷你K线
    union_codes = t1set | {r["code"] for r in t2_full}
    kline_map = {c: {"name": rowmap[c]["name"], "dates": rowmap[c]["dates"], "close": rowmap[c]["close"]}
                 for c in union_codes if c in rowmap}

    def slim(r, pullback=False):
        x = {"code": r["code"], "name": r["name"], "p5": r["p5"], "p20": r["p20"]}
        if pullback:
            x["is_pullback"] = (r["p20"] >= PULLBACK_P20 and r["p5"] < 0)
        return x

    t1 = [slim(r) for r in t1_full]
    t2 = [slim(r) for r in t2_full]
    t3 = [slim(r, pullback=True)
          for r in sorted([x for x in rows if x["code"] in t1set], key=lambda x: x["p5"])]
    groups = build_groups(t1)
    direction = build_direction(t1, t2)
    unm = sorted({r["name"] for r in t1 + t2[:DIR_TOP30] if classify_dir(r["name"]) == "其他"})
    if unm:
        print(f"[warn] 表1+表2TOP30 有 {len(unm)} 个未归11方向（计入「其他」）：{unm}", flush=True)

    out = {
        "date": date,
        "midday": midday,
        "pool": "concept_only",
        "pool_size": len(rows),
        "concept_raw": raw_n,
        "cfg_source_date": cfg_date,
        "cfg_fallback_days": back,
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "table1": t1, "t1_group": groups,
        "table2": t2, "table3": t3,
        "direction": direction,
        "kline": kline_map,
        "thresholds": {"topn": TOPN, "dir_t2_top": DIR_TOP30, "pullback_p20": PULLBACK_P20},
    }
    outp = os.path.join(DATA, f"{date}_mainline.json")
    json.dump(out, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[ok] 已写出 {outp}", flush=True)
    print(f"[summary] 表1/2/3 各{TOPN}；方向判定 " +
          " / ".join(f"{x['dir']}{x['t1']}-{x['t2']}({x['signal']})" for x in direction), flush=True)


if __name__ == "__main__":
    main()
