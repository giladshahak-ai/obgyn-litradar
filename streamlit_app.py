"""
ObGyn-LitRadar — ממשק משתמש (Streamlit).
הרצה:  streamlit run streamlit_app.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from app import db
from app.config import (JOURNALS, TOPIC_MAP, DEFAULT_TOPIC, DEFAULT_LOOKBACK_DAYS,
                        HIGH_VALUE_ONLY, MIN_IMPORTANCE)
from app.ingest_pubmed import fetch_new
from app.critic import get_or_create_analysis, AnalysisError

st.set_page_config(page_title="ObGyn-LitRadar", page_icon="🩺", layout="wide")

# ── עיצוב גלובלי (RTL + פונט עברי + כרטיסים) ────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#f4f6fb; --card:#ffffff; --ink:#1a2233; --muted:#6b7688;
  --line:#e6eaf2; --brand:#3257d6; --brand-soft:#eef2ff;
}
html, body, [class*="css"]  { font-family:'Heebo', sans-serif; }
.stApp { direction: rtl; background:var(--bg); }
section[data-testid="stSidebar"] { direction: rtl; background:#fff; border-left:1px solid var(--line); }
section[data-testid="stSidebar"] * { font-family:'Heebo', sans-serif; }
#MainMenu, header[data-testid="stHeader"], footer { visibility:hidden; height:0; }
.block-container{ padding-top:1.2rem; max-width:1050px; }

/* כותרת על */
.hero{ background:linear-gradient(120deg,#3257d6,#5b8def); color:#fff;
  border-radius:18px; padding:20px 26px; margin-bottom:18px;
  box-shadow:0 8px 24px rgba(50,87,214,.18); }
.hero h1{ margin:0; font-size:26px; font-weight:800; letter-spacing:-.5px; }
.hero p{ margin:4px 0 0; opacity:.92; font-size:14px; }

/* כרטיס מאמר */
.lr-card{ background:var(--card); border:1px solid var(--line); border-radius:16px;
  padding:18px 20px; margin-bottom:16px; transition:.15s; }
.lr-card:hover{ box-shadow:0 6px 22px rgba(20,30,60,.09); transform:translateY(-1px); }
.lr-title{ font-size:18px; font-weight:700; line-height:1.45; color:var(--ink);
  text-decoration:none; }
.lr-title:hover{ color:var(--brand); }
.lr-meta{ color:var(--muted); font-size:13px; margin:6px 0 10px; }

/* ציון — עיגול צבעוני */
.score-ring{ width:60px; height:60px; border-radius:50%; display:flex; flex-direction:column;
  align-items:center; justify-content:center; font-weight:800; font-size:20px; line-height:1; }
.score-ring small{ font-size:9px; font-weight:500; opacity:.8; margin-top:2px; }
.s-hi{ background:#e6f4ea; color:#1a7f37; border:2px solid #1a7f37; }
.s-mid{ background:#fff5e0; color:#9a6700; border:2px solid #d9a300; }
.s-lo{ background:#eef1f4; color:#57606a; border:2px solid #b6bfcc; }

/* תגיות */
.chip{ display:inline-block; border-radius:20px; padding:3px 11px; font-size:12px;
  font-weight:500; margin:0 0 5px 5px; }
.chip-topic{ background:var(--brand-soft); color:#2742a8; }
.chip-star{ background:#fff3cd; color:#8a6d00; font-weight:700; }

/* בלוקים בניתוח */
.verdict{ background:linear-gradient(90deg,#fff9e8,#fffdf6); border-right:5px solid #e8b500;
  padding:12px 16px; border-radius:10px; margin:10px 0; font-weight:600; font-size:15px; }
.strong{ background:#edf9f0; border-right:3px solid #2a9d4a; padding:8px 12px;
  border-radius:8px; margin:5px 0; font-size:14px; }
.weak{ background:#fdeeee; border-right:3px solid #d9534f; padding:8px 12px;
  border-radius:8px; margin:5px 0; font-size:14px; }
div.stButton > button{ border-radius:10px; font-weight:600; border:1px solid var(--line); }
div.stButton > button:hover{ border-color:var(--brand); color:var(--brand); }
</style>
""", unsafe_allow_html=True)

db.init_db()

TOPIC_NAMES = [t[0] for t in TOPIC_MAP] + [DEFAULT_TOPIC]
STUDY_TYPES = ["Meta-Analysis", "Randomized Controlled Trial", "Systematic Review",
               "Practice Guideline", "Guideline"]
_HV_KEYS = ["Randomized", "Meta-Analysis", "Systematic Review", "Guideline",
            "Phase III", "Phase IV", "Consensus"]
_HV_TITLE = ["randomi", "meta-analysis", "systematic review", "guideline",
             "committee opinion", "consensus", "phase 3", "phase iii"]


def score_class(v):
    return "s-hi" if v >= 65 else "s-mid" if v >= 52 else "s-lo"


def high_value_label(art):
    """מחזיר תווית ערך-גבוה (RCT/מטא/סקירה/הנחיה) או None."""
    pts = " ".join(art.get("pub_types", []))
    title = (art.get("title") or "").lower()
    if "Randomized" in pts or "randomi" in title:
        return "RCT"
    if "Meta-Analysis" in pts or "meta-analysis" in title or "metaanalysis" in title:
        return "מטא-אנליזה"
    if "Systematic Review" in pts or "systematic review" in title:
        return "סקירה שיטתית"
    if "Guideline" in pts or "guideline" in title or "committee opinion" in title:
        return "הנחיה"
    if "Phase III" in pts or "phase 3" in title or "phase iii" in title:
        return "Phase III"
    return None


# ── סרגל צד ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🩺 LitRadar")
    st.caption("מכ\"ם ספרות מיילדות וגינקולוגיה — איכות בלבד")

    with st.expander("⬇️ איסוף מאמרים", expanded=False):
        lookback = st.number_input("משוך מ-N הימים האחרונים", 1, 90, DEFAULT_LOOKBACK_DAYS)
        hv_only = st.checkbox("רק ערך גבוה (RCT/מטא/הנחיות)", value=HIGH_VALUE_ONLY)
        if st.button("משוך מ-PubMed עכשיו", use_container_width=True):
            log = st.empty(); msgs = []
            def prog(m): msgs.append(m); log.text("\n".join(msgs[-12:]))
            with st.spinner("מושך…"):
                s = fetch_new(lookback_days=int(lookback), progress=prog, high_value_only=hv_only)
            st.success(f'נוספו {s["new"]} מאמרים.')
        last = db.get_meta("last_run")
        if last: st.caption(f"ריצה אחרונה: {last[:16].replace('T',' ')}")

    st.divider()
    st.markdown("**סינון**")
    f_topic = st.selectbox("נושא", ["— הכל —"] + TOPIC_NAMES)
    f_journal = st.selectbox("עיתון", ["— הכל —"] + db.all_journals_in_db())
    f_study = st.selectbox("סוג מחקר", ["— הכל —"] + STUDY_TYPES)
    f_min = st.slider("ציון חשיבות מינימלי", 0, 100, int(MIN_IMPORTANCE))
    f_days = st.slider("פורסם ב-N הימים האחרונים", 0, 365, 0, help="0 = ללא הגבלה")
    f_search = st.text_input("חיפוש חופשי")


# ── כותרת ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="hero"><h1>📰 ספרות נבחרת — מיילדות וגינקולוגיה</h1>'
    '<p>רק מחקרים משני-פרקטיקה, רעיונות חדשניים ו-RCTs · מדורגים לפי חשיבות</p></div>',
    unsafe_allow_html=True)

articles = db.query_articles(
    topic=None if f_topic.startswith("—") else f_topic,
    journal=None if f_journal.startswith("—") else f_journal,
    study_type=None if f_study.startswith("—") else f_study,
    days=f_days or None, search=f_search or None,
)
articles = [a for a in articles if a.get("importance", 0) >= f_min]

st.caption(f"מציג {len(articles)} מאמרים")
if not articles:
    st.info("אין מאמרים. פתח **'איסוף מאמרים'** בסרגל הצד ולחץ **'משוך מ-PubMed עכשיו'**.")


# ── רינדור ניתוח ─────────────────────────────────────────────────────────
def render_analysis(payload, scope, from_cache):
    if scope == "ABSTRACT_ONLY":
        st.warning("⚠️ ניתוח מבוסס **תקציר בלבד** (טקסט מלא לא נשלף).")
    if payload.get("source_scope_warning"):
        st.warning(payload["source_scope_warning"])
    c1, c2 = st.columns([4, 1])
    c1.markdown(f'<div class="verdict">⚖️ {payload.get("verdict_line","")}</div>', unsafe_allow_html=True)
    c2.metric("ציון ביקורתי", f'{payload.get("critic_score","?")}/5')
    st.caption(payload.get("score_rationale", ""))
    st.markdown(f'**רמת ראיות:** {payload.get("evidence_level","—")}')

    snap = payload.get("study_snapshot", {})
    if snap:
        with st.expander("📋 תמצית המחקר", expanded=True):
            st.markdown(
                f"- **תכנון:** {snap.get('design','—')}\n"
                f"- **אוכלוסייה:** {snap.get('population','—')}\n"
                f"- **N:** {snap.get('n','—')}\n"
                f"- **התערבות:** {snap.get('intervention','—')}\n"
                f"- **תוצא ראשוני:** {snap.get('primary_outcome','—')}\n"
                f"- **תוצאה מרכזית:** {snap.get('key_result','—')}")

    cs, cw = st.columns(2)
    cs.markdown("#### ✅ חוזקות")
    for s in payload.get("strengths", []):
        cs.markdown(f'<div class="strong">{s}</div>', unsafe_allow_html=True)
    cw.markdown("#### ⚠️ חולשות")
    for w in payload.get("weaknesses", []):
        if isinstance(w, dict):
            cw.markdown(f'<div class="weak"><b>[{w.get("severity","")}]</b> {w.get("issue","")}'
                        f'<br><small>{w.get("impact","")}</small></div>', unsafe_allow_html=True)
        else:
            cw.markdown(f'<div class="weak">{w}</div>', unsafe_allow_html=True)

    spin = payload.get("spin_alert", {})
    if spin and spin.get("detected"):
        st.markdown("#### 🎈 התראת Spin")
        st.error(f'**ציטוט:** "{spin.get("quote","")}"\n\n**המציאות:** {spin.get("reality","")}')
    flags = payload.get("stats_red_flags", [])
    if flags:
        st.markdown("#### 🚩 דגלים אדומים סטטיסטיים")
        for fl in flags: st.markdown(f"- {fl}")

    st.markdown("#### 🩺 שורה תחתונה קלינית")
    st.info(payload.get("clinical_bottom_line", "—"))
    cc1, cc2 = st.columns(2)
    cc1.markdown("**🔄 מה היה משנה את ההכרעה**"); cc1.write(payload.get("what_would_change_my_mind", "—"))
    cc2.markdown("**😈 פרקליט השטן**"); cc2.write(payload.get("devils_advocate", "—"))
    if payload.get("one_liner_for_rounds"):
        st.success(f'💬 לג\'רנל קלאב: "{payload["one_liner_for_rounds"]}"')
    if from_cache:
        st.caption("↻ מתוך מטמון. לחץ 'נתח מחדש' לרענון.")


# ── כרטיסים ──────────────────────────────────────────────────────────────
for art in articles:
    pmid = art["pmid"]
    with st.container():
        st.markdown('<div class="lr-card">', unsafe_allow_html=True)
        col_score, col_body = st.columns([1, 8])
        with col_score:
            v = art.get("importance", 0)
            st.markdown(f'<div class="score-ring {score_class(v)}">{v:.0f}<small>חשיבות</small></div>',
                        unsafe_allow_html=True)
        with col_body:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            st.markdown(f'<a class="lr-title" href="{url}" target="_blank">{art["title"]}</a>',
                        unsafe_allow_html=True)
            authors = art.get("authors", [])
            meta = art.get("journal", "")
            if art.get("pub_date"): meta += f' · {art["pub_date"]}'
            if authors: meta += f' · {authors[0]}{" et al." if len(authors)>1 else ""}'
            st.markdown(f'<div class="lr-meta">{meta}</div>', unsafe_allow_html=True)

            chips = ""
            hv = high_value_label(art)
            if hv: chips += f'<span class="chip chip-star">⭐ {hv}</span>'
            for t in art.get("topics", []):
                chips += f'<span class="chip chip-topic">{t}</span>'
            st.markdown(chips, unsafe_allow_html=True)

            with st.expander("תקציר"):
                st.write(art.get("abstract") or "— אין תקציר —")

            b = st.columns([1, 1, 5])
            analyze = b[0].button("⚡ ניתוח", key=f"an_{pmid}")
            reanalyze = b[1].button("↻ מחדש", key=f"re_{pmid}")
            if analyze or reanalyze:
                try:
                    with st.spinner("המבקר הקליני עובד…"):
                        payload, scope, cached = get_or_create_analysis(pmid, force=reanalyze)
                    render_analysis(payload, scope, cached and not reanalyze)
                except AnalysisError as e:
                    st.error(f"שגיאת ניתוח: {e}")
            elif db.get_analysis(pmid):
                st.caption("✓ קיים ניתוח שמור — לחץ '⚡ ניתוח' להצגה.")
        st.markdown('</div>', unsafe_allow_html=True)
