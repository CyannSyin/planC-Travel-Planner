'use client';

import { FormEvent, useMemo, useState } from 'react';

type Stop = { id:number; day:number; time:string; end:string; name:string; type:string; rating:string; duration:string; travel:string; x:number; y:number };

const days = [
  { day:1, label:'老城漫游', color:'#f26b4f' },
  { day:2, label:'城市地标', color:'#168e9d' },
  { day:3, label:'岭南园林', color:'#528562' },
  { day:4, label:'松弛食光', color:'#8066aa' },
];

const stops: Stop[] = [
  { id:1, day:1, time:'10:00', end:'11:40', name:'陈家祠', type:'历史建筑', rating:'4.7', duration:'1小时40分', travel:'旅程起点', x:22, y:59 },
  { id:2, day:1, time:'12:05', end:'13:25', name:'西关老街', type:'街区漫步', rating:'4.6', duration:'1小时20分', travel:'步行 1.6 km · 24分钟', x:39, y:45 },
  { id:3, day:1, time:'13:40', end:'15:10', name:'泮溪酒家', type:'粤菜', rating:'4.5', duration:'1小时30分', travel:'步行 0.9 km · 14分钟', x:53, y:58 },
  { id:4, day:1, time:'15:35', end:'17:15', name:'沙面岛', type:'城市漫步', rating:'4.7', duration:'1小时40分', travel:'步行 1.7 km · 25分钟', x:69, y:36 },
  { id:5, day:2, time:'10:00', end:'12:00', name:'广东省博物馆', type:'博物馆', rating:'4.7', duration:'2小时', travel:'旅程起点', x:77, y:66 },
  { id:6, day:2, time:'12:25', end:'14:00', name:'花城广场', type:'城市地标', rating:'4.6', duration:'1小时35分', travel:'步行 1.4 km · 21分钟', x:64, y:72 },
];

const suggestions = ['每天十点再出发','少安排一点博物馆','把节奏调轻松一些'];

export default function Home() {
  const [mode,setMode] = useState<'home'|'plan'>('plan');
  const [activeDay,setActiveDay] = useState(1);
  const [activeStop,setActiveStop] = useState(1);
  const [message,setMessage] = useState('');
  const [draft,setDraft] = useState('');
  const [chat,setChat] = useState([
    { role:'user', text:'去广州玩四天，喜欢历史和美食，每天不要超过六小时。' },
    { role:'assistant', text:'明白了。我安排了一份从老城人文到城市地标的四日行程，每天约 5–6 小时，留出充足的休息和吃饭时间。' },
  ]);
  const visibleStops = useMemo(() => stops.filter((stop) => stop.day === activeDay),[activeDay]);
  const dayColor = days[activeDay-1].color;

  function beginPlan(event:FormEvent) {
    event.preventDefault();
    if (draft.trim()) setChat([{role:'user',text:draft.trim()},{role:'assistant',text:'收到。我先为你生成一份节奏舒适、动线紧凑的四日行程，你可以随时继续修改。'}]);
    setMode('plan');
  }
  function sendMessage(text=message) {
    const value=text.trim(); if(!value) return;
    setChat((current)=>[...current,{role:'user',text:value},{role:'assistant',text:'已记下这个调整。我会保留现有偏好，并重新平衡每天的地点与时间。'}]); setMessage('');
  }

  if(mode==='home') return <main className="home-shell">
    <header className="home-nav"><Brand/><div className="nav-actions"><button className="text-button">我的行程</button><button className="avatar">NW</button></div></header>
    <section className="hero">
      <div className="hero-kicker"><span>✦</span> AI 原生旅行规划</div>
      <h1>说说你想怎么旅行，<br/><em>剩下的交给 PlanC。</em></h1>
      <p>从一句话到每天的路线、时间和地点安排。想改计划，继续说就好。</p>
      <form className="hero-prompt" onSubmit={beginPlan}>
        <textarea value={draft} onChange={(e)=>setDraft(e.target.value)} placeholder="例如：去广州玩四天，喜欢历史和美食，每天不要超过六小时……" aria-label="描述旅行需求"/>
        <div className="prompt-footer"><span>支持连续对话修改</span><button type="submit">开始规划 <b>↗</b></button></div>
      </form>
      <div className="examples"><span>试试看</span><button onClick={()=>setDraft('上海周末两日游，不要太赶')}>上海周末两日游</button><button onClick={()=>setDraft('带父母去成都，每天十点后出发')}>带父母去成都</button><button onClick={()=>setDraft('东京五天，预算有限，少走路')}>东京预算之旅</button></div>
    </section><div className="home-orbit orbit-one"/><div className="home-orbit orbit-two"/>
  </main>;

  return <main className="app-shell">
    <header className="topbar"><Brand/><div className="trip-heading"><span className="trip-city">广州</span><span className="trip-meta">4 天 · 10 个地点</span><span className="saved"><i/> 已保存</span></div><div className="top-actions"><button className="icon-button" aria-label="更多选项">•••</button><button className="secondary-button">分享</button><button className="primary-button">导出行程</button></div></header>
    <section className="workspace">
      <aside className="chat-panel">
        <div className="panel-heading"><div><span className="eyebrow">PLAN WITH AI</span><h2>和 PlanC 一起规划</h2></div><button className="new-trip" onClick={()=>setMode('home')}><span>＋</span> 新行程</button></div>
        <div className="constraint-card"><div className="constraint-title"><span>✦</span> 已理解你的旅行</div><div className="chips"><span>广州</span><span>4 天</span><span>历史文化</span><span>地道美食</span><span>轻松节奏</span><span>10:00 出发</span></div></div>
        <div className="chat-scroll">{chat.map((item,index)=><div className={`chat-row ${item.role}`} key={`${item.role}-${index}`}>{item.role==='assistant'&&<div className="mini-logo">C</div>}<div className="bubble">{item.text}</div></div>)}</div>
        <div className="suggestions">{suggestions.map((item)=><button key={item} onClick={()=>sendMessage(item)}>{item}</button>)}</div>
        <form className="chat-input" onSubmit={(e)=>{e.preventDefault();sendMessage();}}><textarea value={message} onChange={(e)=>setMessage(e.target.value)} placeholder="告诉我你想怎么调整……" aria-label="调整行程"/><div><span>⌘ ↵ 发送</span><button type="submit" aria-label="发送消息">↑</button></div></form>
      </aside>
      <section className="map-panel" aria-label="行程地图">
        <div className="map-grid"/><div className="river river-a"/><div className="river river-b"/><div className="park park-a">荔湾湖公园</div><div className="park park-b">珠江新城</div><span className="map-label label-a">荔湾区</span><span className="map-label label-b">越秀区</span><span className="map-label label-c">海珠区</span>
        <div className="route-line line-1" style={{background:dayColor}}/><div className="route-line line-2" style={{background:dayColor}}/><div className="route-line line-3" style={{background:dayColor}}/>
        {visibleStops.map((stop,index)=><button key={stop.id} className={`map-pin ${activeStop===stop.id?'active':''}`} style={{left:`${stop.x}%`,top:`${stop.y}%`,'--pin':dayColor} as React.CSSProperties} onClick={()=>setActiveStop(stop.id)} aria-label={`${stop.name}，第 ${index+1} 站`}><span>{index+1}</span><em>{stop.name}</em></button>)}
        <div className="map-controls"><button aria-label="放大">＋</button><button aria-label="缩小">−</button></div><div className="map-legend"><span className="legend-dot" style={{background:dayColor}}/> Day {activeDay} 路线 <i/> 约 {activeDay===1?'5.8':'4.6'} km</div><div className="estimate-note">⌁ 交通时间按步行速度估算</div>
      </section>
      <aside className="itinerary-panel">
        <div className="itinerary-head"><div><span className="eyebrow">YOUR ITINERARY</span><h2>四日行程</h2></div><button className="icon-button">⚙</button></div>
        <div className="day-tabs" role="tablist">{days.map((item)=><button key={item.day} className={activeDay===item.day?'active':''} style={{'--day-color':item.color} as React.CSSProperties} onClick={()=>{setActiveDay(item.day);const first=stops.find((stop)=>stop.day===item.day);if(first)setActiveStop(first.id);}}><b>Day {item.day}</b><span>{item.label}</span></button>)}</div>
        <div className="day-summary"><div><b>{activeDay===1?'10:00 — 17:15':'10:00 — 16:30'}</b><span>{visibleStops.length} 个地点 · 约 {activeDay===1?'5 小时 50 分':'5 小时 20 分'}</span></div><span className="weather">☀ 28°</span></div>
        <div className="timeline">{visibleStops.length?visibleStops.map((stop,index)=><article key={stop.id} className={`stop-card ${activeStop===stop.id?'selected':''}`} onClick={()=>setActiveStop(stop.id)} style={{'--day-color':dayColor} as React.CSSProperties}><div className="time-col"><b>{stop.time}</b><span>{stop.end}</span></div><div className="timeline-mark"><i>{index+1}</i></div><div className="stop-content"><div className="stop-top"><div><span className="stop-type">{stop.type}</span><h3>{stop.name}</h3></div><button aria-label="地点选项">•••</button></div><div className="stop-stats"><span>★ {stop.rating}</span><span>◷ {stop.duration}</span></div><div className="travel-note">{stop.travel}</div></div></article>):<div className="empty-day"><span>✦</span><h3>这一天还在路上</h3><p>继续和 PlanC 对话，完善当天安排。</p></div>}</div>
        <div className="itinerary-footer"><span>路线与时间均为估算值</span><button>查看未安排地点 <b>3</b></button></div>
      </aside>
    </section>
  </main>;
}

function Brand(){return <button className="brand" aria-label="PlanC 首页"><span className="brand-mark"><i/><i/><i/></span><span>Plan<span>C</span></span></button>}
