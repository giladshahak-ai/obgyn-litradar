"""
מחולל אתר הדייג'סט הסטטי — קורא את הבחירה השבועית מה-DB ומייצר site/index.html
עצמאי (RTL מלא, אינטראקטיבי). הרצה:  python build_site.py
"""
import json
from pathlib import Path
from datetime import date, timedelta

from app import db
from app.digest import digest_with_analyses, _PRIMARY_LIST
from app.config import DIGEST_PER_JOURNAL, DIGEST_WINDOW_DAYS

OUT_DIR = Path(__file__).resolve().parent / "site"
OUT_DIR.mkdir(exist_ok=True)
BASE_DIR_DOCS = Path(__file__).resolve().parent / "docs"


def build(window_days: int = DIGEST_WINDOW_DAYS, per_journal: int = DIGEST_PER_JOURNAL,
          today: str | None = None) -> Path:
    if today is None:
        today = date.today().strftime("%d/%m/%Y")
    db.init_db()
    items = digest_with_analyses(per_journal=per_journal, window_days=window_days)
    data = []
    for a in items:
        data.append({
            "pmid": a["pmid"],
            "title": a["title"],
            "abstract": a.get("abstract") or "",
            "journal": a.get("journal_nick") or a.get("journal") or "",
            "journal_full": a.get("journal") or "",
            "date": a.get("pub_date") or "",
            "authors": a.get("authors") or [],
            "topics": a.get("topics") or [],
            "pub_types": a.get("pub_types") or [],
            "importance": round(a.get("importance", 0)),
            "doi": a.get("doi") or "",
            "analysis": a.get("analysis"),
            "analysis_scope": a.get("analysis_scope"),
        })

    journals = [j.get("nick") or j["name"] for j in _PRIMARY_LIST]
    meta = {
        "count": len(data),
        "journals": journals,
        "per_journal": per_journal,
        "window_days": window_days,
        "generated": today or "",
    }
    html = TEMPLATE.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False)) \
                   .replace("/*__META__*/", json.dumps(meta, ensure_ascii=False))
    out = OUT_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    # כתיבה גם ל-docs/ (מקור GitHub Pages) כדי שהאתר החי יתעדכן
    docs = BASE_DIR_DOCS
    docs.mkdir(exist_ok=True)
    (docs / "index.html").write_text(html, encoding="utf-8")
    (docs / "digest.html").write_text(html, encoding="utf-8")
    return out


TEMPLATE = r"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LitRadar · דייג'סט שבועי</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#eef2f9; --card:#ffffff; --ink:#16203a; --muted:#69748c;
  --line:#e4e9f2; --brand:#2f6df6; --brand-2:#13b5b1; --soft:#eaf1ff;
  --hi:#15914a; --hi-bg:#e3f6ea; --mid:#b07a00; --mid-bg:#fcf3da; --lo:#5b6678; --lo-bg:#eef1f6;
}
*{box-sizing:border-box}
body{margin:0;font-family:'Heebo',sans-serif;background:var(--bg);color:var(--ink);}
a{color:inherit;text-decoration:none}

/* hero */
.hero{background:linear-gradient(125deg,#2f6df6 0%,#5b8def 55%,#13b5b1 130%);color:#fff;padding:30px 0 70px;}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px;}
.hero h1{margin:0;font-size:30px;font-weight:900;letter-spacing:-.6px;display:flex;align-items:center;gap:10px}
.hero .sub{margin-top:8px;opacity:.95;font-size:15px;font-weight:400}
.hero .stats{margin-top:16px;display:flex;gap:22px;flex-wrap:wrap;font-size:13px;opacity:.95}
.hero .stats b{font-size:18px;display:block;font-weight:800}

/* toolbar */
.toolbar{max-width:1080px;margin:-44px auto 0;padding:14px 16px;background:#fff;border:1px solid var(--line);
  border-radius:16px;box-shadow:0 10px 30px rgba(20,30,70,.10);display:flex;gap:12px;align-items:center;flex-wrap:wrap;position:sticky;top:10px;z-index:30}
.search{flex:1;min-width:200px;display:flex;align-items:center;gap:8px;background:#f3f6fc;border:1px solid var(--line);border-radius:11px;padding:9px 13px}
.search input{border:0;background:transparent;outline:0;width:100%;font-family:inherit;font-size:14px;color:var(--ink)}
.sortsel{border:1px solid var(--line);border-radius:11px;padding:9px 12px;background:#fff;font-family:inherit;font-size:14px;color:var(--ink);cursor:pointer}
.seg{display:flex;border:1px solid var(--line);border-radius:11px;overflow:hidden}
.seg button{border:0;background:#fff;padding:9px 14px;font-family:inherit;font-size:13.5px;font-weight:600;color:#43506a;cursor:pointer;transition:.15s}
.seg button.on{background:var(--brand);color:#fff}
.jhead{max-width:1080px;margin:8px 0 2px;padding:6px 14px;font-weight:800;font-size:15px;color:#10243f;border-right:4px solid #10243f;background:#fff;border-radius:10px}

/* journal chips */
.chips{max-width:1080px;margin:14px auto 0;padding:0 16px;display:flex;gap:8px;flex-wrap:wrap}
.jchip{border:1px solid var(--line);background:#fff;border-radius:20px;padding:6px 14px;font-size:13px;font-weight:600;cursor:pointer;transition:.15s;color:#43506a}
.jchip:hover{border-color:var(--brand);color:var(--brand)}
.jchip.on{background:var(--brand);color:#fff;border-color:var(--brand)}

/* feed */
.feed{max-width:1080px;margin:18px auto 60px;padding:0 16px;display:grid;gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px 22px;
  box-shadow:0 2px 10px rgba(20,30,70,.04);transition:.18s;animation:rise .4s ease both}
.card:hover{box-shadow:0 14px 34px rgba(20,30,70,.10);transform:translateY(-2px)}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.card .head{display:flex;gap:16px;align-items:flex-start}
.ring{flex:none;width:62px;height:62px;border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;font-weight:900;font-size:21px;line-height:1}
.ring small{font-size:9px;font-weight:600;opacity:.85;margin-top:2px}
.r-hi{background:var(--hi-bg);color:var(--hi);box-shadow:inset 0 0 0 2px var(--hi)}
.r-mid{background:var(--mid-bg);color:var(--mid);box-shadow:inset 0 0 0 2px var(--mid)}
.r-lo{background:var(--lo-bg);color:var(--lo);box-shadow:inset 0 0 0 2px #aeb8c8}
.ttl{display:block;font-size:18.5px;font-weight:700;line-height:1.45}
.ttl:hover{color:var(--brand)}
.meta{color:var(--muted);font-size:13px;margin-top:6px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.jpill{background:#10243f;color:#fff;border-radius:7px;padding:2px 9px;font-size:12px;font-weight:700}
.tags{margin-top:11px;display:flex;gap:6px;flex-wrap:wrap}
.tag{border-radius:20px;padding:3px 11px;font-size:12px;font-weight:600}
.t-star{background:#fff2cc;color:#8a6a00}
.t-topic{background:var(--soft);color:#274aa8}
.actions{margin-top:14px;display:flex;gap:9px;flex-wrap:wrap}
.btn{border:1px solid var(--line);background:#fff;border-radius:11px;padding:9px 16px;font-family:inherit;font-size:14px;
  font-weight:700;cursor:pointer;transition:.15s;display:inline-flex;align-items:center;gap:7px}
.btn:hover{border-color:var(--brand);color:var(--brand);background:#f7faff}
.btn-primary{background:var(--brand);color:#fff;border-color:var(--brand)}
.btn-primary:hover{background:#1f5be0;color:#fff}
.btn-primary.active{background:#10243f;border-color:#10243f}
.btn:focus-visible,.jchip:focus-visible,.sortsel:focus-visible,.search input:focus-visible,.ttl:focus-visible{outline:3px solid #1652d6;outline-offset:2px;border-radius:8px}
.search:focus-within{border-color:var(--brand);box-shadow:0 0 0 3px rgba(47,109,246,.15)}
.panel{margin-top:14px;border-top:1px dashed var(--line);padding-top:14px;display:none}
.panel.open{display:block;animation:rise .3s ease both}
.abx{color:#33405c;font-size:14.5px;line-height:1.7}

/* analysis */
.an-verdict{background:linear-gradient(90deg,#fff7df,#fffdf6);border-right:5px solid #e7b400;padding:13px 16px;border-radius:11px;font-weight:700;font-size:15.5px;margin-bottom:12px}
.an-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.an-h{font-weight:800;font-size:14px;margin:14px 0 7px;display:flex;align-items:center;gap:6px}
.an-strong{background:#edf9f0;border-right:3px solid #2a9d4a;padding:8px 12px;border-radius:9px;margin:6px 0;font-size:13.5px;line-height:1.55}
.an-weak{background:#fdeeee;border-right:3px solid #d9534f;padding:8px 12px;border-radius:9px;margin:6px 0;font-size:13.5px;line-height:1.55}
.sev{font-weight:800;font-size:11px;border-radius:6px;padding:1px 6px;margin-left:5px}
.sev-גבוהה{background:#d9534f;color:#fff}.sev-בינונית{background:#e8a200;color:#fff}.sev-נמוכה{background:#9aa6b8;color:#fff}
.an-info{background:#eaf3ff;border:1px solid #cfe0fb;padding:11px 14px;border-radius:11px;font-size:14px;line-height:1.65;margin:8px 0}
.an-bottom{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:12px}
.an-box{background:#f6f8fc;border:1px solid var(--line);border-radius:11px;padding:11px 14px;font-size:13.5px;line-height:1.6}
.an-box b{display:block;margin-bottom:5px}
.an-rounds{margin-top:12px;background:#e8f7ee;border:1px solid #bfe6cd;border-radius:11px;padding:11px 14px;font-weight:600}
.scope-warn{background:#fff3cd;border:1px solid #f3df9a;border-radius:10px;padding:9px 13px;font-size:13px;margin-bottom:10px}
.empty{text-align:center;color:var(--muted);padding:50px 0}
.badge5{background:#10243f;color:#fff;border-radius:9px;padding:5px 11px;font-weight:800;font-size:14px}
@media(max-width:680px){
  .an-grid,.an-bottom{grid-template-columns:1fr}
  .hero{padding:22px 0 64px}.hero h1{font-size:22px}.hero .sub{font-size:13px}
  .hero .stats{gap:14px}.hero .stats b{font-size:15px}
  .toolbar{margin-top:-40px;flex-direction:column;align-items:stretch}
  .sortsel{width:100%}
  .card{padding:16px 16px}.card .head{gap:11px}
  .ring{width:52px;height:52px;font-size:18px}
  .ttl{font-size:16.5px}
  .btn{padding:8px 13px;font-size:13px}
  .feed{margin-top:14px}
}
.foot{max-width:1080px;margin:0 auto 40px;padding:0 16px;color:var(--muted);font-size:12.5px;text-align:center}
.legend{max-width:1080px;margin:0 auto 8px;padding:0 16px;display:flex;gap:14px;flex-wrap:wrap;justify-content:center;font-size:12px;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:5px}
.dot{width:11px;height:11px;border-radius:3px;display:inline-block}
.fab{position:fixed;bottom:22px;left:22px;display:flex;flex-direction:column;gap:10px;z-index:50}
.fab button{width:46px;height:46px;border-radius:50%;border:0;background:#fff;color:var(--brand);box-shadow:0 6px 18px rgba(20,30,70,.18);
  font-size:18px;cursor:pointer;transition:.15s}
.fab button:hover{background:var(--brand);color:#fff;transform:translateY(-2px)}
@media print{
  body{background:#fff}
  .toolbar,.chips,.fab,.actions,.hero .stats{display:none!important}
  .hero{background:#fff!important;color:#10243f!important;box-shadow:none;padding:6px 0}
  .card{break-inside:avoid;box-shadow:none;border:1px solid #ccc;margin-bottom:10px}
  .panel{display:block!important}
  .ring{box-shadow:none!important;border:1.5px solid #444}
  a{color:#10243f!important}
}
</style>
</head>
<body>
<div class="hero"><div class="wrap">
  <h1>🩺 LitRadar — דייג'סט שבועי</h1>
  <div class="sub">המאמרים הנבחרים מעיתוני הליבה · רק RCT, מטא-אנליזות, סקירות והנחיות · מדורגים לפי חשיבות</div>
  <div class="stats" id="stats"></div>
</div></div>

<div class="toolbar">
  <div class="search">🔎<input id="q" aria-label="חיפוש מאמרים" placeholder="חיפוש בכותרת / תקציר / נושא…" oninput="render()"></div>
  <select class="sortsel" id="topic" aria-label="סינון לפי נושא" onchange="render()">
    <option value="">כל הנושאים</option>
  </select>
  <select class="sortsel" id="sort" aria-label="מיון" onchange="render()">
    <option value="imp">מיון: חשיבות</option>
    <option value="date">מיון: תאריך</option>
    <option value="journal">מיון: עיתון</option>
  </select>
  <div class="seg">
    <button id="vr" class="on" onclick="setView('rank')">מדורג</button>
    <button id="vg" onclick="setView('group')">לפי עיתון</button>
  </div>
</div>
<div class="chips" id="chips"></div>
<div class="feed" id="feed"></div>
<div class="legend" id="legend"></div>
<div class="foot" id="foot"></div>
<div class="fab">
  <button title="הדפסה לג'רנל קלאב" aria-label="הדפסה" onclick="printAll()">🖨</button>
  <button title="חזרה למעלה" aria-label="חזרה למעלה" onclick="window.scrollTo({top:0,behavior:'smooth'})">↑</button>
</div>

<script>
const DATA = /*__DATA__*/;
const META = /*__META__*/;
let activeJournal = null;
let viewMode = 'rank';

function ringCls(v){return v>=65?'r-hi':v>=52?'r-mid':'r-lo';}
const JCOLOR={'AJOG':'#1f6feb','Green Journal':'#15803d','BJOG':'#7c3aed','NEJM':'#a4262c','Lancet':'#b51f2e','White Journal?':'#475569'};
function jColor(n){return JCOLOR[n]||'#10243f';}
function hvLabel(a){
  const pt=(a.pub_types||[]).join(' '); const t=(a.title||'').toLowerCase();
  if(pt.includes('Randomized')||t.includes('randomi'))return'RCT';
  if(pt.includes('Meta-Analysis')||t.includes('meta-analysis')||t.includes('metaanalysis'))return'מטא-אנליזה';
  if(pt.includes('Systematic Review')||t.includes('systematic review'))return'סקירה שיטתית';
  if(pt.includes('Guideline')||t.includes('guideline')||t.includes('committee opinion'))return'הנחיה';
  if(pt.includes('Phase III')||t.includes('phase 3')||t.includes('phase iii'))return'Phase III';
  return null;
}
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

function renderStats(){
  document.getElementById('stats').innerHTML =
    `<div><b>${META.count}</b> מאמרים נבחרים</div>`+
    `<div><b>${META.journals.length}</b> עיתוני ליבה</div>`+
    `<div><b>${META.per_journal}</b> מקס׳ לעיתון</div>`+
    `<div><b>${META.window_days}</b> ימים אחרונים</div>`+
    (META.generated?`<div><b>${esc(META.generated)}</b> עודכן</div>`:'');
  document.getElementById('foot').textContent =
    'LitRadar · כלי עזר לקריאה ביקורתית — אינו תחליף לקריאת המאמר המלא ולשיקול דעת קליני.';
}
function renderChips(){
  const counts={}; DATA.forEach(a=>counts[a.journal]=(counts[a.journal]||0)+1);
  const el=document.getElementById('chips'); el.innerHTML='';
  const all=document.createElement('div'); all.className='jchip'+(activeJournal?'':' on');
  all.textContent='הכל ('+DATA.length+')'; all.onclick=()=>{activeJournal=null;renderChips();render();};
  el.appendChild(all);
  Object.keys(counts).forEach(j=>{
    const c=document.createElement('div'); c.className='jchip'+(activeJournal===j?' on':'');
    c.textContent=j+' ('+counts[j]+')'; c.onclick=()=>{activeJournal=activeJournal===j?null:j;renderChips();render();};
    el.appendChild(c);
  });
}
function analysisHTML(an,scope){
  if(!an)return '<div class="an-info">אין עדיין ניתוח שמור למאמר זה. הניתוח האוטומטי ("המבקר הקליני") ירוץ באפליקציה עם מפתח ה-API.</div>';
  let h='';
  if(scope==='ABSTRACT_ONLY')h+='<div class="scope-warn">⚠️ ניתוח מבוסס תקציר בלבד.</div>';
  if(an.source_scope_warning)h+='<div class="scope-warn">'+esc(an.source_scope_warning)+'</div>';
  h+=`<div style="display:flex;gap:12px;align-items:center;margin-bottom:6px">
     <span class="badge5">${esc(String(an.critic_score))}/5</span>
     <div class="an-verdict" style="flex:1;margin:0">⚖️ ${esc(an.verdict_line)}</div></div>`;
  if(an.score_rationale)h+=`<div style="color:#69748c;font-size:13px;margin-bottom:6px">${esc(an.score_rationale)}</div>`;
  if(an.evidence_level)h+=`<div style="font-size:13.5px;margin-bottom:8px"><b>רמת ראיות:</b> ${esc(an.evidence_level)}</div>`;
  const s=an.study_snapshot||{};
  h+=`<div class="an-box"><b>📋 תמצית המחקר</b>תכנון: ${esc(s.design)} · אוכלוסייה: ${esc(s.population)} · N: ${esc(s.n)}<br>תוצא ראשוני: ${esc(s.primary_outcome)}<br>תוצאה: ${esc(s.key_result)}</div>`;
  h+='<div class="an-grid"><div><div class="an-h">✅ חוזקות</div>';
  (an.strengths||[]).forEach(x=>h+=`<div class="an-strong">${esc(x)}</div>`);
  h+='</div><div><div class="an-h">⚠️ חולשות</div>';
  (an.weaknesses||[]).forEach(w=>{ if(typeof w==='object')h+=`<div class="an-weak"><span class="sev sev-${esc(w.severity)}">${esc(w.severity)}</span>${esc(w.issue)}<br><small>${esc(w.impact)}</small></div>`; else h+=`<div class="an-weak">${esc(w)}</div>`;});
  h+='</div></div>';
  if(an.spin_alert&&an.spin_alert.detected)h+=`<div class="an-h">🎈 התראת Spin</div><div class="an-weak"><b>ציטוט:</b> "${esc(an.spin_alert.quote)}"<br><b>המציאות:</b> ${esc(an.spin_alert.reality)}</div>`;
  if((an.stats_red_flags||[]).length){h+='<div class="an-h">🚩 דגלים סטטיסטיים</div>';an.stats_red_flags.forEach(f=>h+=`<div class="an-weak">${esc(f)}</div>`);}
  h+=`<div class="an-h">🩺 שורה תחתונה קלינית</div><div class="an-info">${esc(an.clinical_bottom_line)}</div>`;
  h+=`<div class="an-bottom"><div class="an-box"><b>🔄 מה היה משנה את ההכרעה</b>${esc(an.what_would_change_my_mind)}</div><div class="an-box"><b>😈 פרקליט השטן</b>${esc(an.devils_advocate)}</div></div>`;
  if(an.one_liner_for_rounds)h+=`<div class="an-rounds">💬 לג'רנל קלאב: "${esc(an.one_liner_for_rounds)}"</div>`;
  return h;
}
function cardHTML(a,i){
  const hv=hvLabel(a);
  const auth=(a.authors||[]); const am=auth.length?(esc(auth[0])+(auth.length>1?' et al.':'')):'';
  const tags=(hv?`<span class="tag t-star">⭐ ${hv}</span>`:'')+(a.topics||[]).map(t=>`<span class="tag t-topic">${esc(t)}</span>`).join('');
  return `<div class="card" style="animation-delay:${i*30}ms;border-right:5px solid ${jColor(a.journal)}">
    <div class="head">
      <div class="ring ${ringCls(a.importance)}">${a.importance}<small>חשיבות</small></div>
      <div style="flex:1">
        <a class="ttl" dir="auto" href="https://pubmed.ncbi.nlm.nih.gov/${a.pmid}/" target="_blank">${esc(a.title)}</a>
        <div class="meta"><span class="jpill" style="background:${jColor(a.journal)}">${esc(a.journal)}</span><span>${esc(a.date)}</span>${am?'<span>·&nbsp;<bdi>'+am+'</bdi></span>':''}</div>
        <div class="tags">${tags}</div>
        <div class="actions">
          <button class="btn btn-primary" aria-label="הצג ניתוח ביקורתי" onclick="toggleAn(this,${i})">⚡ ניתוח ביקורתי</button>
          <button class="btn" aria-label="הצג תקציר" onclick="toggle(${i},'ab')">📄 תקציר</button>
          ${a.doi?`<a class="btn" href="https://doi.org/${esc(a.doi)}" target="_blank" aria-label="פתח מקור">🔗 מקור</a>`:''}
        </div>
        <div class="panel" id="ab-${i}"><div class="abx" dir="auto">${esc(a.abstract)||'— אין תקציר —'}</div></div>
        <div class="panel" id="an-${i}">${analysisHTML(a.analysis,a.analysis_scope)}</div>
      </div>
    </div></div>`;
}
function toggle(i,kind){
  const p=document.getElementById(kind+'-'+i); p.classList.toggle('open');
}
function toggleAn(btn,i){
  const p=document.getElementById('an-'+i); const open=p.classList.toggle('open');
  btn.classList.toggle('active',open);
  btn.innerHTML = open?'✕ סגור ניתוח':'⚡ ניתוח ביקורתי';
}
function renderLegend(){
  const used={}; DATA.forEach(a=>used[a.journal]=jColor(a.journal));
  document.getElementById('legend').innerHTML='<b>עיתוני ליבה:</b> '+
    Object.keys(used).map(j=>`<span><i class="dot" style="background:${used[j]}"></i>${esc(j)}</span>`).join('');
}
function printAll(){
  document.querySelectorAll('[id^="an-"]').forEach(p=>p.classList.add('open'));
  setTimeout(()=>window.print(),60);
}
function populateTopics(){
  const set=new Set(); DATA.forEach(a=>(a.topics||[]).forEach(t=>set.add(t)));
  const sel=document.getElementById('topic');
  [...set].sort().forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=t;sel.appendChild(o);});
}
function render(){
  const q=(document.getElementById('q').value||'').toLowerCase().trim();
  const sort=document.getElementById('sort').value;
  const topic=document.getElementById('topic').value;
  let list=DATA.filter(a=>{
    if(activeJournal&&a.journal!==activeJournal)return false;
    if(topic&&!(a.topics||[]).includes(topic))return false;
    if(!q)return true;
    return (a.title+' '+a.abstract+' '+(a.topics||[]).join(' ')).toLowerCase().includes(q);
  });
  if(sort==='imp')list.sort((x,y)=>y.importance-x.importance);
  if(sort==='date')list.sort((x,y)=>(y.date||'').localeCompare(x.date||''));
  if(sort==='journal')list.sort((x,y)=>(x.journal||'').localeCompare(y.journal||''));
  const feed=document.getElementById('feed');
  if(!list.length){feed.innerHTML='<div class="empty">לא נמצאו מאמרים תואמים.</div>';return;}
  if(viewMode==='group'){
    const order={}; META.journals.forEach((j,k)=>order[j]=k);
    list.sort((x,y)=>(order[x.journal]??99)-(order[y.journal]??99)||y.importance-x.importance);
    let html='',last=null,idx=0;
    list.forEach(a=>{
      if(a.journal!==last){html+=`<div class="jhead" style="border-color:${jColor(a.journal)}">${esc(a.journal)}</div>`;last=a.journal;}
      html+=cardHTML(a,idx++);
    });
    feed.innerHTML=html;
  } else {
    feed.innerHTML=list.map((a,i)=>cardHTML(a,i)).join('');
  }
}
function setView(m){
  viewMode=m;
  document.getElementById('vr').classList.toggle('on',m==='rank');
  document.getElementById('vg').classList.toggle('on',m==='group');
  render();
}
document.addEventListener('keydown',e=>{
  if(e.key==='/'&&document.activeElement.id!=='q'){e.preventDefault();document.getElementById('q').focus();}
  if(e.key==='Escape'&&document.activeElement.id==='q'){document.getElementById('q').value='';render();}
});
function savePrefs(){try{localStorage.setItem('lr_sort',document.getElementById('sort').value);
  localStorage.setItem('lr_topic',document.getElementById('topic').value);}catch(e){}}
function loadPrefs(){try{const s=localStorage.getItem('lr_sort'),t=localStorage.getItem('lr_topic');
  if(s)document.getElementById('sort').value=s;
  if(t&&[...document.getElementById('topic').options].some(o=>o.value===t))document.getElementById('topic').value=t;}catch(e){}}
renderStats();populateTopics();loadPrefs();renderChips();renderLegend();render();
document.getElementById('sort').addEventListener('change',savePrefs);
document.getElementById('topic').addEventListener('change',savePrefs);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    p = build()
    print("נוצר:", p)
