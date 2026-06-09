"""
תצורה מרכזית: רשימת עיתונים, מיפוי נושאים, ומשקלי דירוג.
ערוך כאן כדי להוסיף/להסיר עיתונים או לכוונן את הדירוג — בלי לגעת בקוד הלוגי.
"""
import os
from pathlib import Path

# ── נתיבים ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "litradar.db"
BROWSER_PROFILE_DIR = BASE_DIR / ".browser_profile"  # פרופיל Playwright מתמשך

# ── הגדרות איסוף ────────────────────────────────────────────────────────
# כמה ימים אחורה למשוך בכל ריצה (datetype=edat — תאריך כניסה ל-PubMed).
# תזמון שבועי → 7 ימים. הוסף מרווח קטן (10) כדי לא לפספס בגבול.
DEFAULT_LOOKBACK_DAYS = 10

# רק מאמרים "משני-פרקטיקה": RCT, מטא-אנליזות, סקירות שיטתיות, הנחיות.
# כשדולק — מצמצם דרמטית את הנפח לאיכות בלבד. כבה (False) כדי לאסוף הכל.
HIGH_VALUE_ONLY = True

# סף חשיבות מינימלי לתצוגה (0..100). 0 = ללא סף. ניתן לכוונון גם בממשק.
MIN_IMPORTANCE = 0
# אימייל ל-NCBI (חובה באתיקה; מאפשר rate-limit גבוה יותר). אופציונלי key.
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")

# ── עיתוני יעד ──────────────────────────────────────────────────────────
# filter_obgyn=True  → עיתון כללי, נסנן רק מאמרי מיילדות/גינקולוגיה.
# filter_obgyn=False → עיתון ייעודי, ניקח הכל.
# primary=True → עיתוני הליבה של המשתמש; הדייג'סט השבועי מתמקד בהם (2-3 לכל אחד).
# primary=False → נאספים לחיפוש/ארכיון אך לא נכנסים לדייג'סט השבועי.
JOURNALS = [
    # ── עיתוני הליבה (לפי בקשת המשתמש). issn=print (לחיפוש), issn_e=electronic (כפי שמאוחסן) ──
    {"name": "Am J Obstet Gynecol",      "issn": "0002-9378", "issn_e": "1097-6868", "filter_obgyn": False, "weight": 9,  "primary": True,  "nick": "AJOG"},
    {"name": "Obstet Gynecol (Green J)", "issn": "0029-7844", "issn_e": "1873-233X", "filter_obgyn": False, "weight": 9,  "primary": True,  "nick": "Green Journal"},
    {"name": "BJOG",                     "issn": "1470-0328", "issn_e": "1471-0528", "filter_obgyn": False, "weight": 8,  "primary": True,  "nick": "BJOG"},
    {"name": "NEJM",                     "issn": "0028-4793", "issn_e": "1533-4406", "filter_obgyn": True,  "weight": 10, "primary": True,  "nick": "NEJM"},
    {"name": "The Lancet",               "issn": "0140-6736", "issn_e": "1474-547X", "filter_obgyn": True,  "weight": 10, "primary": True,  "nick": "Lancet"},
    # "White Journal" = Ultrasound in Obstetrics & Gynecology (לפי בקשת המשתמש)
    {"name": "Ultrasound Obstet Gynecol","issn": "0960-7692", "issn_e": "1469-0705", "filter_obgyn": False, "weight": 8,  "primary": True,  "nick": "Ultrasound O&G"},
    # ── עיתונים נוספים (לא בדייג'סט; לחיפוש/ארכיון) ──
    {"name": "JAMA",                     "issn": "0098-7484", "filter_obgyn": True,  "weight": 9,  "primary": False},
    {"name": "BMJ",                      "issn": "0959-8138", "filter_obgyn": True,  "weight": 8,  "primary": False},
    {"name": "Human Reproduction",       "issn": "0268-1161", "filter_obgyn": False, "weight": 7,  "primary": False},
    {"name": "Fertility & Sterility",    "issn": "0015-0282", "filter_obgyn": False, "weight": 7,  "primary": False},
]

# ── דייג'סט שבועי ───────────────────────────────────────────────────────
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  לוח הבקרה של הדייג'סט — שנֵה כאן (וזהו) כדי לכוונן זמן וכמות          ║
# ╚══════════════════════════════════════════════════════════════════════╝
DIGEST_WINDOW_DAYS  = 14    # ⏱️  ברירת מחדל: כמה ימים אחורה להציג (ניתן לשינוי חי גם באתר)
DIGEST_PER_JOURNAL  = 3     # 🔢  ברירת מחדל: כמה מאמרים מקסימום מכל עיתון (ניתן לשינוי חי באתר)
DIGEST_MAX_TOTAL    = 30    # 🔝  תקרה לכמות המאמרים הכוללת המוצגת

# כמה לאסוף "למאגר האתר" (superset) — גדול מספיק כדי שהפקדים באתר יוכלו להרחיב:
DIGEST_BAKE_WINDOW_DAYS = 90
DIGEST_BAKE_PER_JOURNAL = 8

# פילטר לעיתונים הכלליים. משלב MeSH (מדויק) עם מילות טקסט בכותרת/תקציר (tiab) —
# כי מאמרים טריים עדיין חסרי MeSH, וה-tiab תופס אותם ביום הפרסום.
OBGYN_FILTER = (
    '('
    '"Obstetrics"[Mesh] OR "Gynecology"[Mesh] OR "Pregnancy"[Mesh] '
    'OR "Pregnancy Complications"[Mesh] OR "Genital Diseases, Female"[Mesh] '
    'OR "Reproductive Medicine"[Mesh] OR "Reproductive Techniques, Assisted"[Mesh] '
    'OR "Labor, Obstetric"[Mesh] OR "Prenatal Care"[Mesh] '
    'OR pregnan*[tiab] OR obstetric*[tiab] OR gyneco*[tiab] OR gynaeco*[tiab] '
    'OR cesarean[tiab] OR caesarean[tiab] OR preeclampsia[tiab] OR "pre-eclampsia"[tiab] '
    'OR eclampsia[tiab] OR endometri*[tiab] OR menopaus*[tiab] OR "preterm birth"[tiab] '
    'OR stillbirth[tiab] OR "in vitro fertilization"[tiab] OR "in vitro fertilisation"[tiab] '
    'OR contracepti*[tiab] OR "cervical cancer"[tiab] OR "ovarian cancer"[tiab]'
    ')'
)

# פילטר "ערך גבוה" — מחקרים משני-פרקטיקה בלבד. משלב PublicationType (מאמרים מתויגים)
# עם מילות כותרת [ti] (מאמרים טריים שעדיין לא תויגו). ביחד: RCT / מטא / סקירה / הנחיה.
HIGH_VALUE_FILTER = (
    '('
    '"Randomized Controlled Trial"[ptyp] OR "Meta-Analysis"[ptyp] '
    'OR "Systematic Review"[ptyp] OR "Practice Guideline"[ptyp] OR "Guideline"[ptyp] '
    'OR "Clinical Trial, Phase III"[ptyp] OR "Clinical Trial, Phase IV"[ptyp] '
    'OR "Consensus Development Conference"[ptyp] '
    'OR randomized[ti] OR randomised[ti] OR "randomized controlled"[tiab] '
    'OR "randomised controlled"[tiab] OR "meta-analysis"[ti] OR metaanalysis[ti] '
    'OR "systematic review"[ti] OR "phase 3"[ti] OR "phase III"[ti] '
    'OR "phase 3"[tiab] OR "practice guideline"[ti] OR "clinical practice guideline"[ti] '
    'OR "committee opinion"[ti] OR "consensus statement"[ti] OR guideline[ti]'
    ')'
)

# ── מיפוי נושאים — 6 קטגוריות בלבד (לפי בקשת המשתמש) ───────────────────
# נבדק לפי הכלת מילת מפתח ב-MeSH/כותרת/תקציר. מאמר יכול לקבל כמה תגיות.
TOPIC_MAP = [
    ("מיילדות", [  # הריון, לידה, סיבוכים, רפואת אם-עובר
        "Pregnan", "Obstetric", "Pre-Eclampsia", "Preeclampsia", "Eclampsia",
        "Gestational", "Premature Birth", "Preterm", "Ectopic", "Miscarriage", "Abortion",
        "Stillbirth", "Twin", "Antenatal", "Corticosteroid", "Labor", "Labour", "Delivery",
        "Cesarean", "Caesarean", "Parturition", "Postpartum", "Fetal", "Fetus", "Foetal",
        "Prenatal", "Amniocentesis", "Placenta", "Doppler", "Maternal", "Perinatal", "Neonatal"]),
    ("פוריות", [  # פוריות והפריה
        "Reproductive Techniques", "Fertilization in Vitro", "Infertility", "Subfertility",
        "Ovulation Induction", "Embryo", "Sperm", "Oocyte", "IVF", "ICSI",
        "Assisted Reproduct", "Fertility Preservation", "Frozen Embryo", "Blastocyst"]),
    ("אנדוקרינולוגיה", [  # אנדוקרינולוגיה רבייתית
        "Polycystic Ovary", "PCOS", "Menopaus", "Amenorrhea", "Hormone Replacement",
        "Hot Flash", "Vasomotor", "Menstruation Disturbances", "Hyperandrogen",
        "Hyperprolactin", "Hypogonad", "Estrogen", "Androgen", "Endocrine"]),
    ("אונקוגינקולוגיה", [  # ממאירויות גינקולוגיות
        "Neoplasm", "Cancer", "Carcinoma", "Tumor", "Tumour", "Oncolog", "Malignan",
        "Sarcoma", "Cervical Intraepithelial", "Trophoblastic"]),
    ("אנדומטריוזיס", [
        "Endometriosis", "Adenomyosis", "Pelvic Pain", "Dysmenorrhea"]),
    ("גינקולוגיה כללית", [  # כולל רצפת אגן, ניתוחי, זיהומים, מניעה
        "Hysterectomy", "Leiomyoma", "Fibroid", "Contraception", "Heavy Menstrual",
        "Menorrhagia", "Pelvic Floor", "Urinary Incontinence", "Pelvic Organ Prolapse",
        "Sexually Transmitted", "Vaginosis", "Papillomavirus", "Pelvic Inflammatory",
        "Gynecologic Surgical", "Laparoscop", "Hysteroscop", "Vulva", "Cervical Cancer Screening",
        "Papanicolaou"]),
]
DEFAULT_TOPIC = "גינקולוגיה כללית"

# ── ציון חשיבות (0..100) — שלושה גורמים אובייקטיביים בלבד ───────────────
# הציון = רמת ראיות (סוג מחקר) 40% + השפעת העיתון 30% + מעמד החוקרים 30%.
# "מעמד החוקרים" = מדד h-index של החוקר המשפיע ביותר ברשימת המחברים
# (נמשך מ-Semantic Scholar). הסרנו "טריות" — היה סובייקטיבי ולא ברור.
SCORE_WEIGHTS = {
    "design":  0.40,   # רמת ראיות — מטא-אנליזה/RCT > תצפיתי > דעה
    "journal": 0.30,   # השפעת העיתון
    "author":  0.30,   # מעמד החוקרים (h-index מקסימלי בין המחברים)
}
# נרמול ה-h-index: ערך זה נחשב "פסגת התחום" (h-index שמעליו = ציון מלא).
AUTHOR_HINDEX_TOP = 50

# דירוג סוג מחקר (0..1) לפי Publication Type של PubMed
# כל קבוצה: מילות מפתח (נסרקות גם ב-PublicationType וגם בכותרת) → דירוג.
DESIGN_RANK = [
    (["Meta-Analysis", "Meta-analysis", "Systematic Review"],         1.00),
    (["Randomized Controlled Trial", "Randomized", "Randomised",
      "RCT", "Double-Blind", "Placebo-Controlled"],                   0.90),
    (["Clinical Trial", "Controlled Clinical Trial"],                 0.70),
    (["Multicenter Study", "Multicentre", "Comparative Study"],       0.60),
    (["Observational Study", "Cohort", "Prospective", "Population-Based"], 0.55),
    (["Case-Control"],                                                0.45),
    (["Review", "Practice Guideline", "Guideline", "Committee Opinion"], 0.50),
    (["Case Report", "Case Reports", "Case Series"],                  0.20),
    (["Editorial", "Comment", "Letter"],                             0.10),
]
DESIGN_RANK_DEFAULT = 0.35

# ── ניתוח LLM ──────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "claude-sonnet-4-6")
ANALYSIS_MAX_TOKENS = 4000
