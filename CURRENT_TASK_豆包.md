# 当前任务交接说明（给豆包）— 2026-08-24

> 适用项目：A股每日复盘页面（https://liaohao.cc/stock-a/ 收盘版 / https://liaohao.cc/stock-a/午盘/ 午间版）
> 项目路径：`/Users/sugieliao/WorkBuddy/A股每日复盘/`
> 维护分工：**巴蒂** = 数据管线 + 浏览器复现验证 + 部署；**豆包** = 页面前端（render.py 的图表/交互）
> 配套文档：`PROJECT_SPEC.md`（整体架构，豆包若不熟悉本项目先读那个）

---

## 一、当前线上状态（截至 2026-08-24）

- 收盘版与午间版均已更新：hover 的**竖线 + tooltip 精确跟随鼠标 X**，已部署上线。
- 你（豆包）早前的 TR 情绪模块提交（约 `7cd3338`）引入了 `* dpr` 乘子，导致 Retina 屏（dpr=2）上竖线/tooltip 错位、tooltip 丢失。该问题已修复，**请勿再引入同类写法**。

---

## 二、本次完成的核心修复：hover 竖线/tooltip 对齐

**根因（两层）：**

1. 旧版在 `attachHover` 里把鼠标坐标乘了 `dpr`（`* dpr`）。但 Chart.js 4.4.4 的 scale 接口（`chartArea.left/right`、`getValueForPixel`、`getPixelForValue`）内部已是 **CSS 像素**，**不该再乘 dpr**；乘了会在 Retina 上溢出/错位。
2. 后续改版用 `getElementsAtEventForMode(e,'index',{intersect:false},true)[0].element.x` 取 `_hx`，那取的是**最近数据点的 x**，竖线会吸附到离散点而非光标——光标落在两点之间时偏离半个点距（离线实测 **+8.55px**）。

**正确行为（已实现）：** 纵向图竖线 = `e.clientX - rect.left`（精确跟随鼠标 CSS 像素）；超出绘图区则隐藏；tooltip 文字内容仍按最近点取索引。

代码位置：`render.py` → `attachHover`（约 1246 行）、`verticalLinePlugin`（约 1179 行）。

---

## 三、豆包必须遵守的硬性规矩（防止回归）

1. **绝不乘 dpr。** 所有 `chartArea.left/right`、`getBoundingClientRect()`、鼠标 `clientX/clientY` 都是 CSS 像素，直接相减即可。**不要写 `* dpr` / `* devicePixelRatio`**（本项目没用 canvas 底层 `getContext().scale` 绘制，不需要）。
2. **纵向图竖线跟随鼠标精确 X：** `_hx = e.clientX - rect.left`，不要取 `element.x` / 最近点像素。
3. **移出绘图区要隐藏：** `mx < left || mx > right` 时 `_hx = null`（见 1272 行 `if(mx >= left && mx <= right)`）。
4. **横向图（RPS 模块）保持吸附不动：** `isH` 分支仍用 `getElementsAtEventForMode` 对齐最近点，不要改（不影响其原生 tooltip）。
5. 改完任何 hover/tooltip 交互后，**自己对照下方"验证方法"在浏览器里过一遍**，别只靠代码推断（之前两次"以为修好了"都是只改代码、没真机验证）。

---

## 四、部署纪律（豆包最容易踩的坑）

`deploy_light_pos.py` 只是把**已存在**的 HTML 文件 copy 出去，**不会**替你重渲染。改了 `render.py` 后，**收盘 + 午间两个 HTML 都要 render 一遍**，再 deploy：

```bash
PY=/Users/sugieliao/.workbuddy/binaries/python/versions/3.13.12/bin/python3
$PY render.py 2026-08-24            # 收盘版 → A股复盘_2026-08-24.html
$PY render.py 2026-08-24 --midday   # 午间版 → A股午盘_2026-08-24.html
$PY deploy_light_pos.py 2026-08-24  # 部署两端
```

（把日期换成你要发布的交易日。只 render 一端就 deploy，另一端会是旧代码——这是上一轮"午间版仍有问题"的直接原因。）

---

## 五、验证方法（离线浏览器复现）

本机 agent-browser 访问外网被代理拦截，但能直接 `file://` 打开本地生成的 HTML 离线复现 Chart.js 交互：

```bash
agent-browser open "file:///Users/sugieliao/WorkBuddy/A股每日复盘/A股复盘_2026-08-24.html"
```

- 肉眼法：把鼠标移到两个数据点正中间，竖线/tooltip 应精确落在光标处（无可见偏离）。
- 严格法：用合成 `MouseEvent` `dispatchEvent` 后读 `ch._hx` 与光标 X 差值，应 **< 1px**（亚像素取整属正常）。

---

## 六、参考：当前正确的 `attachHover` 纵向分支（勿回退）

```js
} else {
  // 纵向图：竖线精确跟随鼠标 X（CSS 像素，与 Chart.js 内部一致，不受 dpr 影响）；移出绘图区则隐藏
  const xs = ch.scales.x; if(!xs) return;
  const left = ch.chartArea.left, right = ch.chartArea.right;
  let x = null, idx = null;
  if(mx >= left && mx <= right){
    x = mx;
    const points = ch.getElementsAtEventForMode(e, 'index', {intersect:false}, true);
    if(points && points.length){ idx = points[0].index; }
  }
  if(x !== ch._hx){
    ch._hx = x;
    if(rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(()=>{ ch.update('none'); rafId=null; });
  }
  if(onMove) onMove((idx!=null && idx>=0 && idx<labels.length)?idx:null, e);
}
```

## 七、反面教材（不要再写）

- ❌ 错误 A（乘 dpr）：`const x = (e.clientX - rect.left) * dpr;` —— 导致 Retina 错位、tooltip 丢失。
- ❌ 错误 B（吸附到点）：`x = points[0].element.x;` —— 导致"竖线/tooltip 和鼠标位置有出入"。

---

## 八、若豆包要接新前端任务

1. 先读 `PROJECT_SPEC.md` 确认模块结构与数据源口径（尤其板块三/四走 THS、RPS 走 TDX，代码体系不同，别混用）。
2. 改动后按第四节 render 两端 + 按第五节自测，再通知巴蒂 deploy（或自行 deploy 均可，但务必两端都 render）。
3. 任何涉及数据字段增删的改动，先与巴蒂确认采集层（collect_*.py）是否同步，避免页面读空。
