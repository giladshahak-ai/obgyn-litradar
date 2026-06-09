"""
מחולל אתר הדייג'סט הסטטי — קורא את הבחירה מה-DB ומייצר docs/index.html
עצמאי (RTL, אינטראקטיבי, פלטת פסטל יוקרתי). הרצה:  python build_site.py
האתר אופה "superset" גדול; הפקדים באתר מסננים זמן/כמות בזמן אמת.
"""
import json
from pathlib import Path
from datetime import date

from app import db
from app.digest import digest_with_analyses, _PRIMARY_LIST
from app.scoring import importance_breakdown
from app.config import (DIGEST_PER_JOURNAL, DIGEST_WINDOW_DAYS, DIGEST_MAX_TOTAL,
                        DIGEST_BAKE_WINDOW_DAYS, DIGEST_BAKE_PER_JOURNAL)

OUT_DIR = Path(__file__).resolve().parent / "site"
OUT_DIR.mkdir(exist_ok=True)
DOCS_DIR = Path(__file__).resolve().parent / "docs"


def _rescore_db():
    """מרענן ציוני חשיבות לכל המאמרים לפי הנוסחה הנוכחית (3 גורמים)."""
    for a in db.query_articles(limit=5000):
        new = importance_breakdown(a)["total"]
        if abs(new - (a.get("importance") or 0)) > 0.05:
            a["importance"] = new
            db.upsert_article(a)


def build(today: str | None = None) -> Path:
    if today is None:
        today = date.today().strftime("%d/%m/%Y")
    db.init_db()
    _rescore_db()
    # אופים superset; הפקדים באתר מסננים ממנו
    items = digest_with_analyses(per_journal=DIGEST_BAKE_PER_JOURNAL,
                                 window_days=DIGEST_BAKE_WINDOW_DAYS)
    data = []
    for a in items:
        data.append({
            "pmid": a["pmid"],
            "title": a["title"],
            "abstract": a.get("abstract") or "",
            "journal": a.get("journal_nick") or a.get("journal") or "",
            "date": a.get("pub_date") or "",
            "authors": a.get("authors") or [],
            "topics": a.get("topics") or [],
            "pub_types": a.get("pub_types") or [],
            "importance": round(a.get("importance", 0)),
            "breakdown": importance_breakdown(a),
            "doi": a.get("doi") or "",
            "analysis": a.get("analysis"),
            "analysis_scope": a.get("analysis_scope"),
        })

    meta = {
        "count": len(data),
        "journals": [j.get("nick") or j["name"] for j in _PRIMARY_LIST],
        "default_per_journal": DIGEST_PER_JOURNAL,
        "default_window": DIGEST_WINDOW_DAYS,
        "max_total": DIGEST_MAX_TOTAL,
        "generated": today,
        "today_iso": date.today().isoformat(),
    }
    html = TEMPLATE.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False)) \
                   .replace("/*__META__*/", json.dumps(meta, ensure_ascii=False))
    out = OUT_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
    (DOCS_DIR / "digest.html").write_text(html, encoding="utf-8")
    return out


TEMPLATE = r"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LitRadar · דייג'סט שבועי</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&family=Frank+Ruhl+Libre:wght@500;700;900&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#F4F1EC; --card:#FBF9F5; --ink:#33302B; --muted:#7C766C; --line:#E6E0D6;
  --brand:#7E6A8F; --brand-d:#5F4F6E; --soft:#EEEAE2;
  --hi:#3F6149; --hi-bg:#E1ECE2; --mid:#8A6A3A; --mid-bg:#F3E8D5; --lo:#5E5950; --lo-bg:#E8E6E1;
  --chip-bg:#EEEAE2; --chip-fg:#5E584E; --star-bg:#F3E7CF; --star-fg:#8A6B33;
  --strong-bg:#E4EDE5; --strong-bd:#9DBFA4; --weak-bg:#F5E7E4; --weak-bd:#D6AfA6;
  --verdict-bg:#ECE8F0; --verdict-bd:#D0C6DA;
}
*{box-sizing:border-box}
body{margin:0;font-family:'Heebo',sans-serif;background:var(--bg);color:var(--ink);}
a{color:inherit;text-decoration:none}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px;}

/* hero */
.hero{background:linear-gradient(125deg,#EDE4E0 0%,#E7E2EC 55%,#E1E8E4 130%);color:var(--ink);padding:30px 0 66px;border-bottom:1px solid var(--line);}
.hero h1{margin:0;font-family:'Frank Ruhl Libre',serif;font-size:32px;font-weight:900;letter-spacing:-.4px;display:flex;align-items:center;gap:10px}
.hero .sub{margin-top:8px;color:#6a6258;font-size:15px;font-weight:400;max-width:680px}
.hero .stats{margin-top:18px;display:flex;gap:26px;flex-wrap:wrap;font-size:12.5px;color:#6a6258}
.hero .stats b{font-size:19px;display:block;font-weight:800;color:var(--ink);font-family:'Frank Ruhl Libre',serif}

/* toolbar */
.toolbar{max-width:1080px;margin:-42px auto 0;padding:13px 15px;background:var(--card);border:1px solid var(--line);
  border-radius:16px;box-shadow:0 12px 34px rgba(90,70,60,.10);display:flex;gap:10px;align-items:center;flex-wrap:wrap;position:sticky;top:10px;z-index:30}
.search{flex:1;min-width:190px;display:flex;align-items:center;gap:8px;background:#F4F1EC;border:1px solid var(--line);border-radius:11px;padding:9px 13px}
.search input{border:0;background:transparent;outline:0;width:100%;font-family:inherit;font-size:14px;color:var(--ink)}
.search:focus-within{border-color:var(--brand);box-shadow:0 0 0 3px rgba(126,106,143,.15)}
.ctl{display:flex;flex-direction:column;gap:2px}
.ctl label{font-size:10px;color:var(--muted);padding-right:3px}
.sortsel{border:1px solid var(--line);border-radius:10px;padding:8px 11px;background:var(--card);font-family:inherit;font-size:13.5px;color:var(--ink);cursor:pointer}
.seg{display:flex;border:1px solid var(--line);border-radius:10px;overflow:hidden;align-self:flex-end}
.seg button{border:0;background:var(--card);padding:8px 13px;font-family:inherit;font-size:13px;font-weight:600;color:#6a6258;cursor:pointer;transition:.15s}
.seg button.on{background:var(--brand);color:#fff}

.chips{max-width:1080px;margin:14px auto 0;padding:0 16px;display:flex;gap:8px;flex-wrap:wrap}
.jchip{border:1px solid var(--line);background:var(--card);border-radius:20px;padding:6px 14px;font-size:13px;font-weight:600;cursor:pointer;transition:.15s;color:#5e574c}
.jchip:hover{border-color:var(--brand);color:var(--brand)}
.jchip.on{background:var(--brand);color:#fff;border-color:var(--brand)}

.countbar{max-width:1080px;margin:12px auto 0;padding:0 18px;color:var(--muted);font-size:13px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
.countbar b{color:var(--ink)}

/* feed */
.feed{max-width:1080px;margin:10px auto 60px;padding:0 16px;display:grid;gap:15px}
.jhead{margin:10px 0 0;padding:7px 15px;font-family:'Frank Ruhl Libre',serif;font-weight:700;font-size:16px;color:var(--ink);border-right:4px solid var(--ink);background:var(--card);border-radius:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px 22px;
  box-shadow:0 2px 10px rgba(90,70,60,.05);transition:.18s;animation:rise .4s ease both}
.card:hover{box-shadow:0 16px 38px rgba(90,70,60,.12);transform:translateY(-2px)}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.card .head{display:flex;gap:16px;align-items:flex-start}
.ring{flex:none;width:64px;height:64px;border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;font-weight:800;font-size:21px;line-height:1;cursor:help;font-family:'Frank Ruhl Libre',serif}
.ring small{font-size:9px;font-weight:600;opacity:.85;margin-top:2px;font-family:'Heebo',sans-serif}
.r-hi{background:var(--hi-bg);color:var(--hi);box-shadow:inset 0 0 0 2px var(--hi)}
.r-mid{background:var(--mid-bg);color:var(--mid);box-shadow:inset 0 0 0 2px var(--mid)}
.r-lo{background:var(--lo-bg);color:var(--lo);box-shadow:inset 0 0 0 2px #C9C2B6}
.ttl{display:block;font-size:18.5px;font-weight:700;line-height:1.45}
.ttl:hover{color:var(--brand)}
.meta{color:var(--muted);font-size:13px;margin-top:6px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.jpill{color:#fff;border-radius:7px;padding:2px 9px;font-size:12px;font-weight:700;background:#5E584E}
.tags{margin-top:11px;display:flex;gap:6px;flex-wrap:wrap}
.tag{border-radius:20px;padding:3px 11px;font-size:12px;font-weight:600}
.t-star{background:var(--star-bg);color:var(--star-fg)}
.t-topic{background:var(--chip-bg);color:var(--chip-fg)}
.actions{margin-top:14px;display:flex;gap:9px;flex-wrap:wrap}
.btn{border:1px solid var(--line);background:var(--card);border-radius:11px;padding:9px 16px;font-family:inherit;font-size:14px;
  font-weight:700;cursor:pointer;transition:.15s;display:inline-flex;align-items:center;gap:7px;color:var(--ink)}
.btn:hover{border-color:var(--brand);color:var(--brand);background:#F6F2F8}
.btn-primary{background:var(--brand);color:#fff;border-color:var(--brand)}
.btn-primary:hover{background:var(--brand-d);color:#fff}
.btn-primary.active{background:var(--brand-d);border-color:var(--brand-d)}
.btn:focus-visible,.jchip:focus-visible,.sortsel:focus-visible,.search input:focus-visible,.ttl:focus-visible{outline:3px solid var(--brand);outline-offset:2px;border-radius:8px}
.panel{margin-top:14px;border-top:1px dashed var(--line);padding-top:14px;display:none}
.panel.open{display:block;animation:rise .3s ease both}
.abx{color:#4a443b;font-size:14.5px;line-height:1.7}

/* analysis */
.an-verdict{background:var(--verdict-bg);border-right:5px solid var(--verdict-bd);padding:13px 16px;border-radius:11px;font-weight:700;font-size:15.5px;margin-bottom:12px}
.an-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.an-h{font-weight:800;font-size:14px;margin:14px 0 7px;display:flex;align-items:center;gap:6px}
.an-strong{background:var(--strong-bg);border-right:3px solid var(--strong-bd);padding:8px 12px;border-radius:9px;margin:6px 0;font-size:13.5px;line-height:1.55}
.an-weak{background:var(--weak-bg);border-right:3px solid var(--weak-bd);padding:8px 12px;border-radius:9px;margin:6px 0;font-size:13.5px;line-height:1.55}
.sev{font-weight:800;font-size:11px;border-radius:6px;padding:1px 6px;margin-left:5px;color:#fff}
.sev-גבוהה{background:#B5736B}.sev-בינונית{background:#B89055}.sev-נמוכה{background:#9aa28f}
.an-info{background:#EAEFE9;border:1px solid #CFE0CE;padding:11px 14px;border-radius:11px;font-size:14px;line-height:1.65;margin:8px 0}
.an-bottom{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:12px}
.an-box{background:#F4F1EC;border:1px solid var(--line);border-radius:11px;padding:11px 14px;font-size:13.5px;line-height:1.6}
.an-box b{display:block;margin-bottom:5px}
.an-rounds{margin-top:12px;background:var(--strong-bg);border:1px solid var(--strong-bd);border-radius:11px;padding:11px 14px;font-weight:600}
.scope-warn{background:var(--mid-bg);border:1px solid #E4CFA0;border-radius:10px;padding:9px 13px;font-size:13px;margin-bottom:10px}
.badge5{background:var(--ink);color:#fff;border-radius:9px;padding:5px 11px;font-weight:800;font-size:14px;font-family:'Frank Ruhl Libre',serif}
.empty{text-align:center;color:var(--muted);padding:50px 0}
@media(max-width:680px){.an-grid,.an-bottom{grid-template-columns:1fr}}

.legend{max-width:1080px;margin:6px auto;padding:0 16px;display:flex;gap:14px;flex-wrap:wrap;justify-content:center;font-size:12px;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:5px}
.dot{width:11px;height:11px;border-radius:4px;display:inline-block}
.explain{max-width:1080px;margin:2px auto 0;padding:0 16px;text-align:center;font-size:12px;color:var(--muted)}
.foot{max-width:1080px;margin:14px auto 40px;padding:0 16px;color:var(--muted);font-size:12.5px;text-align:center}
.fab{position:fixed;bottom:22px;left:22px;display:flex;flex-direction:column;gap:10px;z-index:50}
.fab button{width:46px;height:46px;border-radius:50%;border:0;background:var(--card);color:var(--brand);box-shadow:0 6px 18px rgba(90,70,60,.18);font-size:18px;cursor:pointer;transition:.15s}
.fab button:hover{background:var(--brand);color:#fff;transform:translateY(-2px)}
@media print{
  body{background:#fff}
  .toolbar,.chips,.fab,.actions,.hero .stats,.countbar{display:none!important}
  .hero{background:#fff!important;padding:6px 0}
  .card{break-inside:avoid;box-shadow:none;border:1px solid #ccc;margin-bottom:10px}
  .panel{display:block!important}
}
@media(max-width:680px){
  .hero h1{font-size:25px}.toolbar{margin-top:-38px}
  .ring{width:54px;height:54px;font-size:18px}.ttl{font-size:16.5px}
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
  <div class="ctl"><label>תקופה</label>
    <select class="sortsel" id="window" aria-label="טווח זמן" onchange="persist();render()">
      <option value="7">7 ימים</option><option value="14">14 יום</option>
      <option value="30">30 יום</option><option value="60">60 יום</option>
      <option value="90">90 יום</option><option value="0">הכל</option>
    </select></div>
  <div class="ctl"><label>מקס׳ לעיתון</label>
    <select class="sortsel" id="perj" aria-label="כמה מכל עיתון" onchange="persist();render()">
      <option value="1">1</option><option value="2">2</option><option value="3">3</option>
      <option value="5">5</option><option value="99">הכל</option>
    </select></div>
  <div class="ctl"><label>נושא</label>
    <select class="sortsel" id="topic" aria-label="נושא" onchange="persist();render()"><option value="">הכל</option></select></div>
  <div class="ctl"><label>מיון</label>
    <select class="sortsel" id="sort" aria-label="מיון" onchange="persist();render()">
      <option value="imp">חשיבות</option><option value="date">תאריך</option><option value="journal">עיתון</option>
    </select></div>
  <div class="seg">
    <button id="vr" class="on" onclick="setView('rank')">מדורג</button>
    <button id="vg" onclick="setView('group')">לפי עיתון</button>
  </div>
</div>
<div class="chips" id="chips"></div>
<div class="countbar" id="countbar"></div>
<div class="feed" id="feed"></div>
<div class="legend" id="legend"></div>
<div class="explain">ℹ️ ציון החשיבות = סוג המחקר ‎50%‎ + יוקרת העיתון ‎30%‎ + טריות ‎20%‎ · רחף מעל העיגול לפירוט</div>
<div class="foot" id="foot"></div>
<div class="fab">
  <button title="הדפסה לג'רנל קלאב" aria-label="הדפסה" onclick="printAll()">🖨</button>
  <button title="חזרה למעלה" aria-label="חזרה למעלה" onclick="window.scrollTo({top:0,behavior:'smooth'})">↑</button>
</div>

<script>
const DATA = /*__DATA__*/;
const META = /*__META__*/;
let activeJournal=null, viewMode='rank';
const JCOLOR={'AJOG':'#B08299','Green Journal':'#7E9B7E','BJOG':'#7E94B0','NEJM':'#A87E6C','Lancet':'#9E8AA8','Ultrasound O&G':'#5F9494'};
function jColor(n){return JCOLOR[n]||'#5E584E';}
function ringCls(v){return v>=65?'r-hi':v>=52?'r-mid':'r-lo';}
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function hvLabel(a){
  const pt=(a.pub_types||[]).join(' '),t=(a.title||'').toLowerCase();
  if(pt.includes('Randomized')||t.includes('randomi'))return'RCT';
  if(pt.includes('Meta-Analysis')||t.includes('meta-analysis')||t.includes('metaanalysis'))return'מטא-אנליזה';
  if(pt.includes('Systematic Review')||t.includes('systematic review'))return'סקירה שיטתית';
  if(pt.includes('Guideline')||t.includes('guideline')||t.includes('committee opinion'))return'הנחיה';
  if(pt.includes('Phase III')||t.includes('phase 3')||t.includes('phase iii'))return'Phase III';
  return null;
}
function cutoffDate(days){
  if(!days)return '0000-00-00';
  const t=new Date(META.today_iso+'T00:00:00'); t.setDate(t.getDate()-days);
  return t.toISOString().slice(0,10);
}
function renderStats(){
  document.getElementById('stats').innerHTML =
    `<div><b id="liveCount">${META.count}</b> מאמרים מוצגים</div>`+
    `<div><b>${META.journals.length}</b> עיתוני ליבה</div>`+
    `<div><b id="liveWin">${META.default_window}</b> ימים אחרונים</div>`+
    `<div><b id="livePerj">${META.default_per_journal}</b> מקס׳ לעיתון</div>`+
    (META.generated?`<div><b>${esc(META.generated)}</b> עודכן</div>`:'');
  document.getElementById('foot').textContent='LitRadar · כלי עזר לקריאה ביקורתית — אינו תחליף לקריאת המאמר המלא ולשיקול דעת קליני.';
}
function renderChips(list){
  const counts={}; list.forEach(a=>counts[a.journal]=(counts[a.journal]||0)+1);
  const el=document.getElementById('chips'); el.innerHTML='';
  const all=document.createElement('div'); all.className='jchip'+(activeJournal?'':' on');
  all.textContent='הכל'; all.onclick=()=>{activeJournal=null;render();}; el.appendChild(all);
  META.journals.forEach(j=>{
    const c=document.createElement('div'); c.className='jchip'+(activeJournal===j?' on':'');
    c.style.borderRightColor=jColor(j);
    c.textContent=j+(counts[j]?' ('+counts[j]+')':''); c.onclick=()=>{activeJournal=activeJournal===j?null:j;render();};
    el.appendChild(c);
  });
}
function renderLegend(){
  document.getElementById('legend').innerHTML='<b>עיתוני ליבה:</b> '+
    META.journals.map(j=>`<span><i class="dot" style="background:${jColor(j)}"></i>${esc(j)}</span>`).join('');
}
function analysisHTML(an,scope){
  if(!an)return '<div class="an-info">אין עדיין ניתוח שמור למאמר זה. הניתוח האוטומטי ("המבקר הקליני") ירוץ באפליקציה עם מפתח ה-API.</div>';
  let h='';
  if(scope==='ABSTRACT_ONLY')h+='<div class="scope-warn">⚠️ ניתוח מבוסס תקציר בלבד.</div>';
  if(an.source_scope_warning)h+='<div class="scope-warn">'+esc(an.source_scope_warning)+'</div>';
  h+=`<div style="display:flex;gap:12px;align-items:center;margin-bottom:6px"><span class="badge5">${esc(String(an.critic_score))}/5</span><div class="an-verdict" style="flex:1;margin:0">⚖️ ${esc(an.verdict_line)}</div></div>`;
  if(an.score_rationale)h+=`<div style="color:var(--muted);font-size:13px;margin-bottom:6px">${esc(an.score_rationale)}</div>`;
  if(an.evidence_level)h+=`<div style="font-size:13.5px;margin-bottom:8px"><b>רמת ראיות:</b> ${esc(an.evidence_level)}</div>`;
  const s=an.study_snapshot||{};
  h+=`<div class="an-box"><b>📋 תמצית המחקר</b>תכנון: ${esc(s.design)} · אוכלוסייה: ${esc(s.population)} · N: ${esc(s.n)}<br>תוצא ראשוני: ${esc(s.primary_outcome)}<br>תוצאה: ${esc(s.key_result)}</div>`;
  h+='<div class="an-grid"><div><div class="an-h">✅ חוזקות</div>';
  (an.strengths||[]).forEach(x=>h+=`<div class="an-strong">${esc(x)}</div>`);
  h+='</div><div><div class="an-h">⚠️ חולשות</div>';
  (an.weaknesses||[]).forEach(w=>{if(typeof w==='object')h+=`<div class="an-weak"><span class="sev sev-${esc(w.severity)}">${esc(w.severity)}</span>${esc(w.issue)}<br><small>${esc(w.impact)}</small></div>`;else h+=`<div class="an-weak">${esc(w)}</div>`;});
  h+='</div></div>';
  if(an.spin_alert&&an.spin_alert.detected)h+=`<div class="an-h">🎈 התראת Spin</div><div class="an-weak"><b>ציטוט:</b> "${esc(an.spin_alert.quote)}"<br><b>המציאות:</b> ${esc(an.spin_alert.reality)}</div>`;
  if((an.stats_red_flags||[]).length){h+='<div class="an-h">🚩 דגלים סטטיסטיים</div>';an.stats_red_flags.forEach(f=>h+=`<div class="an-weak">${esc(f)}</div>`);}
  h+=`<div class="an-h">🩺 שורה תחתונה קלינית</div><div class="an-info">${esc(an.clinical_bottom_line)}</div>`;
  h+=`<div class="an-bottom"><div class="an-box"><b>🔄 מה היה משנה את ההכרעה</b>${esc(an.what_would_change_my_mind)}</div><div class="an-box"><b>😈 פרקליט השטן</b>${esc(an.devils_advocate)}</div></div>`;
  if(an.one_liner_for_rounds)h+=`<div class="an-rounds">💬 לג'רנל קלאב: "${esc(an.one_liner_for_rounds)}"</div>`;
  return h;
}
function cardHTML(a,i){
  const hv=hvLabel(a), b=a.breakdown||{};
  const auth=(a.authors||[]), am=auth.length?(esc(auth[0])+(auth.length>1?' et al.':'')):'';
  const tip=`חשיבות ${a.importance}/100 — סוג מחקר ${b.design||'?'} · עיתון ${b.journal||'?'} · טריות ${b.recency||'?'}`;
  const tags=(hv?`<span class="tag t-star">⭐ ${hv}</span>`:'')+(a.topics||[]).map(t=>`<span class="tag t-topic">${esc(t)}</span>`).join('');
  return `<div class="card" style="animation-delay:${i*28}ms;border-right:5px solid ${jColor(a.journal)}">
    <div class="head">
      <div class="ring ${ringCls(a.importance)}" title="${tip}">${a.importance}<small>חשיבות</small></div>
      <div style="flex:1">
        <a class="ttl" dir="auto" href="https://pubmed.ncbi.nlm.nih.gov/${a.pmid}/" target="_blank">${esc(a.title)}</a>
        <div class="meta"><span class="jpill" style="background:${jColor(a.journal)}">${esc(a.journal)}</span><span>${esc(a.date)}</span>${am?'<span>·&nbsp;<bdi>'+am+'</bdi></span>':''}</div>
        <div class="tags">${tags}</div>
        <div class="actions">
          <button class="btn btn-primary" onclick="toggleAn(this,${i})">⚡ ניתוח ביקורתי</button>
          <button class="btn" onclick="toggle(${i},'ab')">📄 תקציר</button>
          ${a.doi?`<a class="btn" href="https://doi.org/${esc(a.doi)}" target="_blank">🔗 מקור</a>`:''}
        </div>
        <div class="panel" id="ab-${i}"><div class="abx" dir="auto">${esc(a.abstract)||'— אין תקציר —'}</div></div>
        <div class="panel" id="an-${i}">${analysisHTML(a.analysis,a.analysis_scope)}</div>
      </div>
    </div></div>`;
}
function toggle(i,k){document.getElementById(k+'-'+i).classList.toggle('open');}
function toggleAn(btn,i){const p=document.getElementById('an-'+i);const o=p.classList.toggle('open');btn.classList.toggle('active',o);btn.innerHTML=o?'✕ סגור ניתוח':'⚡ ניתוח ביקורתי';}
function setView(m){viewMode=m;document.getElementById('vr').classList.toggle('on',m==='rank');document.getElementById('vg').classList.toggle('on',m==='group');persist();render();}
function printAll(){document.querySelectorAll('[id^="an-"]').forEach(p=>p.classList.add('open'));setTimeout(()=>window.print(),60);}

function render(){
  const q=(document.getElementById('q').value||'').toLowerCase().trim();
  const win=+document.getElementById('window').value;
  const perj=+document.getElementById('perj').value;
  const topic=document.getElementById('topic').value;
  const sort=document.getElementById('sort').value;
  const cut=cutoffDate(win);
  // 1) סינון: עיתון פעיל, נושא, חיפוש, חלון זמן
  let list=DATA.filter(a=>{
    if(activeJournal&&a.journal!==activeJournal)return false;
    if(topic&&!(a.topics||[]).includes(topic))return false;
    if(win&&(a.date||'')<cut)return false;
    if(q&&!(a.title+' '+a.abstract+' '+(a.topics||[]).join(' ')).toLowerCase().includes(q))return false;
    return true;
  });
  // 2) תקרה לכל עיתון (לפי חשיבות)
  const byJ={}; list.sort((x,y)=>y.importance-x.importance);
  list=list.filter(a=>{byJ[a.journal]=(byJ[a.journal]||0)+1;return byJ[a.journal]<=perj;});
  // 3) תקרה כוללת
  if(META.max_total&&list.length>META.max_total)list=list.slice(0,META.max_total);
  // עדכון מונים
  const lc=document.getElementById('liveCount'),lw=document.getElementById('liveWin'),lp=document.getElementById('livePerj');
  if(lc)lc.textContent=list.length; if(lw)lw.textContent=win?win:'הכל'; if(lp)lp.textContent=perj>=99?'הכל':perj;
  document.getElementById('countbar').innerHTML=`מציג <b>${list.length}</b> מאמרים · חלון <b>${win?win+' ימים':'הכל'}</b> · עד <b>${perj>=99?'הכל':perj}</b> לעיתון`;
  renderChips(list);
  // 4) מיון תצוגה
  if(sort==='imp')list.sort((x,y)=>y.importance-x.importance);
  if(sort==='date')list.sort((x,y)=>(y.date||'').localeCompare(x.date||''));
  if(sort==='journal')list.sort((x,y)=>(x.journal||'').localeCompare(y.journal||''));
  const feed=document.getElementById('feed');
  if(!list.length){feed.innerHTML='<div class="empty">לא נמצאו מאמרים תואמים. נסה להרחיב את התקופה.</div>';return;}
  if(viewMode==='group'){
    const order={}; META.journals.forEach((j,k)=>order[j]=k);
    list.sort((x,y)=>(order[x.journal]??99)-(order[y.journal]??99)||y.importance-x.importance);
    let html='',last=null,idx=0;
    list.forEach(a=>{if(a.journal!==last){html+=`<div class="jhead" style="border-color:${jColor(a.journal)}">${esc(a.journal)}</div>`;last=a.journal;}html+=cardHTML(a,idx++);});
    feed.innerHTML=html;
  } else { feed.innerHTML=list.map((a,i)=>cardHTML(a,i)).join(''); }
}
function populateTopics(){
  const set=new Set(); DATA.forEach(a=>(a.topics||[]).forEach(t=>set.add(t)));
  const sel=document.getElementById('topic');
  [...set].sort().forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=t;sel.appendChild(o);});
}
function persist(){try{['window','perj','topic','sort'].forEach(id=>localStorage.setItem('lr_'+id,document.getElementById(id).value));localStorage.setItem('lr_view',viewMode);}catch(e){}}
function loadPrefs(){try{
  ['window','perj','topic','sort'].forEach(id=>{const v=localStorage.getItem('lr_'+id);if(v!==null&&[...document.getElementById(id).options].some(o=>o.value===v))document.getElementById(id).value=v;});
  const vw=localStorage.getItem('lr_view'); if(vw)setView(vw);
}catch(e){}}
document.addEventListener('keydown',e=>{
  if(e.key==='/'&&document.activeElement.id!=='q'){e.preventDefault();document.getElementById('q').focus();}
  if(e.key==='Escape'&&document.activeElement.id==='q'){document.getElementById('q').value='';render();}
});
// init
document.getElementById('window').value=String(META.default_window);
document.getElementById('perj').value=String(META.default_per_journal);
renderStats();populateTopics();renderLegend();loadPrefs();render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    print("נוצר:", build())
