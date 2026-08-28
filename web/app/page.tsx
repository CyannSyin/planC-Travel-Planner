'use client';

import { CSSProperties, FormEvent, useMemo, useState } from 'react';

type ChatItem = { role:'user'|'assistant'; text:string; error?:boolean };
type Intent = {
  city:string|null; num_days:number|null; preferences:string|null; budget:string|null;
  interests:string[]; max_daily_hours:number; start_time:string;
};
type Visit = {
  poi_id:string; name:string; category:string; lat:number; lon:number; rating:number;
  arrival_time:string; departure_time:string; visit_minutes:number;
  travel_from_previous_km:number; travel_from_previous_minutes:number;
};
type DayPlan = {
  day:number; visits:Visit[]; route_length_km:number; visit_minutes:number;
  travel_minutes:number; total_minutes:number; skipped_poi_ids:string[];
};
type TripPlan = {
  plan_id:string; city:string; num_days:number; days:DayPlan[]; total_pois:number;
  total_route_length_km:number; total_minutes:number; created_at:string;
};
type ChatResponse = {
  session_id:string;
  turn:{ status:'needs_input'|'planned'; message:string; intent:Intent; plan:TripPlan|null };
};

const dayColors = ['#f26b4f','#168e9d','#528562','#8066aa','#c28b30','#3972a4','#a45472'];
const suggestions = ['每天十点再出发','少安排一点博物馆','把节奏调轻松一些'];
const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/,'');

function minutesLabel(minutes:number) {
  const rounded = Math.round(minutes);
  const hours = Math.floor(rounded/60);
  const rest = rounded%60;
  if (!hours) return `${rest} 分钟`;
  return rest ? `${hours} 小时 ${rest} 分` : `${hours} 小时`;
}

function categoryLabel(category:string) {
  const value = category.includes('=') ? category.split('=').at(-1) ?? category : category;
  return value.replaceAll('_',' ');
}

function positionedVisits(visits:Visit[]) {
  if (!visits.length) return [];
  const lats = visits.map((visit)=>visit.lat);
  const lons = visits.map((visit)=>visit.lon);
  const latMin = Math.min(...lats); const latMax = Math.max(...lats);
  const lonMin = Math.min(...lons); const lonMax = Math.max(...lons);
  return visits.map((visit,index)=>({
    ...visit,
    x: lonMax===lonMin ? 50+(index-(visits.length-1)/2)*12 : 18+((visit.lon-lonMin)/(lonMax-lonMin))*64,
    y: latMax===latMin ? 50+(index-(visits.length-1)/2)*10 : 78-((visit.lat-latMin)/(latMax-latMin))*56,
  }));
}

export default function Home() {
  const [mode,setMode] = useState<'home'|'plan'>('home');
  const [activeDay,setActiveDay] = useState(1);
  const [activeStop,setActiveStop] = useState('');
  const [message,setMessage] = useState('');
  const [draft,setDraft] = useState('');
  const [chat,setChat] = useState<ChatItem[]>([]);
  const [plan,setPlan] = useState<TripPlan|null>(null);
  const [intent,setIntent] = useState<Intent|null>(null);
  const [sessionId,setSessionId] = useState<string|null>(null);
  const [loading,setLoading] = useState(false);

  const currentDay = plan?.days.find((day)=>day.day===activeDay) ?? null;
  const visibleStops = useMemo(()=>positionedVisits(currentDay?.visits ?? []),[currentDay]);
  const routeSegments = visibleStops.slice(1).map((stop,index)=>{
    const previous = visibleStops[index];
    const dx = stop.x-previous.x;
    const dy = stop.y-previous.y;
    return {left:previous.x,top:previous.y,width:Math.hypot(dx,dy),angle:Math.atan2(dy,dx)*180/Math.PI};
  });
  const dayColor = dayColors[(activeDay-1)%dayColors.length];

  async function submitMessage(rawMessage:string) {
    const value=rawMessage.trim();
    if(!value || loading) return;
    setMode('plan');
    setLoading(true);
    setChat((current)=>[...current,{role:'user',text:value}]);
    setMessage('');
    try {
      const response = await fetch(`${API_BASE}/api/chat`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({message:value,session_id:sessionId}),
      });
      const payload = await response.json().catch(()=>null) as ChatResponse|{detail?:string}|null;
      if(!response.ok) throw new Error(payload && 'detail' in payload ? payload.detail : '后端暂时没有响应');
      const result = payload as ChatResponse;
      setSessionId(result.session_id);
      setIntent(result.turn.intent);
      setChat((current)=>[...current,{role:'assistant',text:result.turn.message}]);
      if(result.turn.plan){
        setPlan(result.turn.plan);
        const firstDay=result.turn.plan.days[0];
        setActiveDay(firstDay?.day ?? 1);
        setActiveStop(firstDay?.visits[0]?.poi_id ?? '');
      }
    } catch(error) {
      const detail = error instanceof Error ? error.message : '未知错误';
      setChat((current)=>[...current,{role:'assistant',error:true,text:`暂时无法生成行程：${detail}`}]);
    } finally {
      setLoading(false);
    }
  }

  function beginPlan(event:FormEvent) {
    event.preventDefault();
    void submitMessage(draft);
  }

  function sendMessage(text=message) {
    void submitMessage(text);
  }

  function startNewTrip() {
    if(sessionId) void fetch(`${API_BASE}/api/reset`,{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId}),
    }).catch(()=>undefined);
    setMode('home'); setPlan(null); setIntent(null); setSessionId(null); setChat([]);
    setDraft(''); setMessage(''); setActiveDay(1); setActiveStop('');
  }

  function exportPlan() {
    if(!plan) return;
    const blob = new Blob([JSON.stringify(plan,null,2)],{type:'application/json'});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href=url; anchor.download=`${plan.city}-${plan.num_days}日行程.json`; anchor.click();
    URL.revokeObjectURL(url);
  }

  const chips = intent ? [
    intent.city,
    intent.num_days ? `${intent.num_days} 天` : null,
    ...intent.interests,
    intent.preferences,
    intent.budget,
    `${intent.start_time} 出发`,
  ].filter((item):item is string=>Boolean(item)) : [];

  if(mode==='home') return <main className="home-shell">
    <header className="home-nav"><Brand onClick={()=>undefined}/><div className="nav-actions"><button className="text-button">我的行程</button><button className="avatar">NW</button></div></header>
    <section className="hero">
      <div className="hero-kicker"><span>✦</span> AI 原生旅行规划</div>
      <h1>说说你想怎么旅行，<br/><em>剩下的交给 PlanC。</em></h1>
      <p>从一句话到每天的路线、时间和地点安排。想改计划，继续说就好。</p>
      <form className="hero-prompt" onSubmit={beginPlan}>
        <textarea value={draft} onChange={(e)=>setDraft(e.target.value)} placeholder="例如：去广州玩四天，喜欢历史和美食，每天不要超过六小时……" aria-label="描述旅行需求" disabled={loading}/>
        <div className="prompt-footer"><span>{loading?'正在理解需求并规划路线…':'支持连续对话修改'}</span><button type="submit" disabled={loading||!draft.trim()}>{loading?'规划中…':'开始规划'} <b>↗</b></button></div>
      </form>
      <div className="examples"><span>试试看</span><button onClick={()=>setDraft('上海周末两日游，不要太赶')}>上海周末两日游</button><button onClick={()=>setDraft('带父母去成都，每天十点后出发')}>带父母去成都</button><button onClick={()=>setDraft('东京五天，预算有限，少走路')}>东京预算之旅</button></div>
    </section><div className="home-orbit orbit-one"/><div className="home-orbit orbit-two"/>
  </main>;

  return <main className="app-shell">
    <header className="topbar"><Brand onClick={startNewTrip}/><div className="trip-heading"><span className="trip-city">{plan?.city ?? intent?.city ?? '新行程'}</span><span className="trip-meta">{plan?`${plan.num_days} 天 · ${plan.total_pois} 个地点`:'补充需求后生成路线'}</span>{plan&&<span className="saved"><i/> 已保存</span>}</div><div className="top-actions"><button className="icon-button" aria-label="更多选项">•••</button><button className="secondary-button">分享</button><button className="primary-button" onClick={exportPlan} disabled={!plan}>导出行程</button></div></header>
    <section className="workspace">
      <aside className="chat-panel">
        <div className="panel-heading"><div><span className="eyebrow">PLAN WITH AI</span><h2>和 PlanC 一起规划</h2></div><button className="new-trip" onClick={startNewTrip}><span>＋</span> 新行程</button></div>
        <div className="constraint-card"><div className="constraint-title"><span>✦</span> {chips.length?'已理解你的旅行':'告诉我目的地和旅行天数'}</div><div className="chips">{chips.length?chips.map((chip,index)=><span key={`${chip}-${index}`}>{chip}</span>):<span>等待旅行需求</span>}</div></div>
        <div className="chat-scroll">{chat.map((item,index)=><div className={`chat-row ${item.role} ${item.error?'error':''}`} key={`${item.role}-${index}`}>
          {item.role==='assistant'&&<div className="mini-logo">C</div>}<div className="bubble">{item.text}</div>
        </div>)}{loading&&<div className="chat-row assistant"><div className="mini-logo">C</div><div className="bubble planning">正在检索地点并规划路线<span>…</span></div></div>}</div>
        <div className="suggestions">{suggestions.map((item)=><button key={item} disabled={loading} onClick={()=>sendMessage(item)}>{item}</button>)}</div>
        <form className="chat-input" onSubmit={(event)=>{event.preventDefault();sendMessage();}}><textarea value={message} onChange={(e)=>setMessage(e.target.value)} placeholder="告诉我你想怎么调整……" aria-label="调整行程" disabled={loading}/><div><span>{loading?'规划中…':'⌘ ↵ 发送'}</span><button type="submit" aria-label="发送消息" disabled={loading||!message.trim()}>↑</button></div></form>
      </aside>
      <section className="map-panel" aria-label="行程地图">
        <div className="map-grid"/><div className="river river-a"/><div className="river river-b"/><div className="park park-a">城市绿地</div><div className="park park-b">旅行区域</div><span className="map-label label-a">CITY</span><span className="map-label label-b">PLANC</span><span className="map-label label-c">ROUTE</span>
        {routeSegments.map((segment,index)=><div key={`route-${index}`} className="route-line" style={{left:`${segment.left}%`,top:`${segment.top}%`,width:`${segment.width}%`,transform:`rotate(${segment.angle}deg)`,background:dayColor}}/>)}
        {visibleStops.map((stop,index)=><button key={stop.poi_id} className={`map-pin ${activeStop===stop.poi_id?'active':''}`} style={{left:`${stop.x}%`,top:`${stop.y}%`,'--pin':dayColor} as CSSProperties} onClick={()=>setActiveStop(stop.poi_id)} aria-label={`${stop.name}，第 ${index+1} 站`}><span>{index+1}</span><em>{stop.name}</em></button>)}
        {!plan&&<div className="map-empty"><span>⌁</span><b>等待生成路线</b><small>继续对话补全目的地和旅行天数</small></div>}
        <div className="map-controls"><button aria-label="放大">＋</button><button aria-label="缩小">−</button></div><div className="map-legend"><span className="legend-dot" style={{background:dayColor}}/> Day {activeDay} 路线 <i/> 约 {currentDay?.route_length_km.toFixed(1) ?? '0.0'} km</div><div className="estimate-note">⌁ 交通时间按步行速度估算</div>
      </section>
      <aside className="itinerary-panel">
        <div className="itinerary-head"><div><span className="eyebrow">YOUR ITINERARY</span><h2>{plan?`${plan.num_days} 日行程`:'行程待生成'}</h2></div><button className="icon-button" aria-label="行程设置">⚙</button></div>
        <div className="day-tabs" role="tablist" style={{gridTemplateColumns:`repeat(${Math.min(plan?.days.length ?? 1,7)},1fr)`}}>{plan?.days.map((day)=><button key={day.day} className={activeDay===day.day?'active':''} style={{'--day-color':dayColors[(day.day-1)%dayColors.length]} as CSSProperties} onClick={()=>{setActiveDay(day.day);setActiveStop(day.visits[0]?.poi_id ?? '');}}><b>Day {day.day}</b><span>{day.visits[0]?categoryLabel(day.visits[0].category):'待安排'}</span></button>)}</div>
        <div className="day-summary"><div><b>{currentDay?.visits.length?`${currentDay.visits[0].arrival_time} — ${currentDay.visits.at(-1)?.departure_time}`:'等待规划'}</b><span>{currentDay?`${currentDay.visits.length} 个地点 · 约 ${minutesLabel(currentDay.total_minutes)}`:'行程会显示在这里'}</span></div><span className="weather">⌁ {currentDay?.route_length_km.toFixed(1) ?? '0.0'} km</span></div>
        <div className="timeline">{currentDay?.visits.length?currentDay.visits.map((stop,index)=><article key={stop.poi_id} className={`stop-card ${activeStop===stop.poi_id?'selected':''}`} onClick={()=>setActiveStop(stop.poi_id)} style={{'--day-color':dayColor} as CSSProperties}><div className="time-col"><b>{stop.arrival_time}</b><span>{stop.departure_time}</span></div><div className="timeline-mark"><i>{index+1}</i></div><div className="stop-content"><div className="stop-top"><div><span className="stop-type">{categoryLabel(stop.category)}</span><h3>{stop.name}</h3></div><button aria-label="地点选项">•••</button></div><div className="stop-stats"><span>★ {stop.rating.toFixed(1)}</span><span>◷ {minutesLabel(stop.visit_minutes)}</span></div><div className="travel-note">{index===0?'旅程起点':`步行 ${stop.travel_from_previous_km.toFixed(1)} km · ${Math.round(stop.travel_from_previous_minutes)} 分钟`}</div></div></article>):<div className="empty-day"><span>✦</span><h3>{loading?'正在生成你的行程':'这一天还在路上'}</h3><p>{loading?'地点、时间与路线很快就好。':'继续和 PlanC 对话，完善当天安排。'}</p></div>}</div>
        <div className="itinerary-footer"><span>路线与时间均为估算值</span><button>未安排地点 <b>{currentDay?.skipped_poi_ids.length ?? 0}</b></button></div>
      </aside>
    </section>
  </main>;
}

function Brand({onClick}:{onClick:()=>void}){return <button className="brand" aria-label="PlanC 首页" onClick={onClick}><span className="brand-mark"><i/><i/><i/></span><span>Plan<span>C</span></span></button>}
