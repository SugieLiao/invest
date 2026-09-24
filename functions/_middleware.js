// 笔记即时覆盖（middleware）：
// GET /learn/** 时，先查 KV 里是否有用户在线编辑保存的最新版本（HTML 或新上传图片）。
// 命中则直接返回最新内容（保存后秒级可见，无需重新部署）；未命中则回退静态文件。
const IMG_CT = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
  ".gif": "image/gif",
};

export async function onRequest(context) {
  const { request, env, next } = context;

  // 非 GET、或没有 KV 绑定，一律走静态资源
  if (request.method !== "GET" || !env.NOTE_KV) return next();

  const url = new URL(request.url);
  const p = url.pathname;
  if (!p.startsWith("/learn/")) return next();

  // 规范化为仓库内路径：/learn/a/ -> learn/a/index.html
  let repo = p.replace(/^\//, "");
  if (repo.endsWith("/")) repo += "index.html";

  try {
    if (repo.endsWith(".html")) {
      const html = await env.NOTE_KV.get(repo);
      if (html !== null) {
        return new Response(html, {
          headers: {
            "content-type": "text/html; charset=utf-8",
            "cache-control": "no-store",
          },
        });
      }
    } else {
      const ext = repo.slice(repo.lastIndexOf(".")).toLowerCase();
      const ct = IMG_CT[ext];
      if (ct) {
        const img = await env.NOTE_KV.get(repo, "arrayBuffer");
        if (img && img.byteLength) {
          return new Response(img, {
            headers: {
              "content-type": ct,
              // 新图片文件名唯一（时间戳+随机），短缓存安全
              "cache-control": "public, max-age=300",
            },
          });
        }
      }
    }
  } catch (e) {
    // KV 异常时回退静态资源，不阻塞访问
  }

  return next();
}
