
function saSet(t,m){document.querySelectorAll('.ctrl-status').forEach(function(e){e.textContent=m||'';e.className='ctrl-status '+(t||'')})}
function lastTradingDate(){
  var d=new Date();var dow=d.getDay();
  if(dow===0) d.setDate(d.getDate()-2);      /* Sun → Fri */
  else if(dow===6) d.setDate(d.getDate()-1);  /* Sat → Fri */
  var off=d.getTimezoneOffset()*60000;
  return new Date(d.getTime()-off).toISOString().slice(0,10);
}
function saTrigger(cmd, el, opts){
  opts=opts||{};
  var btns = el ? [el] : document.querySelectorAll('.re-btn');
  btns.forEach(function(b){b.disabled=true});
  saSet('busy','正在提交…');
  var tries=0;
  function done(ok,msg){saSet(ok?'ok':'err',msg);btns.forEach(function(b){b.disabled=false})}
  function attempt(){
    tries++;
    var url=location.origin+'/api/trigger?cmd='+encodeURIComponent(cmd);
    if(cmd==='reextract') url+='&type='+encodeURIComponent(PAGE_MODE);
    if(opts.date) url+='&date='+encodeURIComponent(opts.date);
    fetch(url,{method:'POST'})
      .then(function(r){return r.json()})
      .then(function(d){
        var label=(cmd==='tdx'?'通达信量化 Task1-5':'重新抽数'+(opts.date?'（'+opts.date+'）':''));
        if(d&&d.ok) done(true,'✅ 已提交：'+label+'。完成后邮件通知 hao.liao01@qq.com');
        else if(tries<3) setTimeout(attempt,800);
        else done(false,'❌ 提交失败：'+(d&&d.error||'未知错误，请稍后重试'));
      })
      .catch(function(e){ if(tries<3) setTimeout(attempt,800); else done(false,'❌ 网络错误：'+e.message) });
  }
  attempt();
}
function localToday(){var d=new Date();var off=d.getTimezoneOffset()*60000;return new Date(d.getTime()-off).toISOString().slice(0,10)}
function copyAndOpenDoubao(el,text){
  function done(){
    var orig=el.innerHTML;
    el.innerHTML='✅ 已复制，正在打开豆包…';
    el.disabled=true;
    setTimeout(function(){ window.location.href='doubao://'; }, 300);
    setTimeout(function(){ el.innerHTML=orig; el.disabled=false; }, 2500);
  }
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(done).catch(function(){ fallbackCopy(text,done); });
  } else { fallbackCopy(text,done); }
}
function fallbackCopy(text,cb){
  var ta=document.createElement('textarea');
  ta.value=text;ta.style.position='fixed';ta.style.opacity='0';
  document.body.appendChild(ta);ta.select();
  try{document.execCommand('copy');}catch(e){}
  document.body.removeChild(ta);cb();
}

function renderLight(d){
  var box=document.getElementById('saLight'),dot=document.getElementById('saDot'),txt=document.getElementById('saTxt');
  if(!box||!dot||!txt) return;
  function set(cls,text,title){box.className='sa-light '+(cls||'off');txt.textContent=text;if(title)box.title=title;else box.removeAttribute('title')}
  // 静态部署页：隧道未运行时显示快照就绪，避免被误解为数据离线
  var pageDate=(typeof REPORT_DATE!=='undefined'?REPORT_DATE:'')||'';
  var pageMode=(typeof PAGE_MODE!=='undefined'?PAGE_MODE:'')||'';
  var cutoffText=pageDate+(pageMode==='midday'?' 11:30':(pageMode==='close'?' 15:00':''));
  if(!d||!d.ok){set('ok','快照已就绪','数据截止：'+cutoffText+'；实时抽数服务未连接');return}
  var st=d.state,last=d.last;
  if(st==='running'){
    var rn=d.running||{},src=rn.note||'';
    var label=(rn.cmd==='tdx')?'通达信刷新':(rn.cmd==='external'?'定时自动化':'抽数');
    set('running',label+'进行中'+(src?'（'+src+'）':''),'开始于 '+(rn.started||'?'));
  }else if(st==='done_ok'){
    var warns=(last&&last.warns||[]);
    var title='最近完成：'+(last&&last.finished||'?')+'（耗时 '+(last&&last.elapsed_s!=null?last.elapsed_s+'s':'?')+'）'+(warns.length?'\n提示：'+warns.join('；'):'');
    set('ok','抽数成功',title);
  }else if(st==='done_error'){
    var issues=(last&&last.issues||[]),err=last&&last.error||'';
    var isQ=issues.length>0&&!(last&&last.rc);
    var msg=isQ?'完成但有缺口':'抽数失败';
    var title='最近完成：'+(last&&last.finished||'?');
    if((last&&last.rc)!=null)title+='（rc='+last.rc+'，耗时 '+(last&&last.elapsed_s!=null?last.elapsed_s+'s':'?')+'）';
    if(issues.length)title+='\n缺口：'+issues.join('；');
    if(err)title+='\n错误：'+err;
    set('err',msg,title);
  }else{
    set('off','待机','暂无抽数记录');
  }
}
function pollStatus(){
  fetch(location.origin+'/api/status?ts='+Date.now())
    .then(function(r){return r.json()})
    .then(function(d){renderLight(d)})
    .catch(function(){renderLight(null)})
    .then(function(){setTimeout(pollStatus,30000)});
}
pollStatus();

/* ---- hover 迷你K线弹窗 ---- */
var saTip=null,saTimer=null,saCurReq=0;
function initSaHover(){
  if(saTip)return;
  saTip=document.createElement('div');saTip.id='saKlineTip';
  var lbl=document.createElement('div');lbl.id='saKlineLbl';
  var cv=document.createElement('canvas');cv.id='saKlineCv';
  var ft=document.createElement('div');ft.id='saKlineFoot';
  saTip.appendChild(lbl);saTip.appendChild(cv);saTip.appendChild(ft);
  document.body.appendChild(saTip);
  document.querySelectorAll('.sa-hover').forEach(function(td){
    td.addEventListener('mouseenter',function(e){clearTimeout(saTimer);saTimer=setTimeout(function(){showKlineTip(td,e)},300)});
    td.addEventListener('mouseleave',function(){clearTimeout(saTimer);hideKlineTip()});
    td.addEventListener('mousemove',function(e){posTip(e)});
  });
}
function showKlineTip(td,e){
  var code=td.getAttribute('data-code')||'';
  var mkt=td.getAttribute('data-mkt')||'';
  var isSector=td.getAttribute('data-sector')==='1';
  var histKey=td.getAttribute('data-hist-key')||'';
  var name=td.textContent.trim();
  var lbl=document.getElementById('saKlineLbl');
  lbl.textContent=name+' 加载中…';
  posTip(e);saTip.style.display='block';
  /* 优先用页面已嵌入的历史数据（指数、板块） */
  if(histKey){
    var found=null;
    if(histKey.indexOf('sec:')===0){
      var sc=histKey.slice(4);
      (D.rps&&D.rps.passed||[]).forEach(function(x){if(x.code===sc)found=x});
      if(!found&&(D.top_sectors||[]))D.top_sectors.forEach(function(x){if((x.code||'').replace('URFI','')===sc)found=x});
      if(!found&&D.net_inflow_sectors){
        var ni=D.net_inflow_sectors;
        (ni.top||[]).forEach(function(x){if((x.code||'').replace('URFI','')===sc)found=x});
        if(!found)(ni.bottom||[]).forEach(function(x){if((x.code||'').replace('URFI','')===sc)found=x});
      }
      if(!found&&D.pct_sectors){
        var ps=D.pct_sectors;
        (ps.top||[]).forEach(function(x){if((x.code||'').replace('URFI','')===sc)found=x});
        if(!found)(ps.bottom||[]).forEach(function(x){if((x.code||'').replace('URFI','')===sc)found=x});
      }
      if(!found&&D.mainline_kline&&D.mainline_kline[sc]){var _mk=D.mainline_kline[sc];found={hist_dates:_mk.dates,hist_close:_mk.close};}
    }else{
      (D.indices||[]).forEach(function(x){if(x.code===histKey)found=x});
      if(!found&&(D.style_indices||[]))D.style_indices.forEach(function(x){if(x.code===histKey)found=x});
    }
    if(found&&found.hist_dates&&found.hist_close){
      drawMiniKline(found.hist_dates,found.hist_close,null,null,null,name,'页面嵌入数据');
      return;
    }
  }
  /* 否则 fetch API */
  var myReq=++saCurReq;
  var url=location.origin+'/api/kline?lmt=150';
  if(isSector){url+='&secid='+encodeURIComponent(code)}
  else{url+='&code='+encodeURIComponent(code);if(mkt)url+='&mkt='+mkt}
  fetch(url).then(function(r){return r.json()}).then(function(d){
    if(myReq!==saCurReq)return;
    if(!d.ok){lbl.textContent=name+'：'+(d.error||'获取失败');return}
    drawMiniKline(d.dates,d.close,d.open,d.high,d.low,name,d.name||'');
  }).catch(function(){if(myReq===saCurReq)lbl.textContent=name+'：网络错误'});
}
function drawMiniKline(dates,close,open,high,low,name,foot){
  var cv=document.getElementById('saKlineCv');
  var lbl=document.getElementById('saKlineLbl');
  var ft=document.getElementById('saKlineFoot');
  lbl.textContent=name;
  var n=dates.length;if(!n){lbl.textContent=name+'：无K线数据';return}
  var dpr=window.devicePixelRatio||1;
  var w=cv.clientWidth||360,h=cv.clientHeight||230;
  cv.width=w*dpr;cv.height=h*dpr;
  var ctx=cv.getContext('2d');ctx.scale(dpr,dpr);
  ctx.clearRect(0,0,w,h);
  /* 计算价格范围 */
  var hasOHLC=open&&open.length===n;
  var mn=Infinity,mx=-Infinity;
  for(var i=0;i<n;i++){
    var lo=hasOHLC?Math.min(open[i],close[i],high[i],low[i]):close[i];
    var hi=hasOHLC?Math.max(open[i],close[i],high[i],low[i]):close[i];
    if(lo<mn)mn=lo;if(hi>mx)mx=hi;
  }
  if(mn===mx){mn-=1;mx+=1}
  var rng=mx-mn;mn-=rng*0.08;mx+=rng*0.08;
  var pad=12,pw=w-pad*2,ph=h-pad*2;
  var cw=hasOHLC?Math.max(2,(n>1?pw/(n-1):0)*0.55):0;
  var x0=pad+cw/2,xEnd=w-pad-cw/2;
  var xStep=n>1?(xEnd-x0)/(n-1):0;
  var yOf=function(v){return pad+ph-(v-mn)/(mx-mn)*ph};
  /* 网格线 */
  ctx.strokeStyle='#f0f0f0';ctx.lineWidth=1;
  for(var g=0;g<=4;g++){var y=pad+g*ph/4;ctx.beginPath();ctx.moveTo(x0,y);ctx.lineTo(x0+pw,y);ctx.stroke()}
  /* K线或折线 */
  var RED='#d8392b',GREEN='#16a34a';
  if(hasOHLC){
    for(var i=0;i<n;i++){
      var x=x0+i*xStep;
      var yO=yOf(open[i]),yC=yOf(close[i]),yH=yOf(high[i]),yL=yOf(low[i]);
      var up=close[i]>=open[i];
      ctx.strokeStyle=up?RED:GREEN;ctx.fillStyle=up?RED:GREEN;
      ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,yH);ctx.lineTo(x,yL);ctx.stroke();
      var top=Math.min(yO,yC),bh=Math.max(1,Math.abs(yC-yO));
      ctx.fillRect(x-cw/2,top,cw,bh);
    }
  }else{
    ctx.strokeStyle='#2b6cb0';ctx.lineWidth=1.5;ctx.beginPath();
    for(var i=0;i<n;i++){var x=x0+i*xStep,y=yOf(close[i]);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)}
    ctx.stroke();
  }
  /* 末点标签 */
  var lastV=close[n-1];
  ctx.fillStyle='#1f2329';ctx.font='9px sans-serif';ctx.textAlign='right';
  ctx.fillText(lastV.toFixed(2),w-pad,pad+14);
  ctx.textAlign='left';
  ctx.fillText(dates[0],pad,h-pad-4);
  ctx.textAlign='right';ctx.fillText(dates[n-1],w-pad,h-pad-4);
  ft.textContent=foot||('近'+n+'个交易日');
}
function posTip(e){
  if(!saTip)return;
  var tw=420,th=340,off=14;
  var x=e.clientX+off,y=e.clientY-th-18;
  if(x+tw>window.innerWidth)x=e.clientX-tw-off;
  if(x<4)x=4;if(y<4)y=4;if(y+th>window.innerHeight)y=window.innerHeight-th-4;
  saTip.style.left=x+'px';saTip.style.top=y+'px';
}
function hideKlineTip(){if(saTip)saTip.style.display='none'}
if(document.readyState!=='loading')initSaHover();
else document.addEventListener('DOMContentLoaded',initSaHover);
