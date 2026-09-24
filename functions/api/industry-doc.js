// 势宫行研内容读取：GET /api/industry-doc?path=<urlencoded 仓库相对路径>
// 直接从 GitHub 读最新内容（仓库为 public），保证线上编辑后立即回显。
// 经 Cloudflare 边缘代理，避免国内直连 raw.githubusercontent.com 不稳。
// 返回 { ok, content, sha, size }

const OWNER = "SugieLiao";
const REPO = "shaohao-ruchang";
const BRANCH = "main";
const ALLOW_PREFIX = "02 势宫/0201 产业研究所/";

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8",
               "Access-Control-Allow-Origin": "*",
               "Cache-Control": "no-store" },
  });
}

function unb64(b64) {
  const bin = atob(b64.replace(/\s/g, ""));
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder().decode(bytes);
}

export async function onRequestGet(context) {
  const { request, env } = context;
  const path = new URL(request.url).searchParams.get("path") || "";
  if (!path.startsWith(ALLOW_PREFIX) || !path.endsWith(".md"))
    return json({ ok: false, error: "路径不在允许范围：" + path }, 400);

  const H = { Accept: "application/vnd.github+json", "User-Agent": "liaohao-industry" };
  if (env.GH_PAT) H.Authorization = `Bearer ${env.GH_PAT}`;

  try {
    const r = await fetch(
      `https://api.github.com/repos/${OWNER}/${REPO}/contents/${encodeURI(path)}?ref=${BRANCH}`,
      { headers: H });
    if (!r.ok) {
      const t = await r.text();
      return json({ ok: false, error: `GitHub 读取失败 (${r.status}) ${t.slice(0, 160)}` }, 502);
    }
    const j = await r.json();
    return json({ ok: true, content: unb64(j.content || ""), sha: j.sha, size: j.size });
  } catch (e) {
    return json({ ok: false, error: String(e.message || e) }, 502);
  }
}

export async function onRequest(context) {
  if (context.request.method !== "GET")
    return json({ ok: false, error: "仅支持 GET" }, 405);
  return onRequestGet(context);
}
