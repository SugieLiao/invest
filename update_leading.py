#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_leading.py — 每日领先股数据自动更新

功能：
  1. 检查当天通达信备份文件夹是否存在（TdxBak_YYYYMMDD）
  2. 读取备份中 2-LXG.blk（领先股板块）的股票列表
  3. 与当前 leading_industry.json 对比，更新股票列表和日期
  4. 新增股票优先从本地行业字典（stock_classify.json + name_map.json + tdx_industry_flat.json）
     自动补全名称和行业信息；本地未找到的标记为"待查询"并发送飞书提醒
  5. 重新渲染收盘版 + 午间版并部署
  6. 备份不存在时发送错误通知

用法：
  python3 update_leading.py              # 默认今天
  python3 update_leading.py 2026-08-26  # 指定日期
  python3 update_leading.py --midday     # 午间版模式（不更新数据，仅渲染）
"""
import os, sys, json, subprocess, datetime
from collections import Counter

BASE = "/Users/sugieliao/WorkBuddy/A股每日复盘"
DATA = os.path.join(BASE, "data")
BACKUP_ROOT = "/Users/sugieliao/Documents/01 通达信/通达信自定义数据备份"
LEADING_JSON = os.path.join(DATA, "leading_industry.json")
BLK_FILE = "2-LXG.blk"  # 领先股板块文件

# 飞书机器人 webhook
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/0e04b8ee-4993-49ad-b4ef-d971aecafb65"


def notify_error(title, body):
    """发送错误通知到飞书机器人"""
    print(f"[ERROR] {title}: {body}", flush=True)
    if not FEISHU_WEBHOOK:
        print("[notify] 飞书webhook未配置，跳过通知", flush=True)
        return
    try:
        import urllib.request
        payload = json.dumps({
            "msg_type": "text",
            "content": {"text": f"{title}\n{body}"}
        }).encode()
        req = urllib.request.Request(FEISHU_WEBHOOK, data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            print("[notify] 飞书通知已发送", flush=True)
        else:
            print(f"[notify] 飞书通知返回异常: {result}", flush=True)
    except Exception as e:
        print(f"[notify] 飞书通知失败: {e}", flush=True)


def read_blk_codes(blk_path):
    """读取 .blk 文件，返回股票代码列表（6位代码）"""
    codes = []
    with open(blk_path, "r", encoding="gbk", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if len(line) >= 7:
                # 第1位市场标记（0深/1沪/2北），后6位股票代码
                code = line[1:7]
                if code.isdigit():
                    codes.append(code)
    return sorted(set(codes))


def get_market_suffix(code):
    """根据股票代码判断市场后缀"""
    if code.startswith('6') or code.startswith('9'):
        return '.SH'
    elif code.startswith('0') or code.startswith('3') or code.startswith('2'):
        return '.SZ'
    elif code.startswith('8') or code.startswith('4'):
        return '.BJ'
    return '.SH'


# 本地数据缓存（懒加载）
_local_cache = {}

def load_local_data():
    """加载本地 stock_classify.json、name_map.json、tdx_industry_flat.json"""
    if _local_cache:
        return _local_cache
    # stock_classify.json（个股→行业映射）
    sc_path = os.path.join(DATA, "stock_classify.json")
    _local_cache["classify"] = json.load(open(sc_path, encoding="utf-8")) if os.path.exists(sc_path) else {}
    # name_map.json（股票代码→名称映射）
    nm_path = os.path.join(BASE, "name_map.json")
    _local_cache["name_map"] = json.load(open(nm_path, encoding="utf-8")) if os.path.exists(nm_path) else {}
    # tdx_industry_flat.json（通达信行业字典，用于查找一级行业）
    ind_path = os.path.join(DATA, "tdx_industry_flat.json")
    _local_cache["industry_flat"] = json.load(open(ind_path, encoding="utf-8")) if os.path.exists(ind_path) else {}
    return _local_cache


def get_node_name(code_or_name, code_to_node):
    """通过代码或名称获取节点名称"""
    if not code_or_name:
        return ''
    if code_or_name.startswith('X') and code_or_name in code_to_node:
        return code_to_node[code_or_name].get('name', '')
    return code_or_name


def fill_stock_info_from_local(code):
    """
    从本地数据补全单只股票的名称和行业信息。
    返回 dict，包含 name/industry_l1/l2/l3/industry_path 等字段。
    若本地无数据，返回 None。
    """
    local = load_local_data()
    classify = local.get("classify", {})
    name_map = local.get("name_map", {})
    industry_flat = local.get("industry_flat", {})

    key = code + get_market_suffix(code)
    name = name_map.get(key, "")

    # industry数组按[三级,二级]排列
    industries = classify.get(key, {}).get("industry", []) if key in classify else []
    if not industries and not name:
        return None

    ind_l3 = industries[0] if len(industries) >= 1 else ""
    ind_l2 = industries[1] if len(industries) >= 2 else ""
    ind_l1 = ""

    # 构建名称到节点和代码到节点的映射
    name_to_node = {}
    code_to_node = {}
    for k, node in industry_flat.items():
        if isinstance(node, dict):
            name_to_node[node.get('name', '')] = node
            code_to_node[k] = node

    # 通过三级行业节点找parent（二级），再找parent（一级）
    if ind_l3 and ind_l3 in name_to_node:
        node = name_to_node[ind_l3]
        parent_code = node.get('parent', '')
        parent_name = get_node_name(parent_code, code_to_node)
        if parent_name:
            if parent_name in name_to_node:
                parent_node = name_to_node[parent_name]
                ind_l1 = get_node_name(parent_node.get('parent', ''), code_to_node)
                if not ind_l2:
                    ind_l2 = parent_name
            else:
                ind_l1 = parent_name
    if not ind_l1 and ind_l2 and ind_l2 in name_to_node:
        node = name_to_node[ind_l2]
        ind_l1 = get_node_name(node.get('parent', ''), code_to_node)

    path_parts = [p for p in [ind_l1, ind_l2, ind_l3] if p]
    return {
        "code": key,
        "name": name or code,
        "industry_l1": ind_l1 or "—",
        "industry_l2": ind_l2 or "—",
        "industry_l3": ind_l3 or "—",
        "industry_path": " > ".join(path_parts) if path_parts else "—",
    }


def load_current_leading():
    """加载当前 leading_industry.json"""
    if os.path.exists(LEADING_JSON):
        with open(LEADING_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"date": "", "stocks": []}


def save_leading(data):
    """保存 leading_industry.json"""
    with open(LEADING_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_latest_backup(target_date):
    """
    查找目标日期的备份文件夹，若不存在则回退到最近8天内的备份。
    返回 (backup_path, actual_date) 或 (None, None)
    """
    # 先找目标日期
    target_dir = os.path.join(BACKUP_ROOT, f"TdxBak_{target_date.replace('-', '')}")
    if os.path.exists(target_dir):
        return target_dir, target_date

    # 回退到最近8天
    target_dt = datetime.datetime.strptime(target_date, "%Y-%m-%d")
    for i in range(1, 9):
        check_dt = target_dt - datetime.timedelta(days=i)
        check_dir = os.path.join(BACKUP_ROOT, f"TdxBak_{check_dt.strftime('%Y%m%d')}")
        if os.path.exists(check_dir):
            actual_date = check_dt.strftime("%Y-%m-%d")
            print(f"[backup] 当天备份不存在，回退到 {actual_date} 的备份", flush=True)
            return check_dir, actual_date

    return None, None


def run(cmd, label, timeout=300):
    """运行命令并打印结果"""
    print(f"[run] {label}: {' '.join(cmd)}", flush=True)
    try:
        r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            print(f"  x {label} 失败 (rc={r.returncode})", flush=True)
            print((r.stderr or r.stdout)[-500:], file=sys.stderr, flush=True)
            return False
        print(f"  ok {label} 完成", flush=True)
        return True
    except Exception as e:
        print(f"  x {label} 异常: {e}", flush=True)
        return False


def main():
    # 确定日期和模式
    args = sys.argv[1:]
    midday_mode = "--midday" in args
    if midday_mode:
        args.remove("--midday")

    if args:
        target_date = args[0]
    else:
        target_date = datetime.date.today().strftime("%Y-%m-%d")

    print(f"===== 领先股数据更新 {target_date} ({'午间版' if midday_mode else '收盘版'}) =====", flush=True)

    # 午间版模式：不更新数据，仅渲染
    if midday_mode:
        print("[mode] 午间版：不更新领先股数据，沿用上一交易日数据", flush=True)
        run(["python3", "render.py", target_date, "--midday"], "渲染午间版")
        run(["/Users/sugieliao/.workbuddy/binaries/python/versions/3.13.12/bin/python3",
             "deploy_light_pos.py", target_date], "部署")
        return

    # 查找备份文件夹
    backup_path, actual_date = find_latest_backup(target_date)
    if not backup_path:
        notify_error("领先股数据更新失败",
                     f"日期 {target_date} 及最近8天内均无通达信备份文件夹，无法读取领先股板块数据。")
        return

    # 读取领先股板块
    blk_path = os.path.join(backup_path, "T0002", "blocknew", BLK_FILE)
    if not os.path.exists(blk_path):
        notify_error("领先股数据更新失败",
                     f"备份文件夹 {backup_path} 中未找到 {BLK_FILE} 文件。")
        return

    new_codes = read_blk_codes(blk_path)
    print(f"[blk] 从 {BLK_FILE} 读取到 {len(new_codes)} 只股票", flush=True)

    # 加载当前数据
    current = load_current_leading()
    current_stocks = {s.get("code", "").split(".")[0]: s for s in current.get("stocks", [])}

    # 更新股票列表
    updated_stocks = []
    new_added = []
    for code in new_codes:
        if code in current_stocks:
            # 已有股票，保留原数据
            updated_stocks.append(current_stocks[code])
        else:
            # 新增股票，从本地补全
            info = fill_stock_info_from_local(code)
            if info:
                updated_stocks.append(info)
                new_added.append(info)
            else:
                # 本地未找到，标记为待查询
                updated_stocks.append({
                    "code": code + get_market_suffix(code),
                    "name": code,
                    "industry_l1": "待查询",
                    "industry_l2": "—",
                    "industry_l3": "—",
                    "industry_path": "待查询",
                })
                new_added.append({"code": code, "name": code, "status": "待查询"})

    # 统计行业分布
    l1_counter = Counter(s.get("industry_l1", "") for s in updated_stocks if s.get("industry_l1") and s.get("industry_l1") != "—")
    industry_dist = [{"industry": k, "count": v} for k, v in l1_counter.most_common()]

    # 保存数据
    leading_data = {
        "date": actual_date,
        "source": f"通达信自定义板块 {BLK_FILE}",
        "count": len(updated_stocks),
        "stocks": updated_stocks,
        "industry_dist": industry_dist,
    }
    save_leading(leading_data)
    print(f"[save] 已保存 {len(updated_stocks)} 只领先股数据到 leading_industry.json", flush=True)

    # 新增股票提醒
    if new_added:
        pending = [s for s in new_added if s.get("status") == "待查询"]
        if pending:
            names = ", ".join(s.get("name", "") for s in pending[:10])
            notify_error("领先股板块新增股票待查询",
                         f"新增 {len(new_added)} 只股票，其中 {len(pending)} 只本地行业字典未找到：{names}")
        else:
            names = ", ".join(s.get("name", "") for s in new_added[:10])
            print(f"[notify] 新增 {len(new_added)} 只股票，已全部从本地补全行业信息：{names}", flush=True)

    # 渲染和部署
    run(["python3", "render.py", target_date], "渲染收盘版")
    run(["python3", "render.py", target_date, "--midday"], "渲染午间版")
    run(["/Users/sugieliao/.workbuddy/binaries/python/versions/3.13.12/bin/python3",
         "deploy_light_pos.py", target_date], "部署")

    print(f"===== 领先股数据更新完成 {target_date} =====", flush=True)


if __name__ == "__main__":
    main()
