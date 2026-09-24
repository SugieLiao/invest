#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_koudai.py — 每日口袋支点数据自动更新

功能：
  1. 检查当天通达信备份文件夹是否存在（TdxBak_YYYYMMDD）
  2. 读取备份中 KD.blk（口袋板块）的股票列表
  3. 与当前 koudai_industry.json 对比，更新股票列表和日期
  4. 新增股票优先从本地行业字典（tdx_stock_industry.json + name_map_full.json）
     自动补全名称和行业信息；本地未找到的标记为"待查询"并发送飞书提醒
  5. 重新渲染收盘版 + 午间版并部署
  6. 备份不存在时发送错误通知
  7. 数据日期非当日时，不再由脚本 sleep 重试，改由 17:30、21:00 两个独立定时任务兜底补采

【重要】板块十一（行业热度得分）依赖口袋+领先股数据，本脚本更新数据后会自动
重新render，板块十一及其历史趋势会同步更新。任何板块数据修正后都必须重新render。

用法：
  python3 update_koudai.py              # 默认今天
  python3 update_koudai.py 2026-08-26  # 指定日期
  python3 update_koudai.py --retry      # 重试模式（由自动重试触发）
"""
import os, sys, json, subprocess, datetime, time

BASE = "/Users/sugieliao/WorkBuddy/A股每日复盘"
DATA = os.path.join(BASE, "data")
BACKUP_ROOT = "/Users/sugieliao/Documents/01 通达信/通达信自定义数据备份"
KOUDAI_JSON = os.path.join(DATA, "koudai_industry.json")

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


def notify_feishu(title, content_lines):
    """发送富文本通知到飞书机器人"""
    if not FEISHU_WEBHOOK:
        return
    try:
        import urllib.request
        content = [[{"tag": "text", "text": line}] for line in content_lines]
        payload = json.dumps({
            "msg_type": "post",
            "content": {"post": {"zh_cn": {"title": title, "content": content}}}
        }).encode()
        req = urllib.request.Request(FEISHU_WEBHOOK, data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            print("[notify] 飞书通知已发送", flush=True)
    except Exception as e:
        print(f"[notify] 飞书通知失败: {e}", flush=True)


RETRY_FLAG = "/tmp/koudai_retry_scheduled"
RETRY_LOG = "/tmp/koudai_retry.log"

def schedule_retry(target_date):
    """安排1小时后自动重试一次（后台进程，避免重复调度）"""
    if os.path.exists(RETRY_FLAG):
        print("[retry] 已有重试任务在等待，跳过重复调度", flush=True)
        return
    # 写入标记文件
    with open(RETRY_FLAG, "w") as f:
        f.write(f"scheduled_at={datetime.datetime.now().isoformat()}\ntarget_date={target_date}\n")
    # 启动后台进程：1小时后重新执行
    cmd = (
        f'nohup bash -c "'
        f'sleep 3600 && '
        f'cd {BASE} && '
        f'/usr/bin/python3 update_koudai.py {target_date} --retry'
        f'" > {RETRY_LOG} 2>&1 &'
    )
    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    retry_time = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%H:%M")
    print(f"[retry] 已安排1小时后（约{retry_time}）自动重试板块十抽取", flush=True)
    notify_feishu(
        f"[A股复盘] 板块十数据非当日，已安排重试 - {target_date}",
        [
            f"当前数据日期非当天（通达信备份尚未生成）",
            f"已安排1小时后（约{retry_time}）自动重试板块十抽取",
            f"重试结果将另行通知",
        ]
    )


def read_blk_codes(blk_path):
    """读取 .blk 文件，返回股票代码列表（6位代码）"""
    codes = []
    with open(blk_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if len(line) >= 7:
                # 第1位市场标记（0深/1沪/2北），后6位股票代码
                code = line[1:7]
                if code.isdigit():
                    codes.append(code)
    return sorted(set(codes))


def load_current_koudai():
    """加载当前 koudai_industry.json"""
    if os.path.exists(KOUDAI_JSON):
        with open(KOUDAI_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"date": "", "stocks": []}


def save_koudai(data):
    """保存 koudai_industry.json"""
    with open(KOUDAI_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
    """加载本地 stock_classify.json、name_map.json、tdx_industry_flat.json、tdx_stock_industry.json"""
    if _local_cache:
        return _local_cache
    # stock_classify.json（个股→行业映射，5556只）
    sc_path = os.path.join(DATA, "stock_classify.json")
    _local_cache["classify"] = json.load(open(sc_path, encoding="utf-8")) if os.path.exists(sc_path) else {}
    # name_map_full.json（完整A股名称，5551只）优先，name_map.json（2000只）兜底
    nm_full_path = os.path.join(BASE, "name_map_full.json")
    nm_path = os.path.join(BASE, "name_map.json")
    name_map = {}
    if os.path.exists(nm_path):
        name_map.update(json.load(open(nm_path, encoding="utf-8")))
    if os.path.exists(nm_full_path):
        name_map.update(json.load(open(nm_full_path, encoding="utf-8")))
    _local_cache["name_map"] = name_map
    # tdx_industry_flat.json（通达信行业字典，用于查找一级行业）
    ind_path = os.path.join(DATA, "tdx_industry_flat.json")
    _local_cache["industry_flat"] = json.load(open(ind_path, encoding="utf-8")) if os.path.exists(ind_path) else {}
    # tdx_stock_industry.json（通达信研究行业三级分类，个股→一二三级行业，5568只）
    tdx_ind_path = os.path.join(DATA, "tdx_stock_industry.json")
    _local_cache["tdx_stock_industry"] = json.load(open(tdx_ind_path, encoding="utf-8")) if os.path.exists(tdx_ind_path) else {}
    return _local_cache


def fill_stock_info_from_local(code):
    """
    从本地数据补全单只股票的名称和行业信息。
    优先使用 tdx_stock_industry.json（通达信研究行业三级分类），
    回退到 stock_classify.json + tdx_industry_flat.json。
    返回 dict，包含 name/industry/industry_l1/l2/l3/industry_path 等字段。
    若本地无数据，返回 None。
    """
    local = load_local_data()
    name_map = local.get("name_map", {})
    tdx_stock_ind = local.get("tdx_stock_industry", {})

    key = code + get_market_suffix(code)
    name = name_map.get(code, "") or name_map.get(key, "")

    # 优先使用通达信研究行业三级分类
    tdx_info = tdx_stock_ind.get(code)
    if tdx_info and tdx_info.get("l1"):
        ind_l1 = tdx_info.get("l1", "")
        ind_l2 = tdx_info.get("l2", "")
        ind_l3 = tdx_info.get("l3", "")
        path_parts = [p for p in [ind_l1, ind_l2, ind_l3] if p]
        return {
            "code": code,
            "name": name,
            "industry": ind_l3,
            "industry_code": "",
            "industry_l1": ind_l1 or "—",
            "industry_l2": ind_l2 or "—",
            "industry_l3": ind_l3 or "—",
            "industry_path": " > ".join(path_parts) if path_parts else "—",
            "industry_blockid": tdx_info.get("blockid", ""),
        }

    # 回退到 stock_classify.json
    classify = local.get("classify", {})
    industry_flat = local.get("industry_flat", {})
    industries = classify.get(key, {}).get("industry", []) if key in classify else []
    if not industries and not name:
        return None

    # 映射：industry[0]最细分(三级)，industry[1]二级，industry[2]一级
    ind_l3 = industries[0] if len(industries) >= 1 else ""
    ind_l2 = industries[1] if len(industries) >= 2 else (industries[0] if industries else "")
    ind_l1 = industries[2] if len(industries) >= 3 else ""

    # 尝试从通达信行业字典查找一级行业（通过二级行业名称匹配父节点）
    if not ind_l1 and ind_l2 and industry_flat:
        for blockid, info in industry_flat.items():
            if info.get("name") == ind_l2:
                parent = info.get("parent")
                if parent and parent in industry_flat:
                    ind_l1 = industry_flat[parent].get("name", "")
                    break

    path_parts = [p for p in [ind_l1, ind_l2, ind_l3] if p]
    return {
        "code": code,
        "name": name,
        "industry": ind_l3,
        "industry_code": "",
        "industry_l1": ind_l1 or "—",
        "industry_l2": ind_l2 or "—",
        "industry_l3": ind_l3 or "—",
        "industry_path": " > ".join(path_parts) if path_parts else "—",
        "industry_blockid": "",
    }


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
    retry_mode = "--retry" in args
    if midday_mode:
        args.remove("--midday")
    if retry_mode:
        args.remove("--retry")

    if args:
        target_date = args[0]
    else:
        target_date = datetime.date.today().strftime("%Y-%m-%d")

    date_compact = target_date.replace("-", "")
    mode_label = "（重试）" if retry_mode else ""
    print(f"===== 口袋支点数据自动更新 {target_date}{mode_label} =====", flush=True)

    # 1. 检查当天备份是否存在，不存在则回退到前一个交易日的备份
    def find_backup(date_str):
        """查找指定日期的备份目录，返回(backup_dir, kd_blk, lxg_blk, fault_blk, data_date)或None"""
        dc0 = date_str.replace("-", "")
        bd = os.path.join(BACKUP_ROOT, f"TdxBak_{dc0}")
        if not os.path.isdir(bd):
            return None
        kd = os.path.join(bd, "T0002", "blocknew", "KD.blk")
        if not os.path.exists(kd):
            return None
        # 领先股板块（可选，不存在则返回None）
        lxg = os.path.join(bd, "T0002", "blocknew", "2-LXG.blk")
        if not os.path.exists(lxg):
            lxg = None
        # 净利润断层板块（可选，不存在则返回None）
        fault = os.path.join(bd, "T0002", "blocknew", "2-JLRDC.blk")
        if not os.path.exists(fault):
            fault = None
        return (bd, kd, lxg, fault, date_str)

    # 先尝试今天，再尝试前一天（最多回退7天找最近的备份）
    backup_info = None
    fallback_days = 0
    for i in range(8):
        d = (datetime.datetime.strptime(target_date, "%Y-%m-%d") - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        result = find_backup(d)
        if result:
            backup_info = result
            fallback_days = i
            break

    if backup_info is None:
        msg = f"通达信备份文件夹不存在：已尝试最近8天均无 TdxBak_YYYYMMDD 备份\n请确认通达信已完成数据备份后手动重跑。"
        notify_error(f"[A股复盘] 口袋数据更新失败 - {target_date}", msg)
        sys.exit(1)

    backup_dir, kd_blk, lxg_blk, fault_blk, data_date = backup_info
    if fallback_days > 0:
        print(f"[warn] 当天备份不存在，回退使用 {data_date} 的备份（差{fallback_days}天），页面将显示红色感叹号", flush=True)
    else:
        print(f"[ok] 使用当天备份 {data_date}", flush=True)

    # 读取口袋板块、领先股板块、净利润断层板块，合并去重
    kd_codes = read_blk_codes(kd_blk)
    lxg_codes = read_blk_codes(lxg_blk) if lxg_blk else []
    fault_codes = read_blk_codes(fault_blk) if fault_blk else []
    new_codes = sorted(set(kd_codes + lxg_codes + fault_codes))
    print(f"[read] 口袋板块：{len(kd_codes)} 只，领先股板块：{len(lxg_codes)} 只，净利润断层：{len(fault_codes)} 只，合并去重后：{len(new_codes)} 只", flush=True)

    # 3. 对比当前数据
    current = load_current_koudai()
    current_stocks = current.get("stocks", [])
    current_codes = {s.get("code", "") for s in current_stocks}
    current_map = {s.get("code", ""): s for s in current_stocks}

    added = [c for c in new_codes if c not in current_codes]
    removed = [c for c in current_codes if c not in set(new_codes)]

    print(f"[diff] 新增：{len(added)} 只，移除：{len(removed)} 只", flush=True)
    if added:
        print(f"  新增代码：{added}", flush=True)
    if removed:
        print(f"  移除代码：{removed}", flush=True)

    # 4. 构建新的股票列表（合并口袋+领先股+净利润断层，记录来源）
    kd_set = set(kd_codes)
    lxg_set = set(lxg_codes)
    fault_set = set(fault_codes)
    new_stocks = []
    for code in new_codes:
        source_list = []
        if code in kd_set:
            source_list.append('口袋')
        if code in lxg_set:
            source_list.append('领先股')
        if code in fault_set:
            source_list.append('断层')
        source = '+'.join(source_list)
        
        if code in current_map:
            # 已有股票，保留原信息，更新来源
            stock = dict(current_map[code])
            stock['source'] = source
            new_stocks.append(stock)
        else:
            # 新增股票，优先从本地行业字典补全名称和行业信息
            local_info = fill_stock_info_from_local(code)
            if local_info:
                local_info['source'] = source
                new_stocks.append(local_info)
                print(f"  [local] {code} {local_info.get('name','')}: {local_info.get('industry_path','')}", flush=True)
            else:
                # 本地无数据，标记为待查询
                new_stocks.append({
                    "code": code,
                    "name": "",
                    "industry": "",
                    "industry_code": "",
                    "industry_l1": "",
                    "industry_l2": "",
                    "industry_l3": "",
                    "industry_path": "待查询",
                    "industry_blockid": "",
                    "source": source,
                    "note": "新增股票，行业信息待通过问小达查询补全"
                })

    # 5. 更新 date 为实际备份日期并保存
    # 若回退到前一天备份，date=前一天日期，页面会自动显示红色感叹号
    current["date"] = data_date
    current["source"] = "口袋(KD.blk) + 领先股(2-LXG.blk) + 净利润断层(2-JLRDC.blk)"
    current["koudai_count"] = len(kd_codes)
    current["leading_count"] = len(lxg_codes)
    current["fault_count"] = len(fault_codes)
    current["count"] = len(new_stocks)
    current["stocks"] = new_stocks
    save_koudai(current)
    print(f"[save] koudai_industry.json 已更新，数据日期={data_date}，股票数={len(new_stocks)}", flush=True)

    # 5.5 数据非当日：不再由脚本 sleep 重试，改由 17:30、21:00 两个独立定时任务兜底补采
    is_stale = (data_date != target_date)
    if is_stale and not retry_mode and not midday_mode:
        print("[retry] 数据非当日，将由 17:30、21:00 定时补采任务兜底，本脚本不再启动后台重试", flush=True)
        notify_feishu(
            f"[A股复盘] 板块十数据非当日，等待定时补采 - {target_date}",
            [
                f"当前数据日期：{data_date}（差{fallback_days}天，通达信当天备份尚未生成）",
                f"17:30、21:00 的板块十补采任务将自动再尝试，无需手动干预",
            ]
        )
    if retry_mode:
        # 重试模式：清理标记文件，根据结果发送飞书通知
        if os.path.exists(RETRY_FLAG):
            os.remove(RETRY_FLAG)
        if is_stale:
            notify_feishu(
                f"[A股复盘] 板块十重试仍未获取当天数据 - {target_date}",
                [
                    f"重试结果：❌ 仍未获取当天备份",
                    f"当前数据日期：{data_date}（差{fallback_days}天）",
                    f"通达信当天备份仍未生成，请稍后手动检查或等待下一交易日",
                ]
            )
        else:
            notify_feishu(
                f"[A股复盘] 板块十重试成功 - {target_date}",
                [
                    f"重试结果：✅ 成功获取当天数据",
                    f"数据日期：{data_date}",
                    f"口袋：{len(kd_codes)}只，领先股：{len(lxg_codes)}只，净利润断层：{len(fault_codes)}只，合计去重：{len(new_stocks)}只",
                    f"收盘版+午间版已重新渲染并部署",
                ]
            )

    # 6. 重新渲染
    # 自动检测当天数据文件是否存在，不存在则回退到最近一个有数据的交易日
    def find_render_date(date_str):
        """找到最近一个有hithink数据文件的交易日"""
        for i in range(10):
            d = (datetime.datetime.strptime(date_str, "%Y-%m-%d") - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            hithink_file = os.path.join(DATA, f"{d}_hithink.json")
            if os.path.exists(hithink_file):
                return d, i
        return date_str, 0

    render_date, render_fallback = find_render_date(target_date)
    if render_fallback > 0:
        print(f"[warn] 当天数据文件不存在，回退使用 {render_date} 的数据渲染（差{render_fallback}天），页面将显示红色感叹号", flush=True)
    else:
        print(f"[ok] 使用当天数据 {render_date} 渲染", flush=True)

    render_ok = True
    if midday_mode:
        # 午间版模式：只渲染午间版
        # 报告日期=当天，数据日期=回退后的日期（模块会显示红色感叹号）
        print("[mode] 午间版模式：仅渲染午间版", flush=True)
        render_cmd = ["python3", "render.py", target_date, "--midday"]
        if render_date != target_date:
            render_cmd.extend(["--data-date", render_date])
        if not run(render_cmd, "渲染午间版"):
            render_ok = False
    else:
        # 收盘版模式：渲染收盘版+午间版
        close_cmd = ["python3", "render.py", target_date]
        midday_cmd = ["python3", "render.py", target_date, "--midday"]
        if render_date != target_date:
            close_cmd.extend(["--data-date", render_date])
            midday_cmd.extend(["--data-date", render_date])
        if not run(close_cmd, "渲染收盘版"):
            render_ok = False
        if not run(midday_cmd, "渲染午间版"):
            render_ok = False

    if not render_ok:
        notify_error(f"[A股复盘] 口袋数据渲染失败 - {target_date}", "渲染失败，请检查日志。")
        sys.exit(1)

    # 7. 部署
    # 输出文件名按报告日期（当天日期）命名，部署日期使用当天日期
    deploy_date = target_date
    if midday_mode:
        # 午间版模式：当天可能没有收盘版HTML，需找到最近一个有收盘版HTML的交易日来部署
        for i in range(10):
            d = (datetime.datetime.strptime(target_date, "%Y-%m-%d") - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            close_html = os.path.join(BASE, f"A股复盘_{d}.html")
            if os.path.exists(close_html):
                deploy_date = d
                if i > 0:
                    print(f"[deploy] 当天无收盘版HTML，使用 {deploy_date} 部署（覆盖其午间版）", flush=True)
                break
        # 把今天渲染的午间版HTML复制为deploy_date的午间版HTML（覆盖）
        today_midday_html = os.path.join(BASE, f"A股午盘_{target_date}.html")
        deploy_midday_html = os.path.join(BASE, f"A股午盘_{deploy_date}.html")
        if os.path.exists(today_midday_html) and deploy_date != target_date:
            import shutil
            shutil.copy2(today_midday_html, deploy_midday_html)
            print(f"[deploy] 已将午间版HTML复制为 {deploy_midday_html}", flush=True)

    deploy_cmd = [
        "/Users/sugieliao/.workbuddy/binaries/python/versions/3.13.12/bin/python3",
        "deploy_light_pos.py", deploy_date
    ]
    if not run(deploy_cmd, "部署到线上", timeout=180):
        notify_error(f"[A股复盘] 口袋数据部署失败 - {target_date}", "部署到 Cloudflare Pages 失败，请检查日志。")
        sys.exit(1)

    # 8. 如果有新增股票且本地未找到行业信息，提醒需要补全
    pending_stocks = [s for s in new_stocks if s.get("industry_path") == "待查询"]
    if pending_stocks:
        pending_codes = [s["code"] for s in pending_stocks]
        msg = (f"口袋板块新增 {len(added)} 只股票，其中 {len(pending_stocks)} 只本地未找到行业信息：{pending_codes}\n"
               f"已自动从本地行业字典补全 {len(added)-len(pending_stocks)} 只的行业信息。\n"
               f"未补全的股票请通过问小达MCP逐只查询后更新 koudai_industry.json。")
        notify_error(f"[A股复盘] 口袋板块新增股票提醒 - {target_date}", msg)
    elif added:
        print(f"[info] 新增 {len(added)} 只股票，行业信息已全部从本地行业字典自动补全", flush=True)

    print(f"===== 完成（已部署） =====", flush=True)


if __name__ == "__main__":
    main()
