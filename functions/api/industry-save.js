// 势宫行研在线编辑回写：POST /api/industry-save
// body: { key, path, content, message }
// 1) 校验编辑密钥（secret EDIT_KEY）
// 2) 校验 path 白名单（只允许 02 势宫/0201 产业研究所/*.md）
// 3) 先 GET 拿文件 sha，再 PUT 提交到 SugieLiao/shaohao-ruchang 的 main 分支
// 返回 { ok, commit, sha }

const OWNER = "SugieLiao";
const REPO = "shaohao-ruchang";
const BRANCH = "main";
const ALLOW_PREFIX = "02 势宫/0201 产业研究所/";

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8",
               "Access-Control-Allow-Origin": "*" },
  });
}

function unb64(b64) {
  const bin = atob((b64 || "").replace(/\s/g, ""));
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

function b64(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = "";
  const CH = 0x8000;
  for (let i = 0; i < bytes.length; i += CH) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CH));
  }
  return btoa(bin);
}

export async function onRequestPost(context) {
  const { request, env } = context;
  let body;
  try { body = await request.json(); }
  catch { return json({ ok: false, error: "请求体不是合法 JSON" }, 400); }

  const key = (body.key || "").trim();
  const path = (body.path || "").trim();
  const content = body.content;

  if (!env.EDIT_KEY) return json({ ok: false, error: "服务端未配置 EDIT_KEY" }, 500);
  if (key !== env.EDIT_KEY) return json({ ok: false, error: "编辑密钥错误" }, 403);
  if (!path.startsWith(ALLOW_PREFIX) || !path.endsWith(".md"))
    return json({ ok: false, error: "路径不在允许范围：" + path }, 400);
  if (typeof content !== "string" || !content.trim())
    return json({ ok: false, error: "内容为空" }, 400);

  const apiPath = `/repos/${OWNER}/${REPO}/contents/${encodeURI(path)}`;
  const H = { Authorization: `Bearer ${env.GH_PAT}`,
              Accept: "application/vnd.github+json",
              "User-Agent": "liaohao-industry",
              "Content-Type": "application/json" };

  try {
    // 取当前 sha（不预存，避免过期）
    const cur = await fetch(`https://api.github.com${apiPath}?ref=${BRANCH}`, { headers: H });
    if (!cur.ok) {
      const t = await cur.text();
      return json({ ok: false, error: `读取原文件失败 (${cur.status}) ${t.slice(0, 200)}` }, 502);
    }
    const meta = await cur.json();

    // dry=1：只校验密钥与路径可达性，不产生提交（用于自检）
    if (body.dry) {
      return json({ ok: true, dry: true, sha: meta.sha, size: meta.size });
    }

    // 内容无变化则不提交，避免污染仓库历史
    if (unb64(meta.content) === content) {
      return json({ ok: true, unchanged: true, sha: meta.sha });
    }

    const put = await fetch(`https://api.github.com${apiPath}`, {
      method: "PUT",
      headers: H,
      body: JSON.stringify({
        message: body.message || "docs(industry): 线上编辑",
        content: b64(content),
        sha: meta.sha,
        branch: BRANCH,
      }),
    });
    const j = await put.json();
    if (!put.ok) {
      return json({ ok: false, error: `提交失败 (${put.status}) ${j.message || ""}` }, 502);
    }
    return json({ ok: true, commit: (j.commit && j.commit.sha || "").slice(0, 7),
                  sha: j.content && j.content.sha });
  } catch (e) {
    return json({ ok: false, error: String(e.message || e) }, 502);
  }
}

export async function onRequest(context) {
  if (context.request.method === "OPTIONS")
    return new Response(null, { headers: { "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Allow-Methods": "POST,OPTIONS" } });
  if (context.request.method !== "POST")
    return json({ ok: false, error: "仅支持 POST" }, 405);
  return onRequestPost(context);
}
