/*!
 * shared/nav.js — liaohao.cc 投资类应用统一顶部菜单栏
 * 结构：盘面全景 | A股复盘(收盘版/午间版) | 宏观看板
 *
 * 用法（每个页面 <head> 或 </body> 前加一行即可）：
 *   <script src="/shared/nav.js" defer></script>
 *
 * 深浅色：自动取样页面背景色亮度决定；可用以下方式强制覆盖
 *   1) <script>window.NAV_THEME="dark"|"light"</script>
 *   2) <html data-nav-theme="dark"> 或 <body data-nav-theme="light">
 *
 * 会自动移除页面里原有的旧导航（.topnav / nav:not(.invest-nav) 及含 .topnav 规则的 <style>）。
 */
(function () {
  "use strict";

  var LINKS = [
    { label: "盘面全景", href: "/a-overview/", match: ["/a-overview"] },
    {
      label: "A股复盘",
      href: "/stock-a/",
      match: ["/stock-a"],
      children: [
        { label: "收盘版", href: "/stock-a/", match: ["/stock-a"], exclude: ["/stock-a/noon"] },
        { label: "午间版", href: "/stock-a/noon/", match: ["/stock-a/noon"] }
      ]
    },
    { label: "宏观看板", href: "/macro-cn/", match: ["/macro-cn"] },
    { label: "势宫行研", href: "/industry/", match: ["/industry"] },
    {
      label: "投资学习",
      href: "/learn/",
      match: ["/learn"],
      children: [
        { label: "小爆姐宏观框架课", href: "/learn/xiaobaojie/", match: ["/learn/xiaobaojie"] },
        {
          label: "宏观",
          href: "/learn/macro/",
          match: ["/learn/macro"],
          children: [
            { label: "小邓老师", href: "/learn/macro/xiaodeng/", match: ["/learn/macro/xiaodeng"] },
            { label: "陈鹏老师", href: "/learn/macro/chenpeng/", match: ["/learn/macro/chenpeng"] },
            { label: "陈晓丹", href: "/learn/macro/chenxiaodan/", match: ["/learn/macro/chenxiaodan"] }
          ]
        },
        {
          label: "行业课",
          href: "/learn/industry/",
          match: ["/learn/industry"],
          children: [
            { label: "半导体", href: "/learn/industry/semiconductor/", match: ["/learn/industry/semiconductor"] },
            { label: "医药", href: "/learn/industry/pharma/", match: ["/learn/industry/pharma"] },
            { label: "电新", href: "/learn/industry/electric-new/", match: ["/learn/industry/electric-new"] },
            { label: "消费", href: "/learn/industry/consumer/", match: ["/learn/industry/consumer"] }
          ]
        },
        { label: "地金刚体系", href: "https://dijingang.liaohao.cc", match: [] },
        { label: "猛兽体系", href: "https://beast.liaohao.cc", match: [] },
        { label: "舍一体系", href: "https://sheyi.liaohao.cc", match: [] }
      ]
    }
  ];

  /* ---------- 主题判定 ---------- */
  function parseColor(str) {
    var m = /rgba?\(([^)]+)\)/.exec(str || "");
    if (!m) return null;
    var p = m[1].split(",").map(function (s) { return parseFloat(s); });
    return { r: p[0] || 0, g: p[1] || 0, b: p[2] || 0, a: p.length > 3 ? p[3] : 1 };
  }
  function relLum(c) {
    function ch(v) {
      v = v / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    }
    return 0.2126 * ch(c.r) + 0.7152 * ch(c.g) + 0.0722 * ch(c.b);
  }
  function bgOf(el) {
    while (el && el.parentNode) {
      var s = window.getComputedStyle(el);
      var c = parseColor(s.backgroundColor);
      if (c && c.a > 0.15) {
        // 背景图中若含明显的深色渐变/图层，按深色处理
        var bi = s.backgroundImage || "none";
        if (bi && bi !== "none" && /gradient/.test(bi)) {
          var gm = /rgba?\(([^)]+)\)/.exec(bi);
          var g1 = gm ? parseColor("rgb(" + gm[1].split(",").slice(0, 3).join(",") + ")") : null;
          if (g1 && relLum(g1) < 0.2) return g1;
        }
        return c;
      }
      // 无实色背景但有图片/渐变：取其中第一个可识别颜色判定
      if (s.backgroundImage && s.backgroundImage !== "none") {
        var m = /rgba?\(([^)]+)\)/.exec(s.backgroundImage);
        if (m) {
          var ic = parseColor("rgb(" + m[1].split(",").slice(0, 3).join(",") + ")");
          if (ic) return ic;
        }
      }
      el = el.parentElement;
    }
    return null;
  }
  function detectTheme() {
    var forced = window.NAV_THEME ||
      document.documentElement.getAttribute("data-nav-theme") ||
      (document.body && document.body.getAttribute("data-nav-theme"));
    if (forced === "dark" || forced === "light") return forced;
    var c = bgOf(document.body) || bgOf(document.documentElement);
    if (c) return relLum(c) > 0.45 ? "light" : "dark";
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  /* ---------- 清理旧导航 ---------- */
  function removeLegacy() {
    var killed = 0;
    // 旧导航元素
    var nodes = document.querySelectorAll(".topnav, nav:not(.invest-nav), .nav-bar, .site-nav, .global-nav");
    Array.prototype.forEach.call(nodes, function (n) {
      if (n.classList && n.classList.contains("invest-nav")) return;
      // 只清理页面顶部的导航条：位于 .wrap / 容器内的第一个元素或 body 直属
      if (n.tagName === "NAV" && n.querySelector("a")) { n.remove(); killed++; }
      else if (n.classList && (n.classList.contains("topnav") || n.classList.contains("nav-bar"))) { n.remove(); killed++; }
    });
    // 旧导航的样式：只剥离 .topnav 相关的单条规则，绝不整块删除 <style>
    // （很多页面的 .topnav 规则与页面主体样式写在同一个 <style> 里，整块删除会让页面失样式）
    Array.prototype.forEach.call(document.querySelectorAll("style"), function (s) {
      var txt = s.textContent || "";
      if (/\.topnav\b/.test(txt)) {
        s.textContent = txt.replace(/\.topnav[^{}]*\{[^{}]*\}/gi, "");
      }
    });
    return killed;
  }

  /* ---------- 高亮判定 ---------- */
  var PATH = location.pathname.replace(/index\.html?$/i, "");
  if (!/\/$/.test(PATH)) PATH = PATH + "/";
  function hit(item) {
    var ms = item.match || [];
    for (var i = 0; i < ms.length; i++) if (PATH.indexOf(ms[i]) === 0) return true;
    return false;
  }
  function excluded(item) {
    var ex = item.exclude || [];
    for (var i = 0; i < ex.length; i++) if (PATH.indexOf(ex[i]) === 0) return true;
    return false;
  }
  function isActive(item) { return hit(item) && !excluded(item); }

  /* ---------- 渲染 ---------- */
  function build() {
    var theme = detectTheme();
    var dark = theme === "dark";
    var P = {
      bg: dark ? "rgba(13,17,23,.88)" : "rgba(255,255,255,.9)",
      bd: dark ? "rgba(255,255,255,.10)" : "rgba(0,0,0,.08)",
      fg: dark ? "#e6edf3" : "#1f2329",
      dim: dark ? "#8b949e" : "#6b7280",
      hover: dark ? "rgba(255,255,255,.08)" : "rgba(0,0,0,.05)",
      accent: dark ? "#58a6ff" : "#1366d6",
      panel: dark ? "rgba(22,27,34,.97)" : "rgba(255,255,255,.98)",
      shadow: dark ? "0 4px 16px rgba(0,0,0,.45)" : "0 4px 16px rgba(15,23,42,.08)"
    };

    var st = document.createElement("style");
    st.textContent = [
      ".invest-nav{position:sticky;top:0;z-index:2147483000;width:100%;background:" + P.bg + ";",
      "border-bottom:1px solid " + P.bd + ";backdrop-filter:saturate(180%) blur(12px);",
      "-webkit-backdrop-filter:saturate(180%) blur(12px);font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;}",
      ".invest-nav .nav-inner{max-width:1140px;margin:0 auto;padding:0 18px;height:48px;display:flex;align-items:center;gap:2px}",
      ".invest-nav .nav-brand{font-size:18px;font-weight:700;color:" + P.fg + ";margin-right:18px;letter-spacing:.5px;white-space:nowrap}",
      ".invest-nav a{color:" + P.fg + ";text-decoration:none;font-size:14.5px;font-weight:500;",
      "padding:7px 13px;border-radius:8px;line-height:1;transition:background .15s,color .15s;white-space:nowrap;display:inline-flex;align-items:center;gap:5px}",
      ".invest-nav a:hover{background:" + P.hover + ";text-decoration:none}",
      ".invest-nav a.cur{color:" + P.accent + ";font-weight:600}",
      ".invest-nav .nav-item{position:relative}",
      ".invest-nav .caret{width:0;height:0;border-left:4px solid transparent;border-right:4px solid transparent;",
      "border-top:4px solid currentColor;opacity:.55;margin-left:2px}",
      ".invest-nav .drop{position:absolute;left:0;top:calc(100% + 6px);min-width:132px;background:" + P.panel + ";",
      "border:1px solid " + P.bd + ";border-radius:10px;box-shadow:" + P.shadow + ";padding:6px;display:none;flex-direction:column;gap:2px}",
      ".invest-nav .drop::before{content:'';position:absolute;top:-10px;left:0;right:0;height:10px;background:transparent}",
      ".invest-nav .nav-item.open .drop,.invest-nav .nav-item:hover .drop{display:flex}",
      ".invest-nav .drop a{font-size:14px;padding:8px 12px;border-radius:7px}",
      ".invest-nav .drop .has-sub{position:relative;display:flex;align-items:center;justify-content:space-between;width:100%}",
      ".invest-nav .drop .has-sub .sub-caret{width:0;height:0;border-top:4px solid transparent;border-bottom:4px solid transparent;border-left:4px solid currentColor;opacity:.55;margin-left:8px}",
      ".invest-nav .drop .sub-drop{position:absolute;left:calc(100% + 4px);top:-6px;min-width:120px;background:" + P.panel + ";",
      "border:1px solid " + P.bd + ";border-radius:10px;box-shadow:" + P.shadow + ";padding:6px;display:none;flex-direction:column;gap:2px}",
      ".invest-nav .drop .has-sub:hover .sub-drop{display:flex}",
      "@media(max-width:560px){.invest-nav .nav-inner{height:44px;padding:0 10px;gap:0}",
      ".invest-nav .nav-brand{display:none}.invest-nav a{padding:6px 9px;font-size:13.5px}}"
    ].join("");
    document.head.appendChild(st);

    var nav = document.createElement("nav");
    nav.className = "invest-nav";
    nav.setAttribute("data-nav-theme", theme);
    var inner = document.createElement("div");
    inner.className = "nav-inner";

    var brand = document.createElement("span");
    brand.className = "nav-brand";
    brand.textContent = "苏奇投研平台";
    inner.appendChild(brand);

    LINKS.forEach(function (item) {
      var wrap = document.createElement("div");
      wrap.className = "nav-item";
      var active = isActive(item);
      if (item.children) {
        var childActive = item.children.some(isActive);
        var a = document.createElement("a");
        a.href = item.href;
        a.innerHTML = item.label + '<span class="caret"></span>';
        if (childActive) a.className = "cur";
        wrap.appendChild(a);
        var drop = document.createElement("div");
        drop.className = "drop";
        item.children.forEach(function (c) {
          if (c.children) {
            // 有二级菜单的子项
            var subWrap = document.createElement("div");
            subWrap.className = "has-sub";
            var ca = document.createElement("a");
            ca.href = c.href;
            if (/^https?:\/\//.test(c.href)) { ca.target = "_blank"; ca.rel = "noopener noreferrer"; }
            ca.textContent = c.label;
            if (isActive(c)) ca.className = "cur";
            subWrap.appendChild(ca);
            var caret = document.createElement("span");
            caret.className = "sub-caret";
            subWrap.appendChild(caret);
            var subDrop = document.createElement("div");
            subDrop.className = "sub-drop";
            c.children.forEach(function (sc) {
              var sca = document.createElement("a");
              sca.href = sc.href;
              if (/^https?:\/\//.test(sc.href)) { sca.target = "_blank"; sca.rel = "noopener noreferrer"; }
              sca.textContent = sc.label;
              if (isActive(sc)) sca.className = "cur";
              subDrop.appendChild(sca);
            });
            subWrap.appendChild(subDrop);
            drop.appendChild(subWrap);
          } else {
            var ca2 = document.createElement("a");
            ca2.href = c.href;
            if (/^https?:\/\//.test(c.href)) { ca2.target = "_blank"; ca2.rel = "noopener noreferrer"; }
            ca2.textContent = c.label;
            if (isActive(c)) ca2.className = "cur";
            drop.appendChild(ca2);
          }
        });
        wrap.appendChild(drop);
        // 移动端点击展开
        wrap.addEventListener("click", function (e) {
          if (e.target === a || wrap.contains(e.target)) {
            if (window.matchMedia && window.matchMedia("(hover: none)").matches) {
              wrap.classList.toggle("open");
            }
          }
        });
        void active;
      } else {
        var a2 = document.createElement("a");
        a2.href = item.href;
        a2.textContent = item.label;
        if (active) a2.className = "cur";
        wrap.appendChild(a2);
      }
      inner.appendChild(wrap);
    });

    nav.appendChild(inner);
    return nav;
  }

  function mount() {
    removeLegacy();
    if (document.querySelector(".invest-nav")) return;
    var nav = build();
    if (document.body) document.body.insertBefore(nav, document.body.firstChild);
    else document.documentElement.appendChild(nav);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
