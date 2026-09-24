#!/usr/bin/env python3
# Cloudflare Pages 发布脚本（从 /tmp/cfpub 用 Assets API 部署到 stock-a 项目）。
# 凭据从环境变量读取：CF_TOKEN（Cloudflare API Token）、CF_ACCOUNT（账户 ID）。
# 由 daily_pipeline.py 调用；BASEDIR 默认 /tmp/cfpub（发布源）。
import os, sys, json, base64, hashlib, mimetypes, urllib.request, urllib.error

TOKEN = os.environ.get("CF_TOKEN")
ACCT = os.environ.get("CF_ACCOUNT")
if not TOKEN or not ACCT:
    print("缺少 CF_TOKEN / CF_ACCOUNT"); sys.exit(1)

BASE = "https://api.cloudflare.com/client/v4"
APIH = {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}

def api(method, path, body=None, extra=None, raw_body=None):
    url = BASE + path
    headers = dict(APIH)
    data = None
    if raw_body is not None:
        data = raw_body
        if extra: headers.update(extra)
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        if extra: headers.update(extra)
    else:
        if extra: headers.update(extra)
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")

# 1) upload JWT
c, t = api("GET", f"/accounts/{ACCT}/pages/projects/stock-a/upload-token")
print("1) upload-token http=", c)
jwt = json.loads(t).get("result", {}).get("jwt")
if not jwt:
    print("无 jwt，终止"); sys.exit(1)

# 2) gather files
BASEDIR = os.environ.get("CF_PUB_DIR", "/tmp/cfpub")
files = []
for root, _, fs in os.walk(BASEDIR):
    for fn in fs:
        full = os.path.join(root, fn)
        rel = os.path.relpath(full, BASEDIR).replace(os.sep, "/")
        if rel.startswith("."):
            continue
        files.append((rel, full))
print("2) files:", [f[0] for f in files])

def md5hex(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

file_hashes = {rel: md5hex(full) for rel, full in files}

# 3) check-missing
c, t = api("POST", "/pages/assets/check-missing", {"hashes": list(file_hashes.values())},
           extra={"Authorization": "Bearer " + jwt})
print("3) check-missing http=", c)
missing = None
try:
    data = json.loads(t)
    if isinstance(data, dict):
        missing = data.get("result")   # API 正常返回 {"success":..,"result":[缺失哈希...]}
    elif isinstance(data, list):
        missing = data
except Exception:
    missing = None
if not isinstance(missing, list):
    print("   check-missing 响应非预期，按全量缺失处理。响应片段:", t[:120])
    missing = list(file_hashes.values())
print("   missing count:", len(missing))

# 4) upload missing —— 分批上传（2026-09-23 修复：原实现把全部文件 base64 塞进单个 POST，
#    全量约 11MB（base64 后约 14.7MB），大请求体写入易被卡死导致 120s 超时。
#    改为每批 ≤8 个文件且原始体积 ≤2MB，单批最多重试 3 次。）
to_up = [(rel, full) for rel, full in files if file_hashes[rel] in missing]
payload = []
for rel, full in to_up:
    data = open(full, "rb").read()
    ctype = "text/html; charset=utf-8" if rel.endswith(".html") else (mimetypes.guess_type(rel)[0] or "application/octet-stream")
    payload.append({"key": file_hashes[rel], "value": base64.b64encode(data).decode(),
                    "metadata": {"contentType": ctype}, "base64": True})

MAX_BATCH_FILES = 8
MAX_BATCH_BYTES = 2 * 1024 * 1024   # 以 base64 后体积计
batches, cur, cur_size = [], [], 0
for it in payload:
    sz = len(it["value"])
    if cur and (cur_size + sz > MAX_BATCH_BYTES or len(cur) >= MAX_BATCH_FILES):
        batches.append(cur); cur, cur_size = [], 0
    cur.append(it); cur_size += sz
if cur:
    batches.append(cur)
print(f"4) upload: {len(payload)} 个文件分 {len(batches)} 批（本次共 {sum(len(b) for b in batches)}）")
for i, b in enumerate(batches):
    ok = False
    for attempt in range(1, 4):
        try:
            c, t = api("POST", "/pages/assets/upload", b, extra={"Authorization": "Bearer " + jwt})
            if c == 200:
                print(f"   批次 {i+1}/{len(batches)} ok（{len(b)} 个文件，第 {attempt} 次尝试）")
                ok = True
                break
            print(f"   批次 {i+1}/{len(batches)} http={c}（第 {attempt} 次）: {t[:120]}")
        except Exception as e:
            print(f"   批次 {i+1}/{len(batches)} 第 {attempt} 次异常: {e}")
    if not ok:
        print(f"   批次 {i+1} 上传失败，终止"); sys.exit(1)

# 5) upsert-hashes
c, t = api("POST", "/pages/assets/upsert-hashes", {"hashes": list(file_hashes.values())},
           extra={"Authorization": "Bearer " + jwt})
print("5) upsert-hashes http=", c)

# 6) manifest + deployment
manifest = {"/" + rel: file_hashes[rel] for rel, _ in files}
boundary = "----cfbound_" + os.urandom(8).hex()
body = b""
for k, v in (("manifest", json.dumps(manifest)), ("branch", "main")):
    body += ("--" + boundary + "\r\n").encode()
    body += ('Content-Disposition: form-data; name="%s"\r\n' % k).encode()
    body += b"\r\n"
    body += (v.encode() if isinstance(v, str) else v)
    body += b"\r\n"
body += ("--" + boundary + "--\r\n").encode()
ctype = "multipart/form-data; boundary=" + boundary

c, t = api("POST", f"/accounts/{ACCT}/pages/projects/stock-a/deployments",
           raw_body=body, extra={"Content-Type": ctype, "Authorization": "Bearer " + TOKEN})
print("6) deployment http=", c)
try:
    d = json.loads(t)
    res = d.get("result", {})
    print("   deployment id:", res.get("id"))
    print("   url:", res.get("url"))
    print("   environment:", res.get("environment"))
except Exception:
    print("   raw:", t[:300])
print("== 完成 ==")
