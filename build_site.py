"""
מחולל אתר LitRadar — גרסה חיה (client-side).
הדף שואל את PubMed (eutils) ו-OpenAlex ישירות מהדפדפן בכל שינוי הגדרות —
חיפוש אמיתי בכל פעם, טווח תאריכים חופשי, ו"מגמות בתחום". פייתון רק אופה את הקונפיג.
הרצה:  python build_site.py
"""
import json
from pathlib import Path
from datetime import date

from app import db
from app.config import (JOURNALS, OBGYN_FILTER, HIGH_VALUE_FILTER, TOPIC_MAP,
                        DEFAULT_TOPIC, DESIGN_RANK, DESIGN_RANK_DEFAULT, SCORE_WEIGHTS,
                        AUTHOR_HINDEX_TOP, IMPACT_FWCI_TOP,
                        CITATION_MIN_MONTHS, CITATION_MATURE_MONTHS,
                        DIGEST_PER_JOURNAL, DIGEST_WINDOW_DAYS,
                        DIGEST_MAX_TOTAL, TREND_TOPICS, ANALYSIS_MODEL)
from app.prompts import CRITIC_SYSTEM_PROMPT

OUT_DIR = Path(__file__).resolve().parent / "site"
OUT_DIR.mkdir(exist_ok=True)
DOCS_DIR = Path(__file__).resolve().parent / "docs"


def _all_analyses() -> dict:
    out = {}
    try:
        with db.get_conn() as conn:
            for r in conn.execute("SELECT pmid, payload, source_scope FROM analyses").fetchall():
                out[r["pmid"]] = {"payload": json.loads(r["payload"]), "scope": r["source_scope"]}
    except Exception:
        pass
    return out


def build(today: str | None = None) -> Path:
    if today is None:
        today = date.today().strftime("%d/%m/%Y")
    db.init_db()
    primary = [j for j in JOURNALS if j.get("primary")]
    cfg = {
        "journals": [{"nick": j.get("nick") or j["name"], "issn": j["issn"],
                      "issn_e": j.get("issn_e", ""), "weight": j["weight"],
                      "tier": j.get("tier", 2), "filter_obgyn": j.get("filter_obgyn", False)}
                     for j in primary],
        "max_weight": max((j["weight"] for j in JOURNALS), default=10),
        "obgyn_filter": OBGYN_FILTER,
        "high_value_filter": HIGH_VALUE_FILTER,
        "topics": [[name, kws] for name, kws in TOPIC_MAP],
        "default_topic": DEFAULT_TOPIC,
        "design_rank": [[kws, rank] for kws, rank in DESIGN_RANK],
        "design_default": DESIGN_RANK_DEFAULT,
        "weights": SCORE_WEIGHTS,
        "author_top": AUTHOR_HINDEX_TOP,
        "impact_fwci_top": IMPACT_FWCI_TOP,
        "cit_min_months": CITATION_MIN_MONTHS,
        "cit_mature_months": CITATION_MATURE_MONTHS,
        "default_window": DIGEST_WINDOW_DAYS,
        "default_per_journal": DIGEST_PER_JOURNAL,
        "max_total": DIGEST_MAX_TOTAL,
        "trend_topics": [[label, q, cat] for label, q, cat in TREND_TOPICS],
        "critic_prompt": CRITIC_SYSTEM_PROMPT,
        "analysis_model": ANALYSIS_MODEL,
        "generated": today,
        "today_iso": date.today().isoformat(),
    }
    html = (TEMPLATE.replace("/*__CFG__*/", json.dumps(cfg, ensure_ascii=False))
                    .replace("/*__ANALYSES__*/", json.dumps(_all_analyses(), ensure_ascii=False)))
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
<title>LitRadar · מכ"ם ספרות חי</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;500;600;700;800&family=Frank+Ruhl+Libre:wght@400;500;700&family=Playfair+Display:ital,wght@0,600;0,700;0,800;1,600;1,700&family=Archivo:wght@700;800;900&family=Heebo:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#F1ECE5; --card:#FFFFFF; --ink:#2A2722; --muted:#8A8378; --line:#EAE3D9;
  --brand:#6B5680; --brand-d:#4F3E61; --soft:#F1ECE4;
  --hi:#3C5E47; --hi-bg:#E6F0E8; --mid:#8A6A3A; --mid-bg:#F5EBD8; --lo:#6A645B; --lo-bg:#EEEAE3;
  --chip-bg:#F1ECE4; --chip-fg:#6B6459; --star-bg:#F4E9D2; --star-fg:#8A6B33;
  --strong-bg:#E9F1EA; --strong-bd:#AECbB2; --weak-bg:#F7EAE6; --weak-bd:#DEC1B9;
  --verdict-bg:#EFEAF2; --verdict-bd:#D6CCE0; --gold:#B08A3E;
}
*{box-sizing:border-box}
body{margin:0;font-family:'Assistant',sans-serif;background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased;}
a{color:inherit;text-decoration:none}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px;}
.hero{background:linear-gradient(120deg,#ECE5DF 0%,#E9E3EC 60%,#E3EAE5 120%);color:var(--ink);padding:30px 0 64px;border-bottom:1px solid var(--line);}
.hero h1{margin:0;font-family:'Frank Ruhl Libre',serif;font-size:32px;font-weight:700;letter-spacing:-.3px;display:flex;align-items:center;gap:12px}
.hero .sub{margin-top:9px;color:#7b7468;font-size:14.5px;font-weight:400;letter-spacing:.1px}
.toolbar{max-width:1080px;margin:-40px auto 0;padding:13px 15px;background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 12px 34px rgba(90,70,60,.10);display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;position:sticky;top:8px;z-index:30}
.search{flex:1;min-width:170px;display:flex;align-items:center;gap:8px;background:#F4F1EC;border:1px solid var(--line);border-radius:11px;padding:9px 13px;align-self:stretch}
.search input{border:0;background:transparent;outline:0;width:100%;font-family:inherit;font-size:14px;color:var(--ink)}
.ctl{display:flex;flex-direction:column;gap:2px}
.ctl label{font-size:10px;color:var(--muted);padding-right:3px}
.sortsel,.dateinp{border:1px solid var(--line);border-radius:10px;padding:8px 10px;background:var(--card);font-family:inherit;font-size:13.5px;color:var(--ink);cursor:pointer}
.dateinp{cursor:text}
.seg{display:flex;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.seg button{border:0;background:var(--card);padding:8px 12px;font-family:inherit;font-size:13px;font-weight:600;color:#6a6258;cursor:pointer}
.seg button.on{background:var(--brand);color:#fff}
.btn{border:1px solid var(--line);background:var(--card);border-radius:11px;padding:9px 15px;font-family:inherit;font-size:14px;font-weight:700;cursor:pointer;transition:.15s;color:var(--ink)}
.btn:hover{border-color:var(--brand);color:var(--brand)}
.btn-primary{background:var(--brand);color:#fff;border-color:var(--brand)}
.btn-primary:hover{background:var(--brand-d);color:#fff}
.btn-trend{background:linear-gradient(135deg,#B98E3C,#caa052);color:#fff;border:0}
.chips{max-width:1080px;margin:14px auto 0;padding:0 16px;display:flex;gap:8px;flex-wrap:wrap}
.jchip{border:1px solid var(--line);background:var(--card);border-radius:20px;padding:6px 13px;font-size:13px;font-weight:600;cursor:pointer;color:#5e574c}
.jchip.on{background:var(--brand);color:#fff;border-color:var(--brand)}
.jchip.tier1{border-color:var(--gold)}
.countbar{max-width:1080px;margin:12px auto 0;padding:0 18px;color:var(--muted);font-size:13px}
.countbar b{color:var(--ink)}
.feed{max-width:1080px;margin:10px auto 60px;padding:0 16px;display:grid;gap:15px}
.jhead{margin:10px 0 0;padding:7px 15px;font-family:'Frank Ruhl Libre',serif;font-weight:700;font-size:16px;border-right:4px solid var(--ink);background:var(--card);border-radius:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px 22px;box-shadow:0 2px 10px rgba(90,70,60,.05);transition:.18s;animation:rise .4s ease both}
.card:hover{box-shadow:0 16px 38px rgba(90,70,60,.12);transform:translateY(-2px)}
.card.tier1{box-shadow:0 0 0 2px var(--gold),0 2px 10px rgba(90,70,60,.05)}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.head{display:flex;gap:16px;align-items:flex-start}
.ring{flex:none;width:64px;height:64px;border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;font-weight:800;font-size:21px;line-height:1;cursor:help;font-family:'Frank Ruhl Libre',serif}
.ring small{font-size:9px;font-weight:600;opacity:.85;margin-top:2px;font-family:'Heebo',sans-serif}
.r-hi{background:var(--hi-bg);color:var(--hi);box-shadow:inset 0 0 0 2px var(--hi)}
.r-mid{background:var(--mid-bg);color:var(--mid);box-shadow:inset 0 0 0 2px var(--mid)}
.r-lo{background:var(--lo-bg);color:var(--lo);box-shadow:inset 0 0 0 2px #C9C2B6}
.ttl{display:block;font-size:18px;font-weight:700;line-height:1.45}
.ttl:hover{color:var(--brand)}
.meta{color:var(--muted);font-size:13px;margin-top:6px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.jpill{color:#fff;border-radius:7px;padding:2px 9px;font-size:12px;font-weight:700;background:#5E584E}
.jbrand{display:inline-block;font-size:20px;line-height:1.05;margin-bottom:7px}
.lg-serif{font-family:'Playfair Display',serif;font-weight:800;letter-spacing:.2px}
.lg-serifi{font-family:'Playfair Display',serif;font-weight:700;font-style:italic;letter-spacing:.2px}
.lg-cond{font-family:'Archivo',sans-serif;font-weight:900;letter-spacing:.6px}
.favbtn{border:0;background:none;cursor:pointer;font-size:23px;line-height:1;color:#CFC8BC;transition:.15s;padding:0}
.favbtn:hover,.favbtn.on{color:var(--gold)}
.crown{color:var(--gold);font-weight:800}
.tags{margin-top:11px;display:flex;gap:6px;flex-wrap:wrap}
.tag{border-radius:20px;padding:3px 11px;font-size:12px;font-weight:600}
.t-star{background:var(--star-bg);color:var(--star-fg)}
.t-topic{background:var(--chip-bg);color:var(--chip-fg)}
.t-pos{background:#F6E6C8;color:#8A6B33;font-weight:700;border:1px solid #E4CFA0}
.actions{margin-top:14px;display:flex;gap:9px;flex-wrap:wrap}
.panel{margin-top:14px;border-top:1px dashed var(--line);padding-top:14px;display:none}
.panel.open{display:block}
.abx{color:#4a443b;font-size:14.5px;line-height:1.7}
.an-verdict{background:var(--verdict-bg);border-right:5px solid var(--verdict-bd);padding:13px 16px;border-radius:11px;font-weight:700;font-size:15.5px;margin-bottom:12px}
.an-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.an-h{font-weight:800;font-size:14px;margin:14px 0 7px}
.an-strong{background:var(--strong-bg);border-right:3px solid var(--strong-bd);padding:8px 12px;border-radius:9px;margin:6px 0;font-size:13.5px;line-height:1.55}
.an-weak{background:var(--weak-bg);border-right:3px solid var(--weak-bd);padding:8px 12px;border-radius:9px;margin:6px 0;font-size:13.5px;line-height:1.55}
.sev{font-weight:800;font-size:11px;border-radius:6px;padding:1px 6px;margin-left:5px;color:#fff}
.sev-גבוהה{background:#B5736B}.sev-בינונית{background:#B89055}.sev-נמוכה{background:#9aa28f}
.an-info{background:#EAEFE9;border:1px solid #CFE0CE;padding:11px 14px;border-radius:11px;font-size:14px;line-height:1.65;margin:8px 0}
.an-box{background:#F4F1EC;border:1px solid var(--line);border-radius:11px;padding:11px 14px;font-size:13.5px;line-height:1.6;margin-top:8px}
.an-box b{display:block;margin-bottom:5px}
.scope-warn{background:var(--mid-bg);border:1px solid #E4CFA0;border-radius:10px;padding:9px 13px;font-size:13px;margin-bottom:10px}
.badge5{background:var(--ink);color:#fff;border-radius:9px;padding:5px 11px;font-weight:800;font-size:14px}
.status{max-width:1080px;margin:18px auto;padding:14px 18px;text-align:center;color:var(--muted)}
.spinner{display:inline-block;width:18px;height:18px;border:3px solid var(--line);border-top-color:var(--brand);border-radius:50%;animation:spin .8s linear infinite;vertical-align:middle;margin-left:8px}
@keyframes spin{to{transform:rotate(360deg)}}
.explain{max-width:1080px;margin:2px auto;padding:0 16px;text-align:center;font-size:12px;color:var(--muted)}
.legend{max-width:1080px;margin:6px auto;padding:0 16px;display:flex;gap:13px;flex-wrap:wrap;justify-content:center;font-size:12px;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:5px}.dot{width:11px;height:11px;border-radius:4px;display:inline-block}
/* trends modal */
.overlay{position:fixed;inset:0;background:rgba(40,34,30,.45);z-index:100;display:none;align-items:flex-start;justify-content:center;overflow:auto;padding:30px 16px}
.overlay.open{display:flex}
.modal{background:var(--bg);border-radius:18px;max-width:760px;width:100%;padding:24px 26px;box-shadow:0 30px 70px rgba(0,0,0,.3)}
.modal h2{font-family:'Frank Ruhl Libre',serif;margin:0 0 4px;font-size:24px;display:flex;align-items:center;gap:8px}
.trow{display:flex;align-items:center;gap:12px;padding:10px 12px;border-radius:12px;background:var(--card);border:1px solid var(--line);margin:8px 0}
.tgrow{font-weight:800;font-size:15px;width:74px;text-align:center;border-radius:9px;padding:5px 0}
.tg-up{background:var(--hi-bg);color:var(--hi)}.tg-flat{background:var(--lo-bg);color:var(--lo)}.tg-down{background:var(--weak-bg);color:#9a4a40}
.tbar{flex:1}.tbar .lbl{font-weight:600;font-size:14px}.tbar .sm{color:var(--muted);font-size:12px}
.closeX{float:left;cursor:pointer;font-size:22px;color:var(--muted);border:0;background:none}
.fab{position:fixed;bottom:22px;left:22px;z-index:50}
.fab button{width:46px;height:46px;border-radius:50%;border:0;background:var(--card);color:var(--brand);box-shadow:0 6px 18px rgba(90,70,60,.18);font-size:18px;cursor:pointer}
@media(max-width:680px){.an-grid{grid-template-columns:1fr}.hero h1{font-size:24px}}
</style>
</head>
<body>
<div class="hero"><div class="wrap">
  <h1>🩺 LitRadar — מכ"ם ספרות חי</h1>
  <div class="sub">חיפוש חי ב-PubMed בכל פעם · רק RCT/מטא/סקירות/הנחיות · NEJM·Lancet·JAMA תמיד בראש</div>
</div></div>

<div class="toolbar">
  <div class="search">🔎<input id="q" placeholder="סינון חופשי בתוצאות…" oninput="applyView()"></div>
  <div class="ctl"><label>תקופה</label>
    <select class="sortsel" id="window" onchange="onDatePreset()">
      <option value="30">30 יום</option><option value="90">90 יום</option>
      <option value="180">חצי שנה</option><option value="365">שנה</option>
      <option value="730">שנתיים</option><option value="0">טווח מותאם ↓</option>
    </select></div>
  <div class="ctl"><label>מ-תאריך</label><input type="date" class="dateinp" id="from" onchange="customDate()"></div>
  <div class="ctl"><label>עד</label><input type="date" class="dateinp" id="to" onchange="customDate()"></div>
  <div class="ctl"><label>גיליון מלא</label><input type="month" class="dateinp" id="issueMonth" title="הצג את כל מאמרי הגיליון (בחר עיתון יחיד תחילה)" onchange="onIssueMonth()"></div>
  <div class="ctl"><label>מקס׳/עיתון</label>
    <select class="sortsel" id="perj" onchange="applyView()">
      <option value="1">1</option><option value="2">2</option><option value="3">3</option>
      <option value="5">5</option><option value="10">10</option><option value="99">הכל</option>
    </select></div>
  <div class="ctl"><label>נושא</label><select class="sortsel" id="topic" onchange="applyView()"><option value="">הכל</option></select></div>
  <div class="ctl"><label>מיון</label><select class="sortsel" id="sort" onchange="applyView()"><option value="imp">חשיבות</option><option value="date">תאריך</option></select></div>
  <button class="btn btn-primary" onclick="runSearch()">🔄 חפש</button>
  <button class="btn btn-trend" onclick="openTrends()">📈 מגמות בתחום</button>
  <button class="btn" id="favViewBtn" onclick="toggleFavView()">★ מועדפים (0)</button>
  <button class="btn" onclick="setKey()" title="מפתח Claude API לניתוח ביקורתי חי (נשמר רק בדפדפן)">🔑 ניתוח</button>
</div>
<div class="chips" id="chips"></div>
<div class="countbar" id="countbar"></div>
<div class="status" id="status"></div>
<div class="feed" id="feed"></div>
<div class="legend" id="legend"></div>
<div class="explain">ℹ️ ציון מסתגל לגיל המאמר: מאמר טרי מדורג בעיקר לפי <b>רמת ראיות</b> (ציטוטים עדיין חסרי-משמעות); ככל שמתבגר, ה<b>השפעה בפועל</b> (FWCI/ציטוטים) נכנסת לתוקף · רחף מעל העיגול לפירוט</div>

<div class="overlay" id="trendsOverlay">
  <div class="modal">
    <button class="closeX" onclick="closeTrends()">✕</button>
    <h2>📈 מגמות בתחום</h2>
    <div class="sub" style="color:var(--muted);font-size:13px;margin-bottom:10px">גידול בנפח הפרסום ב-PubMed: 12 חודשים אחרונים מול 12 הקודמים</div>
    <div style="margin-bottom:12px"><label style="font-size:13px;color:var(--muted)">נושא: </label>
      <select class="sortsel" id="trendCat" onchange="openTrends()"><option value="">כל הנושאים</option></select></div>
    <div id="trendsBody"></div>
  </div>
</div>
<div class="fab"><button title="חזרה למעלה" onclick="window.scrollTo({top:0,behavior:'smooth'})">↑</button></div>

<script>
const CFG = /*__CFG__*/;
const ANALYSES = /*__ANALYSES__*/;
const EUT='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/';
const TAIL='&tool=LitRadar&email=giladshahak@gmail.com';
let state={articles:[], activeJournal:null};

// ---- rate-limited fetch gates ----
function makeGate(spacing){let q=Promise.resolve();return fn=>{const r=q.then(fn);q=r.catch(()=>{}).then(()=>new Promise(s=>setTimeout(s,spacing)));return r;};}
const ncbiGate=makeGate(340);   // ~3/sec
const oaGate=makeGate(130);

async function eutilsJSON(url){return ncbiGate(()=>fetch(url).then(r=>r.json()));}
async function eutilsText(url){return ncbiGate(()=>fetch(url).then(r=>r.text()));}
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function pad(n){return n<10?'0'+n:''+n;}
function isoToSlash(d){return d?d.replace(/-/g,'/'):'';}

// ---- date clause ----
function dateClause(){
  const f=document.getElementById('from').value, t=document.getElementById('to').value;
  if(f||t){const a=isoToSlash(f)||'1900/01/01', b=isoToSlash(t)||'3000/01/01';return `&datetype=pdat&mindate=${a}&maxdate=${b}`;}
  const w=+document.getElementById('window').value||30;
  return `&datetype=pdat&reldate=${w}`;
}
function exitIssue(){state.issueMode=false; const im=document.getElementById('issueMonth'); if(im)im.value='';}
function onDatePreset(){exitIssue(); const w=document.getElementById('window').value; if(w!=='0'){document.getElementById('from').value='';document.getElementById('to').value='';} runSearch();}
function customDate(){exitIssue(); runSearch();}

// ---- PubMed search ----
function journalTerm(j,fullIssue){
  let t=`(${j.issn_e}[IS] OR ${j.issn}[IS])`;
  if(j.filter_obgyn) t+=` AND ${CFG.obgyn_filter}`;
  if(!fullIssue) t+=` AND ${CFG.high_value_filter}`;   // גיליון מלא = בלי פילטר ערך-גבוה
  return t;
}
async function esearch(term,retmax){
  const url=EUT+'esearch.fcgi?db=pubmed&retmode=json&retmax='+(retmax||60)+'&sort=pub_date&term='+encodeURIComponent(term)+dateClause()+TAIL;
  const j=await eutilsJSON(url); return (j.esearchresult&&j.esearchresult.idlist)||[];
}
function onIssueMonth(){
  const m=document.getElementById('issueMonth').value;
  if(!m){state.issueMode=false; runSearch(); return;}
  const j=state.activeJournal?CFG.journals.find(x=>x.nick===state.activeJournal):null;
  if(!j||j.filter_obgyn){setStatus('לתצוגת גיליון מלא: בחר תחילה עיתון גינקולוגי <b>יחיד</b> (לא NEJM/Lancet/JAMA).');return;}
  const [y,mo]=m.split('-'); const last=new Date(+y,+mo,0).getDate();
  document.getElementById('from').value=`${y}-${mo}-01`;
  document.getElementById('to').value=`${y}-${mo}-${String(last).padStart(2,'0')}`;
  document.getElementById('window').value='0';
  state.issueMode=true; runSearch();
}
async function efetch(pmids){
  if(!pmids.length) return [];
  const url=EUT+'efetch.fcgi?db=pubmed&retmode=xml&id='+pmids.join(',')+TAIL;
  const xml=await eutilsText(url);
  return parsePubmed(xml);
}
function parsePubmed(xmlText){
  const doc=new DOMParser().parseFromString(xmlText,'text/xml');
  const out=[];
  doc.querySelectorAll('PubmedArticle').forEach(pa=>{
    const pmid=(pa.querySelector('MedlineCitation>PMID')||{}).textContent||'';
    const art=pa.querySelector('Article'); if(!art)return;
    const title=(art.querySelector('ArticleTitle')||{}).textContent||'';
    let abs=[...art.querySelectorAll('Abstract>AbstractText')].map(n=>{const l=n.getAttribute('Label');return (l?l+': ':'')+n.textContent;}).join('\n');
    const issn=(art.querySelector('Journal>ISSN')||{}).textContent||'';
    const jtitle=(art.querySelector('Journal>Title')||{}).textContent||'';
    const authors=[...art.querySelectorAll('AuthorList>Author')].map(a=>{const ln=(a.querySelector('LastName')||{}).textContent;const fn=(a.querySelector('ForeName')||{}).textContent;return ln?(ln+(fn?' '+fn:'')):null;}).filter(Boolean);
    const ptypes=[...art.querySelectorAll('PublicationTypeList>PublicationType')].map(n=>n.textContent);
    const mesh=[...pa.querySelectorAll('MeshHeading>DescriptorName')].map(n=>n.textContent);
    let doi='';pa.querySelectorAll('ArticleIdList>ArticleId').forEach(n=>{if(n.getAttribute('IdType')==='doi')doi=n.textContent;});
    // date
    let d='';const ad=art.querySelector('ArticleDate')||art.querySelector('Journal JournalIssue PubDate');
    if(ad){const y=(ad.querySelector('Year')||{}).textContent;let m=(ad.querySelector('Month')||{}).textContent||'01';const dd=(ad.querySelector('Day')||{}).textContent||'01';const mm={jan:'01',feb:'02',mar:'03',apr:'04',may:'05',jun:'06',jul:'07',aug:'08',sep:'09',oct:'10',nov:'11',dec:'12'};if(isNaN(+m))m=mm[(m||'').slice(0,3).toLowerCase()]||'01';if(y)d=`${y}-${pad(+m)}-${pad(+dd)}`;}
    const hasEditorial=[...pa.querySelectorAll('CommentsCorrections')].some(c=>c.getAttribute('RefType')==='CommentIn');
    out.push({pmid,title,abstract:abs,issn,journal_full:jtitle,authors,pub_types:ptypes,mesh,doi,date:d,hasEditorial});
  });
  return out;
}

// ---- scoring (mirrors Python) ----
const J_BY_ISSN={}; CFG.journals.forEach(j=>{J_BY_ISSN[j.issn]=j;J_BY_ISSN[j.issn_e]=j;});
function journalOf(a){return J_BY_ISSN[a.issn]||null;}
function designScore(a){const blob=(a.pub_types.join(' ')+' '+a.title).toLowerCase();for(const[kws,rank]of CFG.design_rank){if(kws.some(k=>blob.includes(k.toLowerCase())))return rank;}return CFG.design_default;}
function journalScore(a){const j=journalOf(a);return (j?j.weight:4)/CFG.max_weight;}
function authorScore(h){if(h==null)return 0.30;return Math.min(Math.log1p(Math.max(h,0))/Math.log1p(CFG.author_top),1);}
function impactScore(fwci,cites){
  if(fwci!=null) return Math.min(Math.log1p(Math.max(fwci,0))/Math.log1p(CFG.impact_fwci_top),1);
  if(cites!=null) return Math.min(Math.log1p(Math.max(cites,0))/Math.log1p(100),1);
  return 0;
}
function maturity(dateStr){
  if(!dateStr) return 0;
  const months=(new Date(CFG.today_iso)-new Date(dateStr))/(1000*60*60*24*30.44);
  const span=Math.max(CFG.cit_mature_months-CFG.cit_min_months,1);
  return Math.max(0,Math.min((months-CFG.cit_min_months)/span,1));
}
function scoreOf(a){
  const d=designScore(a),jr=journalScore(a),au=authorScore(a.hindex),im=impactScore(a.fwci,a.citations);
  const m=maturity(a.date),w=CFG.weights;
  const wi=w.impact*m, wd=w.design+w.impact*(1-m);           // משקל מסתגל לגיל
  const total=(wd*d+w.journal*jr+w.author*au+wi*im)*100;
  a.b={design:Math.round(d*100),journal:Math.round(jr*100),author:Math.round(au*100),
       impact:Math.round(im*100),impW:Math.round(wi*100),mat:Math.round(m*100)};
  a.importance=Math.round(total*10)/10;return a.importance;}
function metaBadge(a){let s='';if(a.hindex!=null)s+=' · 👤 h-index '+a.hindex;if(a.citations!=null&&a.citations>0)s+=' · 📊 '+a.citations+' ציטוטים';return s;}
function classify(a){const strong=(a.mesh.join(' | ')+' || '+a.title).toLowerCase();let hits=CFG.topics.filter(([n,kw])=>kw.some(k=>strong.includes(k.toLowerCase()))).map(x=>x[0]);
  if(!hits.length){const blob=strong+' '+a.abstract.toLowerCase();hits=CFG.topics.filter(([n,kw])=>kw.some(k=>blob.includes(k.toLowerCase()))).map(x=>x[0]);}
  return hits.length?hits:[CFG.default_topic];}

// ---- run live search ----
function setStatus(html){document.getElementById('status').innerHTML=html;}
async function runSearch(){
  state.favView=false; updateFavBtn();
  const journals=state.activeJournal?CFG.journals.filter(j=>j.nick===state.activeJournal):CFG.journals;
  const fi=!!state.issueMode;
  setStatus((fi?'טוען את הגיליון המלא':'סורק את PubMed בזמן אמת')+'… <span class="spinner"></span>');
  document.getElementById('feed').innerHTML='';
  try{
    // esearch per journal (parallel via gate)
    const idLists=await Promise.all(journals.map(j=>esearch(journalTerm(j,fi), fi?300:60).catch(()=>[])));
    const allIds=[...new Set([].concat(...idLists))];
    if(!allIds.length){setStatus('לא נמצאו מאמרים בטווח הזה. נסה להרחיב את התקופה.');state.articles=[];renderChips();document.getElementById('countbar').innerHTML='';return;}
    // efetch in chunks of 150
    let arts=[];
    for(let i=0;i<allIds.length;i+=150){arts=arts.concat(await efetch(allIds.slice(i,i+150)));}
    arts.forEach(a=>{a.topics=classify(a);a.hindex=null;scoreOf(a);});
    // keep only those from our journals
    arts=arts.filter(a=>journalOf(a));
    state.articles=arts;
    setStatus('');
    applyView();
    enrichAuthors();   // async OpenAlex
  }catch(e){setStatus('שגיאה בחיפוש: '+e);}
}

// ---- client-side view (cap/sort/filter) ----
function tierOf(a){const j=journalOf(a);return j?j.tier:2;}
function applyView(){
  if(!state.articles.length){document.getElementById('feed').innerHTML='';return;}
  const q=(document.getElementById('q').value||'').toLowerCase().trim();
  const perj=+document.getElementById('perj').value;
  const topic=document.getElementById('topic').value;
  const sortBy=document.getElementById('sort').value;
  let list=state.articles.filter(a=>{
    if(topic&&!a.topics.includes(topic))return false;
    if(q&&!(a.title+' '+a.abstract).toLowerCase().includes(q))return false;
    return true;
  });
  if(state.favView){
    list.sort((x,y)=>(sortBy==='date'?(''+(y.date||'')).localeCompare(''+(x.date||'')):y.importance-x.importance));
    document.getElementById('countbar').innerHTML=`★ מועדפים · <b>${list.length}</b> מאמרים שמורים`;
  } else if(!state.issueMode){
    // cap per journal by importance, tier-1 first
    list.sort((x,y)=>y.importance-x.importance);
    const byJ={};list=list.filter(a=>{const j=journalOf(a).nick;byJ[j]=(byJ[j]||0)+1;return byJ[j]<=perj;});
    if(CFG.max_total&&list.length>CFG.max_total)list=list.slice(0,CFG.max_total);
    const key=sortBy==='date'?(a=>a.date||''):(a=>a.importance);
    list.sort((x,y)=>(tierOf(x)-tierOf(y))||(sortBy==='date'?(''+key(y)).localeCompare(''+key(x)):key(y)-key(x)));
    document.getElementById('countbar').innerHTML=`מציג <b>${list.length}</b> מאמרים · עד <b>${perj>=99?'הכל':perj}</b> לעיתון`;
  } else {
    // גיליון מלא: כל המאמרים בחודש, לפי תאריך, ללא תקרות
    list.sort((x,y)=>(y.date||'').localeCompare(x.date||''));
    document.getElementById('countbar').innerHTML=`📖 גיליון מלא · <b>${list.length}</b> מאמרים (כל המאמרים בחודש)`;
  }
  renderChips();
  const feed=document.getElementById('feed');
  feed.innerHTML=list.map((a,i)=>cardHTML(a,i)).join('');
  state.shown=list;
}
function renderChips(){
  const counts={};state.articles.forEach(a=>{const j=journalOf(a);if(j)counts[j.nick]=(counts[j.nick]||0)+1;});
  const el=document.getElementById('chips');el.innerHTML='';
  const all=document.createElement('div');all.className='jchip'+(state.activeJournal?'':' on');all.textContent='הכל';all.onclick=()=>{exitIssue();state.activeJournal=null;runSearch();};el.appendChild(all);
  CFG.journals.forEach(j=>{const c=document.createElement('div');c.className='jchip'+(j.tier===1?' tier1':'')+(state.activeJournal===j.nick?' on':'');c.style.borderRightColor=jBrand(j.nick);c.style.borderRightWidth='3px';c.textContent=(j.tier===1?'👑 ':'')+j.nick+(counts[j.nick]?' ('+counts[j.nick]+')':'');c.onclick=()=>{exitIssue();state.activeJournal=state.activeJournal===j.nick?null:j.nick;runSearch();};el.appendChild(c);});
}
function renderLegend(){document.getElementById('legend').innerHTML='<b>עיתוני ליבה:</b> '+CFG.journals.map(j=>`<span><i class="dot" style="background:${jBrand(j.nick)}"></i>${j.tier===1?'👑 ':''}${esc(j.nick)}</span>`).join(' · ');}

function ringCls(v){return v>=65?'r-hi':v>=52?'r-mid':'r-lo';}
function hvLabel(a){const pt=a.pub_types.join(' '),t=a.title.toLowerCase();
  if(pt.includes('Randomized')||t.includes('randomi'))return'RCT';
  if(pt.includes('Meta-Analysis')||t.includes('meta-analysis'))return'מטא-אנליזה';
  if(pt.includes('Systematic Review')||t.includes('systematic review'))return'סקירה שיטתית';
  if(pt.includes('Phase III')||t.includes('phase 3'))return'Phase III';return null;}
function specialBadges(a){
  const pt=a.pub_types.join(' ').toLowerCase(),t=a.title.toLowerCase();let s='';
  if(pt.includes('guideline')||pt.includes('consensus')||t.includes('committee opinion')||t.includes('position statement')||t.includes('practice bulletin')||t.includes('consensus statement'))
    s+='<span class="tag t-pos">📋 נייר עמדה / הנחיה</span>';
  else if(pt.includes('editorial')) s+='<span class="tag t-pos">✍️ מאמר מערכת</span>';
  if(a.hasEditorial) s+='<span class="tag t-pos" title="פורסם עליו מאמר מערכת/פרשנות — סימן להתייחסות מיוחדת">⭐ זכה למאמר מערכת</span>';
  return s;}
// וורדמרק טיפוגרפי לכל עיתון — צבע מותג + סגנון גופן שמדמה את הלוגו (serif/condensed)
const JLOGO={
  'NEJM':{c:'#A6122B',f:'serif'}, 'Lancet':{c:'#8A1A2E',f:'serifi'}, 'JAMA':{c:'#B61F2E',f:'cond'},
  'AJOG':{c:'#1F4E8C',f:'cond'}, 'Green Journal':{c:'#15673C',f:'serif'}, 'BJOG':{c:'#08589E',f:'cond'},
  'Ultrasound O&G':{c:'#0E7C7B',f:'cond'}, 'AJOG MFM':{c:'#6A3FA0',f:'cond'},
  'Gyn Oncology':{c:'#A23048',f:'serif'}, 'Fertility & Sterility':{c:'#B26B12',f:'serif'}};
function jLogo(n){return JLOGO[n]||{c:'#5E584E',f:'cond'};}
function jBrand(n){return jLogo(n).c;}
function jLogoHTML(j){const lg=jLogo(j.nick),cls=lg.f==='serif'?'lg-serif':lg.f==='serifi'?'lg-serifi':'lg-cond';
  return `<div class="jbrand ${cls}" style="color:${lg.c}">${j.tier===1?'<span style="color:var(--gold)">👑 </span>':''}${esc(j.nick)}</div>`;}
function cardHTML(a,i){
  const j=journalOf(a),hv=hvLabel(a),b=a.b||{};
  const am=a.authors.length?(esc(a.authors[0])+(a.authors.length>1?' et al.':'')):'';
  const fresh=(b.mat!=null&&b.mat<10);
  const tip=`חשיבות ${a.importance}/100\nרמת ראיות ${b.design} · עיתון ${b.journal} · חוקרים ${b.author}${a.hindex!=null?' (h '+a.hindex+')':''}\nהשפעה בפועל ${b.impact!=null?b.impact:'?'}${a.fwci!=null?' (FWCI '+(Math.round(a.fwci*10)/10)+')':''} — משקל ${b.impW!=null?b.impW:0}%${fresh?'\n(מאמר טרי: מדורג בעיקר לפי רמת ראיות)':''}`;
  const tags=(hv?`<span class="tag t-star">⭐ ${hv}</span>`:'')+specialBadges(a)+a.topics.map(t=>`<span class="tag t-topic">${esc(t)}</span>`).join('');
  const an=ANALYSES[a.pmid]||loadLocalAn(a.pmid);
  return `<div class="card${j.tier===1?' tier1':''}" style="border-right:6px solid ${jBrand(j.nick)}">
    <div class="head">
      <div class="ring ${ringCls(a.importance)}" title="${tip}">${a.importance}<small>חשיבות</small></div>
      <div style="flex:1">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px">${jLogoHTML(j)}<button class="favbtn${isFav(a.pmid)?' on':''}" title="הוסף למועדפים" onclick="toggleFav('${a.pmid}',this)">${isFav(a.pmid)?'★':'☆'}</button></div>
        <a class="ttl" dir="auto" href="https://pubmed.ncbi.nlm.nih.gov/${a.pmid}/" target="_blank">${esc(a.title)}</a>
        <div class="meta"><span>${esc(a.date)}</span>${am?'<span>·&nbsp;<bdi>'+am+'</bdi></span>':''}<span id="h-${a.pmid}">${metaBadge(a)}</span></div>
        <div class="tags">${tags}</div>
        <div class="actions">
          <button class="btn btn-primary" onclick="toggleAn('${a.pmid}',this)">⚡ ניתוח ביקורתי</button>
          <button class="btn" onclick="pasteFullText('${a.pmid}')" title="נתח מטקסט מלא שתדביק">📋 טקסט מלא</button>
          <button class="btn" onclick="document.getElementById('ab-${a.pmid}').classList.toggle('open')">📄 תקציר</button>
          ${a.doi?`<a class="btn" href="https://doi.org/${esc(a.doi)}" target="_blank">🔗 מקור</a>`:''}
        </div>
        <div class="panel" id="ab-${a.pmid}"><div class="abx" dir="auto">${esc(a.abstract)||'— אין תקציר —'}</div></div>
        <div class="panel" id="an-${a.pmid}"${an?' data-ready="1"':''}>${an?analysisHTML(an.payload,an.scope):''}</div>
      </div>
    </div></div>`;
}
const LIVE_AN={};
// ---- מועדפים ----
function getFavs(){try{return JSON.parse(localStorage.getItem('lr_favs')||'{}');}catch(e){return {};}}
function isFav(pmid){return !!getFavs()[pmid];}
function favCount(){return Object.keys(getFavs()).length;}
function toggleFav(pmid,btn){
  const f=getFavs();
  if(f[pmid])delete f[pmid];
  else{const a=(state.articles||[]).find(x=>x.pmid===pmid)||f[pmid];if(a)f[pmid]=a;}
  localStorage.setItem('lr_favs',JSON.stringify(f));
  if(btn){const on=!!f[pmid];btn.innerHTML=on?'★':'☆';btn.classList.toggle('on',on);}
  updateFavBtn(); if(state.favView)showFavs();
}
function updateFavBtn(){const b=document.getElementById('favViewBtn');if(b)b.innerHTML=(state.favView?'✕ סגור מועדפים':'★ מועדפים')+' ('+favCount()+')';}
function showFavs(){
  state.favView=true;exitIssue();
  const favs=Object.values(getFavs());favs.forEach(a=>{if(!a.b)scoreOf(a);});
  state.articles=favs;
  setStatus(favs.length?'':'אין עדיין מאמרים במועדפים. לחץ ☆ על מאמר כדי לשמור.');
  updateFavBtn();applyView();
}
function toggleFavView(){if(state.favView){state.favView=false;updateFavBtn();runSearch();}else showFavs();}
// ---- ניתוח מטקסט מלא ----
function pasteFullText(pmid){
  const p=document.getElementById('an-'+pmid);p.classList.add('open');p.dataset.ready='';
  p.innerHTML=`<div class="an-box"><b>📋 הדבק את הטקסט המלא של המאמר</b><div style="color:var(--muted);font-size:12px;margin-bottom:5px">היכנס למאמר דרך המנוי שלך (🔗 מקור), העתק את גוף המאמר והדבק כאן לניתוח מעמיק יותר.</div><textarea id="ft-${pmid}" placeholder="הדבק כאן…" style="width:100%;height:150px;border:1px solid var(--line);border-radius:9px;padding:9px;font-family:inherit;font-size:13px"></textarea><button class="btn btn-primary" style="margin-top:7px" onclick="runFull('${pmid}')">⚡ נתח טקסט מלא</button></div>`;
}
function runFull(pmid){const t=(document.getElementById('ft-'+pmid).value||'').trim();if(t.length<200){alert('הדבק טקסט ארוך יותר של המאמר (לפחות פסקה).');return;}analyzeLive(pmid,t);}
function cleanKey(s){return (s||'').replace(/[^\x21-\x7E]/g,'');}  // רק ASCII נראה — בלי רווחים/שורות
function setKey(){
  const cur=localStorage.getItem('lr_key')||'';
  const k=prompt('הדבק מפתח Claude API (sk-ant-…).\nנשמר אך ורק בדפדפן שלך ונשלח רק ל-Anthropic.\nהשג ב-console.anthropic.com', cur);
  if(k!=null){const c=cleanKey(k);localStorage.setItem('lr_key',c);
    alert(c?(c.startsWith('sk-ant')?'✓ המפתח נשמר. לחץ "⚡ ניתוח ביקורתי" על מאמר.':'⚠ נשמר, אך המפתח לא נראה תקין (אמור להתחיל ב-sk-ant).'):'המפתח נמחק.');}
}
function loadLocalAn(pmid){if(LIVE_AN[pmid])return LIVE_AN[pmid];try{const s=localStorage.getItem('lr_an_'+pmid);if(s){LIVE_AN[pmid]=JSON.parse(s);return LIVE_AN[pmid];}}catch(e){}return null;}
function criticUserMsg(a,content,scope){
  const meta=`כותרת: ${a.title}\nעיתון: ${a.journal_full||''} | שנה: ${(a.date||'').slice(0,4)}\nסוגי פרסום: ${a.pub_types.join(', ')||'לא דווח'}\nMeSH: ${a.mesh.slice(0,15).join(', ')||'לא דווח'}\nDOI: ${a.doi||'לא דווח'}\nSOURCE_SCOPE: ${scope}\n`;
  return meta+`\n===== טקסט המאמר (${scope==='FULL_TEXT'?'טקסט מלא':'תקציר בלבד'}) =====\n${content}\n===== סוף הטקסט =====\n\nבצע את הניתוח המלא והחזר JSON תקין יחיד בלבד.`;
}
async function callClaude(user){
  const key=cleanKey(localStorage.getItem('lr_key'));
  if(!key) throw new Error('חסר מפתח. לחץ 🔑 ניתוח.');
  const r=await fetch('https://api.anthropic.com/v1/messages',{method:'POST',
    headers:{'content-type':'application/json','x-api-key':key,'anthropic-version':'2023-06-01','anthropic-dangerous-direct-browser-access':'true'},
    body:JSON.stringify({model:CFG.analysis_model,max_tokens:4000,system:CFG.critic_prompt,messages:[{role:'user',content:user}]})});
  if(!r.ok){let t='';try{t=(await r.json()).error.message;}catch(e){t=await r.text();}throw new Error(r.status+' '+String(t).slice(0,140));}
  const j=await r.json();const txt=((j.content&&j.content[0]&&j.content[0].text)||'');
  const s=txt.indexOf('{'),e=txt.lastIndexOf('}');
  if(s<0||e<0)throw new Error('לא הוחזר JSON תקין מהמודל');
  return JSON.parse(txt.slice(s,e+1));
}
async function analyzeLive(pmid,fullText){
  const a=state.articles.find(x=>x.pmid===pmid),p=document.getElementById('an-'+pmid);if(!a||!p)return;
  if(!localStorage.getItem('lr_key')){p.innerHTML='<div class="an-info">להפעלת הניתוח הביקורתי החי דרוש מפתח Claude API.<br><button class="btn btn-primary" style="margin-top:8px" onclick="setKey()">🔑 הזן מפתח</button><br><small style="color:var(--muted)">נשמר רק בדפדפן שלך ונשלח אך ורק ל-Anthropic. השג ב-console.anthropic.com</small></div>';p.dataset.ready='1';return;}
  p.innerHTML='⏳ המבקר הקליני עובד… <span class="spinner"></span>';
  try{
    const scope=fullText?'FULL_TEXT':'ABSTRACT_ONLY';
    const content=fullText||a.abstract||'';if(!content){p.innerHTML='<div class="an-info">אין תוכן לניתוח. נסה "📋 טקסט מלא".</div>';p.dataset.ready='1';return;}
    const payload=await callClaude(criticUserMsg(a,content,scope));
    LIVE_AN[pmid]={payload,scope};try{localStorage.setItem('lr_an_'+pmid,JSON.stringify(LIVE_AN[pmid]));}catch(e){}
    p.innerHTML=analysisHTML(payload,scope);p.dataset.ready='1';
  }catch(e){p.innerHTML='<div class="an-weak">שגיאת ניתוח: '+esc(String(e.message||e))+'</div><button class="btn" style="margin-top:6px" onclick="setKey()">🔑 עדכן מפתח</button>';}
}
function toggleAn(pmid,btn){
  const p=document.getElementById('an-'+pmid);const o=p.classList.toggle('open');
  btn.innerHTML=o?'✕ סגור ניתוח':'⚡ ניתוח ביקורתי';
  if(o&&!p.dataset.ready){const c=ANALYSES[pmid]||loadLocalAn(pmid);
    if(c){p.innerHTML=analysisHTML(c.payload,c.scope);p.dataset.ready='1';}else analyzeLive(pmid);}
}
function analysisHTML(an,scope){
  let h='';if(scope==='ABSTRACT_ONLY')h+='<div class="scope-warn">⚠️ ניתוח מבוסס תקציר בלבד.</div>';
  h+=`<div style="display:flex;gap:12px;align-items:center;margin-bottom:6px"><span class="badge5">${esc(String(an.critic_score))}/5</span><div class="an-verdict" style="flex:1;margin:0">⚖️ ${esc(an.verdict_line)}</div></div>`;
  if(an.evidence_level)h+=`<div style="font-size:13.5px;margin-bottom:8px"><b>רמת ראיות:</b> ${esc(an.evidence_level)}</div>`;
  const s=an.study_snapshot||{};h+=`<div class="an-box"><b>📋 תמצית</b>תכנון: ${esc(s.design)} · N: ${esc(s.n)}<br>תוצאה: ${esc(s.key_result)}</div>`;
  h+='<div class="an-grid"><div><div class="an-h">✅ חוזקות</div>';(an.strengths||[]).forEach(x=>h+=`<div class="an-strong">${esc(x)}</div>`);
  h+='</div><div><div class="an-h">⚠️ חולשות</div>';(an.weaknesses||[]).forEach(w=>{if(typeof w==='object')h+=`<div class="an-weak"><span class="sev sev-${esc(w.severity)}">${esc(w.severity)}</span>${esc(w.issue)}</div>`;else h+=`<div class="an-weak">${esc(w)}</div>`;});h+='</div></div>';
  h+=`<div class="an-h">🩺 שורה תחתונה</div><div class="an-info">${esc(an.clinical_bottom_line)}</div>`;
  if(an.one_liner_for_rounds)h+=`<div class="an-box"><b>💬 לג'רנל קלאב</b>${esc(an.one_liner_for_rounds)}</div>`;
  return h;
}

// ---- OpenAlex author enrichment (senior author h-index) ----
async function enrichAuthors(){
  const arts=(state.shown||state.articles).filter(a=>a.doi && a.hindex==null);
  await Promise.all(arts.map(a=>oaGate(async()=>{
    try{
      const w=await fetch('https://api.openalex.org/works/doi:'+encodeURIComponent(a.doi)+'?mailto=giladshahak@gmail.com').then(r=>r.json());
      a.fwci=(typeof w.fwci==='number')?w.fwci:null;
      a.citations=(typeof w.cited_by_count==='number')?w.cited_by_count:null;
      const aus=(w.authorships||[]).map(x=>x.author&&x.author.id).filter(Boolean);
      let best=null;
      // check up to first 3 + last 2 authors, take max h-index
      const ids=[...aus.slice(0,3),...aus.slice(-2)];
      for(const u of [...new Set(ids)]){
        const aj=await fetch('https://api.openalex.org/authors/'+u.split('/').pop()+'?mailto=giladshahak@gmail.com').then(r=>r.json());
        const hh=(aj.summary_stats||{}).h_index;if(hh!=null&&(best==null||hh>best))best=hh;
      }
      a.hindex=best==null?0:best;
    }catch(e){a.hindex=0;}
    scoreOf(a);
    const el=document.getElementById('h-'+a.pmid);if(el)el.innerHTML=metaBadge(a);
  })));
  applyView();   // re-rank with author scores
}

// ---- Trends agent ----
async function countQuery(term,minD,maxD){
  const url=EUT+'esearch.fcgi?db=pubmed&retmode=json&rettype=count&retmax=0&datetype=pdat&mindate='+minD+'&maxdate='+maxD+'&term='+encodeURIComponent(term)+TAIL;
  const j=await eutilsJSON(url);return +(j.esearchresult&&j.esearchresult.count||0);
}
function daysAgo(n){const t=new Date(CFG.today_iso+'T00:00:00');t.setDate(t.getDate()-n);return `${t.getFullYear()}/${pad(t.getMonth()+1)}/${pad(t.getDate())}`;}
async function openTrends(){
  document.getElementById('trendsOverlay').classList.add('open');
  const body=document.getElementById('trendsBody');
  body.innerHTML='מנתח את הספרות בשנתיים האחרונות… <span class="spinner"></span>';
  const now=daysAgo(0), y1=daysAgo(365), y2=daysAgo(730);
  const res=[];
  const cat=document.getElementById('trendCat').value;
  const topics=CFG.trend_topics.filter(t=>!cat||t[2]===cat);
  let done=0; const N=topics.length;
  // countQuery כבר עובר דרך ncbiGate — אסור לעטוף שוב (deadlock). מריצים ישירות.
  await Promise.all(topics.map(async([label,q,c])=>{
    try{
      const recent=await countQuery(q,y1,now);
      const prior=await countQuery(q,y2,y1);
      res.push({label,recent,prior,growth:prior>0?(recent-prior)/prior:(recent>0?1:0)});
    }catch(e){res.push({label,recent:0,prior:0,growth:0});}
    done++;document.getElementById('trendsBody').innerHTML=`מנתח… ${done}/${N} נושאים <span class="spinner"></span>`;
  }));
  res.sort((a,b)=>b.growth-a.growth || b.recent-a.recent);
  body.innerHTML=res.map(r=>{
    const pct=Math.round(r.growth*100);
    const cls=pct>=15?'tg-up':pct<=-15?'tg-down':'tg-flat';
    const arrow=pct>=15?'📈':pct<=-15?'📉':'➡️';
    return `<div class="trow"><div class="tgrow ${cls}">${arrow} ${pct>0?'+':''}${pct}%</div>
      <div class="tbar"><div class="lbl">${esc(r.label)}</div><div class="sm">${r.recent} פרסומים בשנה האחרונה · ${r.prior} בקודמת</div></div></div>`;
  }).join('')+'<div class="sm" style="color:var(--muted);font-size:11px;margin-top:10px;text-align:center">מבוסס על ספירת פרסומים ב-PubMed לפי נושא. ערוך את רשימת הנושאים ב-config.TREND_TOPICS</div>';
}
function closeTrends(){document.getElementById('trendsOverlay').classList.remove('open');}

// ---- init ----
function init(){
  document.getElementById('window').value=String(CFG.default_window>=30?CFG.default_window:30);
  document.getElementById('perj').value=String(CFG.default_per_journal);
  const ts=document.getElementById('topic');CFG.topics.forEach(([n])=>{const o=document.createElement('option');o.value=n;o.textContent=n;ts.appendChild(o);});
  const tc=document.getElementById('trendCat');CFG.topics.forEach(([n])=>{const o=document.createElement('option');o.value=n;o.textContent=n;tc.appendChild(o);});
  updateFavBtn();renderLegend();renderChips();runSearch();
}
init();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    print("נוצר:", build())
