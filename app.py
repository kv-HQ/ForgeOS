import streamlit as st
import json
import os
import uuid
import random
import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ForgeOS",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Design System & CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ══ Reset & base ══════════════════════════════════════════ */
*, html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif !important;
    box-sizing: border-box;
}
.stApp { background: #0d1117; }

/* ══ Sidebar ════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: #010409 !important;
    border-right: 1px solid #21262d !important;
    min-width: 220px !important;
    max-width: 220px !important;
}
[data-testid="stSidebar"] > div { padding: 0 !important; }
[data-testid="stSidebarContent"] { padding: 0 !important; }

/* Hide default radio label */
[data-testid="stSidebar"] .stRadio > label { display: none !important; }
[data-testid="stSidebar"] .stRadio > div {
    display: flex !important;
    flex-direction: column !important;
    gap: 1px !important;
}
[data-testid="stSidebar"] .stRadio > div > label {
    display: flex !important;
    align-items: center !important;
    padding: 6px 12px 6px 16px !important;
    border-radius: 6px !important;
    margin: 1px 6px !important;
    cursor: pointer !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #b0b8c4 !important;
    transition: background 0.15s, color 0.15s !important;
    border: none !important;
}
[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: #161b22 !important;
    color: #f0f6fc !important;
}
[data-testid="stSidebar"] .stRadio > div > label[data-baseweb="radio"] { }
[data-testid="stSidebar"] .stRadio [aria-checked="true"] ~ span,
[data-testid="stSidebar"] .stRadio input:checked ~ span {
    color: #e6edf3 !important;
}
[data-testid="stSidebar"] .stRadio > div > label > div:first-child {
    display: none !important;
}
[data-testid="stSidebar"] .stRadio > div > label > div:last-child > p {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: inherit !important;
    margin: 0 !important;
}

/* ══ Main content padding ═══════════════════════════════════ */
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ══ Top bar ════════════════════════════════════════════════ */
.forge-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 28px;
    border-bottom: 1px solid #21262d;
    background: #0d1117;
    position: sticky;
    top: 0;
    z-index: 100;
}
.forge-topbar-left {
    display: flex;
    align-items: center;
    gap: 8px;
}
.forge-breadcrumb {
    font-size: 12px;
    color: #7d8490;
    font-weight: 500;
}
.forge-breadcrumb span {
    color: #f0f6fc;
    font-weight: 600;
    font-size: 14px;
}
.forge-topbar-actions {
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ══ Page content wrapper ═══════════════════════════════════ */
.page-content { padding: 24px 28px; }

/* ══ Stat strip (Apollo-style) ══════════════════════════════ */
.stat-strip {
    display: flex;
    border: 1px solid #21262d;
    border-radius: 8px;
    overflow: hidden;
    background: #161b22;
    margin-bottom: 20px;
}
.stat-item {
    flex: 1;
    padding: 16px 20px;
    border-right: 1px solid #21262d;
    min-width: 0;
}
.stat-item:last-child { border-right: none; }
.stat-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #7d8490;
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.stat-value {
    font-size: 22px;
    font-weight: 700;
    color: #f0f6fc;
    line-height: 1;
    margin-bottom: 4px;
}
.stat-sub {
    font-size: 11px;
    color: #7d8490;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.stat-delta-up   { color: #3fb950; font-size: 11px; font-weight: 600; }
.stat-delta-down { color: #f85149; font-size: 11px; font-weight: 600; }

/* ══ Section header ══════════════════════════════════════════ */
.section-hd {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8b949e;
    margin: 24px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #21262d;
}

/* ══ Card ════════════════════════════════════════════════════ */
.forge-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 16px 20px;
    transition: border-color 0.15s;
}
.forge-card:hover { border-color: #30363d; }

/* ══ Score badge ════════════════════════════════════════════ */
.badge-score {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}
.badge-green  { background: #0d2b1a; color: #3fb950; border: 1px solid #238636; }
.badge-yellow { background: #2b1f05; color: #d29922; border: 1px solid #9e6a03; }
.badge-red    { background: #2b0f0f; color: #f85149; border: 1px solid #6e1818; }

/* ══ Status pill ════════════════════════════════════════════ */
.pill {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.02em;
    white-space: nowrap;
}
.pill-new      { background: #0c1e35; color: #58a6ff; border: 1px solid #1f6feb44; }
.pill-scored   { background: #0d2b1a; color: #3fb950; border: 1px solid #23863644; }
.pill-review   { background: #2b1f05; color: #d29922; border: 1px solid #9e6a0344; }
.pill-approved { background: #1b0f2e; color: #a371f7; border: 1px solid #6e40c944; }
.pill-rejected { background: #2b0f0f; color: #f85149; border: 1px solid #6e181844; }

/* ══ Table ═══════════════════════════════════════════════════ */
.forge-table { width: 100%; border-collapse: collapse; }
.forge-th {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #484f58;
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid #21262d;
    white-space: nowrap;
}
.forge-tr {
    border-bottom: 1px solid #161b22;
    transition: background 0.1s;
}
.forge-tr:hover { background: #161b22; }
.forge-td {
    padding: 10px 12px;
    font-size: 13px;
    color: #b0b8c4;
    vertical-align: middle;
}
.forge-td-primary { color: #f0f6fc; font-weight: 500; }
.forge-id {
    font-size: 11px;
    font-weight: 600;
    color: #8b949e;
    font-family: 'SF Mono', monospace !important;
    background: #161b22;
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid #30363d;
}

/* ══ Kanban column ══════════════════════════════════════════ */
.kanban-col-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 0 10px 0;
    margin-bottom: 10px;
    border-bottom: 1px solid #21262d;
}
.kanban-col-name {
    font-size: 12px;
    font-weight: 600;
    color: #b0b8c4;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.kanban-count {
    font-size: 11px;
    font-weight: 600;
    color: #8b949e;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 9999px;
    padding: 1px 7px;
}
.kanban-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 8px;
    transition: border-color 0.15s, box-shadow 0.15s;
    cursor: default;
}
.kanban-card:hover {
    border-color: #484f58;
    box-shadow: 0 2px 12px #00000040;
}
.kanban-card-title {
    font-size: 12px;
    font-weight: 500;
    color: #f0f6fc;
    margin-bottom: 6px;
    line-height: 1.4;
}
.kanban-card-meta {
    font-size: 11px;
    color: #7d8490;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.kanban-empty {
    font-size: 12px;
    color: #484f58;
    text-align: center;
    padding: 20px 8px;
    border: 1px dashed #30363d;
    border-radius: 6px;
}

/* ══ Upload zone ════════════════════════════════════════════ */
[data-testid="stFileUploader"] {
    background: #161b22 !important;
    border: 1px dashed #30363d !important;
    border-radius: 8px !important;
    transition: border-color 0.15s !important;
}
[data-testid="stFileUploader"]:hover { border-color: #58a6ff !important; }
[data-testid="stFileUploader"] label { color: #8d96a3 !important; }

/* ══ Buttons ════════════════════════════════════════════════ */
.stButton > button {
    background: #21262d !important;
    color: #c9d1d9 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    padding: 5px 14px !important;
    transition: background 0.15s, border-color 0.15s !important;
    white-space: nowrap !important;
}
.stButton > button:hover {
    background: #30363d !important;
    border-color: #8b949e !important;
    color: #e6edf3 !important;
}
.stButton > button[kind="primary"],
.stButton > button:first-child[data-primary="true"] {
    background: #1f6feb !important;
    border-color: #1f6feb !important;
    color: white !important;
}

/* ══ Inputs ════════════════════════════════════════════════ */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] > div > div {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    color: #c9d1d9 !important;
    font-size: 13px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #1f6feb !important;
    box-shadow: 0 0 0 3px #1f6feb25 !important;
}

/* ══ Expander ═══════════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary { color: #c9d1d9 !important; }

/* ══ Progress bar ═══════════════════════════════════════════ */
[data-testid="stProgress"] > div > div { border-radius: 2px !important; }
[data-testid="stProgress"] { border-radius: 2px !important; }

/* ══ Alerts ════════════════════════════════════════════════ */
[data-testid="stAlert"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
}

/* ══ Rubric criterion card ══════════════════════════════════ */
.crit-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 16px 18px;
    margin-bottom: 10px;
    transition: border-color 0.15s;
}
.crit-card:hover { border-color: #30363d; }
.crit-name {
    font-size: 13px;
    font-weight: 600;
    color: #e6edf3;
    margin-bottom: 2px;
}
.crit-desc { font-size: 12px; color: #8d96a3; }
.crit-weight {
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    background: #0c1e35;
    color: #58a6ff;
    border: 1px solid #1f6feb33;
}
.anchor-band {
    background: #0d1117;
    border-radius: 6px;
    padding: 8px 12px;
    margin: 4px 0;
    font-size: 12px;
}
.anchor-low  { border-left: 3px solid #f85149; }
.anchor-mid  { border-left: 3px solid #d29922; }
.anchor-high { border-left: 3px solid #3fb950; }
.subfactor-tag {
    display: inline-block;
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    color: #8d96a3;
    margin: 2px;
}
.redflag-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #f85149;
    margin: 3px 0;
}

/* ══ Gating rule ════════════════════════════════════════════ */
.gate-rule {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: #2b0f0f18;
    border: 1px solid #6e181822;
    border-radius: 6px;
    margin-bottom: 6px;
    font-size: 12px;
    color: #e6edf3;
}

/* ══ Sidebar custom HTML ════════════════════════════════════ */
.sb-logo {
    padding: 16px 14px 12px 14px;
    border-bottom: 1px solid #21262d;
    margin-bottom: 8px;
}
.sb-wordmark {
    font-size: 15px;
    font-weight: 800;
    color: #e6edf3;
    letter-spacing: -0.03em;
    display: flex;
    align-items: center;
    gap: 8px;
}
.sb-tag {
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #30363d;
    margin-top: 2px;
}
.sb-section-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #30363d;
    padding: 12px 16px 4px 16px;
}
.sb-divider { border-top: 1px solid #21262d; margin: 8px 0; }
.sb-stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 16px;
    font-size: 12px;
}
.sb-stat-label { color: #8b949e; }
.sb-stat-val   { color: #b0b8c4; font-weight: 600; }

/* ══ Empty state ════════════════════════════════════════════ */
.empty-state {
    text-align: center;
    padding: 60px 24px;
}
.empty-icon  { font-size: 32px; margin-bottom: 12px; opacity: 0.3; }
.empty-title { font-size: 15px; font-weight: 600; color: #8b949e; margin-bottom: 6px; }
.empty-sub   { font-size: 13px; color: #484f58; }

/* ══ Overrides ══════════════════════════════════════════════ */
hr { border-color: #30363d !important; margin: 12px 0 !important; }
[data-testid="stMarkdownContainer"] p { font-size: 13px; color: #b0b8c4; }
</style>
""", unsafe_allow_html=True)

# ─── Load Rubric ─────────────────────────────────────────────────────────────
@st.cache_data
def load_rubric():
    path = os.path.join(os.path.dirname(__file__), "rubric.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

rubric = load_rubric()

# ─── Session State ────────────────────────────────────────────────────────────
if "submissions" not in st.session_state:
    st.session_state.submissions = []
if "next_id" not in st.session_state:
    st.session_state.next_id = 1001

STAGES = rubric.get("pipeline_stages", [
    {"id": 1, "name": "Intake",       "color": "#6e40c9"},
    {"id": 2, "name": "Concept",      "color": "#1f6feb"},
    {"id": 3, "name": "Validation",   "color": "#0ea5e9"},
    {"id": 4, "name": "Prototyping",  "color": "#238636"},
    {"id": 5, "name": "Market Test",  "color": "#9e6a03"},
    {"id": 6, "name": "Scaling",      "color": "#d18000"},
    {"id": 7, "name": "Monitoring",   "color": "#8b949e"},
])
STAGE_NAMES = [s["name"] for s in STAGES]
THRESHOLDS  = rubric.get("scoring_thresholds", {"green": 70, "yellow": 50})

# ─── Helpers ──────────────────────────────────────────────────────────────────
def score_badge_class(score):
    if score >= THRESHOLDS["green"]:  return "badge-green"
    if score >= THRESHOLDS["yellow"]: return "badge-yellow"
    return "badge-red"

def score_hex(score):
    if score >= THRESHOLDS["green"]:  return "#3fb950"
    if score >= THRESHOLDS["yellow"]: return "#d29922"
    return "#f85149"

def pill_class(status):
    return {
        "New":      "pill-new",
        "Scored":   "pill-scored",
        "In Review":"pill-review",
        "Approved": "pill-approved",
        "Rejected": "pill-rejected",
    }.get(status, "pill-new")

def make_gauge(score, title="", height=150):
    color = score_hex(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"size": 24, "color": color, "family": "Inter"}, "suffix": ""},
        title={"text": title, "font": {"size": 10, "color": "#484f58", "family": "Inter"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#21262d",
                     "tickfont": {"color": "#30363d", "size": 8}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "#0d1117",
            "bordercolor": "#21262d",
            "borderwidth": 1,
            "steps": [
                {"range": [0, THRESHOLDS["yellow"]], "color": "#2b0f0f18"},
                {"range": [THRESHOLDS["yellow"], THRESHOLDS["green"]], "color": "#2b1f0518"},
                {"range": [THRESHOLDS["green"], 100], "color": "#0d2b1a18"},
            ],
        }
    ))
    fig.update_layout(
        paper_bgcolor="#161b22", plot_bgcolor="#161b22",
        height=height, margin=dict(l=10, r=10, t=24, b=4),
        font={"family": "Inter"},
    )
    return fig

def ai_score_submission(submission, rubric_data):
    category_scores = {}
    innovation = None
    feasibility = None
    for crit in rubric_data.get("criteria", []):
        base  = random.randint(45, 92)
        noise = random.randint(-10, 10)
        s     = max(10, min(100, base + noise))
        w     = crit.get("weight", 10)
        key   = crit["criterion"]
        category_scores[key] = {"name": key, "score": s, "weight": w / 100}
        if "Innovation" in key:
            innovation = s
        if "Feasibility" in key or "Manufacturing" in key:
            feasibility = s
    total_w = sum(v["weight"] for v in category_scores.values())
    overall = round(
        sum(v["score"] * v["weight"] for v in category_scores.values()) / max(total_w, 0.01),
        1
    )
    overall = min(overall, 100)
    return {
        "overall":    overall,
        "innovation": innovation or random.randint(50, 88),
        "feasibility":feasibility or random.randint(50, 88),
        "categories": category_scores,
    }

def add_demo_submissions():
    demos = [
        ("Self-Healing Polymer Coating",     "PDF",   "Validation",  "Scored"),
        ("Modular Exoskeleton Frame",         "Image", "Prototyping", "In Review"),
        ("Biodegradable Packaging System",    "PDF",   "Concept",     "Scored"),
        ("Micro-Motor Precision Drive",       "Video", "Market Test", "Approved"),
        ("Smart Thermal Regulator",           "PDF",   "Intake",      "New"),
        ("Carbon-Fibre Compression Sleeve",   "PDF",   "Scaling",     "Approved"),
        ("Mycelium Foam Insulation Panel",    "PDF",   "Validation",  "In Review"),
    ]
    for name, ftype, stage, status in demos:
        sid = f"FOS-{st.session_state.next_id}"
        st.session_state.next_id += 1
        scores = ai_score_submission({}, rubric) if status != "New" else {"overall": 0.0, "innovation": 0.0, "feasibility": 0.0, "categories": {}}
        days_ago = random.randint(1, 45)
        st.session_state.submissions.append({
            "id":           sid,
            "name":         name,
            "file_type":    ftype,
            "status":       status,
            "stage":        stage,
            "overall":      scores["overall"],
            "innovation":   scores["innovation"],
            "feasibility":  scores["feasibility"],
            "categories":   scores["categories"],
            "submitted_at": (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
            "notes":        "",
        })

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-logo">
        <div class="sb-wordmark">⚙ ForgeOS</div>
        <div class="sb-tag">Physical Goods Innovation</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-section-label">Main</div>', unsafe_allow_html=True)

    page = st.radio("nav", [
        "Dashboard",
        "Submissions",
        "Pipeline",
        "Rubric Settings",
    ], label_visibility="collapsed")

    subs = st.session_state.submissions
    total    = len(subs)
    scored   = sum(1 for s in subs if s["status"] in ("Scored","In Review","Approved"))
    approved = sum(1 for s in subs if s["status"] == "Approved")
    high_pot = sum(1 for s in subs if s["overall"] >= THRESHOLDS["green"])
    avg_score= round(sum(s["overall"] for s in subs) / max(total, 1), 1)

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-section-label">Overview</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="sb-stat-row"><span class="sb-stat-label">Submissions</span><span class="sb-stat-val">{total}</span></div>
    <div class="sb-stat-row"><span class="sb-stat-label">Scored</span><span class="sb-stat-val">{scored}</span></div>
    <div class="sb-stat-row"><span class="sb-stat-label">Approved</span><span class="sb-stat-val">{approved}</span></div>
    <div class="sb-stat-row"><span class="sb-stat-label">High Potential</span><span class="sb-stat-val" style="color:#3fb950">{high_pot}</span></div>
    <div class="sb-stat-row"><span class="sb-stat-label">Avg Score</span><span class="sb-stat-val" style="color:{score_hex(avg_score) if total else '#484f58'}">{avg_score if total else '—'}</span></div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

    if st.button("Load Demo Data", use_container_width=True):
        if not st.session_state.submissions:
            add_demo_submissions()
            st.rerun()
        else:
            st.warning("Submissions already loaded.")

    st.markdown("""
    <div style="padding: 20px 16px 0 16px;">
        <div style="font-size:10px;color:#30363d;">ForgeOS v2.0 · AI Scoring Engine</div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":

    st.markdown("""
    <div class="forge-topbar">
      <div class="forge-topbar-left">
        <div class="forge-breadcrumb">ForgeOS &nbsp;/&nbsp; <span>Dashboard</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-content">', unsafe_allow_html=True)

    # ── Apollo-style stat strip ───────────────────────────────────────────────
    avg_innov = round(sum(s["innovation"] for s in subs if s["innovation"] > 0) / max(sum(1 for s in subs if s["innovation"] > 0), 1), 1)
    avg_feas  = round(sum(s["feasibility"] for s in subs if s["feasibility"] > 0) / max(sum(1 for s in subs if s["feasibility"] > 0), 1), 1)

    st.markdown(f"""
    <div class="stat-strip">
      <div class="stat-item">
        <div class="stat-label">Total Submissions</div>
        <div class="stat-value">{total}</div>
        <div class="stat-sub">All time</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Avg Overall Score</div>
        <div class="stat-value" style="color:{score_hex(avg_score) if total else '#484f58'}">{avg_score if total else '—'}</div>
        <div class="stat-sub">Out of 100</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">High Potential</div>
        <div class="stat-value" style="color:#3fb950">{high_pot}</div>
        <div class="stat-sub">Score ≥ {THRESHOLDS['green']}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Approved</div>
        <div class="stat-value" style="color:#a371f7">{approved}</div>
        <div class="stat-sub">Proceeding to production</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Avg Innovation</div>
        <div class="stat-value" style="color:{score_hex(avg_innov) if avg_innov else '#484f58'}">{avg_innov if avg_innov else '—'}</div>
        <div class="stat-sub">Innovation criterion</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Avg Feasibility</div>
        <div class="stat-value" style="color:{score_hex(avg_feas) if avg_feas else '#484f58'}">{avg_feas if avg_feas else '—'}</div>
        <div class="stat-sub">Manufacturing criterion</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if subs:
        # ── Charts row ────────────────────────────────────────────────────────
        col_c1, col_c2 = st.columns([3, 2], gap="medium")

        with col_c1:
            st.markdown('<div class="section-hd">Score Distribution</div>', unsafe_allow_html=True)
            df = pd.DataFrame(subs)
            scored_df = df[df["overall"] > 0]
            if not scored_df.empty:
                fig_hist = px.histogram(
                    scored_df, x="overall", nbins=12,
                    color_discrete_sequence=["#1f6feb"],
                )
                fig_hist.update_traces(marker_line_width=0)
                fig_hist.update_layout(
                    paper_bgcolor="#161b22", plot_bgcolor="#161b22",
                    font={"color": "#8d96a3", "family": "Inter", "size": 11},
                    xaxis=dict(gridcolor="#21262d", color="#484f58", title="Overall Score"),
                    yaxis=dict(gridcolor="#21262d", color="#484f58", title="Count"),
                    height=220, margin=dict(l=0, r=0, t=8, b=0),
                    bargap=0.08,
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.markdown('<div style="height:220px;display:flex;align-items:center;justify-content:center;color:#30363d;font-size:13px;">No scored submissions yet</div>', unsafe_allow_html=True)

        with col_c2:
            st.markdown('<div class="section-hd">Status Breakdown</div>', unsafe_allow_html=True)
            status_counts = pd.DataFrame(subs)["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            fig_pie = px.pie(
                status_counts, names="Status", values="Count",
                color_discrete_sequence=["#1f6feb","#3fb950","#d29922","#a371f7","#f85149"],
                hole=0.6,
            )
            fig_pie.update_layout(
                paper_bgcolor="#161b22", plot_bgcolor="#161b22",
                font={"color": "#8d96a3", "family": "Inter", "size": 11},
                height=220, margin=dict(l=0, r=0, t=8, b=0),
                legend=dict(font=dict(color="#8d96a3", size=11), bgcolor="#161b22"),
                showlegend=True,
            )
            fig_pie.update_traces(textfont_color="#e6edf3", textfont_size=11)
            st.plotly_chart(fig_pie, use_container_width=True)

        # ── Recent submissions table ───────────────────────────────────────
        st.markdown('<div class="section-hd">Recent Submissions</div>', unsafe_allow_html=True)
        recent = sorted(subs, key=lambda x: x["submitted_at"], reverse=True)[:8]

        rows_html = ""
        for sub in recent:
            badge = ""
            if sub["overall"] > 0:
                bc = score_badge_class(sub["overall"])
                badge = f'<span class="badge-score {bc}">{sub["overall"]}</span>'
            else:
                badge = '<span style="color:#30363d;font-size:12px;">—</span>'
            pc = pill_class(sub["status"])
            stage_color = next((s["color"] for s in STAGES if s["name"] == sub["stage"]), "#484f58")
            rows_html += f"""
            <tr class="forge-tr">
              <td class="forge-td"><span class="forge-id">{sub['id']}</span></td>
              <td class="forge-td forge-td-primary">{sub['name']}</td>
              <td class="forge-td">{badge}</td>
              <td class="forge-td"><span class="pill {pc}">{sub['status']}</span></td>
              <td class="forge-td"><span style="font-size:11px;color:{stage_color};font-weight:600;">{sub['stage']}</span></td>
              <td class="forge-td">{sub['submitted_at']}</td>
            </tr>"""

        st.markdown(f"""
        <div class="forge-card" style="padding:0; overflow:hidden;">
        <table class="forge-table">
          <thead>
            <tr>
              <th class="forge-th">ID</th>
              <th class="forge-th">Idea Name</th>
              <th class="forge-th">Score</th>
              <th class="forge-th">Status</th>
              <th class="forge-th">Stage</th>
              <th class="forge-th">Submitted</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
        </div>
        """, unsafe_allow_html=True)

        # ── Pipeline snapshot ──────────────────────────────────────────────
        st.markdown('<div class="section-hd">Pipeline Snapshot</div>', unsafe_allow_html=True)
        stage_counts_map = {s["name"]: 0 for s in STAGES}
        for sub in subs:
            if sub["stage"] in stage_counts_map:
                stage_counts_map[sub["stage"]] += 1

        cols = st.columns(len(STAGES))
        for stage, col in zip(STAGES, cols):
            cnt = stage_counts_map.get(stage["name"], 0)
            with col:
                st.markdown(f"""
                <div class="forge-card" style="text-align:center;padding:14px 10px;border-top:2px solid {stage['color']};">
                    <div style="font-size:18px;font-weight:700;color:{stage['color']};margin-bottom:4px;">{cnt}</div>
                    <div style="font-size:11px;font-weight:600;color:#8d96a3;">{stage['name']}</div>
                </div>""", unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">⚙️</div>
            <div class="empty-title">No submissions yet</div>
            <div class="empty-sub">Go to Submissions to upload your first idea,<br>or click Load Demo Data in the sidebar.</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SUBMISSIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Submissions":

    st.markdown("""
    <div class="forge-topbar">
      <div class="forge-topbar-left">
        <div class="forge-breadcrumb">ForgeOS &nbsp;/&nbsp; <span>Submissions</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-content">', unsafe_allow_html=True)

    # ── Upload panel ──────────────────────────────────────────────────────────
    with st.expander("➕  New Submission", expanded=not st.session_state.submissions):
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            idea_name = st.text_input("Idea Name", placeholder="e.g. Self-Healing Polymer Coating")
            uploaded  = st.file_uploader(
                "Supporting files",
                type=["pdf","png","jpg","jpeg","mp4","mov","txt","docx"],
                accept_multiple_files=True,
                help="PDF, images, videos, or documents",
            )
        with col_f2:
            init_stage = st.selectbox("Initial Stage", STAGE_NAMES)
            notes_txt  = st.text_area("Notes", height=96, placeholder="Brief context…")

        if st.button("Submit Idea"):
            if not idea_name.strip():
                st.error("Idea name is required.")
            else:
                ftypes = list({f.type.split("/")[-1].upper() for f in (uploaded or [])}) or ["—"]
                sid = f"FOS-{st.session_state.next_id}"
                st.session_state.next_id += 1
                st.session_state.submissions.append({
                    "id":           sid,
                    "name":         idea_name.strip(),
                    "file_type":    ", ".join(ftypes),
                    "status":       "New",
                    "stage":        init_stage,
                    "overall":      0.0,
                    "innovation":   0.0,
                    "feasibility":  0.0,
                    "categories":   {},
                    "submitted_at": datetime.now().strftime("%Y-%m-%d"),
                    "notes":        notes_txt,
                })
                st.success(f"Submission {sid} added.")
                st.rerun()

    # ── Toolbar ───────────────────────────────────────────────────────────────
    if st.session_state.submissions:
        tb1, tb2, tb3, tb4, tb5 = st.columns([3, 1.5, 1.5, 1.2, 1.8])
        with tb1:
            search_q = st.text_input("search", placeholder="Search by name or ID…", label_visibility="collapsed")
        with tb2:
            f_status = st.selectbox("st", ["All Statuses","New","Scored","In Review","Approved","Rejected"], label_visibility="collapsed")
        with tb3:
            f_stage  = st.selectbox("sg", ["All Stages"] + STAGE_NAMES, label_visibility="collapsed")
        with tb4:
            f_sort   = st.selectbox("sort", ["Newest","Score ↓","Score ↑","Name"], label_visibility="collapsed")
        with tb5:
            run_bulk = st.button("🤖  Process All with AI", use_container_width=True)

        if run_bulk:
            unscored = [s for s in st.session_state.submissions if s["status"] == "New"]
            if unscored:
                prog = st.progress(0)
                msg  = st.empty()
                for i, sub in enumerate(unscored):
                    msg.markdown(f'<span style="color:#484f58;font-size:12px;">Scoring {sub["name"]}…</span>', unsafe_allow_html=True)
                    time.sleep(0.5)
                    sc = ai_score_submission(sub, rubric)
                    idx = next(j for j, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                    st.session_state.submissions[idx].update({
                        "overall": sc["overall"], "innovation": sc["innovation"],
                        "feasibility": sc["feasibility"], "categories": sc["categories"], "status": "Scored",
                    })
                    prog.progress((i + 1) / len(unscored))
                msg.empty()
                st.success(f"Scored {len(unscored)} submission(s).")
                st.rerun()
            else:
                st.info("No unscored submissions.")

        # ── Filter ────────────────────────────────────────────────────────────
        visible = list(st.session_state.submissions)
        if search_q:
            visible = [s for s in visible if search_q.lower() in s["name"].lower() or search_q.lower() in s["id"].lower()]
        if f_status != "All Statuses":
            visible = [s for s in visible if s["status"] == f_status]
        if f_stage != "All Stages":
            visible = [s for s in visible if s["stage"] == f_stage]
        if f_sort == "Score ↓":
            visible.sort(key=lambda x: x["overall"], reverse=True)
        elif f_sort == "Score ↑":
            visible.sort(key=lambda x: x["overall"])
        elif f_sort == "Name":
            visible.sort(key=lambda x: x["name"])
        else:
            visible.sort(key=lambda x: x["submitted_at"], reverse=True)

        # ── Table ─────────────────────────────────────────────────────────────
        st.markdown('<div class="section-hd" style="margin-top:16px;">All Submissions</div>', unsafe_allow_html=True)

        hd = st.columns([1.2, 3.5, 1.1, 1.1, 1.1, 1.5, 1.5, 2.8])
        for col, label in zip(hd, ["ID","Idea Name","Overall","Innovation","Feasibility","Status","Stage","Actions"]):
            col.markdown(f'<span style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;color:#484f58;font-weight:600;">{label}</span>', unsafe_allow_html=True)

        st.markdown("<hr style='margin:6px 0 0 0'>", unsafe_allow_html=True)

        for sub in visible:
            row = st.columns([1.2, 3.5, 1.1, 1.1, 1.1, 1.5, 1.5, 2.8])

            with row[0]:
                st.markdown(f'<span class="forge-id">{sub["id"]}</span>', unsafe_allow_html=True)

            with row[1]:
                st.markdown(f'<span style="font-size:13px;color:#e6edf3;font-weight:500;">{sub["name"]}</span>'
                            f'<br><span style="font-size:11px;color:#484f58;">{sub["file_type"]} · {sub["submitted_at"]}</span>',
                            unsafe_allow_html=True)

            for col, field in zip(row[2:5], ["overall","innovation","feasibility"]):
                val = sub[field]
                if val > 0:
                    bc = score_badge_class(val)
                    col.markdown(f'<span class="badge-score {bc}">{val}</span>', unsafe_allow_html=True)
                else:
                    col.markdown('<span style="color:#30363d;font-size:13px;">—</span>', unsafe_allow_html=True)

            with row[5]:
                pc = pill_class(sub["status"])
                st.markdown(f'<span class="pill {pc}">{sub["status"]}</span>', unsafe_allow_html=True)

            with row[6]:
                sc = next((s["color"] for s in STAGES if s["name"] == sub["stage"]), "#484f58")
                st.markdown(f'<span style="font-size:11px;font-weight:600;color:{sc};">● {sub["stage"]}</span>', unsafe_allow_html=True)

            with row[7]:
                a1, a2, a3 = st.columns(3)
                with a1:
                    if st.button("Score", key=f"sc_{sub['id']}"):
                        with st.spinner(""):
                            time.sleep(0.8)
                            sc2 = ai_score_submission(sub, rubric)
                            idx = next(i for i, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                            st.session_state.submissions[idx].update({
                                "overall": sc2["overall"], "innovation": sc2["innovation"],
                                "feasibility": sc2["feasibility"], "categories": sc2["categories"], "status": "Scored",
                            })
                            st.rerun()
                with a2:
                    if st.button("Advance", key=f"adv_{sub['id']}"):
                        idx = next(i for i, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                        cur = STAGE_NAMES.index(st.session_state.submissions[idx]["stage"])
                        if cur < len(STAGE_NAMES) - 1:
                            st.session_state.submissions[idx]["stage"] = STAGE_NAMES[cur + 1]
                            st.rerun()
                with a3:
                    if st.button("Delete", key=f"del_{sub['id']}"):
                        st.session_state.submissions = [s for s in st.session_state.submissions if s["id"] != sub["id"]]
                        st.rerun()

            # Score detail
            if sub["categories"]:
                with st.expander(f"Score Detail — {sub['name']}", expanded=False):
                    gauge_cols = st.columns(min(len(sub["categories"]), 4))
                    for i, (cid, cd) in enumerate(list(sub["categories"].items())[:4]):
                        with gauge_cols[i]:
                            st.plotly_chart(make_gauge(cd["score"], cd["name"]), use_container_width=True, key=f"g_{sub['id']}_{i}")
                    for cid, cd in sub["categories"].items():
                        c = score_hex(cd["score"])
                        st.markdown(f"""
                        <div style="display:flex;align-items:center;gap:10px;margin:4px 0;">
                          <span style="width:160px;font-size:11px;color:#8d96a3;flex-shrink:0;">{cd['name']}</span>
                          <span style="font-size:12px;font-weight:700;color:{c};width:36px;">{cd['score']}</span>
                        </div>""", unsafe_allow_html=True)
                        st.progress(int(cd["score"]) / 100)

            st.markdown("<hr style='margin:2px 0;border-color:#161b22;'>", unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">📂</div>
            <div class="empty-title">No submissions yet</div>
            <div class="empty-sub">Use the New Submission panel above to add an idea.</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PIPELINE — Linear-style kanban
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Pipeline":

    st.markdown("""
    <div class="forge-topbar">
      <div class="forge-topbar-left">
        <div class="forge-breadcrumb">ForgeOS &nbsp;/&nbsp; <span>Pipeline</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-content">', unsafe_allow_html=True)

    subs = st.session_state.submissions
    stage_map = {s["name"]: [] for s in STAGES}
    for sub in subs:
        if sub["stage"] in stage_map:
            stage_map[sub["stage"]].append(sub)

    # ── Kanban board ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-hd">Board View</div>', unsafe_allow_html=True)

    cols = st.columns(len(STAGES))
    for stage, col in zip(STAGES, cols):
        items = stage_map.get(stage["name"], [])
        with col:
            st.markdown(f"""
            <div class="kanban-col-header">
                <span class="kanban-col-name" style="color:{stage['color']}">{stage['name']}</span>
                <span class="kanban-count">{len(items)}</span>
            </div>""", unsafe_allow_html=True)

            if items:
                for sub in items:
                    badge = ""
                    if sub["overall"] > 0:
                        bc = score_badge_class(sub["overall"])
                        badge = f'<span class="badge-score {bc}" style="font-size:10px;">{sub["overall"]}</span>'
                    pc = pill_class(sub["status"])
                    st.markdown(f"""
                    <div class="kanban-card">
                        <div class="kanban-card-title">{sub['name']}</div>
                        <div class="kanban-card-meta">
                            <span class="forge-id" style="font-size:10px;">{sub['id']}</span>
                            {badge}
                        </div>
                        <div style="margin-top:6px;">
                            <span class="pill {pc}" style="font-size:10px;">{sub['status']}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="kanban-empty">No ideas</div>', unsafe_allow_html=True)

    # ── Stage distribution bar chart ──────────────────────────────────────────
    if subs:
        st.markdown('<div class="section-hd" style="margin-top:28px;">Stage Distribution</div>', unsafe_allow_html=True)
        names  = [s["name"]  for s in STAGES]
        counts = [len(stage_map.get(s["name"], [])) for s in STAGES]
        colors = [s["color"] for s in STAGES]
        fig_bar = go.Figure(go.Bar(
            x=names, y=counts, marker_color=colors,
            text=counts, textposition="auto",
            textfont=dict(color="#e6edf3", size=11),
        ))
        fig_bar.update_layout(
            paper_bgcolor="#161b22", plot_bgcolor="#161b22",
            font={"color": "#8d96a3", "family": "Inter", "size": 11},
            xaxis=dict(gridcolor="#21262d", color="#484f58"),
            yaxis=dict(gridcolor="#21262d", color="#484f58", title="Submissions"),
            height=220, margin=dict(l=0, r=0, t=8, b=0),
            showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # ── Conversion funnel ──────────────────────────────────────────────
        st.markdown('<div class="section-hd">Conversion Funnel</div>', unsafe_allow_html=True)
        total_subs = max(len(subs), 1)
        for stage in STAGES:
            cnt = len(stage_map.get(stage["name"], []))
            pct = cnt / total_subs
            bar_w = max(int(pct * 100), 2)
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
              <span style="width:100px;font-size:11px;color:#8d96a3;text-align:right;flex-shrink:0;">{stage['name']}</span>
              <div style="flex:1;background:#161b22;border-radius:3px;height:18px;overflow:hidden;border:1px solid #21262d;">
                <div style="width:{bar_w}%;background:{stage['color']};height:100%;border-radius:2px;
                            display:flex;align-items:center;padding-left:6px;">
                  <span style="font-size:10px;color:#0d1117;font-weight:700;">{cnt}</span>
                </div>
              </div>
              <span style="width:36px;font-size:11px;color:#484f58;">{int(pct*100)}%</span>
            </div>""", unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">🔀</div>
            <div class="empty-title">Pipeline is empty</div>
            <div class="empty-sub">Add submissions to see them flow through the pipeline.</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: RUBRIC SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Rubric Settings":

    st.markdown("""
    <div class="forge-topbar">
      <div class="forge-topbar-left">
        <div class="forge-breadcrumb">ForgeOS &nbsp;/&nbsp; <span>Rubric Settings</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-content">', unsafe_allow_html=True)

    if not rubric:
        st.error("No rubric.json found.")
    else:
        criteria_list = rubric.get("criteria", [])
        total_w       = sum(c.get("weight", 0) for c in criteria_list)
        gating        = rubric.get("gating_rules", [])
        cat_palette   = ["#1f6feb","#238636","#9e6a03","#6e40c9","#d18000","#0ea5e9","#ec4899","#f85149"]

        # ── Rubric header ─────────────────────────────────────────────────────
        col_h1, col_h2, col_h3, col_h4 = st.columns(4)
        with col_h1:
            w_ok = abs(total_w - 100) < 1
            st.markdown(f"""
            <div class="forge-card">
              <div class="stat-label">Rubric</div>
              <div style="font-size:13px;font-weight:600;color:#e6edf3;margin:4px 0 2px;">{rubric.get('rubric_name','Innovation Rubric')[:30]}…</div>
              <div style="font-size:11px;color:#484f58;">{len(criteria_list)} criteria</div>
            </div>""", unsafe_allow_html=True)
        with col_h2:
            st.markdown(f"""
            <div class="forge-card">
              <div class="stat-label">Total Weight</div>
              <div class="stat-value" style="color:{'#3fb950' if w_ok else '#f85149'}">{total_w}%</div>
              <div class="stat-sub">{'Balanced ✓' if w_ok else 'Imbalanced'}</div>
            </div>""", unsafe_allow_html=True)
        with col_h3:
            st.markdown(f"""
            <div class="forge-card">
              <div class="stat-label">Green Zone</div>
              <div class="stat-value" style="color:#3fb950">≥ {THRESHOLDS['green']}</div>
              <div class="stat-sub">High potential, fast-track</div>
            </div>""", unsafe_allow_html=True)
        with col_h4:
            st.markdown(f"""
            <div class="forge-card">
              <div class="stat-label">Auto-Reject Rules</div>
              <div class="stat-value" style="color:#f85149">{len(gating)}</div>
              <div class="stat-sub">Gating rules active</div>
            </div>""", unsafe_allow_html=True)

        # ── Tabs ──────────────────────────────────────────────────────────────
        tab_crit, tab_gate, tab_chart, tab_json = st.tabs(["Criteria", "Gating Rules", "Weight Chart", "Raw JSON"])

        with tab_crit:
            for i, crit in enumerate(criteria_list):
                color    = cat_palette[i % len(cat_palette)]
                anchors  = crit.get("scoring_anchors", {})
                subs_f   = crit.get("sub_factors", [])
                redflags = crit.get("red_flags", [])
                evidence = crit.get("evidence_required", "")

                with st.expander(f"{crit['criterion']}  ·  {crit.get('weight', 0)}%"):
                    st.markdown(f'<p style="color:#8d96a3;font-size:12px;margin:0 0 12px 0;">{crit.get("description","")}</p>', unsafe_allow_html=True)

                    cl, cr = st.columns([3, 2])

                    with cl:
                        if anchors:
                            st.markdown('<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#484f58;font-weight:700;margin-bottom:8px;">Scoring Anchors</div>', unsafe_allow_html=True)
                            anchor_map = {"1-3": ("anchor-low","#f85149"), "4-6": ("anchor-mid","#d29922"), "7-10": ("anchor-high","#3fb950")}
                            for band, desc in anchors.items():
                                cls_n, clr = anchor_map.get(band, ("", "#484f58"))
                                st.markdown(f"""
                                <div class="anchor-band {cls_n}">
                                  <span style="color:{clr};font-weight:700;font-size:11px;">{band}</span>
                                  <span style="color:#8d96a3;font-size:11px;margin-left:8px;">{desc}</span>
                                </div>""", unsafe_allow_html=True)

                        if evidence:
                            st.markdown(f"""
                            <div style="margin-top:12px;padding:8px 12px;background:#0d1117;border:1px solid #21262d;border-radius:6px;">
                              <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#484f58;font-weight:700;margin-bottom:4px;">Evidence Required</div>
                              <div style="font-size:12px;color:#8d96a3;">{evidence}</div>
                            </div>""", unsafe_allow_html=True)

                    with cr:
                        if subs_f:
                            st.markdown('<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#484f58;font-weight:700;margin-bottom:8px;">Sub-Factors</div>', unsafe_allow_html=True)
                            tags = "".join(f'<span class="subfactor-tag">▸ {sf}</span>' for sf in subs_f)
                            st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:4px;">{tags}</div>', unsafe_allow_html=True)

                        if redflags:
                            st.markdown('<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#484f58;font-weight:700;margin:12px 0 8px;">Red Flags</div>', unsafe_allow_html=True)
                            flags_html = "".join(f'<div class="redflag-item">⚑ {rf}</div>' for rf in redflags)
                            st.markdown(f'<div style="background:#2b0f0f18;border:1px solid #6e181822;border-radius:6px;padding:10px 12px;">{flags_html}</div>', unsafe_allow_html=True)

        with tab_gate:
            if gating:
                st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
                for rule in gating:
                    st.markdown(f'<div class="gate-rule"><span style="color:#f85149;font-size:14px;">⛔</span> {rule}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="color:#484f58;font-size:13px;">No gating rules defined.</p>', unsafe_allow_html=True)

        with tab_chart:
            names_c  = [c["criterion"] for c in criteria_list]
            weights_c = [c.get("weight", 0) for c in criteria_list]
            fig_w = go.Figure(go.Bar(
                x=names_c, y=weights_c,
                marker_color=[cat_palette[i % len(cat_palette)] for i in range(len(names_c))],
                text=[f"{w}%" for w in weights_c],
                textposition="auto",
                textfont=dict(color="#e6edf3", size=11),
            ))
            fig_w.update_layout(
                paper_bgcolor="#161b22", plot_bgcolor="#161b22",
                font={"color": "#8d96a3", "family": "Inter", "size": 11},
                xaxis=dict(gridcolor="#21262d", color="#484f58", tickangle=-30),
                yaxis=dict(gridcolor="#21262d", color="#484f58", title="Weight (%)"),
                height=300, margin=dict(l=0, r=0, t=8, b=80),
            )
            st.plotly_chart(fig_w, use_container_width=True)

        with tab_json:
            st.json(rubric, expanded=False)
            st.info("Edit rubric.json and restart the app to apply changes.", icon="ℹ️")

    st.markdown('</div>', unsafe_allow_html=True)
