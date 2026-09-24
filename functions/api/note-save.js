// 投资笔记在线编辑回写：POST /api/note-save
// body: { key, path, content, message, dry }
// 1) 校验编辑密钥（secret EDIT_KEY）
// 2) 校验 path 白名单（只允许 learn/**/index.html）
// 3) 把正文里的 data:image 内嵌图提取为 assets/uploads/*.{png,jpg,webp,gif}
// 4) 用 Git Database API（blobs→tree→commit→ref）一次性原子提交 HTML 与配图
//    （比 Contents API 支持更大图片，且只产生一个 commit）
// 返回 { ok, commit, images, unchanged? }

const OWNER = "SugieLiao";
const REPO = "invest";
const BRANCH = "main";

// 仅允许学习目录下的 index.html（课程页 / 目录主页 / 学习主页）
const PATH_RE = /^learn\/(?:[A-Za-z0-9_\-]+\/)*index\.html$/;
const DATA_IMG_RE = /src="data:image\/(png|jpe?g|webp|gif);base64,([^"]+)"/g;

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
    },
  });
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

function unb64(b64str) {
  const bin = atob((b64str || "").replace(/\s/g, ""));
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder().decode(bytes);
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
  if (!env.GH_PAT) return json({ ok: false, error: "服务端未配置 GH_PAT" }, 500);
  if (key !== env.EDIT_KEY) return json({ ok: false, error: "编辑密钥错误" }, 403);
  if (path.includes("..") || !PATH_RE.test(path))
    return json({ ok: false, error: "路径不在允许范围：" + path }, 400);
  if (typeof content !== "string" || !content.trim())
    return json({ ok: false, error: "内容为空" }, 400);

  // 笔记所在目录（用于放置上传图片）
  const dir = path.slice(0, path.lastIndexOf("/") + 1);

  // 提取内嵌 base64 图片 → 落为 assets/uploads 文件，并把 src 替换为相对路径
  const images = [];
  const seen = new Map();
  const stamp = Date.now().toString(36);
  let seq = 0;
  const finalHtml = content.replace(DATA_IMG_RE, (m, fmt, data) => {
    const full = "data:image/" + fmt + ";base64," + data;
    let rel = seen.get(full);
    if (!rel) {
      const ext = fmt === "jpeg" ? "jpg" : fmt;
      seq += 1;
      const rand = Math.random().toString(36).slice(2, 8);
      const name = `u_${stamp}_${seq}_${rand}.${ext}`;
      rel = "assets/uploads/" + name;
      seen.set(full, rel);
      images.push({ repoPath: dir + rel, rel, data });
    }
    return 'src="' + rel + '"';
  });

  const H = {
    Authorization: `Bearer ${env.GH_PAT}`,
    Accept: "application/vnd.github+json",
    "User-Agent": "invest-note-save",
    "Content-Type": "application/json",
  };
  const gh = (p, opt) => fetch("https://api.github.com" + p, opt);

  try {
    // dry=1：只校验密钥与路径，不提交
    if (body.dry) {
      const ref = await gh(`/repos/${OWNER}/${REPO}/git/ref/heads/${BRANCH}`, { headers: H });
      if (!ref.ok) return json({ ok: false, error: `分支不可达 (${ref.status})` }, 502);
      return json({ ok: true, dry: true, images: images.length });
    }

    // 无新图时，若 HTML 与仓库版本一致则不提交
    if (images.length === 0) {
      const cur = await gh(
        `/repos/${OWNER}/${REPO}/contents/${encodeURI(path)}?ref=${BRANCH}`,
        { headers: H }
      );
      if (cur.ok) {
        const meta = await cur.json();
        if (meta.content && unb64(meta.content) === finalHtml) {
          return json({ ok: true, unchanged: true });
        }
      }
    }

    // 1) 当前分支指向的 commit
    const refResp = await gh(`/repos/${OWNER}/${REPO}/git/ref/heads/${BRANCH}`, { headers: H });
    if (!refResp) return json({ ok: false, error: "读取分支失败" }, 502);
    const refJ = await refResp.json();
    if (!refResp.ok)
      return json({ ok: false, error: `读取分支失败 (${refResp.status}) ${refJ.message || ""}` }, 502);
    const parentCommit = refJ.object.sha;

    // 2) 基线 tree
    const commitResp = await gh(`/repos/${OWNER}/${REPO}/git/commits/${parentCommit}`, { headers: H });
    const commitJ = await commitResp.json();
    if (!commitResp.ok)
      return json({ ok: false, error: `读取提交失败 (${commitResp.status})` }, 502);
    const baseTree = commitJ.tree.sha;

    // 3) 为每张图片创建 blob
    const tree = [];
    for (const im of images) {
      const blobResp = await gh(`/repos/${OWNER}/${REPO}/git/blobs`, {
        method: "POST",
        headers: H,
        body: JSON.stringify({ content: im.data, encoding: "base64" }),
      });
      const blobJ = await blobResp.json();
      if (!blobResp.ok)
        return json({ ok: false, error: `图片上传失败 (${blobResp.status}) ${blobJ.message || ""}` }, 502);
      tree.push({ path: im.repoPath, mode: "100644", type: "blob", sha: blobJ.sha });
    }

    // 4) 为最终 HTML 创建 blob
    const htmlBlobResp = await gh(`/repos/${OWNER}/${REPO}/git/blobs`, {
      method: "POST",
      headers: H,
      body: JSON.stringify({ content: b64(finalHtml), encoding: "base64" }),
    });
    const htmlBlobJ = await htmlBlobResp.json();
    if (!htmlBlobResp.ok)
      return json({ ok: false, error: `HTML 上传失败 (${htmlBlobResp.status})` }, 502);
    tree.push({ path, mode: "100644", type: "blob", sha: htmlBlobJ.sha });

    // 5) 基于基线 tree 创建新 tree
    const treeResp = await gh(`/repos/${OWNER}/${REPO}/git/trees`, {
      method: "POST",
      headers: H,
      body: JSON.stringify({ base_tree: baseTree, tree }),
    });
    const treeJ = await treeResp.json();
    if (!treeResp.ok)
      return json({ ok: false, error: `创建 tree 失败 (${treeResp.status}) ${treeJ.message || ""}` }, 502);

    // 6) 创建 commit
    const newCommitResp = await gh(`/repos/${OWNER}/${REPO}/git/commits`, {
      method: "POST",
      headers: H,
      body: JSON.stringify({
        message: body.message || "docs(note): 线上编辑笔记 " + path,
        tree: treeJ.sha,
        parents: [parentCommit],
      }),
    });
    const newCommitJ = await newCommitResp.json();
    if (!newCommitResp.ok)
      return json({ ok: false, error: `创建 commit 失败 (${newCommitResp.status}) ${newCommitJ.message || ""}` }, 502);

    // 7) 移动分支指针
    const updResp = await gh(`/repos/${OWNER}/${REPO}/git/refs/heads/${BRANCH}`, {
      method: "PATCH",
      headers: H,
      body: JSON.stringify({ sha: newCommitJ.sha, force: false }),
    });
    const updJ = await updResp.json();
    if (!updResp.ok)
      return json({ ok: false, error: `更新分支失败 (${updResp.status}) ${updJ.message || ""}` }, 502);

    return json({
      ok: true,
      commit: newCommitJ.sha.slice(0, 7),
      images: images.length,
    });
  } catch (e) {
    return json({ ok: false, error: String(e.message || e) }, 502);
  }
}

export async function onRequest(context) {
  if (context.request.method === "OPTIONS")
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
      },
    });
  if (context.request.method !== "POST")
    return json({ ok: false, error: "仅支持 POST" }, 405);
  return onRequestPost(context);
}
