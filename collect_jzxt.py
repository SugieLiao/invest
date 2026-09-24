#!/usr/bin/env python3
# 取「均占系统」(ghxb.site/jzxt) 均线占比 日线数据，写 data/jzxt_history.json。
# 来源：均占系统 实时/历史接口。均线占比＝站上对应周期均线的股票占比(%)，是衡量市场宽度/情绪的指标。
#   - 实时：GET /api/admin/tick/realtime（含日内分时序列）
#   - 历史/日线：GET /api/admin/daily/range?from=dxb&marketType=sub&startTime=<ms>&endTime=<ms>
# 鉴权：Authorization: Bearer <token>，token 存于 data/.jzxt_token（或环境变量 JZXT_TOKEN）。
# 自动登录：若 data/.jzxt_credentials 存在（{"username","password"}），token 过期时自动用凭据重新登录刷新 token。
# 本脚本取 daily/range（#/history 页同款数据），拉取最近 ~500 天窗口。
import json, os, sys, datetime, subprocess, base64
# /usr/bin/python3 (CommandLineTools) 默认不加载 user site-packages，手动加入以使用 pip --user 安装的 cryptography
import site as _site
_us = _site.getusersitepackages()
if _us and _us not in sys.path:
    sys.path.insert(0, _us)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE = "/Users/sugieliao/WorkBuddy/A股每日复盘"
DATA = os.path.join(BASE, "data")
TOKEN_FILE = os.path.join(DATA, ".jzxt_token")
CRED_FILE = os.path.join(DATA, ".jzxt_credentials")
OUT = os.path.join(DATA, "jzxt_history.json")
HOST = "http://www.ghxb.site"
API = "/api/admin/daily/range"
CLIENT_ID = "dxb_c_end_h5_97aea4dcddd24d68a4054727b145b5d4"
WINDOW_DAYS = 500

def get_token():
    t = os.environ.get("JZXT_TOKEN")
    if t and t.strip():
        return t.strip()
    if os.path.exists(TOKEN_FILE):
        try:
            return open(TOKEN_FILE, encoding="utf-8").read().strip()
        except Exception:
            return None
    return None

def get_credentials():
    """读取本地凭据文件（如有），返回 (username, password) 或 None。"""
    if not os.path.exists(CRED_FILE):
        return None
    try:
        d = json.load(open(CRED_FILE, encoding="utf-8"))
        u = (d.get("username") or "").strip()
        p = d.get("password") or ""
        if u and p:
            return u, p
    except Exception:
        pass
    return None

def get_challenge():
    """获取登录 challenge：返回 (requestId, secretKey, None) 或 (None, None, err)。"""
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "15",
                            f"{HOST}/api/admin/common/auth/challenge"],
                           capture_output=True, text=True, timeout=20)
        j = json.loads(r.stdout)
        if j.get("code") == "0000" and j.get("data"):
            return j["data"].get("requestId"), j["data"].get("secretKey"), None
        return None, None, f"challenge 异常 code={j.get('code')} msg={j.get('message')}"
    except Exception as e:
        return None, None, f"challenge 请求异常：{e}"

def encrypt_password(password, secret_key):
    """AES-GCM 加密密码（与前端一致）：密钥=secret_key UTF-8编码，iv=随机12字节，tagLength=128。
    返回 (iv_base64, encrypted_data_base64)。"""
    key = secret_key.encode("utf-8")
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    ct = aesgcm.encrypt(iv, password.encode("utf-8"), None)  # 返回 ciphertext + tag(16字节)
    return base64.b64encode(iv).decode(), base64.b64encode(ct).decode()

def login(username, password):
    """用用户名密码登录，返回 (token, None) 或 (None, err)。"""
    request_id, secret_key, err = get_challenge()
    if err:
        return None, err
    iv, enc_pwd = encrypt_password(password, secret_key)
    payload = json.dumps({
        "username": username,
        "password": enc_pwd,
        "clientId": CLIENT_ID,
        "grantType": "password",
        "requestId": request_id,
        "iv": iv,
    })
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "20",
                            "-X", "POST",
                            "-H", "Content-Type: application/json",
                            "-d", payload,
                            f"{HOST}/api/admin/c-auth/login"],
                           capture_output=True, text=True, timeout=25)
        j = json.loads(r.stdout)
        if j.get("success") or j.get("code") == "0000":
            data = j.get("data") or j
            token = data.get("accessToken") or data.get("token")
            if token:
                return token, None
            return None, "登录成功但未返回 token"
        return None, f"登录失败 code={j.get('code')} msg={j.get('message')}"
    except Exception as e:
        return None, f"登录请求异常：{e}"

def auto_refresh_token():
    """如果本地有凭据文件，自动登录刷新 token 并写入 .jzxt_token。返回 (token, None) 或 (None, err)。"""
    cred = get_credentials()
    if not cred:
        return None, "无凭据文件（data/.jzxt_credentials），无法自动登录"
    username, password = cred
    token, err = login(username, password)
    if err:
        return None, err
    try:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(token)
        os.chmod(TOKEN_FILE, 0o600)
    except Exception as e:
        return None, f"token 写入失败：{e}"
    return token, None

def ms(y, mo, d, h=0, mi=0, se=0):
    dt = datetime.datetime(y, mo, d, h, mi, se,
                           tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
    return int(dt.timestamp() * 1000)

def fetch(token):
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    start = now - datetime.timedelta(days=WINDOW_DAYS)
    S = ms(start.year, start.month, start.day)
    E = ms(now.year, now.month, now.day, 23, 59, 59)
    url = (f"{HOST}{API}?from=dxb&marketType=sub&startTime={S}&endTime={E}")
    try:
        r = subprocess.run(["curl", "-s", "--max-time", "40",
                            "-H", f"Authorization: Bearer {token}", url],
                           capture_output=True, text=True, timeout=60)
        if not r.stdout.strip():
            return None, "接口返回空", None
        j = json.loads(r.stdout)
        if j.get("code") == "0000" and j.get("data"):
            return j["data"], None, None
        return None, f"接口异常 code={j.get('code')} msg={j.get('message')}", j.get("code")
    except Exception as e:
        return None, f"请求异常：{e}", None

def main():
    token = get_token()
    if not token:
        # 无 token 时尝试自动登录
        token, err = auto_refresh_token()
        if err:
            out = {"ok": False, "reason": f"缺少 token 且自动登录失败：{err}",
                   "updated": datetime.date.today().strftime("%Y-%m-%d")}
            json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
            print(f"[jzxt] 缺少 token，自动登录失败（{err}），已写 ok:false 占位。")
            return
        print("[jzxt] 无 token，已通过凭据自动登录获取新 token。")

    data, err, code = fetch(token)
    # token 过期（C105）时自动刷新重试一次
    if code == "C105" or (err and "过期" in (err or "")):
        print(f"[jzxt] token 过期（{err}），尝试自动登录刷新...")
        new_token, refresh_err = auto_refresh_token()
        if refresh_err:
            print(f"[jzxt] 自动刷新失败：{refresh_err}")
        else:
            token = new_token
            print("[jzxt] token 已刷新，重新取数...")
            data, err, code = fetch(token)

    if err or not data:
        # 失败保护：若已有 ok:true 的历史数据，保留旧文件不覆盖（页面继续显示上一交易日），
        # 仅当无旧数据或旧数据本身是失败占位时才写 ok:false。
        if os.path.exists(OUT):
            try:
                old = json.load(open(OUT, encoding="utf-8"))
                if old.get("ok") and old.get("dates"):
                    print(f"[jzxt] 取数失败（{err}），保留上次数据"
                          f"（截至 {old['dates'][-1]}），不覆盖。")
                    return
            except Exception:
                pass
        out = {"ok": False, "reason": err or "无数据",
               "updated": datetime.date.today().strftime("%Y-%m-%d")}
        json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
        print(f"[jzxt] 取数失败（{err}），无可用旧数据，已写 ok:false 占位；下次运行自动重试。")
        return
    dates = data.get("dates") or []
    out = {
        "ok": True,
        "marketType": data.get("marketType"),
        "source": "均占系统 ghxb.site/jzxt（/api/admin/daily/range，Bearer 鉴权）",
        "updated": datetime.date.today().strftime("%Y-%m-%d"),
        "dates": dates,
        "cdx": data.get("cdx"), "dx": data.get("dx"),
        "zx": data.get("zx"), "cx": data.get("cx"),
        "kx": data.get("kx"), "mx": data.get("mx"),
    }
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"[jzxt] 已写 {len(dates)} 个交易日 均线占比，范围 {dates[0]} → {dates[-1]}"
          f"（最新 5/13/50/120 = {out['cdx'][-1]:.2f}/{out['dx'][-1]:.2f}/{out['zx'][-1]:.2f}/{out['cx'][-1]:.2f}）")

if __name__ == "__main__":
    main()
