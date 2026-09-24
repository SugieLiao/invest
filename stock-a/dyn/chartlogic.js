const RED='#d8392b', GREEN='#16a34a', GREY='#888';
/* ===== 折线末端最新值标注（全局注册，所有 Chart 生效；纯柱图不标，混合图只标折线）===== */
function __endFmt(n,d){
  if(d&&typeof d.endFmt==='function'){try{var t=d.endFmt(n);if(t!=null)return t;}catch(e){}}
  // 整数（涨跌停/新高新低/家数等）直接显示整数，避免 65.00
  if(Math.abs(n-Math.round(n))<0.005) return Math.round(n).toLocaleString();
  var a=Math.abs(n);
  if(a>=1000) return Math.round(n).toLocaleString();
  if(a>=100) return n.toFixed(1);
  return n.toFixed(2);
}
const endValuePlugin={
  id:'endValue',
  _lineDs(chart){
    const ct=chart.config.type||'line', out=[];
    (chart.data.datasets||[]).forEach((d,di)=>{ const dt=d.type||ct; if(dt!=='bar'&&d.hidden!==true) out.push([d,di]); });
    return out;
  },
  _lastValid(d){
    const a=d.data||[];
    for(let k=a.length-1;k>=0;k--){const x=a[k]; if(x!=null && !(typeof x==='number'&&isNaN(x))) return [k,x];}
    return null;
  },
  afterDatasetsDraw(chart){
    try{
      const ctx=chart.ctx, lds=this._lineDs(chart);
      if(!lds.length)return;
      ctx.save();ctx.font='bold 10px -apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif';
      ctx.textAlign='right';ctx.textBaseline='middle';
      const ca=chart.chartArea||{};
      const topLimit=(ca.top!=null?ca.top:0)+2;
      const bottomLimit=(ca.bottom!=null?ca.bottom:chart.height)-2;
      const leftEdge=(ca.right!=null?ca.right:chart.width-60)+6;
      const maxRight=(chart.width||ca.right+80)-4;
      // 第一遍：收集所有末端标签位置
      const labels=[];
      lds.forEach(([d,di])=>{
        const lv=this._lastValid(d); if(!lv)return;
        const i=lv[0],raw=lv[1];
        const meta=chart.getDatasetMeta(di); if(!meta||meta.hidden||!meta.data[i])return;
        let val=(raw&&typeof raw==='object')?(raw.y!=null?raw.y:(raw.close!=null?raw.close:null)):raw;
        val=Number(val); if(isNaN(val))return;
        const txt=__endFmt(val,d);
        let col=d.endColor||d.borderColor;
        if(!col||col==='transparent'||/0,\s*0,\s*0,\s*0/.test(String(col)))col='#e6edf7';
        const px=meta.data[i].x, py=meta.data[i].y, w=ctx.measureText(txt).width;
        let tx=leftEdge+w;
        if(tx>maxRight) tx=maxRight;
        // 垂直：优先点上方，超上边界则放下方
        let labelY=py-0.5;
        if(py-7<topLimit){ labelY=py+10; }
        labels.push({tx,labelY,txt,col,w,val});
      });
      // 边界clamp
      labels.forEach(l=>{
        if(l.labelY<topLimit+7) l.labelY=topLimit+7;
        if(l.labelY>bottomLimit-7) l.labelY=bottomLimit-7;
      });
      // 防重叠：按数值降序（数值大的标签在上），从下往上推，重叠时上方标签上移14px
      // （从上往下推会在底部边界clamp时失效：下方标签下移后又被clamp回原位，导致完全重叠）
      labels.sort((a,b)=>b.val-a.val);
      for(let k=labels.length-2;k>=0;k--){
        if(labels[k].labelY+14 > labels[k+1].labelY){
          labels[k].labelY=labels[k+1].labelY-14;
          if(labels[k].labelY<topLimit+7) labels[k].labelY=topLimit+7;
        }
      }
      // 第二遍：绘制
      labels.forEach(l=>{
        const bx=l.tx-l.w-3, bw=l.w+6, bh=14, rr=3, by=l.labelY-7;
        ctx.beginPath();
        ctx.moveTo(bx+rr,by);ctx.arcTo(bx+bw,by,bx+bw,by+bh,rr);ctx.arcTo(bx+bw,by+bh,bx,by+bh,rr);
        ctx.arcTo(bx,by+bh,bx,by,rr);ctx.arcTo(bx,by,bx+bw,by,rr);ctx.closePath();
        ctx.fillStyle='rgba(12,17,30,.82)';ctx.fill();
        ctx.fillStyle=l.col;ctx.fillText(l.txt,l.tx,l.labelY);
      });
      ctx.restore();
    }catch(e){}
  }
};
if(typeof Chart!=='undefined')Chart.register(endValuePlugin);
/* RPS横向条形图：每根柱子右端标数值 */
const rpsBarLabelPlugin={
  id:'rpsBarLabel',
  afterDatasetsDraw(chart){
    try{
      if(chart.config.type!=='bar')return;
      const ctx=chart.ctx;
      ctx.save();
      ctx.font='bold 10px -apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif';
      ctx.textAlign='left';ctx.textBaseline='middle';
      chart.data.datasets.forEach((ds,di)=>{
        const meta=chart.getDatasetMeta(di);
        if(!meta||meta.hidden)return;
        const col=ds.backgroundColor||'#e6edf7';
        meta.data.forEach((el,i)=>{
          const v=ds.data[i];
          if(v==null||isNaN(Number(v)))return;
          ctx.fillStyle=col;
          ctx.fillText(Number(v).toFixed(1), el.x+4, el.y);
        });
      });
      ctx.restore();
    }catch(e){}
  }
};
const verticalLinePlugin = {
  id:'verticalLine',
  afterDraw(chart){
    const isH = chart.options && chart.options.indexAxis === 'y';
    const ctx = chart.ctx;
    ctx.save();
    ctx.lineWidth = 1.5; ctx.strokeStyle = 'rgba(0,0,0,.4)';
    ctx.setLineDash([4,3]);
    if(isH){
      let y = null;
      const tt = chart.tooltip;
      if(tt && tt.getActiveElements && tt.getActiveElements().length) y = tt.getActiveElements()[0].element.y;
      else if(chart._hy != null) y = chart._hy;
      if(y == null){ ctx.restore(); return; }
      ctx.beginPath();
      ctx.moveTo(chart.chartArea.left, y); ctx.lineTo(chart.chartArea.right, y);
      ctx.stroke();
    } else {
      let x = null;
      if(chart._hx != null) x = chart._hx;
      else { const tt = chart.tooltip; if(tt && tt.getActiveElements && tt.getActiveElements().length) x = tt.getActiveElements()[0].element.x; }
      if(x == null){ ctx.restore(); return; }
      ctx.beginPath();
      ctx.moveTo(x, chart.chartArea.top); ctx.lineTo(x, chart.chartArea.bottom);
      ctx.stroke();
    }
    ctx.restore();
  }
};
const ZONES=[{name:'极冰',value:10,color:'#00BFFF'},{name:'冰点',value:25,color:'#4169E1'},{name:'中枢',value:50,color:'#FFB7C5'},{name:'过热',value:75,color:'#FFD700'},{name:'高潮',value:90,color:'#ff0000'}];
const zonePlugin={id:'zones',afterDraw(chart){const ys=chart.scales.y;if(!ys)return;const ctx=chart.ctx;ctx.save();ctx.font='11px sans-serif';ZONES.forEach(z=>{const y=ys.getPixelForValue(z.value);ctx.beginPath();ctx.moveTo(chart.chartArea.left,y);ctx.lineTo(chart.chartArea.right,y);ctx.lineWidth=1;ctx.setLineDash([5,4]);ctx.strokeStyle=z.color;ctx.stroke();ctx.setLineDash([]);ctx.fillStyle=z.color;ctx.fillText(z.name,chart.chartArea.left+4,y-3);});ctx.restore();}};
const TR_ZONES=[{name:'沸点87',value:87,color:'#d8392b'},{name:'相变50',value:50,color:'#ca8a04'},{name:'冰点13',value:13,color:'#4169E1'}];
const trZonePlugin={id:'trZones',afterDraw(chart){const ys=chart.scales.y;if(!ys)return;const ctx=chart.ctx;ctx.save();ctx.font='11px sans-serif';TR_ZONES.forEach(z=>{const y=ys.getPixelForValue(z.value);ctx.beginPath();ctx.moveTo(chart.chartArea.left,y);ctx.lineTo(chart.chartArea.right,y);ctx.lineWidth=1;ctx.setLineDash([5,4]);ctx.strokeStyle=z.color;ctx.stroke();ctx.setLineDash([]);ctx.fillStyle=z.color;ctx.fillText(z.name,chart.chartArea.left+4,y-3);});ctx.restore();}};
const WANDE = (D.wande && D.wande.ok) ? D.wande : null;
let wandeCurData = WANDE; // 当前显示的K线数据（可被切换范围更新）
const candlePlugin = {
  id:'candle',
  afterDraw(chart){
    if(!wandeCurData) return;
    const xs=chart.scales.x, ys=chart.scales.y;
    const n=wandeCurData.close.length;
    if(!n) return;
    const step = n>1 ? Math.abs(xs.getPixelForValue(1)-xs.getPixelForValue(0)) : 10;
    const w = Math.max(1.5, step*0.6);
    const ctx=chart.ctx;
    for(let i=0;i<n;i++){
      const x=xs.getPixelForValue(i);
      const yO=ys.getPixelForValue(wandeCurData.open[i]);
      const yC=ys.getPixelForValue(wandeCurData.close[i]);
      const yH=ys.getPixelForValue(wandeCurData.high[i]);
      const yL=ys.getPixelForValue(wandeCurData.low[i]);
      const up = wandeCurData.close[i] >= wandeCurData.open[i];
      ctx.strokeStyle = up ? RED : GREEN;
      ctx.fillStyle = up ? RED : GREEN;
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x,yH); ctx.lineTo(x,yL); ctx.stroke();
      const top=Math.min(yO,yC), hgt=Math.max(1,Math.abs(yC-yO));
      ctx.fillRect(x-w/2, top, w, hgt);
    }
  }
};
const INSTANCES = {};
function cloneCfg(config){
  // 克隆「干净、可序列化」的配置，专供大图放大使用。
  // chart.config 是 Chart.js 的 Config 包装对象（内含 chart 自引用），JSON 序列化会抛循环引用错误，
  // 因此必须在创建图表时单独存一份纯数据副本。
  try { return {type:config.type, data:JSON.parse(JSON.stringify(config.data)), options:JSON.parse(JSON.stringify(config.options||{}))}; } catch(e){ return null; }
}
function attachHover(ch, cv, onMove){
  let rafId = null;
  const isH = ch.options && ch.options.indexAxis === 'y';
  cv.addEventListener('mousemove', (e)=>{
    ch._mouseX = e.clientX;
    ch._mouseY = e.clientY;
    const rect = cv.getBoundingClientRect();
    const labels = (ch.data && ch.data.labels) || [];
    const mx = e.clientX - rect.left;
    if(isH){
      // 横向图：横线对齐到最近 data point（保持原行为，不影响 RPS 原生 tooltip 对齐）
      const ys = ch.scales.y; if(!ys) return;
      let v = null, idx = null;
      const points = ch.getElementsAtEventForMode(e, 'index', {intersect:false}, true);
      if(points && points.length){ idx = points[0].index; v = points[0].element.y; }
      if(v !== ch._hy){
        ch._hy = v;
        if(rafId) cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(()=>{ ch.update('none'); rafId=null; });
      }
      if(onMove) onMove((idx!=null && idx>=0 && idx<labels.length)?idx:null, e);
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
  });
  cv.addEventListener('mouseleave', ()=>{
    if(isH){
      if(ch._hy!==null){ ch._hy=null; if(rafId) cancelAnimationFrame(rafId);
        const _te = ch.options.plugins.tooltip.enabled; ch.update('none'); ch.options.plugins.tooltip.enabled=_te; }
    } else {
      if(ch._hx!==null){ ch._hx=null; if(rafId) cancelAnimationFrame(rafId);
        const _te = ch.options.plugins.tooltip.enabled; ch.update('none'); ch.options.plugins.tooltip.enabled=_te; }
    }
    if(onMove) onMove(null, null);
  });
}
function makeChart(id, config, onMove){
  config.options = config.options || {};
  config.options.interaction = {mode:'index', intersect:false};
  config.options.plugins = config.options.plugins || {};
  config.options.plugins.verticalLine = true;
  // 关闭原生图例（改用上方可点击高亮的自定义图例 chip）
  config.options.plugins.legend = Object.assign({}, config.options.plugins.legend||{}, {display:false});
  config.options.plugins.tooltip = Object.assign({
    enabled:true, titleFont:{size:13,weight:'bold'}, bodyFont:{size:12},
    padding:10, filter:(item)=> item.parsed !== null && item.parsed !== undefined
  }, config.options.plugins.tooltip||{});
  config.plugins = (config.plugins||[]).concat([verticalLinePlugin]);
  // 折线/含折线的混合图：右侧预留空白，让末端数值标签落在曲线之外、不遮挡曲线
  const _eds=(config.data&&config.data.datasets)||[];
  const _hasLine = config.type==='line' || _eds.some(d=>d&&d.type==='line');
  if(_hasLine){
    config.options.layout=config.options.layout||{};
    config.options.layout.padding=Object.assign({right:64,top:18}, config.options.layout.padding||{});
  }
  const ch = new Chart(document.getElementById(id), config);
  INSTANCES[id] = ch;
  // 保存干净可序列化配置用于大图放大（见 cloneCfg 说明）
  ch.__zoomCfg = cloneCfg(config);
  ch.__needsCandle = (id==='cWande');
  ch.__needsZone = (id==='cJzxt');
  ch.__needsTrZone = (id==='cTr');
  const cv = document.getElementById(id);
  cv.style.cursor='zoom-in';
  cv.addEventListener('dblclick', ()=>openZoom(id));
  attachHover(ch, cv, onMove);
  return ch;
}
function lineCfg(labels, datasets, opts){ return {type:'line', data:{labels,datasets}, options:Object.assign({responsive:true,elements:{point:{hitRadius:8}},plugins:{legend:{labels:{font:{size:11},color:'#a0aec0'}}},scales:{x:{ticks:{maxTicksLimit:12,font:{size:10},color:'#718096'},grid:{display:false}},y:{ticks:{font:{size:10},color:'#718096'},grid:{color:'#252d40'}}}}, opts||{})}; }
function barCfg(labels, label, data, color, rot){ return {type:'bar', data:{labels,datasets:[{label,data,backgroundColor:color, barPercentage:0.2, categoryPercentage:0.5}]}, options:{responsive:true,plugins:{legend:{display:false}},scales:{x:{ticks:{font:{size:10},maxRotation:rot||0,color:'#718096'}},y:{ticks:{font:{size:10},color:'#718096'},grid:{color:'#252d40'}}}}}; }
/* 时间范围拖动条 */
function attachRangeSlider(chartId, origLabels, origDataArrays, onUpdate, defaultDays, maxDays, showQuickBtns, miniColor){
  miniColor = miniColor || '#60a5fa';
  try {
    const canvas = document.getElementById(chartId);
    if(!canvas || !canvas.parentNode) { console.log('attachRangeSlider: canvas not found for', chartId); return; }
    // 限制最大显示范围
    let labels = origLabels;
    let dataArrays = origDataArrays;
    if(maxDays && origLabels.length > maxDays){
      const startIdx = origLabels.length - maxDays;
      labels = origLabels.slice(startIdx);
      dataArrays = origDataArrays.map(arr => arr.slice(startIdx));
    }
    const wrap = document.createElement('div');
    wrap.className = 'range-slider-wrap';
    const quickBtnsHtml = showQuickBtns === false ? '' : '<div class="range-slider-quick"><button data-days="60">60天</button><button data-days="120">近半年</button><button data-days="250">近一年</button><button data-days="500">近两年</button></div>';
    wrap.innerHTML = '<div class="range-slider-labels"><span class="rs-start"></span><span class="rs-end"></span></div>' + quickBtnsHtml + '<div class="range-slider"><div class="mini-chart"></div><div class="mask-left"></div><div class="sel-box"></div><div class="mask-right"></div><input type="range" class="rs-min" min="0" max="100" value="0"><input type="range" class="rs-max" min="0" max="100" value="100"></div>';
    if(canvas.nextSibling) {
      canvas.parentNode.insertBefore(wrap, canvas.nextSibling);
    } else {
      canvas.parentNode.appendChild(wrap);
    }
    const minInput = wrap.querySelector('.rs-min');
    const maxInput = wrap.querySelector('.rs-max');
    const sliderEl = wrap.querySelector('.range-slider');
    const miniChart = wrap.querySelector('.mini-chart');
    const maskLeft = wrap.querySelector('.mask-left');
    const maskRight = wrap.querySelector('.mask-right');
    const selBox = wrap.querySelector('.sel-box');
    const startLabel = wrap.querySelector('.rs-start');
    const endLabel = wrap.querySelector('.rs-end');
    
    // 绘制曲线缩影（用第一条数据）
    const miniData = dataArrays[0] || [];
    if(miniData.length > 1){
      const validVals = miniData.filter(v => v !== null && v !== undefined && !isNaN(v));
      if(validVals.length > 0){
        const minVal = Math.min(...validVals);
        const maxVal = Math.max(...validVals);
        const range = maxVal - minVal || 1;
        const w = 1000, h = 100;
        const pointArr = miniData.map((v, i) => {
          if(v === null || v === undefined || isNaN(v)) return null;
          const x = (i / (miniData.length - 1)) * w;
          const y = h - ((v - minVal) / range) * (h - 10) - 5;
          return {x, y};
        }).filter(p => p !== null);
        const points = pointArr.map(p => p.x + ',' + p.y).join(' ');
        // 填充路径：曲线 + 底部闭合
        const firstP = pointArr[0], lastP = pointArr[pointArr.length - 1];
        const fillPath = 'M' + firstP.x + ',' + firstP.y + ' L' + pointArr.map(p => p.x + ',' + p.y).join(' L') + ' L' + lastP.x + ',' + h + ' L' + firstP.x + ',' + h + ' Z';
        const gradId = 'miniGrad_' + chartId;
        miniChart.innerHTML = '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none">' +
          '<defs><linearGradient id="' + gradId + '" x1="0" y1="0" x2="0" y2="1">' +
          '<stop offset="0%" stop-color="' + miniColor + '" stop-opacity="0.4"/>' +
          '<stop offset="100%" stop-color="' + miniColor + '" stop-opacity="0.05"/>' +
          '</linearGradient></defs>' +
          '<path d="' + fillPath + '" fill="url(#' + gradId + ')"/>' +
          '<polyline points="' + points + '" fill="none" stroke="' + miniColor + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>' +
          '</svg>';
      }
    }
    // 设置默认显示范围
    if(defaultDays && labels.length > defaultDays){
      const defaultStart = Math.round((1 - defaultDays / labels.length) * 100);
      minInput.value = defaultStart;
    }
    function update(){
      let minVal = parseInt(minInput.value);
      let maxVal = parseInt(maxInput.value);
      if(minVal > maxVal - 2){ minVal = maxVal - 2; maxVal = minVal + 2; }
      // 用像素精确定位，使取值线与滑动按钮中心竖线对齐
      const W = sliderEl.clientWidth;
      const tw = 7; // thumb宽度（box-sizing:border-box，含border）
      // webkit中thumb原生左边缘=p/100*(W-tw)；min用translateX(-50%)、max用translateX(+50%)
      const minX = (minVal / 100) * (W - tw);              // min thumb中心
      const maxX = (maxVal / 100) * (W - tw) + tw;         // max thumb中心
      maskLeft.style.width = minX + 'px';
      maskRight.style.width = (W - maxX) + 'px';
      selBox.style.left = minX + 'px';
      selBox.style.width = (maxX - minX) + 'px';
      const total = labels.length;
      const startIdx = Math.floor(minVal / 100 * total);
      const endIdx = Math.min(total, Math.ceil(maxVal / 100 * total));
      startLabel.textContent = labels[startIdx];
      endLabel.textContent = labels[endIdx - 1];
      const ch = INSTANCES[chartId];
      if(ch){
        ch.data.labels = labels.slice(startIdx, endIdx);
        ch.data.datasets.forEach((ds, i)=>{ ds.data = dataArrays[i].slice(startIdx, endIdx); });
        ch.update();
      }
      if(onUpdate) onUpdate(startIdx, endIdx);
    }
    minInput.addEventListener('input', update);
    maxInput.addEventListener('input', update);
    window.addEventListener('resize', update);
    // 快捷日期按钮
    const quickBtns = wrap.querySelectorAll('.range-slider-quick button');
    quickBtns.forEach(btn => {
      btn.addEventListener('click', function() {
        const days = parseInt(this.dataset.days);
        if(labels.length > days) {
          const startPct = Math.round((1 - days / labels.length) * 100);
          minInput.value = startPct;
          maxInput.value = 100;
        } else {
          minInput.value = 0;
          maxInput.value = 100;
        }
        quickBtns.forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        update();
      });
    });
    update();
    console.log('attachRangeSlider: created for', chartId, 'with', labels.length, 'points (orig:', origLabels.length, ', defaultDays:', defaultDays, ', maxDays:', maxDays, ')');
  } catch(e) {
    console.error('attachRangeSlider error for', chartId, ':', e);
  }
}

const H=D.hist;
makeChart('cTurn', lineCfg(H.dates, [{label:'总成交额(亿)',data:H.turnover,borderColor:'#60a5fa',backgroundColor:'rgba(96,165,250,.15)',fill:true,pointRadius:1,tension:.25,borderWidth:1.5}]));
attachRangeSlider('cTurn', H.dates, [H.turnover], null, 60, 500);
// 裁剪掉数据数组前面全为 null 的前缀：成交额已用长期历史补全（491天），
// 但涨跌家数/涨跌停/新高新低只有 hithink 采集期（近期）有值，不裁剪会被挤到图表最右侧
function trimNullPrefix(labels, arrays){
  let start = labels.length;
  arrays.forEach(a=>{ for(let i=0;i<a.length;i++){ if(a[i]!==null && a[i]!==undefined){ start=Math.min(start,i); break; } } });
  return {labels: labels.slice(start), arrays: arrays.map(a=>a.slice(start))};
}
const upT = trimNullPrefix(H.dates, [H.up, H.down]);
makeChart('cUp', lineCfg(upT.labels, [
  {label:'上涨',data:upT.arrays[0],borderColor:RED,backgroundColor:RED,fill:false,pointRadius:1,tension:.25,borderWidth:1},
  {label:'下跌',data:upT.arrays[1],borderColor:GREEN,backgroundColor:GREEN,fill:false,pointRadius:1,tension:.25,borderWidth:1}]));
const limT = trimNullPrefix(H.dates, [H.lu, H.ld]);
makeChart('cLim', lineCfg(limT.labels, [
  {label:'涨停',data:limT.arrays[0],borderColor:RED,fill:false,pointRadius:1,tension:.25,borderWidth:1},
  {label:'跌停',data:limT.arrays[1],borderColor:GREEN,fill:false,pointRadius:1,tension:.25,borderWidth:1}]));
const hlT = trimNullPrefix(H.dates, [H.hn, H.ln]);
const hlDs=[];
if(hlT.arrays[0].some(x=>x!==null)) hlDs.push({label:'新高',data:hlT.arrays[0],borderColor:RED,fill:false,pointRadius:1,tension:.25,borderWidth:1});
if(hlT.arrays[1].some(x=>x!==null)) hlDs.push({label:'新低',data:hlT.arrays[1],borderColor:GREEN,fill:false,pointRadius:1,tension:.25,borderWidth:1});
if(hlDs.length) makeChart('cHL', lineCfg(hlT.labels, hlDs));
else document.getElementById('cHL').parentElement.innerHTML='<p class="miss">新高/新低：暂无历史数据</p>';
const idxColors=['#2b6cb0','#d8392b','#16a34a','#9333ea','#0891b2','#ca8a04','#db2777','#475569'];
// 重要指数：一律归一化（首日=100），消除点位绝对值差异，便于比强弱
const idxRaw = D.idx_lines.map(l=>l.data.slice());
const idxNorm = idxRaw.map(arr=>{ const b=arr[0]; return arr.map(v=> v==null?null:+(v/b*100).toFixed(2)); });
makeChart('cIdx', lineCfg(D.idx_dates, D.idx_lines.map((l,i)=>({
  label:l.name, data:idxNorm[i], borderColor:idxColors[i%8], fill:false, pointRadius:0, tension:.2, borderWidth:1.5
}))), renderIdxTip);
INSTANCES['cIdx'].options.scales.y.title={display:true,text:'归一化（窗口首日=100）',font:{size:10}};
INSTANCES['cIdx'].options.plugins.tooltip.enabled=false;  // 用自定义 #idxTip 代替原生 tooltip
// 滑动范围变化时：按窗口内第一天重新归一化（窗口起点=100）
function idxRenorm(startIdx,endIdx){
  const ch=INSTANCES['cIdx']; if(!ch) return;
  ch.data.datasets.forEach((ds,i)=>{
    const win=idxRaw[i].slice(startIdx,endIdx);
    const base=win.find(v=>v!==null&&v!==undefined&&!isNaN(v));
    ds.data=base?win.map(v=>(v===null||v===undefined||isNaN(v))?null:+(v/base*100).toFixed(2)):[];
  });
  ch.update();
}
attachRangeSlider('cIdx', D.idx_dates, idxRaw, idxRenorm, 250, 500, true, '#60a5fa');
// 鼠标悬停时渲染各指数当日数值，按强弱（值）降序排列
function renderIdxTip(idx, e){
  const tip=document.getElementById('idxTip');
  if(idx==null || idx<0){ tip.style.display='none'; return; }
  const ch=INSTANCES['cIdx']; if(!ch) return;
  const rows=ch.data.datasets
    .map(d=>({name:d.label, val:d.data[idx]}))
    .filter(r=>r.val!==null && r.val!==undefined)
    .sort((a,b)=>b.val-a.val);
  const date=D.idx_dates[idx];
  tip.innerHTML='<div class="t-date">'+date+'</div>'+rows.map(r=>'<div class="t-row"><span>'+r.name+'</span><b>'+Number(r.val).toFixed(2)+'</b></div>').join('');
  tip.style.display='block';
  const cv=ch.canvas, rect=cv.getBoundingClientRect();
  const v=ch._hx;
  let lx=(v!=null?rect.left+v:e.clientX)+14, ly=e.clientY+14;
  const w=tip.offsetWidth||160;
  if(lx+w>window.innerWidth) lx=(v!=null?rect.left+v:e.clientX)-w-14;
  if(ly+tip.offsetHeight>window.innerHeight) ly=e.clientY-tip.offsetHeight-14;
  tip.style.left=lx+'px';
  tip.style.top=ly+'px';
}
// 风格指数曲线（归一化 · 首日=100）：数据由后端按宽基指数同一 60 日窗口对齐（D.style_lines）
if(D.style_lines && D.style_lines.length){
  const sRaw=D.style_lines.map(l=>l.data.slice());
  const sNorm=sRaw.map(arr=>{ const b=arr.find(v=>v!==null); return b?arr.map(v=>v==null?null:+(v/b*100).toFixed(2)):[]; });
  const styleColors=['#2b6cb0','#d8392b','#16a34a','#9333ea','#0891b2','#ca8a04','#db2777','#475569'];
  const sch=makeChart('cStyle', lineCfg(D.style_dates, D.style_lines.map((l,i)=>({
    label:l.name, data:sNorm[i], borderColor:styleColors[i%styleColors.length], fill:false, pointRadius:0, tension:.2, borderWidth:1.5
  }))), renderStyleTip);
  sch._sd=D.style_dates;  // 供自定义 tooltip 取日期
  sch.options.scales.y.title={display:true,text:'归一化（窗口首日=100）',font:{size:10}};
  sch.options.plugins.tooltip.enabled=false;  // 用自定义 #idxTip 代替原生 tooltip
  // 滑动范围变化时：按窗口内第一天重新归一化（窗口起点=100），再比较各指数强弱
  function styleRenorm(startIdx,endIdx){
    const ch=INSTANCES['cStyle']; if(!ch) return;
    ch.data.datasets.forEach((ds,i)=>{
      const win=sRaw[i].slice(startIdx,endIdx);
      const base=win.find(v=>v!==null&&v!==undefined&&!isNaN(v));
      ds.data=base?win.map(v=>(v===null||v===undefined||isNaN(v))?null:+(v/base*100).toFixed(2)):[];
    });
    ch.update();
  }
  attachRangeSlider('cStyle', D.style_dates, sRaw, styleRenorm, 250, 500, true, '#2b6cb0');
} else {
  document.getElementById('cStyle').parentElement.innerHTML='<p class="miss">风格指数曲线：暂无历史数据（本次采集后自动累积）</p>';
}
function renderStyleTip(idx, e){
  const tip=document.getElementById('idxTip');
  if(idx==null || idx<0){ tip.style.display='none'; return; }
  const ch=INSTANCES['cStyle']; if(!ch) return;
  const rows=ch.data.datasets
    .map(d=>({name:d.label, val:d.data[idx]}))
    .filter(r=>r.val!==null && r.val!==undefined)
    .sort((a,b)=>b.val-a.val);
  const date=(ch._sd||[])[idx];
  tip.innerHTML='<div class="t-date">'+date+'</div>'+rows.map(r=>'<div class="t-row"><span>'+r.name+'</span><b>'+Number(r.val).toFixed(2)+'</b></div>').join('');
  tip.style.display='block';
  const cv=ch.canvas, rect=cv.getBoundingClientRect();
  const v=ch._hx;
  let lx=(v!=null?rect.left+v:e.clientX)+14, ly=e.clientY+14;
  const w=tip.offsetWidth||160;
  if(lx+w>window.innerWidth) lx=(v!=null?rect.left+v:e.clientX)-w-14;
  if(ly+tip.offsetHeight>window.innerHeight) ly=e.clientY-tip.offsetHeight-14;
  tip.style.left=lx+'px';
  tip.style.top=ly+'px';
}
makeChart('cSec', {
  type:'bar',
  data:{labels:D.sec_bar.map(s=>s.name), datasets:[
    {type:'bar', label:'成交额(亿)', data:D.sec_bar.map(s=>s.v), backgroundColor:'#2b6cb0', yAxisID:'y', barPercentage:0.2, categoryPercentage:0.5},
    {type:'line', label:'成交额占比%', data:D.sec_bar.map(s=>s.ratio), borderColor:'#d8392b', backgroundColor:'#d8392b', yAxisID:'y1', pointRadius:3, borderWidth:2, tension:.25}
  ]},
  options:{responsive:true, plugins:{legend:{display:false}}, scales:{
    x:{ticks:{font:{size:10},maxRotation:60}},
    y:{position:'left', grid:{color:'#252d40'}, title:{display:true,text:'成交额(亿)',font:{size:10}}},
    y1:{position:'right', grid:{drawOnChartArea:false}, title:{display:true,text:'成交额占比%',font:{size:10}}, ticks:{font:{size:10}}}
  }}
});
makeChart('cNet', barCfg(D.net_top.map(s=>s.name),'主力净流入(亿)',D.net_top.map(s=>s.v),'#d8392b',60));

// 万得全A(881001) 日K（市值加权全A代理，非等权）
function getWandeSliceByIdx(startIdx, endIdx){
  if(!WANDE) return null;
  const pct = [];
  for(let i = startIdx; i < endIdx; i++){
    if(i > 0 && WANDE.close[i-1] !== 0){
      pct.push((WANDE.close[i] - WANDE.close[i-1]) / WANDE.close[i-1] * 100);
    } else {
      pct.push(null);
    }
  }
  return {
    dates: WANDE.dates.slice(startIdx, endIdx),
    open: WANDE.open.slice(startIdx, endIdx),
    close: WANDE.close.slice(startIdx, endIdx),
    high: WANDE.high.slice(startIdx, endIdx),
    low: WANDE.low.slice(startIdx, endIdx),
    pct: pct
  };
}
if(WANDE){
  let wandeCur = getWandeSliceByIdx(0, WANDE.dates.length);
  wandeCurData = wandeCur;
  const wcfg={type:'line',
    data:{labels:wandeCur.dates, datasets:[{data:wandeCur.close, pointRadius:0, borderColor:'rgba(0,0,0,0)', showLine:false}]},
    options:{responsive:true, maintainAspectRatio:false,
      interaction:{mode:'index', intersect:false},
      layout:{padding:{right:64,top:18}},
      plugins:{legend:{display:false}, verticalLine:true,
        tooltip:{enabled:true, titleFont:{size:13,weight:'bold'}, bodyFont:{size:12}, padding:10,
          callbacks:{label:(c)=>{
            const p = wandeCur.pct[c.dataIndex];
            const pStr = p !== null ? ((p > 0 ? '+' : '') + p.toFixed(2) + '%') : '-';
            return ['开 '+wandeCur.open[c.dataIndex].toFixed(2),'收 '+wandeCur.close[c.dataIndex].toFixed(2),'涨跌幅 '+pStr,'高 '+wandeCur.high[c.dataIndex].toFixed(2),'低 '+wandeCur.low[c.dataIndex].toFixed(2)];
          }}}},
      scales:{x:{offset:true,ticks:{maxTicksLimit:12,font:{size:10}},grid:{display:false}},y:{ticks:{font:{size:10}},grid:{color:'#252d40'}}}
    },
    plugins:[verticalLinePlugin, candlePlugin]
  };
  const wch=new Chart(document.getElementById('cWande'), wcfg);
  INSTANCES['cWande']=wch;
  wch.__zoomCfg = cloneCfg(wcfg);
  wch.__needsCandle = true;
  const wcv=document.getElementById('cWande');
  wcv.style.cursor='zoom-in';
  wcv.addEventListener('dblclick', ()=>openZoom('cWande'));
  attachHover(wch, wcv);
  // 时间范围拖动条
  attachRangeSlider('cWande', WANDE.dates, [WANDE.close], function(startIdx, endIdx){
    wandeCur = getWandeSliceByIdx(startIdx, endIdx);
    wandeCurData = wandeCur;
  }, 250, 600);
}
// 沪深两市融资余额（亿元）
const mg = D.margin;
if(mg && mg.dates && mg.dates.length){
  const mgCfg={type:'line',data:{labels:mg.dates,datasets:[{label:'融资余额(亿)',data:mg.margin_balance,borderColor:'#a78bfa',backgroundColor:'rgba(167,139,250,.15)',fill:true,pointRadius:0,tension:.25,borderWidth:1.8}]},options:{responsive:true,plugins:{legend:{labels:{font:{size:11}}},tooltip:{enabled:true,callbacks:{label:(c)=>'融资余额: '+Number(c.parsed.y).toLocaleString()+' 亿'}}},scales:{x:{ticks:{maxTicksLimit:12,font:{size:10}},grid:{display:false}},y:{ticks:{font:{size:10},callback:(v)=>v>=10000?(v/10000).toFixed(1)+'万':v},grid:{color:'#252d40'},title:{display:true,text:'亿元',font:{size:10}}}}}};
  makeChart('cMargin', mgCfg);
  attachRangeSlider('cMargin', mg.dates, [mg.margin_balance], null, 120, 250, true, '#a78bfa');
}
// 两融交易占市场总成交比例（%）
const mr = D.margin_ratio;
if(mr && mr.dates && mr.dates.length){
  const mrCfg={type:'line',data:{labels:mr.dates,datasets:[{label:'两融交易占比(%)',data:mr.ratio,borderColor:'#c084fc',backgroundColor:'rgba(192,132,252,.15)',fill:true,pointRadius:0,tension:.25,borderWidth:1.8}]},options:{responsive:true,plugins:{legend:{labels:{font:{size:11}}},tooltip:{enabled:true,callbacks:{label:(c)=>'两融交易占比: '+Number(c.parsed.y).toFixed(2)+'%'}}},scales:{x:{ticks:{maxTicksLimit:12,font:{size:10}},grid:{display:false}},y:{ticks:{font:{size:10},callback:(v)=>v+'%'},grid:{color:'#252d40'},title:{display:true,text:'%',font:{size:10}}}}}};
  makeChart('cMarginRatio', mrCfg);
  attachRangeSlider('cMarginRatio', mr.dates, [mr.ratio], null, 120, 250, true, '#c084fc');
}
// 均占系统 均线占比（市场宽度）日线
const jz=D.jzxt;
if(jz && jz.dates && jz.dates.length){
  const jzSeries=[['cdx','5日','#ff0000'],['dx','13日','#4169E1'],['zx','50日','#ff8c00'],['cx','120日','#8B008B']];
  const jzDs=jzSeries.filter(s=>(jz[s[0]]||[]).length).map(s=>({label:s[1],data:jz[s[0]],borderColor:s[2],backgroundColor:s[2],fill:false,pointRadius:0,tension:.2,borderWidth:1.5}));
  const jzCfg={type:'line',data:{labels:jz.dates,datasets:jzDs},options:{responsive:true,plugins:{legend:{labels:{font:{size:11}}},tooltip:{enabled:true,callbacks:{label:(c)=>c.dataset.label+': '+Number(c.parsed.y).toFixed(2)+'%'}}},scales:{x:{ticks:{maxTicksLimit:12,font:{size:10}},grid:{display:false}},y:{min:0,max:100,ticks:{font:{size:10}},grid:{color:'#252d40'},title:{display:true,text:'占比 %',font:{size:10}}}}},plugins:[zonePlugin]};
  makeChart('cJzxt', jzCfg);
  const jzOrigData = jzSeries.filter(s=>(jz[s[0]]||[]).length).map(s=>jz[s[0]]);
  attachRangeSlider('cJzxt', jz.dates, jzOrigData, null, 120, 250);
}
// TR情绪监测（通达信扩展数据 38/39/40：HTR10/HTR20/HTR40）
const trFull = D.tr_emotion;
if(trFull && trFull.dates && trFull.dates.length){
  const TR_RANGES = {'120':120,'half':180,'year':365,'2year':730};
  function trSlice(range){
    const days = TR_RANGES[range] || 180;
    const lastDate = new Date(trFull.dates[trFull.dates.length-1]);
    const cutoff = new Date(lastDate);
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString().slice(0,10);
    let si = trFull.dates.findIndex(d => d >= cutoffStr);
    return si < 0 ? 0 : si;
  }
  let trStart = 0;
  const trSeries=[['htr10','HTR10(短期)','#ff6b6b'],['htr20','HTR20(中期)','#2b6cb0'],['htr40','HTR40(长期)','#9333ea']];
  function trDs(start){
    return trSeries.map(s=>({label:s[1],data:(trFull[s[0]]||[]).slice(start),borderColor:s[2],backgroundColor:s[2],fill:false,pointRadius:0,tension:.2,borderWidth:1.5}));
  }
  const trCfg={type:'line',data:{labels:trFull.dates,datasets:trDs(0)},options:{responsive:true,plugins:{legend:{labels:{font:{size:11}}},tooltip:{enabled:true,callbacks:{label:(c)=>c.dataset.label+': '+Number(c.parsed.y).toFixed(2)+'%'}}},scales:{x:{ticks:{maxTicksLimit:12,font:{size:10}},grid:{display:false}},y:{min:0,max:100,ticks:{font:{size:10}},grid:{color:'#252d40'},title:{display:true,text:'TR占比 %',font:{size:10}}}}},plugins:[trZonePlugin]};
  makeChart('cTr', trCfg);
  const trOrigData = trSeries.map(s=>trFull[s[0]]||[]);
  attachRangeSlider('cTr', trFull.dates, trOrigData, null, 120, 250);
}
// 板块 RPS 共振（东方财富·全市场板块）：横向分组条形图
if(D.rps_chart_cfg){
  D.rps_chart_cfg.plugins=(D.rps_chart_cfg.plugins||[]).concat([rpsBarLabelPlugin]);
  makeChart('cRps', D.rps_chart_cfg);
}


// ---- 自定义图例 + 点击高亮对应曲线 ----
function chartColor(ds){
  var c = ds.borderColor;
  if(c===undefined || (typeof c==='string' && c.indexOf('rgba(0,0,0,0)')>=0)) c = ds.backgroundColor;
  return c;
}
function hexToRgba(c,a){
  if(typeof c!=='string') return c;
  var h=c.replace('#','');
  if(h.length===3) h=h.split('').map(function(x){return x+x;}).join('');
  if(h.length===6){var r=parseInt(h.substr(0,2),16),g=parseInt(h.substr(2,2),16),b=parseInt(h.substr(4,2),16);return 'rgba('+r+','+g+','+b+','+a+')';}
  return c;
}
function darken(c,f){
  if(typeof c!=='string'||c.charAt(0)!=='#') return c;
  var h=c.replace('#',''); if(h.length===3) h=h.split('').map(function(x){return x+x;}).join('');
  if(h.length!==6) return c;
  var r=parseInt(h.substr(0,2),16),g=parseInt(h.substr(2,2),16),b=parseInt(h.substr(4,2),16);
  r=Math.max(0,Math.round(r*f));g=Math.max(0,Math.round(g*f));b=Math.max(0,Math.round(b*f));
  return 'rgb('+r+','+g+','+b+')';
}
// RPS 自定义外部 tooltip：紧凑显示全部 4 个 RPS，值>87 红色
function rpsExternalTooltip(context){
  var t=context.tooltip;
  var el=document.getElementById('rpsTip');
  if(!el){
    el=document.createElement('div');
    el.id='rpsTip';
    el.style.cssText='position:absolute;pointer-events:none;background:rgba(255,255,255,.97);border:1px solid #e1e4e8;border-radius:8px;box-shadow:0 4px 14px rgba(0,0,0,.12);padding:8px 10px;font-size:13px;color:#1f2329;z-index:9999;max-width:260px;line-height:1.55;font-family:-apple-system,BlinkMacSystemFont,sans-serif';
    document.body.appendChild(el);
  }
  if(!t||t.opacity===0){ el.style.opacity=0; return; }
  var items=t.dataPoints;
  if(!items||!items.length){ el.style.opacity=0; return; }
  var board=items[0].label;
  var thr=87;
  var order=['rps50','rps20','rps10','rps5'];
  var map={};
  items.forEach(function(it){ map[it.dataset.label]=it.parsed.x; });
  var html='<div style="font-weight:600;margin-bottom:4px">'+board+'</div>';
  order.forEach(function(k){
    if(map[k]===undefined) return;
    var v=Number(map[k]);
    var col=v>thr?'#d8392b':'#1f2329';
    html+='<div style="color:'+col+'">■ '+k+': '+v.toFixed(2)+'</div>';
  });
  el.innerHTML=html;
  var ch=context.chart;
  var cv=ch.canvas;
  var rect=cv.getBoundingClientRect();
  el.style.opacity=1;
  // 优先用鼠标实际位置，回退到 caret 位置
  var mx = (ch._mouseX != null) ? ch._mouseX : (rect.left + t.caretX);
  var my = (ch._mouseY != null) ? ch._mouseY : (rect.top + t.caretY);
  var tipW = el.offsetWidth || 200;
  var tipH = el.offsetHeight || 100;
  var vw = window.innerWidth;
  var vh = window.innerHeight;
  // 默认在鼠标右下方15px
  var left = mx + 15 + window.pageXOffset;
  var top = my + 15 + window.pageYOffset;
  // 超出右边界则放到鼠标左侧
  if(mx + 15 + tipW > vw) left = mx - tipW - 15 + window.pageXOffset;
  // 超出下边界则放到鼠标上方
  if(my + 15 + tipH > vh) top = my - tipH - 15 + window.pageYOffset;
  el.style.left=left+'px';
  el.style.top=top+'px';
}
function setHighlight(id, idx){
  var ch=INSTANCES[id]; if(!ch) return;
  var same = ch._hlIdx===idx;
  ch._hlIdx = same?null:idx;
  ch.data.datasets.forEach(function(ds,i){
    if(ds.__ob===undefined) ds.__ob={bc:ds.borderColor,bg:ds.backgroundColor,bw:ds.borderWidth,pr:ds.pointRadius};
    var ob=ds.__ob;
    if(ch._hlIdx===null){
      ds.borderColor=ob.bc; ds.backgroundColor=ob.bg; ds.borderWidth=ob.bw; ds.pointRadius=ob.pr;
    } else if(i===ch._hlIdx){
      // 选中系列：保留原色，并加一条更深的描边 + 加粗，使其明显“跳”出来
      ds.borderColor = (ob.bc!==undefined && ob.bc!==null) ? ob.bc : darken(ob.bg, 0.5);
      ds.backgroundColor = ob.bg;
      ds.borderWidth = (typeof ob.bw==='number'?ob.bw:1) + 2.5;
      ds.pointRadius = (typeof ob.pr==='number'?ob.pr:2) + 2;
    } else {
      ds.borderColor=hexToRgba(ob.bc,0.10);
      ds.backgroundColor=hexToRgba(ob.bg,0.10);
      ds.borderWidth=1; ds.pointRadius=0;
    }
  });
  ch.update();
  var box=document.getElementById('leg_'+id);
  if(box) box.querySelectorAll('.chip').forEach(function(c){
    c.classList.toggle('active', !same && (+c.dataset.idx)===idx);
  });
}
function toggleDatasetHidden(id, idx){
  // 双击图例标签：隐藏/显示对应曲线
  var ch=INSTANCES[id]; if(!ch) return;
  var ds=ch.data.datasets[idx];
  if(!ds) return;
  ds.hidden = !ds.hidden;
  ch.update();
  var box=document.getElementById('leg_'+id);
  if(box){
    var chip=box.querySelector('.chip[data-idx="'+idx+'"]');
    if(chip) chip.classList.toggle('hidden', ds.hidden);
  }
}
function buildLegends(){
  var ids=['cTurn','cUp','cLim','cHL','cIdx','cStyle','cSec','cNet','cMargin','cMarginRatio','cJzxt','cTr','cRps'];
  ids.forEach(function(id){
    var ch=INSTANCES[id]; var box=document.getElementById('leg_'+id);
    if(!ch||!box) return;
    ch.data.datasets.forEach(function(ds,i){
      var col=chartColor(ds);
      if(col===undefined) return;
      if(typeof col==='string' && col.indexOf('rgba(0,0,0,0)')>=0) return;
      var chip=document.createElement('span');
      chip.className='chip'; chip.dataset.idx=i;
      var dot=document.createElement('span'); dot.className='dot'; dot.style.background=col;
      var txt=document.createElement('span'); txt.textContent=ds.label||('系列'+(i+1));
      chip.appendChild(dot); chip.appendChild(txt);
      chip.addEventListener('click',(function(i){return function(){setHighlight(id,i);};})(i));
      chip.addEventListener('dblclick',(function(i){return function(e){e.stopPropagation();toggleDatasetHidden(id,i);};})(i));
      box.appendChild(chip);
    });
  });
}
// ---- RPS 图表：悬停某一行列出该板块全部 RPS 值 ----
if(D.rps_chart_cfg){
  var rch=INSTANCES['cRps'];
  if(rch){
    // 横向条形图(indexAxis:y)用 index+axis:y，按鼠标所在行触发整行所有系列；
    // 值取 parsed.x（X轴=RPS数值），parsed.y 是行号索引。
    rch.options.interaction={mode:'index', axis:'y', intersect:false};
    rch.options.plugins.tooltip.enabled=false;
    rch.options.plugins.tooltip.mode='index';
    rch.options.plugins.tooltip.axis='y';
    rch.options.plugins.tooltip.intersect=false;
    rch.options.plugins.tooltip.external=rpsExternalTooltip;
    rch.update();
  }
}
buildLegends();


// ---- 真正用数据重新渲染的大图（新建 Canvas + Chart 实例）----
var __zoomInst = null;   // 当前放大态的 Chart 实例
var __zoomId   = null;   // 当前放大态的原始图表 id

function openZoom(id){
  var m=document.getElementById('zoomModal');
  if(m.style.display==='flex') return;
  var ch=INSTANCES[id]; if(!ch) return;

  // 用创建时保存的「干净可序列化」配置（ch.__zoomCfg）作为大图数据源。
  // 切勿使用 ch.config：它是 Chart.js 的 Config 包装对象，内含 chart 自引用，
  // JSON.stringify 会抛“循环引用”错误，导致大图打不开。
  var box=document.getElementById('zoomBody');
  var cfg=null;
  if(ch.__zoomCfg){ try{ cfg=JSON.parse(JSON.stringify(ch.__zoomCfg)); }catch(e){cfg=null;} }
  if(!cfg){ try{ cfg=JSON.parse(JSON.stringify((ch.config&&ch.config._config)||ch.config)); }catch(e){cfg=null;} }
  if(!cfg){ m.style.display='flex'; box.innerHTML='<p style="color:#f00;padding:20px">该图表暂不支持放大</p>'; return; }

  // 重建插件（JSON 序列化会丢失插件函数对象，这里按原图需要重新挂回）
  cfg.plugins = [verticalLinePlugin];
  if(ch.__needsCandle) cfg.plugins.push(candlePlugin);
  if(ch.__needsZone) cfg.plugins.push(zonePlugin);
  if(ch.__needsTrZone) cfg.plugins.push(trZonePlugin);
  cfg.options = cfg.options || {};
  cfg.options.maintainAspectRatio = false;  // 大图填满弹窗，避免 letterbox

  // 在弹窗中创建全新高分辨率 canvas
  var box=document.getElementById('zoomBody');
  box.innerHTML = '';
  var ncv = document.createElement('canvas');
  ncv.id='zoomCanvas';
  ncv.style.width='92vw';
  ncv.style.height='82vh';
  box.appendChild(ncv);

  m.style.display='flex';
  var tip=document.getElementById('idxTip'); if(tip) tip.style.display='none';

  // 用同一份配置新建 Chart 实例（高分辨率渲染）
  try {
    __zoomInst = new Chart(ncv, cfg);
    INSTANCES['__zoom__'] = __zoomInst;   // 注册到全局映射，使 setHighlight 可用
    __zoomId = id;

    // ---- 补回 JSON 丢失的函数回调 ----
    // RPS 横向条形图：改用 index 模式 + 自定义外部 tooltip
    if(id==='cRps'){
      __zoomInst.options.interaction={mode:'index', intersect:false};
      __zoomInst.options.plugins.tooltip.enabled=false;
      __zoomInst.options.plugins.tooltip.mode='index';
      __zoomInst.options.plugins.tooltip.intersect=false;
      __zoomInst.options.plugins.tooltip.external=rpsExternalTooltip;
      __zoomInst.update();
    }
    // 指数图：关闭原生 tooltip（用自定义 idxTip，但大图中暂不跟随鼠标）
    if(id==='cIdx'){
      __zoomInst.options.scales.y.title={display:true,text:'归一化（首日=100）',font:{size:10}};
      __zoomInst.options.plugins.tooltip.enabled=false;
      __zoomInst.update();
    }
    // 风格指数图：同上（归一化曲线，大图不挂自定义 tooltip）
    if(id==='cStyle'){
      __zoomInst.options.scales.y.title={display:true,text:'归一化（首日=100）',font:{size:10}};
      __zoomInst.options.plugins.tooltip.enabled=false;
      __zoomInst.update();
    }

    // 继承原图的高亮状态
    if(ch._hlIdx!==null && ch._hlIdx!==undefined){
      setHighlight('__zoom__', ch._hlIdx);
    }
  } catch(e){ console.error('[zoom] 新建图表失败', e); box.innerHTML='<p style="color:#f00">图表放大失败：'+e.message+'</p>'; }
}
function closeZoom(){
  // 销毁放大态 Chart 实例（释放 canvas / 事件 / 内存）
  if(__zoomInst){
    try { __zoomInst.destroy(); } catch(e){}
    delete INSTANCES['__zoom__'];
    __zoomInst = null;
    __zoomId = null;
  }
  var box=document.getElementById('zoomBody');
  box.innerHTML='';
  var m=document.getElementById('zoomModal');
  m.style.display='none';
  var tip=document.getElementById('idxTip'); if(tip) tip.style.display='none';
}
document.getElementById('zoomModal').addEventListener('click',(e)=>{ if(e.target.id==='zoomModal') closeZoom(); });
document.addEventListener('keydown',(e)=>{ if(e.key==='Escape') closeZoom(); });

// ---- 表头点击排序（所有数据表通用）----
function parseCell(txt){
  txt=(txt||'').trim();
  if(txt===''||txt==='—'||txt==='-') return {num:false, raw:txt};
  var s=txt.replace(/[^0-9.-]/g,'');
  var n=parseFloat(s);
  if(s!=='' && !isNaN(n) && isFinite(n)) return {num:true, val:n, raw:txt};
  return {num:false, raw:txt};
}
function sortTable(t, ci, dir){
  var rows=[], skips=[];
  t.querySelectorAll('tr').forEach(function(tr){
    if(tr.querySelector(':scope > th')) return;            // 跳过表头行
    var cells=tr.children;
    if(!cells.length || cells.length<=ci) return;
    if(cells[ci].getAttribute('colspan')){ skips.push(tr); return; }  // 跳过合计/占位行
    rows.push(tr);
  });
  rows.sort(function(a,b){
    var av=parseCell(a.children[ci].textContent), bv=parseCell(b.children[ci].textContent);
    if(av.num&&bv.num) return (av.val-bv.val)*dir;
    return av.raw.localeCompare(bv.raw,'zh')*dir;
  });
  // 仅当首列表头为 #（序号列）时，按新顺序重排序号
  var firstTh=t.querySelector('th');
  var renum = firstTh && firstTh.textContent.trim()==='#';
  rows.forEach(function(r, idx){ t.appendChild(r); if(renum){ r.children[0].textContent = (idx+1); } });
  skips.forEach(function(r){ t.appendChild(r); });
  // 排序后，把折叠行（如成交量 51–100）全部显示出来
  var fr=t.querySelectorAll('tr.fold-row');
  if(fr.length && typeof foldState!=='undefined'){ foldState.open=true; if(foldState.apply) foldState.apply(); }
}
function makeTablesSortable(){
  document.querySelectorAll('table').forEach(function(t){
    var ths=t.querySelectorAll('th');
    if(!ths.length) return;
    t.classList.add('sortable');
    var state={col:null, dir:1};
    ths.forEach(function(th, ci){
      var arr=document.createElement('span'); arr.className='arr'; th.appendChild(arr);
      th.addEventListener('click', function(){
        if(state.col===ci){ state.dir=-state.dir; } else { state.col=ci; state.dir=1; }
        sortTable(t, ci, state.dir);
        ths.forEach(function(o){ var a=o.querySelector('.arr'); if(a) a.textContent=''; });
        arr.textContent = state.dir>0 ? '▲' : '▼';
      });
    });
  });
}
makeTablesSortable();
// 成交量表的折叠/展开（51–100 名），折叠行仍参与排序；排序后自动展开
var foldState={open:false};
function setupFold(){
  var t=document.getElementById('stkVolTable'); if(!t) return;
  var btn=document.getElementById('foldToggle'); if(!btn) return;
  var rows=t.querySelectorAll('tr.fold-row');
  foldState.apply=function(){
    rows.forEach(function(r){ r.style.display = foldState.open ? '' : 'none'; });
    btn.textContent = foldState.open ? '折叠 第 51–100 名（点击折叠 / 展开）' : '展开 第 51–100 名（点击折叠 / 展开）';
  };
  btn.addEventListener('click', function(){ foldState.open=!foldState.open; foldState.apply(); });
}
setupFold();
// ── 历史趋势表格（模块三/四/五/七）──
var HT = D.hist_tables || {};
function toggleHist(el){
  var body = el.nextElementSibling;
  var open = el.classList.toggle('open');
  body.classList.toggle('open', open);
  if(open && !body.dataset.rendered){ renderHistBody(body); body.dataset.rendered='1'; }
}
function histRangeBtns(cur){
  return '<div class="hist-range-btns">'+[10,20,60].map(function(n){
    return '<button class="hist-range-btn'+(n===cur?' active':'')+'" data-range="'+n+'">近'+n+'日</button>';
  }).join('')+'</div>';
}
function cellBg(v,type){
  if(v===null||v===undefined) return 'background:#1a1f2e;color:#4a5568';
  if(type==='turnover') return 'background:rgba(43,108,176,0.2);color:#7bb8ff';
  if(type==='inflow') return 'background:rgba(216,57,43,0.15);color:#fc8181';
  if(type==='outflow') return 'background:rgba(22,163,74,0.15);color:#68d391';
  if(type==='rps'){
    var rc=['#1a1f2e','#744210','#9b2c2c','#c53030','#742a2a'];
    var idx=Math.max(0,Math.min(4,Math.round(v)));
    return 'background:'+rc[idx]+';color:'+(idx>=2?'#fed7d7':'#e0e6ed');
  }
  if(type==='high') return 'background:rgba(216,57,43,0.12);color:#fc8181';
  if(type==='low') return 'background:rgba(22,163,74,0.12);color:#68d391';
  return '';
}
function renderRankTable(names,values,dates,offset,topN,type,valFmt){
  var html='<table class="hist-table"><thead><tr><th>#</th>';
  dates.forEach(function(d){ html+='<th>'+d.slice(5)+'</th>'; });
  html+='</tr></thead><tbody>';
  for(var i=0;i<topN;i++){
    html+='<tr><td style="color:#999;font-weight:600">'+(i+1)+'</td>';
    for(var j=0;j<dates.length;j++){
      var di=offset+j;
      var name=names[i]?names[i][di]:null;
      var val=values[i]?values[i][di]:null;
      if(name===null||name===undefined){
        html+='<td class="heat-cell" style="background:#1a1f2e;color:#4a5568">—</td>';
      } else {
        var bg=cellBg(val,type);
        var vtxt=valFmt?valFmt(val):(val!==null&&val!==undefined?val:'');
        html+='<td class="heat-cell hist-cell" data-name="'+name+'" style="'+bg+'" title="'+name+(vtxt?(' ('+vtxt+')'):'')+'" onclick="toggleHistHighlight(this)">'+name+'</td>';
      }
    }
    html+='</tr>';
  }
  html+='</tbody></table>';
  return html;
}
function renderHistBody(body){
  var mod = body.dataset.mod;
  var data = HT[mod];
  if(mod.indexOf('ind_')!==0 && mod!=='sec3_pct' && (!data||!data.dates||!data.dates.length)){ body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>'; return; }
  function render(n){
    var html = histRangeBtns(n);
    if(mod.indexOf('ind_')!==0 && mod!=='sec3_pct'){
      var dates = data.dates.slice(-n);
      var offset = data.dates.length - dates.length;
    }
    if(mod==='sec3'){
      html += renderRankTable(data.names,data.values,dates,offset,data.top_n,'turnover',
        function(v){return v!==null&&v!==undefined?v.toFixed(0)+'亿':'';});
    } else if(mod==='sec4'){
      html += '<h5 style="margin:8px 0 4px;color:#d8392b">主力净流入 TOP10</h5>';
      html += renderRankTable(data.inflow_names,data.inflow_values,dates,offset,data.top_n,'inflow',
        function(v){return v!==null&&v!==undefined?(v>0?'+':'')+v.toFixed(1)+'亿':'';});
      html += '<h5 style="margin:12px 0 4px;color:#16a34a">主力净流出 TOP10</h5>';
      html += renderRankTable(data.outflow_names,data.outflow_values,dates,offset,data.top_n,'outflow',
        function(v){return v!==null&&v!==undefined?v.toFixed(1)+'亿':'';});
    } else if(mod==='sec5'){
      html += renderRankTable(data.names,data.n_pass,dates,offset,data.top_n,'rps',
        function(v){return v!==null&&v!==undefined?v+'/4':'';});
    } else if(mod==='sec7'){
      html += '<h5 style="margin:8px 0 4px;color:#d8392b">创一年新高个股 TOP10</h5>';
      html += renderRankTable(data.high_names,data.high_pct,dates,offset,data.top_n,'high',
        function(v){return v!==null&&v!==undefined?(v>0?'+':'')+v.toFixed(2)+'%':'';});
      html += '<h5 style="margin:12px 0 4px;color:#16a34a">创一年新低个股 TOP10</h5>';
      html += renderRankTable(data.low_names,data.low_pct,dates,offset,data.top_n,'low',
        function(v){return v!==null&&v!==undefined?v.toFixed(2)+'%':'';});
    } else if(mod==='sec3_pct'){
      // 领涨/领跌板块历史趋势
      var pctData = D.hist_pct_sectors || {};
      if(!pctData.dates || !pctData.dates.length){ body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>'; return; }
      function renderPct(n){
        var dts = pctData.dates.slice(-n);
        var off = pctData.dates.length - dts.length;
        var html2 = histRangeBtns(n);
        html2 += '<h5 style="margin:8px 0 4px;color:#d8392b">领涨板块 TOP15</h5>';
        html2 += renderRankTable(pctData.top_names,pctData.top_pcts,dts,off,15,'high',
          function(v){return v!==null&&v!==undefined?(v>0?'+':'')+v.toFixed(2)+'%':'';});
        html2 += '<h5 style="margin:12px 0 4px;color:#16a34a">领跌板块 TOP15</h5>';
        html2 += renderRankTable(pctData.bottom_names,pctData.bottom_pcts,dts,off,15,'low',
          function(v){return v!==null&&v!==undefined?v.toFixed(2)+'%':'';});
        body.innerHTML = html2;
        alignHistTables(body);
        body.querySelectorAll('.hist-range-btn').forEach(function(btn){
          btn.addEventListener('click',function(){ renderPct(parseInt(this.dataset.range)); });
        });
      }
      renderPct(20);
      return;
    } else if(mod==='ind_limit_both'){
      // 涨停/跌停行业分布合并展示
      var upData = (D.hist_industry || {})['limit_up'];
      var downData = (D.hist_industry || {})['limit_down'];
      if((!upData || !upData.dates || !upData.dates.length) && (!downData || !downData.dates || !downData.dates.length)){
        body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>'; return;
      }
      function renderBoth(n){
        var html2 = histRangeBtns(n);
        function renderIndTable(indData, title, color, bgType){
          if(!indData || !indData.dates || !indData.dates.length) return '';
          var dts = indData.dates.slice(-n);
          var off = indData.dates.length - dts.length;
          var nms = indData.names.map(function(row){ return row.slice(off); });
          var vls = indData.values.map(function(row){ return row.slice(off); });
          return '<h5 style="margin:8px 0 4px;color:'+color+'">'+title+'</h5>' +
            renderRankTable(nms, vls, dts, 0, indData.top_n || 10, bgType,
              function(v){return v!==null&&v!==undefined?v+'只':'';});
        }
        html2 += renderIndTable(upData, '涨停行业分布', '#d8392b', 'high');
        html2 += renderIndTable(downData, '跌停行业分布', '#16a34a', 'low');
        body.innerHTML = html2;
        alignHistTables(body);
        body.querySelectorAll('.hist-range-btn').forEach(function(btn){
          btn.addEventListener('click',function(){ renderBoth(parseInt(this.dataset.range)); });
        });
      }
      renderBoth(20);
      return;
    } else if(mod==='ind_high_low_both'){
      // 新高/新低行业分布合并展示
      var highData = (D.hist_industry || {})['high_new'];
      var lowData = (D.hist_industry || {})['low_new'];
      if((!highData || !highData.dates || !highData.dates.length) && (!lowData || !lowData.dates || !lowData.dates.length)){
        body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>'; return;
      }
      function renderHLBoth(n){
        var html2 = histRangeBtns(n);
        function renderIndTable(indData, title, color, bgType){
          if(!indData || !indData.dates || !indData.dates.length) return '';
          var dts = indData.dates.slice(-n);
          var off = indData.dates.length - dts.length;
          var nms = indData.names.map(function(row){ return row.slice(off); });
          var vls = indData.values.map(function(row){ return row.slice(off); });
          return '<h5 style="margin:8px 0 4px;color:'+color+'">'+title+'</h5>' +
            renderRankTable(nms, vls, dts, 0, indData.top_n || 10, bgType,
              function(v){return v!==null&&v!==undefined?v+'只':'';});
        }
        html2 += renderIndTable(highData, '新高行业分布', '#d8392b', 'high');
        html2 += renderIndTable(lowData, '新低行业分布', '#16a34a', 'low');
        body.innerHTML = html2;
        alignHistTables(body);
        body.querySelectorAll('.hist-range-btn').forEach(function(btn){
          btn.addEventListener('click',function(){ renderHLBoth(parseInt(this.dataset.range)); });
        });
      }
      renderHLBoth(20);
      return;
    } else if(mod==='ind_etf_both'){
      // ETF 净申购/净赎回历史双榜
      var etfIn = (D.hist_industry || {})['etf_inflow'];
      var etfOut = (D.hist_industry || {})['etf_outflow'];
      if((!etfIn || !etfIn.dates || !etfIn.dates.length) && (!etfOut || !etfOut.dates || !etfOut.dates.length)){
        body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>'; return;
      }
      function renderEtfBoth(n){
        var html2 = histRangeBtns(n);
        function renderEtfTable(indData, title, color, bgType){
          if(!indData || !indData.dates || !indData.dates.length) return '';
          var dts = indData.dates.slice(-n);
          var off = indData.dates.length - dts.length;
          var nms = indData.names.map(function(row){ return row.slice(off); });
          var vls = indData.values.map(function(row){ return row.slice(off); });
          return '<h5 style="margin:8px 0 4px;color:'+color+'">'+title+'</h5>' +
            renderRankTable(nms, vls, dts, 0, indData.top_n || 10, bgType,
              function(v){return v!==null&&v!==undefined?(v>0?'+':'')+v.toFixed(2)+'亿份':'';});
        }
        html2 += renderEtfTable(etfIn, 'ETF 净申购 TOP10（本周净申赎·亿份）', '#d8392b', 'high');
        html2 += renderEtfTable(etfOut, 'ETF 净赎回 TOP10（本周净申赎·亿份）', '#16a34a', 'low');
        body.innerHTML = html2;
        alignHistTables(body);
        body.querySelectorAll('.hist-range-btn').forEach(function(btn){
          btn.addEventListener('click',function(){ renderEtfBoth(parseInt(this.dataset.range)); });
        });
      }
      renderEtfBoth(20);
      return;
    } else if(mod==='ind_score_both'){
      // 强势/弱势行业得分合并展示
      var strongData = (D.hist_industry || {})['score_strong'];
      var weakData = (D.hist_industry || {})['score_weak'];
      if((!strongData || !strongData.dates || !strongData.dates.length) && (!weakData || !weakData.dates || !weakData.dates.length)){
        body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>'; return;
      }
      function renderScoreBoth(n){
        var html2 = histRangeBtns(n);
        function renderIndTable(indData, title, color, bgType){
          if(!indData || !indData.dates || !indData.dates.length) return '';
          var dts = indData.dates.slice(-n);
          var off = indData.dates.length - dts.length;
          var nms = indData.names.map(function(row){ return row.slice(off); });
          var vls = indData.values.map(function(row){ return row.slice(off); });
          return '<h5 style="margin:8px 0 4px;color:'+color+'">'+title+'</h5>' +
            renderRankTable(nms, vls, dts, 0, indData.top_n || 10, bgType,
              function(v){return v!==null&&v!==undefined?v+'分':'';});
        }
        html2 += renderIndTable(strongData, '强势行业得分', '#d8392b', 'high');
        html2 += renderIndTable(weakData, '弱势行业得分', '#16a34a', 'low');
        body.innerHTML = html2;
        alignHistTables(body);
        body.querySelectorAll('.hist-range-btn').forEach(function(btn){
          btn.addEventListener('click',function(){ renderScoreBoth(parseInt(this.dataset.range)); });
        });
      }
      renderScoreBoth(20);
      return;
    } else if(mod.indexOf('ind_')===0){
      // 行业分布历史趋势表
      var indMod = mod.replace('ind_','');
      var indData = (D.hist_industry || {})[indMod];
      if(!indData || !indData.dates || !indData.dates.length){
        body.innerHTML='<p class="miss">暂无历史数据（采集累积中）</p>';
        return;
      }
      function renderInd(n){
        var dates2 = indData.dates.slice(-n);
        var offset2 = indData.dates.length - dates2.length;
        // 新数据结构：names[i][j] 和 values[i][j] 已是 行(排名)x列(日期) 格式
        var names2 = indData.names.map(function(row){ return row.slice(offset2); });
        var values2 = indData.values.map(function(row){ return row.slice(offset2); });
        var html2 = histRangeBtns(n);
        html2 += renderRankTable(names2, values2, dates2, 0, indData.top_n || 10, 'turnover',
          function(v){return v!==null&&v!==undefined?v+'只':'';});
        body.innerHTML = html2;
        alignHistTables(body);
        body.querySelectorAll('.hist-range-btn').forEach(function(btn){
          btn.addEventListener('click',function(){ renderInd(parseInt(this.dataset.range)); });
        });
      }
      renderInd(20);
      return;
    }
    body.innerHTML = html;
    alignHistTables(body);
    body.querySelectorAll('.hist-range-btn').forEach(function(btn){
      btn.addEventListener('click',function(){ render(parseInt(this.dataset.range)); });
    });
  }
  render(20);
}
function alignHistTables(body){
  var tables = body.querySelectorAll('.hist-table');
  if(tables.length < 2) return;
  setTimeout(function(){
    // 先清除所有固定宽度，让浏览器自然布局
    tables.forEach(function(t){
      t.style.tableLayout = 'auto';
      t.style.width = 'auto';
      var cells = t.querySelectorAll('th, td');
      cells.forEach(function(c){ c.style.width=''; c.style.minWidth=''; c.style.maxWidth=''; });
    });
    // 测量每一列的最大宽度
    var maxCols = 0;
    tables.forEach(function(t){ var c=t.querySelectorAll('thead th').length; if(c>maxCols) maxCols=c; });
    var colW = [];
    for(var i=0;i<maxCols;i++) colW.push(0);
    tables.forEach(function(t){
      var ths = t.querySelectorAll('thead th');
      for(var i=0;i<ths.length;i++){ var w=ths[i].offsetWidth; if(w>colW[i]) colW[i]=w; }
    });
    // 统一设置每一列宽度（用colgroup确保整列一致）
    tables.forEach(function(t){
      var cols = t.querySelectorAll('colgroup col');
      if(cols.length === 0){
        // 没有colgroup则用th设置
        var ths = t.querySelectorAll('thead th');
        for(var i=0;i<ths.length;i++){ if(colW[i]>0){ ths[i].style.width=colW[i]+'px'; ths[i].style.minWidth=colW[i]+'px'; } }
      } else {
        for(var i=0;i<cols.length && i<colW.length;i++){ if(colW[i]>0) cols[i].style.width=colW[i]+'px'; }
        t.style.tableLayout='fixed';
      }
    });
  }, 20);
}
function toggleHistHighlight(cell){
  var body=cell.closest('.hist-body');
  var name=cell.dataset.name;
  var already=cell.classList.contains('hist-highlight');
  body.querySelectorAll('.hist-highlight').forEach(function(c){c.classList.remove('hist-highlight');});
  if(!already){
    body.querySelectorAll('.hist-cell[data-name="'+name.replace(/"/g,'\"')+'"]').forEach(function(c){c.classList.add('hist-highlight');});
  }
}
// 非当日数据：在标记的元素（表格/图表/卡片）上显示红色感叹号，hover 显示数据截至日期
// 非交易日（周末）：A股不开盘，数据本就该截止到最近交易日，不标红
function markStale(elm, date){
  if(!elm) return;
  // 周末为非交易日，没有更新的数据可得，一律不标红（交易日由数据自然决定是否过期）
  var dow = new Date().getDay();
  if(dow === 0 || dow === 6) return;
  var host = (elm.tagName==='CANVAS') ? elm.parentElement : elm;
  if(!host) return;
  if(getComputedStyle(host).position==='static') host.style.position='relative';
  var b=document.createElement('span');
  b.className='stale-badge';
  b.setAttribute('data-tip','当前数据截至 '+date);
  b.textContent='!';
  host.appendChild(b);
}
document.querySelectorAll('[data-stale]').forEach(function(box){
  var date=box.getAttribute('data-stale');
  if(box.classList.contains('card') || box.classList.contains('section')){
    // 子元素自身带 data-stale（如融资/均线占比/TR/平均股价等独立数据源）时以其自身日期为准，不重复打卡片日期
    box.querySelectorAll('table,canvas').forEach(function(c){ if(c.hasAttribute('data-stale'))return; markStale(c, date); });
  } else {
    markStale(box, date);
  }
});
// 数据截止时间戳：在每个数据块（表格/图表）右下角标注「数据截至 YYYY-MM-DD HH:MM」
// 若 data-cutoff 在卡片上，则遍历卡片内所有 table/canvas，在每个数据块上单独标注
function addCutoffBadge(elm, dateStr){
  if(!elm || !elm.parentNode) return;
  // 标签放在数据块（表格/图表）上方右侧，不叠在表头里
  var b=document.createElement('div');
  b.className='cutoff-badge';
  b.textContent='数据截至 '+dateStr;
  elm.parentNode.insertBefore(b, elm);
}
document.querySelectorAll('[data-cutoff]').forEach(function(box){
  var dateStr = box.getAttribute('data-cutoff');
  if(box.classList.contains('card') || box.classList.contains('section')){
    box.querySelectorAll('table,canvas').forEach(function(c){
      // 子元素有独立 data-stale（如均线占比/TR/融资/平均股价等）时，用其自身数据日期，不用卡片统一日期
      var d = c.hasAttribute('data-stale') ? c.getAttribute('data-stale') : dateStr;
      addCutoffBadge(c, d);
    });
  } else {
    addCutoffBadge(box, dateStr);
  }
});
