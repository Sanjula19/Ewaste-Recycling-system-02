import React, { useState, useEffect } from "react";
import { optimizeProcess, getHistory, getHealth, getLatestMoisture } from "../services/api";
import translations from "../translations";

// ── Scope: Plastic + Paper + Glass only (Textile/Rubber/Wood removed) ──
const MATERIALS = [
  { name:"Newspapers",        category:"Paper",   waste_type:"Paper", toxicity:"Low", defaultWeight:"3", defaultMoisture:"Dry" },
  { name:"Cardboard Boxes",   category:"Paper",   waste_type:"Paper", toxicity:"Low", defaultWeight:"5", defaultMoisture:"Dry" },
  { name:"Office Paper",      category:"Paper",   waste_type:"Paper", toxicity:"Low", defaultWeight:"2", defaultMoisture:"Dry" },
  { name:"PET Water Bottles", category:"Plastic", waste_type:"Plastic", toxicity:"Low", defaultWeight:"5", defaultMoisture:"Wet" },
  { name:"Food Containers",   category:"Plastic", waste_type:"Plastic", toxicity:"Low", defaultWeight:"4", defaultMoisture:"Wet" },
  { name:"Plastic Bags",      category:"Plastic", waste_type:"Plastic", toxicity:"Low", defaultWeight:"2", defaultMoisture:"Dry" },
  { name:"Glass Bottles",     category:"Glass",   waste_type:"Glass",   toxicity:"Low", defaultWeight:"6", defaultMoisture:"Dry" },
  { name:"Glass Jars",        category:"Glass",   waste_type:"Glass",   toxicity:"Low", defaultWeight:"4", defaultMoisture:"Dry" },
];

const CAT_ICONS  = { Paper:"📄", Plastic:"🧴", Glass:"🫙" };
const CAT_COLORS = {
  Paper:   { main:"#2A9D70", light:"#EAF8F1", bar:"#62C69B" },
  Plastic: { main:"#D97706", light:"#FFF5DF", bar:"#F2A93B" },
  Glass:   { main:"#16817A", light:"#E3F6F2", bar:"#55BDB2" },
};
const SAFETY_META = {
  CRITICAL:{ color:"#C62828", light:"#FFEBEE", border:"#EF9A9A", icon:"🚨", label:"Critical Risk" },
  WARNING: { color:"#D97706", light:"#FFF5DF", border:"#F3C878", icon:"⚠️", label:"Warning"       },
  SECURE:  { color:"#176B4D", light:"#EAF8F1", border:"#9ADDBB", icon:"✅", label:"Secure"        },
};
const METHOD_META = {
  Mechanical:{ icon:"⚙️", color:"#2A9D70", light:"#EAF8F1", desc:"Shred & Crush"    },
  Thermal:   { icon:"🔥", color:"#C65D24", light:"#FFF0E7", desc:"Melt & Pyrolysis"  },
  Chemical:  { icon:"🧪", color:"#4A148C", light:"#F3E5F5", desc:"Chemical Treatment"},
};
const LANG_OPTIONS = [
  { code:"EN", label:"English", flag:"🇬🇧" },
  { code:"SI", label:"සිංහල",   flag:"🇱🇰" },
  { code:"TA", label:"தமிழ்",   flag:"🇱🇰" },
];

// Light botanical theme
const G  = "#176B4D";   // deep teal green
const GL = "#2A9D70";   // fresh green
const GLL= "#62C69B";   // mint accent
const GB = "#EAF8F1";   // soft mint background

function Donut({ pct, color, size=110, label }) {
  const r=40, cx=size/2, cy=size/2, circ=2*Math.PI*r;
  const dash=circ*Math.min(pct/100,1);
  return (
    <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:4}}>
      <svg width={size} height={size}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#EEEEEE" strokeWidth={9}/>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={9}
          strokeDasharray={`${dash} ${circ-dash}`} strokeDashoffset={circ*0.25}
          strokeLinecap="round" style={{transition:"stroke-dasharray 1.2s ease"}}/>
        <text x={cx} y={cy-4} textAnchor="middle" style={{fontSize:15,fontWeight:700,fill:color,fontFamily:"Times New Roman"}}>{Math.round(pct)}%</text>
        <text x={cx} y={cy+13} textAnchor="middle" style={{fontSize:9,fill:"#9E9E9E",fontFamily:"Times New Roman"}}>of max</text>
      </svg>
      <div style={{fontSize:11,color:"#757575",fontFamily:"Times New Roman",textAlign:"center"}}>{label}</div>
    </div>
  );
}

function BarChart({ data, height=140 }) {
  const maxVal=Math.max(...data.map(d=>d.value),1);
  const barW=36, gap=14, total=data.length*(barW+gap)-gap;
  return (
    <svg width={total+40} height={height+40} style={{overflow:"visible"}}>
      {[0,25,50,75,100].map(g=>{
        const y=10+height-(g/100)*height;
        return <g key={g}>
          <line x1={20} y1={y} x2={total+20} y2={y} stroke="#F0F0F0" strokeWidth={1}/>
          <text x={16} y={y+4} textAnchor="end" style={{fontSize:8,fill:"#BDBDBD",fontFamily:"Times New Roman"}}>{g}%</text>
        </g>;
      })}
      {data.map((d,i)=>{
        const x=20+i*(barW+gap), barH=(d.value/maxVal)*height, y=10+height-barH;
        return <g key={i}>
          <rect x={x} y={y} width={barW} height={barH} rx={4} fill={d.color} opacity={0.85}/>
          <text x={x+barW/2} y={y-5} textAnchor="middle" style={{fontSize:9,fontWeight:700,fill:d.color,fontFamily:"Times New Roman"}}>{d.display}</text>
          <text x={x+barW/2} y={height+26} textAnchor="middle" style={{fontSize:9,fill:"#757575",fontFamily:"Times New Roman"}}>{d.label}</text>
        </g>;
      })}
    </svg>
  );
}

function HBar({ value, max, color, label, unit, delay=0 }) {
  const [w, setW] = useState(0);
  useEffect(()=>{const t=setTimeout(()=>setW((value/max)*100),delay+120);return()=>clearTimeout(t);},[value,max,delay]);
  return (
    <div style={{marginBottom:12}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}>
        <span style={{fontSize:12,color:"#555",fontFamily:"Times New Roman"}}>{label}</span>
        <span style={{fontSize:12,fontWeight:700,color,fontFamily:"Times New Roman"}}>{value}{unit}</span>
      </div>
      <div style={{height:8,background:"#EEEEEE",borderRadius:4,overflow:"hidden"}}>
        <div style={{height:"100%",width:`${w}%`,background:color,borderRadius:4,transition:"width 1.3s ease"}}/>
      </div>
    </div>
  );
}

function Radar({ data, size=180 }) {
  const cx=size/2, cy=size/2, r=size*0.36, n=data.length;
  const ang=(i)=>(Math.PI*2*i/n)-Math.PI/2;
  const pt=(i,v)=>({x:cx+r*Math.cos(ang(i))*v,y:cy+r*Math.sin(ang(i))*v});
  const gridPts=(v)=>data.map((_,i)=>pt(i,v));
  return (
    <svg width={size} height={size}>
      {[0.25,0.5,0.75,1].map(v=>(
        <polygon key={v} points={gridPts(v).map(p=>`${p.x},${p.y}`).join(" ")} fill="none" stroke="#E8E8E8" strokeWidth={0.8}/>
      ))}
      {data.map((_,i)=>{const e=pt(i,1);return<line key={i} x1={cx} y1={cy} x2={e.x} y2={e.y} stroke="#E8E8E8" strokeWidth={0.8}/>;}) }
      <polygon points={data.map((d,i)=>{const p=pt(i,d.value);return`${p.x},${p.y}`;}).join(" ")}
        fill="rgba(46,125,50,0.15)" stroke={GL} strokeWidth={2}/>
      {data.map((d,i)=>{
        const p=pt(i,d.value),lp=pt(i,1.22);
        return <g key={i}>
          <circle cx={p.x} cy={p.y} r={4} fill={GL}/>
          <text x={lp.x} y={lp.y} textAnchor="middle" dominantBaseline="middle"
            style={{fontSize:9,fill:"#555",fontFamily:"Times New Roman"}}>{d.label}</text>
        </g>;
      })}
    </svg>
  );
}

const SIDEBAR_W = 220;

export default function Dashboard() {
  const [lang,setLang]                         = useState("EN");
  const [selectedMaterial,setSelectedMaterial] = useState(MATERIALS[3]); // PET Water Bottles
  const [weight,setWeight]                     = useState(MATERIALS[3].defaultWeight);
  const [moisture,setMoisture]                 = useState(MATERIALS[3].defaultMoisture);
  const [wasteType,setWasteType]               = useState(MATERIALS[3].waste_type);
  const [grade,setGrade]                       = useState("A");
  const [result,setResult]                     = useState(null);
  const [loading,setLoading]                   = useState(false);
  const [error,setError]                       = useState(null);
  const [history,setHistory]                   = useState([]);
  const [apiStatus,setApiStatus]               = useState("checking");
  const [activeTab,setActiveTab]               = useState("home");
  const [darkMode,setDarkMode]                 = useState(() => window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false);

  // ── IoT: Plastic gets moisture automatically from the SHEF sensor.
  // Paper and Glass still use manual input. ──
  const [sensorMoisture,setSensorMoisture]     = useState(null); // e.g. "Wet" once sensor connected
  const isAutoMoisture = selectedMaterial.category === "Plastic";

  const t = translations[lang];
  const F = "Times New Roman, Georgia, serif";

  useEffect(()=>{getHealth().then(()=>setApiStatus("online")).catch(()=>setApiStatus("offline"));},[]);

  useEffect(()=>{
    const mediaQuery = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!mediaQuery) return undefined;
    const updateTheme = event => setDarkMode(event.matches);
    mediaQuery.addEventListener?.("change", updateTheme);
    return () => mediaQuery.removeEventListener?.("change", updateTheme);
  },[]);

  useEffect(()=>{
    if (!isAutoMoisture) return;
    const readSensor = () => getLatestMoisture().then(data=>{
      if (data.raw_value !== null && (data.moisture_status === "Wet" || data.moisture_status === "Dry")) {
        setSensorMoisture(data.moisture_status);
      }
    }).catch(()=>setSensorMoisture(null));
    readSensor();
    const timer = setInterval(readSensor, 3000);
    return () => clearInterval(timer);
  },[isAutoMoisture]);

  // If material switches to Plastic, prefer the live sensor reading when available
  useEffect(()=>{
    if (isAutoMoisture && sensorMoisture) setMoisture(sensorMoisture);
  },[isAutoMoisture, sensorMoisture]);

  const handleGenerate=async()=>{
    setLoading(true); setError(null);
    const batchId=`BATCH-${Date.now()}`;
    try {
      const data=await optimizeProcess({
        material_name:selectedMaterial.name,
        waste_type:wasteType,
        weight_kg:parseFloat(weight)||1,
        moisture_condition:moisture,
        condition: grade === "A" ? "Clean" : grade === "B" ? "Contaminated" : "Damaged",
        grade,
        batch_id:batchId,
      });
      setResult(data); setActiveTab("result");
    } catch(e){ setError(t.errorMsg); }
    setLoading(false);
  };

  const handleHistory=async()=>{
    try{const d=await getHistory();setHistory(d.results||[]);}catch{setHistory([]);}
    setActiveTab("history");
  };

  const getSM=(s)=>SAFETY_META[s]||SAFETY_META.SECURE;
  const getMM=(m)=>{
    if(!m) return METHOD_META.Mechanical;
    const k=Object.keys(METHOD_META).find(k=>m.toLowerCase().includes(k.toLowerCase()));
    return METHOD_META[k]||METHOD_META.Mechanical;
  };

  const buildSteps=(r)=>{
    const steps=[];
    if(r.prewash_required) steps.push({
      title:"Pre-Wash / Cleaning", isPre:true,
      duration:`${r.prewash_time_min||0} min`,
      temp:"Ambient",
      desc:r.prewash_method||"Prepare material before processing",
      icon:"🧼", color:"#00695C", bg:"#E0F2F1", border:"#80CBC4",
    });
    if(r.pre_drying_required) steps.push({
      title:"Pre-Drying Phase", isPre:true,
      duration:r.pre_drying_time_min?`${r.pre_drying_time_min} min`:"15 min",
      temp:r.pre_drying_temp_c?`${r.pre_drying_temp_c}°C`:"80°C",
      desc:"Remove moisture to ensure safe and efficient processing",
      icon:"💧", color:"#1B5E20", bg:"#E8F5E9", border:"#A5D6A7",
    });
    const mm=getMM(r.recommended_method);
    steps.push({
      title:r.recommended_method==="Mechanical"?"Mechanical Processing":r.recommended_method==="Thermal"?"Thermal Processing":"Chemical Treatment",
      duration:`${r.processing_time_min||0} min`,
      temp:r.optimal_temp_c?`${r.optimal_temp_c}°C`:"No heat",
      desc:r.recommended_method==="Mechanical"?"Shred and crush material to reduce size and prepare for recovery":"Apply controlled heat at optimal temperature for material transformation",
      icon:mm.icon, color:mm.color, bg:mm.light, border:`${mm.color}50`,
    });
    if(r.cooling_time_min) steps.push({
      title:r.cooling_method||"Cooling Phase",
      duration:`${r.cooling_time_min} min`,
      temp:`Target ${r.target_temp_c||30}°C`,
      desc:"Allow processed material to cool before safe handling and storage",
      icon:"❄️", color:"#01579B", bg:"#E1F5FE", border:"#81D4FA",
    });
    return steps;
  };

  const catGroups=[...new Set(MATERIALS.map(m=>m.category))];
  const catCount=catGroups.reduce((a,c)=>({...a,[c]:MATERIALS.filter(m=>m.category===c).length}),{});

  const NAV = [
    {id:"home",    icon:"🏠", label:t.tabHome},
    {id:"optimize",icon:"⚡", label:t.tabOptimize},
    {id:"result",  icon:"📊", label:t.tabResult},
    {id:"history", icon:"📜", label:t.tabHistory},
  ];

  return (
    <>
      <style>{`
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
        body{background:linear-gradient(135deg,#F7FCF9 0%,#F1FAF6 52%,#FFF9F0 100%);font-family:'Times New Roman',Georgia,serif;color:#1A1A1A;}
        ::-webkit-scrollbar{width:5px;} ::-webkit-scrollbar-track{background:#F4FAF6;} ::-webkit-scrollbar-thumb{background:#9ADDBB;border-radius:3px;}
        select option{background:#FFFFFF;color:#1A1A1A;}
        input[type=number]::-webkit-inner-spin-button{-webkit-appearance:none;}
        input[type=range]{accent-color:${GL};}
        .card{transition:box-shadow 0.2s;} .card:hover{box-shadow:0 4px 16px rgba(0,0,0,0.09)!important;}
        .mat-btn{transition:all 0.15s;} .mat-btn:hover{background:#F1F8E9!important;}
        .nav-btn{transition:all 0.18s;} .gen-btn{transition:all 0.2s;}
        .gen-btn:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 6px 20px rgba(46,125,50,0.35);}
        .hist-row{transition:background 0.12s;} .hist-row:hover{background:#F9FBF9!important;}
        .lang-btn{transition:all 0.15s;}
        @keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
        .fade-up{animation:fadeUp 0.4s ease forwards;}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}} .pulse{animation:pulse 1.1s ease infinite;}
        @keyframes livePulse{0%,100%{opacity:1}50%{opacity:0.4}} .live-dot{animation:livePulse 1.4s ease infinite;}
        .theme-dark{color-scheme:dark;}
        .theme-dark .card,.theme-dark header{background:#17231F!important;border-color:#315348!important;box-shadow:0 2px 12px rgba(0,0,0,0.24)!important;}
        .theme-dark .hist-row{background:#1B2B25!important;border-color:#315348!important;}
        .theme-dark input,.theme-dark select{background:#20332B!important;color:#F0F7F3!important;border-color:#477563!important;}
        .theme-dark .card div[style*="color: rgb(26, 26, 26)"],.theme-dark .card span[style*="color: rgb(26, 26, 26)"],.theme-dark .card strong{color:#F0F7F3!important;}
        .theme-dark .card div[style*="color: rgb(117, 117, 117)"],.theme-dark .card span[style*="color: rgb(117, 117, 117)"],.theme-dark .card div[style*="color: rgb(85, 85, 85)"]{color:#B8C9C1!important;}
        .theme-dark .card div[style*="background: rgb(250, 250, 250)"],.theme-dark .card div[style*="background: rgb(245, 245, 245)"]{background:#20332B!important;border-color:#315348!important;}
        .theme-dark .card div[style*="color: rgb(158, 158, 158)"],.theme-dark .card span[style*="color: rgb(158, 158, 158)"]{color:#9BB2A8!important;}
        @media (prefers-color-scheme: dark){body{background:#101815;}}
      `}</style>

      <div className={darkMode?"theme-dark":"theme-light"} style={{display:"flex",minHeight:"100vh",background:darkMode?"#101815":"linear-gradient(135deg,#F7FCF9 0%,#F1FAF6 52%,#FFF9F0 100%)"}}>

        {/* ══ SIDEBAR ══ */}
        <aside style={{
          width:SIDEBAR_W, minHeight:"100vh",
          background:G, position:"fixed", top:0, left:0, bottom:0,
          display:"flex", flexDirection:"column",
          boxShadow:"2px 0 12px rgba(0,0,0,0.15)", zIndex:50,
        }}>
          {/* Logo */}
          <div style={{padding:"24px 20px 20px",borderBottom:"1px solid rgba(255,255,255,0.1)"}}>
            <div style={{display:"flex",alignItems:"center",gap:12}}>
              <div style={{width:42,height:42,background:"rgba(255,255,255,0.15)",borderRadius:10,display:"flex",alignItems:"center",justifyContent:"center",fontSize:22}}>♻</div>
              <div>
                <div style={{fontSize:13,fontWeight:700,color:"#FFFFFF",fontFamily:F,lineHeight:1.3}}>EcoProcess AI</div>
              </div>
            </div>
          </div>

          {/* Nav items */}
          <nav style={{flex:1,padding:"16px 12px",display:"flex",flexDirection:"column",gap:4}}>
            <div style={{fontSize:9,color:"rgba(255,255,255,0.4)",letterSpacing:"0.12em",fontFamily:F,fontWeight:700,padding:"4px 8px 8px"}}>MAIN MENU</div>
            {NAV.map(n=>(
              <button key={n.id} className="nav-btn"
                onClick={()=>n.id==="history"?handleHistory():setActiveTab(n.id)}
                style={{
                  display:"flex",alignItems:"center",gap:12,
                  padding:"11px 14px",borderRadius:10,border:"none",
                  cursor:"pointer",fontFamily:F,fontSize:13,
                  fontWeight:activeTab===n.id?700:400,
                  textAlign:"left",width:"100%",
                  background:activeTab===n.id?"rgba(255,255,255,0.2)":"transparent",
                  color:activeTab===n.id?"#FFFFFF":"rgba(255,255,255,0.65)",
                  borderLeft:activeTab===n.id?"3px solid #A5D6A7":"3px solid transparent",
                }}>
                <span style={{fontSize:18}}>{n.icon}</span>
                {n.label.replace(/[🏠⚡📊📜]\s*/,"")}
              </button>
            ))}
          </nav>

          {/* Language switcher */}
          <div style={{padding:"16px 12px",borderTop:"1px solid rgba(255,255,255,0.1)"}}>
            <div style={{fontSize:9,color:"rgba(255,255,255,0.4)",letterSpacing:"0.12em",fontFamily:F,fontWeight:700,marginBottom:8}}>LANGUAGE</div>
            <div style={{display:"flex",gap:4}}>
              {LANG_OPTIONS.map(l=>(
                <button key={l.code} className="lang-btn" onClick={()=>setLang(l.code)}
                  style={{flex:1,padding:"6px 4px",borderRadius:8,border:"none",cursor:"pointer",fontFamily:F,fontSize:11,
                    fontWeight:lang===l.code?700:400,
                    background:lang===l.code?"rgba(255,255,255,0.25)":"rgba(255,255,255,0.08)",
                    color:lang===l.code?"#FFFFFF":"rgba(255,255,255,0.55)",
                    display:"flex",flexDirection:"column",alignItems:"center",gap:2}}>
                  <span style={{fontSize:16}}>{l.flag}</span>
                  <span>{l.code}</span>
                </button>
              ))}
            </div>
          </div>

          {/* API Status */}
          <div style={{padding:"14px 20px",borderTop:"1px solid rgba(255,255,255,0.1)"}}>
            <div style={{fontSize:9,color:"rgba(255,255,255,0.4)",letterSpacing:"0.12em",fontFamily:F,fontWeight:700,marginBottom:8}}>API STATUS</div>
            <div style={{display:"flex",alignItems:"center",gap:8}}>
              <div style={{width:8,height:8,borderRadius:"50%",
                background:apiStatus==="online"?"#69F0AE":"#EF5350",
                boxShadow:apiStatus==="online"?"0 0 8px #69F0AE":"none"}}/>
              <span style={{fontSize:12,color:apiStatus==="online"?"#69F0AE":"#EF9A9A",fontFamily:F,fontWeight:600}}>
                {apiStatus==="online"?t.apiOnline:t.apiOffline}
              </span>
            </div>
          </div>
        </aside>

        {/* ══ MAIN CONTENT ══ */}
        <div style={{marginLeft:SIDEBAR_W,flex:1,display:"flex",flexDirection:"column",background:"rgba(255,255,255,0.24)"}}>

          {/* Top bar */}
          <header style={{
            background:"#FFFFFF",borderBottom:`2px solid ${GB}`,
            padding:"0 32px",position:"sticky",top:0,zIndex:40,
            boxShadow:"0 2px 8px rgba(0,0,0,0.05)",
          }}>
            <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",height:60}}>
              <div>
                <div style={{fontSize:17,fontWeight:700,color:G,fontFamily:F}}>{t.systemTitle}</div>
              </div>
              <div style={{display:"flex",alignItems:"center",gap:10}}>
                <button
                  type="button"
                  onClick={()=>setDarkMode(mode=>!mode)}
                  aria-label={darkMode?"Switch to light mode":"Switch to dark mode"}
                  title={darkMode?"Switch to light mode":"Switch to dark mode"}
                  style={{display:"flex",alignItems:"center",gap:7,padding:"7px 10px",borderRadius:18,border:`1px solid ${darkMode?"#477563":GLL+"60"}`,background:darkMode?"#20332B":GB,color:darkMode?"#F7D774":G,cursor:"pointer",fontFamily:F,fontSize:12,fontWeight:700}}
                >
                  <span style={{fontSize:16}}>{darkMode?"☀️":"🌙"}</span>
                  <span>{darkMode?"Light":"Dark"}</span>
                </button>
                <div style={{padding:"4px 14px",borderRadius:20,background:GB,border:`1px solid ${GLL}40`,fontSize:12,color:GL,fontWeight:600,fontFamily:F}}>
                  {NAV.find(n=>n.id===activeTab)?.icon} {NAV.find(n=>n.id===activeTab)?.label.replace(/[🏠⚡📊📜]\s*/,"")}
                </div>
              </div>
            </div>
          </header>

          <div style={{padding:"28px 32px",flex:1}}>

            {error&&(
              <div className="fade-up" style={{padding:"12px 18px",borderRadius:8,marginBottom:20,background:"#FFEBEE",border:"1px solid #EF9A9A",color:"#B71C1C",fontSize:13,fontFamily:F,display:"flex",alignItems:"center",gap:10}}>
                🚨 {error}
                <button onClick={()=>setError(null)} style={{marginLeft:"auto",background:"none",border:"none",color:"#B71C1C",cursor:"pointer",fontSize:16}}>✕</button>
              </div>
            )}

            {/* HOME TAB */}
            {activeTab==="home"&&(
              <div className="fade-up">
                <div style={{background:`linear-gradient(135deg,${G},${GL})`,borderRadius:12,padding:"28px 36px",marginBottom:24,color:"#FFFFFF",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                  <div>
                    <div style={{fontSize:22,fontWeight:700,fontFamily:F,marginBottom:14}}>{t.welcomeTitle}</div>
                    <button onClick={()=>setActiveTab("optimize")}
                      style={{padding:"10px 24px",borderRadius:6,border:"1px solid rgba(255,255,255,0.5)",background:"rgba(255,255,255,0.15)",color:"#FFFFFF",fontFamily:F,fontSize:13,fontWeight:700,cursor:"pointer"}}>
                      {t.startBtn}
                    </button>
                  </div>
                  <div style={{fontSize:80,opacity:0.12}}>♻</div>
                </div>

                <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:16,marginBottom:24}}>
                  {[
                    {val:"8", sub:t.statSubMat,  label:t.statMaterials, icon:"📦",col:GL, bg:GB},
                    {val:"2", sub:t.statSubMeth, label:t.statMethods,   icon:"⚙️",col:"#00695C",bg:"#E0F2F1"},
                    {val:"3", sub:t.statSubMod,  label:t.statModels,    icon:"🧠",col:"#6A1B9A",bg:"#F3E5F5"},
                    {val:"6K",sub:t.statSubRows, label:t.statRows,      icon:"📊",col:"#E65100",bg:"#FFF3E0"},
                  ].map(s=>(
                    <div key={s.label} className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E8E8E8",padding:"20px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                      <div style={{width:40,height:40,borderRadius:8,background:s.bg,display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,marginBottom:12}}>{s.icon}</div>
                      <div style={{fontSize:28,fontWeight:700,color:s.col,fontFamily:F}}>{s.val}</div>
                      <div style={{fontSize:13,fontWeight:600,color:"#1A1A1A",fontFamily:F,marginTop:2}}>{s.label}</div>
                      <div style={{fontSize:11,color:"#9E9E9E",fontFamily:F,marginTop:2}}>{s.sub}</div>
                    </div>
                  ))}
                </div>

                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:20,marginBottom:24}}>
                  <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E8E8E8",padding:"22px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                    <div style={{fontSize:13,fontWeight:700,color:"#1A1A1A",fontFamily:F,marginBottom:4}}>{t.chartMatTitle}</div>
                    <div style={{fontSize:11,color:"#9E9E9E",fontFamily:F,marginBottom:18}}>{t.chartMatSub}</div>
                    <BarChart data={catGroups.map(c=>({label:c,value:catCount[c],color:CAT_COLORS[c]?.bar||GL,display:catCount[c]}))} height={120}/>
                  </div>
                  <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E8E8E8",padding:"22px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                    <div style={{fontSize:13,fontWeight:700,color:"#1A1A1A",fontFamily:F,marginBottom:4}}>{t.chartMethTitle}</div>
                    <div style={{fontSize:11,color:"#9E9E9E",fontFamily:F,marginBottom:18}}>{t.chartMethSub}</div>
                    <div style={{display:"flex",justifyContent:"center",gap:32,alignItems:"center"}}>
                      <Donut pct={63} color={GL} label="Mechanical (5)" size={110}/>
                      <Donut pct={37} color="#BF360C" label="Thermal (3)" size={110}/>
                    </div>
                  </div>
                </div>

                <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E8E8E8",padding:"22px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                  <div style={{fontSize:13,fontWeight:700,color:"#1A1A1A",fontFamily:F,marginBottom:4}}>{t.matTableTitle}</div>
                  <div style={{fontSize:11,color:"#9E9E9E",fontFamily:F,marginBottom:18}}>{t.matTableSub}</div>
                  <div style={{display:"grid",gridTemplateColumns:"repeat(7,1fr)",background:G,borderRadius:"8px 8px 0 0",overflow:"hidden"}}>
                    {[t.thIcon,t.thMaterial,t.thCategory,t.thWasteType,t.thMethod,t.thDefWeight,t.thToxicity].map(h=>(
                      <div key={h} style={{padding:"10px",fontSize:10,fontWeight:700,color:"#FFFFFF",fontFamily:F,letterSpacing:"0.06em",borderRight:"1px solid rgba(255,255,255,0.1)"}}>{h.toUpperCase()}</div>
                    ))}
                  </div>
                  {MATERIALS.map((m,i)=>{
                    const method=m.category==="Plastic"?"Thermal":"Mechanical";
                    const mc=method==="Thermal"?METHOD_META.Thermal:METHOD_META.Mechanical;
                    return (
                      <div key={m.name}
                        onClick={()=>{setSelectedMaterial(m);setWeight(m.defaultWeight);setMoisture(m.defaultMoisture);setWasteType(m.waste_type);setActiveTab("optimize");}}
                        onMouseEnter={e=>e.currentTarget.style.background=GB}
                        onMouseLeave={e=>e.currentTarget.style.background=i%2===0?"#FAFAFA":"#FFFFFF"}
                        style={{display:"grid",gridTemplateColumns:"repeat(7,1fr)",background:i%2===0?"#FAFAFA":"#FFFFFF",borderBottom:"1px solid #F0F0F0",cursor:"pointer",transition:"background 0.15s"}}>
                        {[
                          <span style={{fontSize:18}}>{CAT_ICONS[m.category]}</span>,
                          <span style={{fontWeight:600,color:"#1A1A1A"}}>{m.name}</span>,
                          <span style={{color:CAT_COLORS[m.category]?.main}}>{m.category}</span>,
                          <span style={{color:"#555"}}>{m.waste_type}</span>,
                          <span style={{color:mc.color,fontWeight:600}}>{mc.icon} {method}</span>,
                          <span style={{color:"#555"}}>{m.defaultWeight} kg / {m.defaultMoisture}</span>,
                          <span style={{color:m.toxicity==="Medium"?"#E65100":"#1B5E20",fontWeight:600}}>{m.toxicity}</span>,
                        ].map((cell,ci)=>(
                          <div key={ci} style={{padding:"9px 10px",fontSize:12,fontFamily:F,borderRight:"1px solid #F0F0F0"}}>{cell}</div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* OPTIMIZE TAB */}
            {activeTab==="optimize"&&(
              <div className="fade-up" style={{display:"grid",gridTemplateColumns:"280px 1fr",gap:24}}>
                <div style={{display:"flex",flexDirection:"column",gap:16}}>
                  <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",overflow:"hidden",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                    <div style={{padding:"12px 18px",borderBottom:"1px solid #F0F0F0",background:`${GB}`}}>
                      <div style={{fontSize:10,fontWeight:700,color:GL,letterSpacing:"0.12em",fontFamily:F}}>{t.sectionCategory}</div>
                    </div>
                    <div style={{padding:10,display:"flex",flexDirection:"column",gap:3}}>
                      {catGroups.map(cat=>{
                        const active=selectedMaterial.category===cat;
                        const cc=CAT_COLORS[cat]||CAT_COLORS.Paper;
                        return (
                          <button key={cat} className="mat-btn"
                            onClick={()=>{const first=MATERIALS.find(m=>m.category===cat);if(first){setSelectedMaterial(first);setWeight(first.defaultWeight);setMoisture(first.defaultMoisture);setWasteType(first.waste_type);}}}
                            style={{display:"flex",alignItems:"center",gap:10,padding:"9px 12px",borderRadius:7,border:`1px solid ${active?cc.main+"50":"transparent"}`,background:active?cc.light:"transparent",cursor:"pointer",textAlign:"left",width:"100%"}}>
                            <span style={{fontSize:18}}>{CAT_ICONS[cat]}</span>
                            <span style={{flex:1,fontSize:13,fontWeight:active?700:400,fontFamily:F,color:active?cc.main:"#555"}}>{cat}</span>
                            {cat==="Plastic"&&(
                              <span style={{fontSize:9,color:active?"#1B5E20":"#66BB6A",background:active?"#E8F5E9":"#F1F8E9",padding:"2px 6px",borderRadius:8,fontFamily:F,fontWeight:700}}>IoT</span>
                            )}
                            <span style={{fontSize:10,color:active?cc.main:"#BDBDBD",background:active?`${cc.main}15`:"#F5F5F5",padding:"2px 7px",borderRadius:10,fontFamily:F}}>{catCount[cat]}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",overflow:"hidden",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                    <div style={{padding:"12px 18px",borderBottom:"1px solid #F0F0F0",background:GB}}>
                      <div style={{fontSize:10,fontWeight:700,color:GL,letterSpacing:"0.12em",fontFamily:F}}>{t.sectionMaterial}</div>
                    </div>
                    <div style={{padding:10,display:"flex",flexDirection:"column",gap:3}}>
                      {MATERIALS.filter(m=>m.category===selectedMaterial.category).map(mat=>{
                        const active=selectedMaterial.name===mat.name;
                        const cc=CAT_COLORS[mat.category]||CAT_COLORS.Paper;
                        return (
                          <button key={mat.name} className="mat-btn"
                            onClick={()=>{setSelectedMaterial(mat);setWeight(mat.defaultWeight);setMoisture(mat.defaultMoisture);setWasteType(mat.waste_type);}}
                            style={{display:"flex",alignItems:"center",gap:10,padding:"9px 12px",borderRadius:7,border:active?`1px solid ${cc.main}40`:"1px solid transparent",background:active?cc.light:"transparent",cursor:"pointer",textAlign:"left",width:"100%"}}>
                            <div style={{width:7,height:7,borderRadius:"50%",background:active?cc.main:"#BDBDBD",flexShrink:0}}/>
                            <span style={{fontSize:13,fontWeight:active?600:400,fontFamily:F,color:active?"#1A1A1A":"#666",flex:1}}>{mat.name}</span>
                            {active&&<span style={{fontSize:10,color:cc.main,fontFamily:F}}>✓</span>}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <div style={{display:"flex",flexDirection:"column",gap:20}}>
                  {(()=>{
                    const cc=CAT_COLORS[selectedMaterial.category]||CAT_COLORS.Paper;
                    return (
                      <div style={{background:"#FFFFFF",borderRadius:10,border:`1px solid ${cc.main}25`,padding:"18px 22px",display:"flex",alignItems:"center",gap:16,borderLeft:`4px solid ${cc.main}`,boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                        <div style={{fontSize:44}}>{CAT_ICONS[selectedMaterial.category]}</div>
                        <div style={{flex:1}}>
                          <div style={{fontSize:20,fontWeight:700,color:"#1A1A1A",fontFamily:F,marginBottom:6}}>{selectedMaterial.name}</div>
                          <div style={{display:"flex",gap:18,flexWrap:"wrap"}}>
                            {[["Category",selectedMaterial.category],["Waste Type",selectedMaterial.waste_type],["Toxicity",selectedMaterial.toxicity]].map(([k,v])=>(
                              <span key={k} style={{fontSize:12,color:"#757575",fontFamily:F}}>{k}: <strong style={{color:"#1A1A1A"}}>{v}</strong></span>
                            ))}
                          </div>
                        </div>
                        <div style={{padding:"6px 16px",borderRadius:20,background:cc.light,border:`1px solid ${cc.main}40`,fontSize:12,color:cc.main,fontWeight:700,fontFamily:F}}>{t.selectedLabel}</div>
                      </div>
                    );
                  })()}

                  <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
                    <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",padding:"20px 22px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                      <div style={{fontSize:10,fontWeight:700,color:GL,letterSpacing:"0.12em",fontFamily:F,marginBottom:14}}>{t.labelWeight}</div>
                      <div style={{display:"flex",alignItems:"baseline",gap:8,marginBottom:16}}>
                        <input type="number" value={weight} min="0.1" max="1000" step="0.5"
                          onChange={e=>setWeight(e.target.value)}
                          style={{background:"#FAFAFA",border:`1px solid ${GLL}40`,borderRadius:6,color:"#1A1A1A",padding:"8px 12px",fontSize:28,fontWeight:700,outline:"none",width:120,fontFamily:F}}/>
                        <span style={{fontSize:16,color:"#9E9E9E",fontFamily:F}}>kg</span>
                      </div>
                      <input type="range" min="0.5" max="50" step="0.5" value={Math.min(parseFloat(weight)||1,50)}
                        onChange={e=>setWeight(e.target.value)} style={{width:"100%",cursor:"pointer"}}/>
                      <div style={{display:"flex",justifyContent:"space-between",fontSize:11,color:"#BDBDBD",fontFamily:F,marginTop:4}}>
                        <span>0.5 kg</span><span>50 kg</span>
                      </div>
                    </div>

                    {/* Moisture — auto (IoT sensor) for Plastic, manual for Paper/Glass */}
                    <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",padding:"20px 22px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:14}}>
                        <div style={{fontSize:10,fontWeight:700,color:GL,letterSpacing:"0.12em",fontFamily:F}}>{t.labelMoisture}</div>
                        {isAutoMoisture&&(
                          <span style={{display:"flex",alignItems:"center",gap:5,fontSize:9,fontWeight:700,color:sensorMoisture?"#1B5E20":"#9E9E9E",fontFamily:F}}>
                            <span className={sensorMoisture?"live-dot":""} style={{width:6,height:6,borderRadius:"50%",background:sensorMoisture?"#43A047":"#BDBDBD"}}/>
                            {sensorMoisture?"IoT SENSOR — LIVE":"IoT SENSOR — WAITING"}
                          </span>
                        )}
                      </div>

                      {isAutoMoisture ? (
                        <div style={{padding:"14px 16px",borderRadius:8,background:sensorMoisture?GB:"#FAFAFA",border:`1.5px solid ${sensorMoisture?GLL+"60":"#E0E0E0"}`,display:"flex",alignItems:"center",gap:12}}>
                          <span style={{fontSize:22}}>{moisture==="Wet"?"💧":"☀️"}</span>
                          <div>
                            <div style={{fontSize:13,fontWeight:700,color:sensorMoisture?G:"#757575",fontFamily:F}}>
                              {sensorMoisture?`${moisture} (from sensor)`:`${moisture} (default — sensor not connected)`}
                            </div>
                            <div style={{fontSize:11,color:"#9E9E9E",fontFamily:F}}>
                              Plastic moisture is read automatically by the SHEF ESP32/DHT22 module
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div style={{display:"flex",flexDirection:"column",gap:10}}>
                          {[
                            {val:"Dry",icon:"☀️",label:t.dryLabel,desc:t.dryDesc,col:"#E65100"},
                            {val:"Wet",icon:"💧",label:t.wetLabel,desc:t.wetDesc,col:GL},
                          ].map(m=>(
                            <button key={m.val} onClick={()=>setMoisture(m.val)}
                              style={{display:"flex",alignItems:"center",gap:12,padding:"11px 14px",borderRadius:8,border:`1.5px solid ${moisture===m.val?m.col+"60":"#E0E0E0"}`,background:moisture===m.val?`${m.col}06`:"#FAFAFA",cursor:"pointer",textAlign:"left",fontFamily:F}}>
                              <span style={{fontSize:20}}>{m.icon}</span>
                              <div>
                                <div style={{fontSize:13,fontWeight:moisture===m.val?700:400,color:moisture===m.val?m.col:"#555",fontFamily:F}}>{m.label}</div>
                                <div style={{fontSize:11,color:"#9E9E9E",fontFamily:F}}>{m.desc}</div>
                              </div>
                              {moisture===m.val&&<div style={{marginLeft:"auto",width:8,height:8,borderRadius:"50%",background:m.col}}/>}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {moisture==="Wet"&&(
                    <div style={{padding:"11px 16px",borderRadius:8,background:GB,border:`1px solid ${GLL}60`,fontSize:12,color:G,fontFamily:F,display:"flex",alignItems:"center",gap:10}}>
                      💧 <strong>{t.noteLabel}:</strong> {t.wetWarning}
                    </div>
                  )}

                  {/* Waste Type Selector */}
                  <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",padding:"20px 22px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                    <div style={{fontSize:10,fontWeight:700,color:GL,letterSpacing:"0.12em",fontFamily:F,marginBottom:6}}>WASTE TYPE</div>
                    <div style={{fontSize:11,color:"#9E9E9E",fontFamily:F,marginBottom:14}}>Auto selected from material — change if needed</div>
                    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:8}}>
                      {[
                        {val:"Paper", icon:"📄", desc:"Newspapers · Boxes · Office paper"},
                        {val:"Plastic", icon:"🧴", desc:"PET · Containers · Bags"},
                        {val:"Glass",   icon:"🫙", desc:"Bottles · Jars"},
                      ].map(wt=>(
                        <button key={wt.val} onClick={()=>setWasteType(wt.val)}
                          style={{display:"flex",alignItems:"center",gap:10,padding:"10px 12px",
                            borderRadius:8,border:"1.5px solid "+(wasteType===wt.val?GL+"70":"#E0E0E0"),
                            background:wasteType===wt.val?GB:"#FAFAFA",
                            cursor:"pointer",textAlign:"left",fontFamily:F}}>
                          <span style={{fontSize:20}}>{wt.icon}</span>
                          <div style={{flex:1}}>
                            <div style={{fontSize:13,fontWeight:wasteType===wt.val?700:400,color:wasteType===wt.val?G:"#555",fontFamily:F}}>{wt.val}</div>
                            <div style={{fontSize:10,color:"#BDBDBD",fontFamily:F}}>{wt.desc}</div>
                          </div>
                          {wasteType===wt.val&&<span style={{fontSize:11,color:GL}}>✓</span>}
                        </button>
                      ))}
                    </div>
                    <div style={{marginTop:10,padding:"8px 12px",borderRadius:6,background:GB,border:"1px solid "+GLL+"40",fontSize:11,color:G,fontFamily:F,display:"flex",alignItems:"center",gap:8}}>
                      <span>🔄</span>
                      <span>Auto: <strong>{selectedMaterial.name}</strong> → <strong>{wasteType}</strong></span>
                    </div>
                  </div>

                  <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",padding:"20px 22px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                    <div style={{fontSize:10,fontWeight:700,color:GL,letterSpacing:"0.12em",fontFamily:F,marginBottom:6}}>ITEM GRADE</div>
                    <div style={{fontSize:11,color:"#9E9E9E",fontFamily:F,marginBottom:14}}>Condition from Component 1</div>
                    <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:8}}>
                      {[{val:"A",label:"Clean"},{val:"B",label:"Contaminated"},{val:"C",label:"Damaged"}].map(item=>(
                        <button key={item.val} onClick={()=>setGrade(item.val)} style={{padding:"10px",borderRadius:8,border:`1.5px solid ${grade===item.val?GL+"70":"#E0E0E0"}`,background:grade===item.val?GB:"#FAFAFA",color:grade===item.val?G:"#555",fontFamily:F,cursor:"pointer"}}>
                          <strong>{item.val}</strong><div style={{fontSize:11,marginTop:3}}>{item.label}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  <button className="gen-btn" onClick={handleGenerate} disabled={loading}
                    style={{padding:"16px 32px",borderRadius:8,border:"none",cursor:loading?"not-allowed":"pointer",
                      background:loading?"#BDBDBD":`linear-gradient(135deg,${GL},${G})`,
                      color:"#FFFFFF",fontSize:15,fontFamily:F,fontWeight:700,letterSpacing:"0.04em",
                      display:"flex",alignItems:"center",justifyContent:"center",gap:12}}>
                    {loading?(<><span className="pulse">●</span><span className="pulse" style={{animationDelay:"0.2s"}}>●</span><span className="pulse" style={{animationDelay:"0.4s"}}>●</span><span style={{marginLeft:6}}>{t.generating}</span></>):<>{t.generateBtn}</>}
                  </button>
                </div>
              </div>
            )}

            {/* RESULT TAB — empty state */}
            {activeTab==="result"&&!result&&(
              <div className="fade-up" style={{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",padding:"100px 20px",gap:16}}>
                <div style={{fontSize:64,opacity:0.15}}>♻️</div>
                <div style={{fontSize:20,fontWeight:700,color:"#BDBDBD",fontFamily:F}}>{t.noResult}</div>
                <div style={{fontSize:14,color:"#BDBDBD",fontFamily:F}}>{t.noResultSub}</div>
                <button onClick={()=>setActiveTab("optimize")} style={{marginTop:8,padding:"12px 28px",borderRadius:8,border:"none",background:`linear-gradient(135deg,${GL},${G})`,color:"#fff",fontFamily:F,fontSize:14,fontWeight:700,cursor:"pointer"}}>{t.startOpt}</button>
              </div>
            )}

            {/* RESULT TAB — results */}
            {activeTab==="result"&&result&&(()=>{
              if (result.action === "REJECT") return (
                <div className="fade-up" style={{padding:"32px",background:"#FFEBEE",border:"1px solid #EF9A9A",borderRadius:10,color:"#B71C1C"}}>
                  <div style={{fontSize:24,fontWeight:700,fontFamily:F,marginBottom:10}}>REJECTED</div>
                  <div style={{fontSize:15,fontFamily:F,marginBottom:18}}>{result.reason}</div>
                  <div style={{fontSize:13,fontFamily:F}}>Grade {result.grade || "C"} · {result.material_name} · {result.weight_kg} kg</div>
                </div>
              );
              const sm=getSM(result.safety_status);
              const mm=getMM(result.recommended_method);
              const steps=buildSteps(result);
              const radarData=[
                {label:"Efficiency", value:(result.recycling_efficiency_pct||80)/100},
                {label:"Energy",     value:Math.min((result.total_energy_kwh||0)/20,1)},
                {label:"Time",       value:Math.min((result.total_time_min||0)/60,1)},
                {label:"Safety",     value:result.safety_status==="SECURE"?1:result.safety_status==="WARNING"?0.55:0.2},
                {label:"Temp",       value:result.optimal_temp_c?Math.min(result.optimal_temp_c/400,1):0.05},
              ];
              return (
                <div className="fade-up" style={{display:"flex",flexDirection:"column",gap:20}}>
                  {/* Input summary */}
                  <div style={{display:"flex",gap:10,flexWrap:"wrap",padding:"12px 18px",background:"#FFFFFF",borderRadius:8,border:"1px solid #E0E0E0",alignItems:"center"}}>
                    <span style={{fontSize:10,fontWeight:700,color:GL,fontFamily:F,marginRight:4}}>{t.inputSummary}</span>
                    {[
                      {val:`${CAT_ICONS[selectedMaterial.category]} ${selectedMaterial.name}`,col:G,bg:GB,border:GLL+"40"},
                      {val:`⚖️ ${weight} kg`,col:"#37474F",bg:"#ECEFF1",border:"#B0BEC5"},
                      {val:(moisture==="Wet"?"💧 Wet":"☀️ Dry")+(isAutoMoisture?" (IoT)":""),col:moisture==="Wet"?G:"#E65100",bg:moisture==="Wet"?GB:"#FFF3E0",border:moisture==="Wet"?GLL+"40":"#FFCC80"},
                      {val:`Grade ${result.grade||grade}`,col:"#37474F",bg:"#ECEFF1",border:"#B0BEC5"},
                      {val:`${result.moisture_source||"manual"} moisture`,col:"#37474F",bg:"#ECEFF1",border:"#B0BEC5"},
                      {val:`📂 ${selectedMaterial.category}`,col:"#37474F",bg:"#ECEFF1",border:"#B0BEC5"},
                    ].map((tag,i)=>(
                      <span key={i} style={{padding:"4px 12px",borderRadius:20,fontSize:12,fontWeight:600,fontFamily:F,color:tag.col,background:tag.bg,border:`1px solid ${tag.border}`}}>{tag.val}</span>
                    ))}
                    <span style={{marginLeft:"auto",fontSize:11,color:"#BDBDBD",fontFamily:F}}>{result.batch_id}</span>
                  </div>

                  {/* Safety banner */}
                  <div style={{padding:"18px 24px",borderRadius:10,border:`1px solid ${sm.border}`,background:sm.light,display:"flex",alignItems:"center",gap:16}}>
                    <div style={{width:52,height:52,borderRadius:10,background:`${sm.color}18`,border:`1px solid ${sm.border}`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:26,flexShrink:0}}>{sm.icon}</div>
                    <div style={{flex:1}}>
                      <div style={{fontSize:18,fontWeight:700,color:sm.color,fontFamily:F,marginBottom:3}}>{sm.label}</div>
                      <div style={{fontSize:13,color:"#757575",fontFamily:F}}>{result.pre_drying_required?t.safetyWet:t.safetyDry}</div>
                    </div>
                    <div style={{padding:"8px 20px",borderRadius:6,background:sm.color,color:"#FFFFFF",fontSize:13,fontWeight:700,fontFamily:F}}>{result.safety_status}</div>
                  </div>

                  <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:20}}>
                    <div style={{display:"flex",flexDirection:"column",gap:14}}>
                      <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:`1px solid ${mm.color}25`,padding:"20px 22px",borderLeft:`4px solid ${mm.color}`,boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                        <div style={{fontSize:10,fontWeight:700,color:GL,letterSpacing:"0.12em",fontFamily:F,marginBottom:14}}>{t.recMethod}</div>
                        <div style={{display:"flex",alignItems:"center",gap:14}}>
                          <div style={{width:54,height:54,borderRadius:10,background:mm.light,display:"flex",alignItems:"center",justifyContent:"center",fontSize:28,border:`1px solid ${mm.color}25`}}>{mm.icon}</div>
                          <div>
                            <div style={{fontSize:22,fontWeight:700,color:"#1A1A1A",fontFamily:F}}>{result.recommended_method}</div>
                            <div style={{fontSize:12,color:"#9E9E9E",fontFamily:F}}>{mm.desc}</div>
                          </div>
                        </div>
                      </div>

                      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
                        {[
                          {label:t.mTemp,       value:result.optimal_temp_c?`${result.optimal_temp_c}°C`:"No Heat", sub:result.optimal_temp_c?t.mProcTemp:t.mMechOnly, icon:"🌡️",col:"#BF360C"},
                          {label:t.mTime,       value:`${result.processing_time_min} min`, sub:t.mTotalDur, icon:"⏱️",col:GL},
                          {label:t.mEnergy,     value:`${result.energy_kwh} kWh`, sub:t.mConsumption, icon:"⚡",col:"#F57F17"},
                          {label:t.mEfficiency, value:`${result.recycling_efficiency_pct||0}%`, sub:t.mRecovery, icon:"📈",col:G},
                        ].map(m=>(
                          <div key={m.label} className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",padding:"16px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                            <div style={{fontSize:10,fontWeight:700,color:"#BDBDBD",letterSpacing:"0.1em",fontFamily:F,marginBottom:10}}>{m.icon} {m.label.toUpperCase()}</div>
                            <div style={{fontSize:22,fontWeight:700,color:m.col,fontFamily:F}}>{m.value}</div>
                            <div style={{fontSize:11,color:"#9E9E9E",fontFamily:F,marginTop:2}}>{m.sub}</div>
                          </div>
                        ))}
                      </div>

                      <div className="card" style={{background:GB,borderRadius:10,border:`1px solid ${GLL}40`,padding:"16px 18px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                        <div style={{fontSize:10,fontWeight:700,color:GL,letterSpacing:"0.1em",fontFamily:F,marginBottom:7}}>FINAL PRODUCT</div>
                        <div style={{fontSize:16,fontWeight:700,color:G,fontFamily:F}}>{result.final_product}</div>
                      </div>

                      {result.pre_drying_required&&(
                        <div style={{background:GB,borderRadius:10,border:`1px solid ${GLL}60`,padding:"14px 16px"}}>
                          <div style={{fontSize:10,fontWeight:700,color:G,letterSpacing:"0.1em",fontFamily:F,marginBottom:10}}>💧 {t.preDrying.toUpperCase()}</div>
                          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
                            <div><div style={{fontSize:10,color:"#757575",fontFamily:F}}>{t.temperature}</div><div style={{fontSize:18,fontWeight:700,color:G,fontFamily:F}}>{result.pre_drying_temp_c}°C</div></div>
                            <div><div style={{fontSize:10,color:"#757575",fontFamily:F}}>{t.duration}</div><div style={{fontSize:18,fontWeight:700,color:G,fontFamily:F}}>{result.pre_drying_time_min} min</div></div>
                          </div>
                        </div>
                      )}

                      {/* Chemical & Safety */}
                      <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",padding:"18px 20px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                        <div style={{fontSize:10,fontWeight:700,color:GL,letterSpacing:"0.12em",fontFamily:F,marginBottom:14}}>🧪 CHEMICAL & SAFETY INFORMATION</div>
                        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
                          <div style={{background:result.chemical_agent==="None"?GB:"#FFEBEE",borderRadius:8,padding:"12px 14px",border:`1px solid ${result.chemical_agent==="None"?GLL+"40":"#EF9A9A"}`}}>
                            <div style={{fontSize:10,color:"#757575",fontFamily:F,marginBottom:4}}>CHEMICAL AGENT</div>
                            <div style={{fontSize:13,fontWeight:700,fontFamily:F,color:result.chemical_agent==="None"?G:"#C62828"}}>
                              {result.chemical_agent==="None"?"✅ No Chemical Required":result.chemical_agent}
                            </div>
                          </div>
                          <div style={{background:"#F5F5F5",borderRadius:8,padding:"12px 14px",border:"1px solid #E0E0E0"}}>
                            <div style={{fontSize:10,color:"#757575",fontFamily:F,marginBottom:4}}>CONCENTRATION</div>
                            <div style={{fontSize:13,fontWeight:700,color:"#1A1A1A",fontFamily:F}}>{result.chemical_concentration==="None"?"—":result.chemical_concentration}</div>
                          </div>
                          <div style={{gridColumn:"1/-1",background:"#F5F5F5",borderRadius:8,padding:"12px 14px",border:"1px solid #E0E0E0"}}>
                            <div style={{fontSize:10,color:"#757575",fontFamily:F,marginBottom:4}}>PROCESSING PURPOSE</div>
                            <div style={{fontSize:12,color:"#1A1A1A",fontFamily:F}}>{result.chemical_purpose}</div>
                          </div>
                          <div style={{gridColumn:"1/-1",background:"#FFF3E0",borderRadius:8,padding:"12px 14px",border:"1px solid #FFCC80"}}>
                            <div style={{fontSize:10,color:"#E65100",fontWeight:700,fontFamily:F,marginBottom:4}}>⚠️ HANDLING NOTE</div>
                            <div style={{fontSize:12,color:"#BF360C",fontFamily:F}}>{result.handling_note}</div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div style={{display:"flex",flexDirection:"column",gap:14}}>
                      <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",padding:"20px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                        <div style={{fontSize:10,fontWeight:700,color:GL,letterSpacing:"0.12em",fontFamily:F,marginBottom:16}}>{t.processRecipe} — {steps.length} {t.steps}</div>
                        {steps.map((step,idx)=>(
                          <div key={idx} style={{display:"flex",gap:14}}>
                            <div style={{display:"flex",flexDirection:"column",alignItems:"center",width:36,flexShrink:0}}>
                              <div style={{width:36,height:36,borderRadius:"50%",background:step.bg,border:`2px solid ${step.border}`,display:"flex",alignItems:"center",justifyContent:"center",fontSize:16}}>{step.icon}</div>
                              {idx<steps.length-1&&<div style={{width:2,flex:1,background:`linear-gradient(to bottom,${step.border},#E0E0E0)`,margin:"4px 0",minHeight:16}}/>}
                            </div>
                            <div style={{flex:1,background:step.bg,borderRadius:8,border:`1px solid ${step.border}`,padding:"12px 14px",marginBottom:12}}>
                              <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:4}}>
                                <div style={{fontSize:13,fontWeight:700,color:step.color,fontFamily:F}}>{t.stepLabel} {idx+1} — {step.title}</div>
                                <span style={{fontSize:11,color:step.color,background:`${step.color}15`,padding:"2px 8px",borderRadius:12,fontWeight:600,fontFamily:F}}>{step.duration}</span>
                              </div>
                              <div style={{fontSize:11,color:"#757575",fontFamily:F,marginBottom:6}}>{step.desc}</div>
                              <span style={{fontSize:11,color:"#555",background:"rgba(255,255,255,0.7)",padding:"2px 8px",borderRadius:6,border:"1px solid rgba(0,0,0,0.06)",fontFamily:F}}>🌡️ {step.temp}</span>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
                        <div style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",padding:"14px 16px",display:"flex",alignItems:"center",gap:10}}>
                          <div style={{width:36,height:36,borderRadius:8,background:"#FFF3E0",display:"flex",alignItems:"center",justifyContent:"center",fontSize:18}}>⚡</div>
                          <div><div style={{fontSize:10,color:"#9E9E9E",fontFamily:F}}>TOTAL ENERGY</div><div style={{fontSize:18,fontWeight:700,color:"#E65100",fontFamily:F}}>{result.total_energy_kwh} kWh</div><div style={{fontSize:11,color:"#757575",fontFamily:F}}>{result.total_time_min} min total</div></div>
                        </div>
                        <div style={{background:"#FFFFFF",borderRadius:10,border:`1px solid ${sm.border}`,padding:"14px 16px",display:"flex",alignItems:"center",gap:10}}>
                          <div style={{width:36,height:36,borderRadius:8,background:sm.light,display:"flex",alignItems:"center",justifyContent:"center",fontSize:18}}>{sm.icon}</div>
                          <div><div style={{fontSize:10,color:"#9E9E9E",fontFamily:F}}>{t.safetyStatus}</div><div style={{fontSize:18,fontWeight:700,color:sm.color,fontFamily:F}}>{result.safety_status}</div></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Graphs */}
                  <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:16}}>
                    <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",padding:"20px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                      <div style={{fontSize:11,fontWeight:700,color:GL,letterSpacing:"0.1em",fontFamily:F,marginBottom:4}}>{t.perfRadar}</div>
                      <div style={{fontSize:11,color:"#BDBDBD",fontFamily:F,marginBottom:12}}>{t.perfRadarSub}</div>
                      <div style={{display:"flex",justifyContent:"center"}}><Radar data={radarData} size={180}/></div>
                    </div>
                    <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",padding:"20px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                      <div style={{fontSize:11,fontWeight:700,color:GL,letterSpacing:"0.1em",fontFamily:F,marginBottom:4}}>{t.paramAnalysis}</div>
                      <div style={{fontSize:11,color:"#BDBDBD",fontFamily:F,marginBottom:16}}>{t.paramSub}</div>
                      <HBar value={result.recycling_efficiency_pct||0} max={100} color={G} label={t.efficiency} unit="%" delay={0}/>
                      <HBar value={result.total_energy_kwh||0} max={20} color="#E65100" label="Total energy" unit=" kWh" delay={150}/>
                      <HBar value={result.total_time_min||0} max={120} color={GL} label="Total time" unit=" min" delay={300}/>
                      {result.optimal_temp_c&&<HBar value={result.optimal_temp_c} max={400} color="#BF360C" label={t.mTemp} unit="°C" delay={450}/>}
                    </div>
                    <div className="card" style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",padding:"20px",boxShadow:"0 1px 4px rgba(0,0,0,0.05)"}}>
                      <div style={{fontSize:11,fontWeight:700,color:GL,letterSpacing:"0.1em",fontFamily:F,marginBottom:4}}>{t.keyIndicators}</div>
                      <div style={{fontSize:11,color:"#BDBDBD",fontFamily:F,marginBottom:12}}>{t.keyIndSub}</div>
                      <div style={{display:"flex",justifyContent:"space-around",flexWrap:"wrap",gap:8}}>
                        <Donut pct={result.recycling_efficiency_pct||0} color={G} label={t.efficiencyLabel} size={90}/>
                        <Donut pct={Math.min(((result.total_energy_kwh||0)/20)*100,100)} color="#E65100" label={t.energyLoad} size={90}/>
                        <Donut pct={result.safety_status==="SECURE"?100:result.safety_status==="WARNING"?60:20} color={sm.color} label={t.safetyScore} size={90}/>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* HISTORY TAB */}
            {activeTab==="history"&&(
              <div className="fade-up">
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:20}}>
                  <div>
                    <div style={{fontSize:18,fontWeight:700,color:G,fontFamily:F}}>{t.histTitle}</div>
                    <div style={{fontSize:13,color:"#9E9E9E",fontFamily:F,marginTop:2}}>{history.length} {t.histRecords}</div>
                  </div>
                  <button onClick={handleHistory} style={{padding:"8px 18px",borderRadius:8,border:`1px solid ${GLL}40`,background:GB,color:G,cursor:"pointer",fontFamily:F,fontSize:13,fontWeight:600}}>{t.histRefresh}</button>
                </div>
                {history.length===0?(
                  <div style={{textAlign:"center",padding:"80px",background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0"}}>
                    <div style={{fontSize:48,marginBottom:12,opacity:0.2}}>📜</div>
                    <div style={{fontSize:16,fontWeight:700,color:"#BDBDBD",fontFamily:F,marginBottom:6}}>{t.histNoData}</div>
                    <div style={{fontSize:13,color:"#BDBDBD",fontFamily:F}}>{t.histNoSub}</div>
                  </div>
                ):(
                  <div style={{background:"#FFFFFF",borderRadius:10,border:"1px solid #E0E0E0",overflow:"hidden"}}>
                    <div style={{display:"grid",gridTemplateColumns:"2fr 1fr 1fr 1fr 1fr 100px",background:G,padding:"12px 20px"}}>
                      {[t.histMaterial,t.histMethod,t.histWeight,t.histEnergy,t.histMoisture,t.histSafety].map(h=>(
                        <div key={h} style={{fontSize:10,fontWeight:700,color:"#FFFFFF",fontFamily:F,letterSpacing:"0.08em"}}>{h.toUpperCase()}</div>
                      ))}
                    </div>
                    {history.map((h,i)=>{
                      const sm2=getSM(h.safety_status);
                      const mm2=getMM(h.recommended_method);
                      return (
                        <div key={i} className="hist-row" style={{display:"grid",gridTemplateColumns:"2fr 1fr 1fr 1fr 1fr 100px",padding:"13px 20px",borderBottom:i<history.length-1?"1px solid #F5F5F5":"none",alignItems:"center",background:i%2===0?"#FAFAFA":"#FFFFFF"}}>
                          <div>
                            <div style={{fontSize:13,fontWeight:600,color:"#1A1A1A",fontFamily:F}}>{h.material_name}</div>
                            <div style={{fontSize:11,color:"#9E9E9E",fontFamily:F,marginTop:1}}>{h.waste_type}</div>
                          </div>
                          <div style={{fontSize:13,color:mm2.color,fontWeight:600,fontFamily:F}}>{mm2.icon} {h.recommended_method}</div>
                          <div style={{fontSize:13,color:"#555",fontFamily:F}}>{h.weight_kg} kg</div>
                          <div style={{fontSize:13,color:"#E65100",fontWeight:600,fontFamily:F}}>{h.energy_kwh} kWh</div>
                          <div style={{fontSize:13,color:h.moisture_condition==="Wet"?G:"#E65100",fontFamily:F}}>{h.moisture_condition==="Wet"?"💧":"☀️"} {h.moisture_condition}</div>
                          <div style={{padding:"4px 10px",borderRadius:20,fontSize:11,fontWeight:700,textAlign:"center",fontFamily:F,color:sm2.color,background:sm2.light,border:`1px solid ${sm2.border}`}}>
                            {sm2.icon} {h.safety_status}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

          </div>
        </div>
      </div>
    </>
  );
}