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

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ForgeOS — Innovation OS",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global reset ─────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar ──────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
[data-testid="stSidebarNav"] {
    padding-top: 1rem;
}

/* ── Top header bar ───────────────────────── */
.forge-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
    border-radius: 12px;
    padding: 28px 36px;
    margin-bottom: 24px;
    border: 1px solid #1e40af33;
    position: relative;
    overflow: hidden;
}
.forge-header::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, #3b82f620 0%, transparent 70%);
    border-radius: 50%;
}
.forge-header h1 {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(90deg, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 4px 0;
}
.forge-header p {
    color: #94a3b8;
    margin: 0;
    font-size: 0.95rem;
}

/* ── Metric cards ─────────────────────────── */
.metric-card {
    background: #1e293b;
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid #334155;
    transition: border-color 0.2s, transform 0.2s;
    cursor: default;
}
.metric-card:hover {
    border-color: #3b82f6;
    transform: translateY(-2px);
}
.metric-card .metric-label {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748b;
    margin-bottom: 8px;
}
.metric-card .metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1;
}
.metric-card .metric-sub {
    font-size: 0.8rem;
    color: #64748b;
    margin-top: 6px;
}
.metric-card .metric-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-top: 8px;
}
.badge-green { background: #052e16; color: #4ade80; }
.badge-blue  { background: #0c1a3b; color: #60a5fa; }
.badge-amber { background: #2d1a03; color: #fbbf24; }
.badge-purple{ background: #1e0936; color: #c084fc; }

/* ── Section titles ───────────────────────── */
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 24px 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #334155;
}

/* ── Score badge ──────────────────────────── */
.score-green { color: #4ade80; font-weight: 700; }
.score-yellow{ color: #fbbf24; font-weight: 700; }
.score-red   { color: #f87171; font-weight: 700; }

/* ── Status pill ──────────────────────────── */
.status-pill {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.status-new      { background:#1e3a5f; color:#60a5fa; }
.status-scored   { background:#052e16; color:#4ade80; }
.status-review   { background:#2d1a03; color:#fbbf24; }
.status-approved { background:#1a0936; color:#c084fc; }
.status-rejected { background:#2a0a0a; color:#f87171; }

/* ── Pipeline stage card ──────────────────── */
.stage-card {
    background: #1e293b;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    border: 1px solid #334155;
    transition: all 0.2s;
    position: relative;
}
.stage-card:hover {
    transform: translateY(-3px);
    border-color: #3b82f6;
    box-shadow: 0 8px 24px #3b82f620;
}
.stage-number {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 700;
    margin: 0 auto 10px auto;
}
.stage-name {
    font-size: 0.85rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 6px;
}
.stage-desc {
    font-size: 0.72rem;
    color: #64748b;
    line-height: 1.4;
}
.stage-count {
    font-size: 1.4rem;
    font-weight: 700;
    margin: 8px 0 2px 0;
}

/* ── Upload zone ──────────────────────────── */
[data-testid="stFileUploader"] {
    background: #1e293b !important;
    border: 2px dashed #334155 !important;
    border-radius: 12px !important;
    padding: 32px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #3b82f6 !important;
}

/* ── Buttons ──────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 8px 20px !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
    box-shadow: 0 4px 16px #3b82f640 !important;
    transform: translateY(-1px) !important;
}

/* ── DataTable ────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #334155;
}

/* ── Expander ─────────────────────────────── */
[data-testid="stExpander"] {
    background: #1e293b;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
}

/* ── Divider ──────────────────────────────── */
hr { border-color: #334155 !important; }

/* ── Progress bar ─────────────────────────── */
[data-testid="stProgress"] > div > div {
    border-radius: 9999px;
}

/* ── Selectbox / inputs ───────────────────── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stTextInput"] input {
    background: #1e293b !important;
    border-color: #334155 !important;
    color: #e2e8f0 !important;
}

/* ── Tab bar ──────────────────────────────── */
[data-testid="stTabs"] [role="tab"] {
    color: #64748b !important;
    font-weight: 500;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #60a5fa !important;
    border-bottom-color: #3b82f6 !important;
}

/* ── Rubric setting card ──────────────────── */
.rubric-category {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.rubric-category-name {
    font-size: 0.95rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 4px;
}
.rubric-category-desc {
    font-size: 0.8rem;
    color: #64748b;
}
.rubric-weight {
    font-size: 0.8rem;
    font-weight: 600;
    color: #60a5fa;
}

/* ── Alert/info ───────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border: 1px solid #334155 !important;
}

/* ── Sidebar logo block ───────────────────── */
.sidebar-logo {
    padding: 16px 8px 24px 8px;
    border-bottom: 1px solid #334155;
    margin-bottom: 16px;
    text-align: center;
}
.sidebar-logo-text {
    font-size: 1.4rem;
    font-weight: 800;
    background: linear-gradient(90deg, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
}
.sidebar-logo-sub {
    font-size: 0.7rem;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 2px;
}

/* ── Tag/chip ─────────────────────────────── */
.info-chip {
    display: inline-block;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 0.75rem;
    color: #94a3b8;
    margin: 2px;
}
</style>
""", unsafe_allow_html=True)

# ─── Load Rubric ─────────────────────────────────────────────────────────────
@st.cache_data
def load_rubric():
    rubric_path = os.path.join(os.path.dirname(__file__), "rubric.json")
    if os.path.exists(rubric_path):
        with open(rubric_path) as f:
            return json.load(f)
    return {}

rubric = load_rubric()

# ─── Session State ────────────────────────────────────────────────────────────
if "submissions" not in st.session_state:
    st.session_state.submissions = []
if "next_id" not in st.session_state:
    st.session_state.next_id = 1001

STAGES = rubric.get("pipeline_stages", [
    {"id": 1, "name": "Intake",       "color": "#6366f1"},
    {"id": 2, "name": "Concept",      "color": "#3b82f6"},
    {"id": 3, "name": "Validation",   "color": "#06b6d4"},
    {"id": 4, "name": "Prototyping",  "color": "#10b981"},
    {"id": 5, "name": "Market Test",  "color": "#f59e0b"},
    {"id": 6, "name": "Scaling",      "color": "#f97316"},
    {"id": 7, "name": "Monitoring",   "color": "#8b5cf6"},
])
STAGE_NAMES = [s["name"] for s in STAGES]

THRESHOLDS = rubric.get("scoring_thresholds", {"green": 70, "yellow": 50})

# ─── Helpers ─────────────────────────────────────────────────────────────────
def score_color(score):
    if score >= THRESHOLDS["green"]:
        return "score-green"
    if score >= THRESHOLDS["yellow"]:
        return "score-yellow"
    return "score-red"

def score_color_hex(score):
    if score >= THRESHOLDS["green"]:
        return "#4ade80"
    if score >= THRESHOLDS["yellow"]:
        return "#fbbf24"
    return "#f87171"

def status_class(status):
    mapping = {
        "New":      "status-new",
        "Scored":   "status-scored",
        "In Review":"status-review",
        "Approved": "status-approved",
        "Rejected": "status-rejected",
    }
    return mapping.get(status, "status-new")

def make_gauge(score, title="", height=160):
    color = score_color_hex(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"size": 28, "color": color, "family": "Inter"}, "suffix": ""},
        title={"text": title, "font": {"size": 11, "color": "#94a3b8", "family": "Inter"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#334155",
                     "tickfont": {"color": "#475569", "size": 9}},
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": "#0f172a",
            "bordercolor": "#334155",
            "borderwidth": 1,
            "steps": [
                {"range": [0, THRESHOLDS["yellow"]],   "color": "#2a0a0a"},
                {"range": [THRESHOLDS["yellow"], THRESHOLDS["green"]], "color": "#2d1a03"},
                {"range": [THRESHOLDS["green"], 100],  "color": "#052e16"},
            ],
            "threshold": {
                "line": {"color": color, "width": 2},
                "thickness": 0.8,
                "value": score,
            },
        }
    ))
    fig.update_layout(
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        height=height,
        margin=dict(l=12, r=12, t=28, b=4),
        font={"family": "Inter"},
    )
    return fig

def ai_score_submission(submission, rubric_data):
    """Simulate AI scoring using rubric weights (v2 flat criteria schema)."""
    category_scores = {}
    innovation = None
    feasibility = None
    for crit in rubric_data.get("criteria", []):
        base = random.randint(45, 95)
        noise = random.randint(-8, 8)
        crit_score = max(10, min(100, base + noise))
        weight_pct = crit.get("weight", 10)
        key = crit["criterion"]
        category_scores[key] = {
            "name": crit["criterion"],
            "score": crit_score,
            "weight": weight_pct / 100,
        }
        if "Innovation" in key:
            innovation = crit_score
        if "Feasibility" in key or "Manufacturing" in key:
            feasibility = crit_score
    total_weight = sum(v["weight"] for v in category_scores.values())
    if total_weight > 0:
        overall = sum(v["score"] * v["weight"] for v in category_scores.values()) / total_weight * 100
    else:
        overall = 0.0
    # Normalise to 0-100
    overall = round(min(overall, 100), 1)
    if innovation is None:
        innovation = random.randint(50, 90)
    if feasibility is None:
        feasibility = random.randint(50, 90)
    return {
        "overall": overall,
        "innovation": innovation,
        "feasibility": feasibility,
        "categories": category_scores,
    }

def add_demo_submissions():
    demo = [
        {"name": "Self-Healing Polymer Coating",  "file_type": "PDF",   "stage": "Validation"},
        {"name": "Modular Exoskeleton Frame",      "file_type": "Image", "stage": "Prototyping"},
        {"name": "Biodegradable Packaging System", "file_type": "PDF",   "stage": "Concept"},
        {"name": "Micro-Motor Precision Drive",    "file_type": "Video", "stage": "Market Test"},
        {"name": "Smart Thermal Regulator",        "file_type": "PDF",   "stage": "Intake"},
    ]
    for d in demo:
        sid = f"FOS-{st.session_state.next_id}"
        st.session_state.next_id += 1
        scores = ai_score_submission({}, rubric)
        status = random.choice(["Scored", "In Review", "Approved", "Scored"])
        st.session_state.submissions.append({
            "id":          sid,
            "name":        d["name"],
            "file_type":   d["file_type"],
            "status":      status,
            "stage":       d["stage"],
            "overall":     scores["overall"],
            "innovation":  scores["innovation"],
            "feasibility": scores["feasibility"],
            "categories":  scores["categories"],
            "submitted_at": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
            "notes":       "",
        })

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="sidebar-logo-text">⚙️ ForgeOS</div>
        <div class="sidebar-logo-sub">AI Innovation OS</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["🏠  Dashboard", "📂  Submissions", "🔀  Pipeline", "⚙️  Rubric Settings"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    total = len(st.session_state.submissions)
    scored = sum(1 for s in st.session_state.submissions if s["status"] in ("Scored", "In Review", "Approved"))
    approved = sum(1 for s in st.session_state.submissions if s["status"] == "Approved")

    st.markdown(f"""
    <div style="padding: 12px 8px;">
        <div style="font-size:0.72rem; text-transform:uppercase; letter-spacing:0.08em; color:#475569; margin-bottom:12px;">
            Quick Stats
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
            <span style="color:#94a3b8; font-size:0.82rem;">Total Submissions</span>
            <span style="color:#e2e8f0; font-weight:600;">{total}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
            <span style="color:#94a3b8; font-size:0.82rem;">Scored</span>
            <span style="color:#4ade80; font-weight:600;">{scored}</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="color:#94a3b8; font-size:0.82rem;">Approved</span>
            <span style="color:#c084fc; font-weight:600;">{approved}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    if st.button("Load Demo Data", use_container_width=True):
        if not st.session_state.submissions:
            add_demo_submissions()
            st.success("Demo submissions loaded!")
            st.rerun()
        else:
            st.warning("Submissions already exist.")

    st.markdown("""
    <div style="padding: 16px 8px 0 8px; font-size: 0.7rem; color: #334155; text-align: center;">
        ForgeOS v1.0 · Physical Goods Innovation<br>
        Powered by AI Agentic Scoring
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🏠  Dashboard":

    st.markdown("""
    <div class="forge-header">
        <h1>ForgeOS — Innovation OS</h1>
        <p>AI-powered innovation pipeline for physical goods companies. Upload ideas, score with your rubric, and track them through the innovation lifecycle.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Metrics row ───────────────────────────────────────────────────────────
    subs = st.session_state.submissions
    total = len(subs)
    avg_score = round(sum(s["overall"] for s in subs) / max(total, 1), 1)
    high_potential = sum(1 for s in subs if s["overall"] >= THRESHOLDS["green"])
    approved = sum(1 for s in subs if s["status"] == "Approved")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Submissions</div>
            <div class="metric-value">{total}</div>
            <div class="metric-sub">Innovation ideas logged</div>
            <span class="metric-badge badge-blue">All Time</span>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Overall Score</div>
            <div class="metric-value" style="color:{score_color_hex(avg_score)}">{avg_score}</div>
            <div class="metric-sub">Out of 100</div>
            <span class="metric-badge badge-green">Rubric-based</span>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">High Potential</div>
            <div class="metric-value" style="color:#4ade80">{high_potential}</div>
            <div class="metric-sub">Score ≥ {THRESHOLDS['green']}</div>
            <span class="metric-badge badge-green">Green Zone</span>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Approved</div>
            <div class="metric-value" style="color:#c084fc">{approved}</div>
            <div class="metric-sub">Proceeding to production</div>
            <span class="metric-badge badge-purple">Pipeline</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    if subs:
        col_chart1, col_chart2 = st.columns([3, 2])

        with col_chart1:
            st.markdown('<div class="section-title">Score Distribution</div>', unsafe_allow_html=True)
            df = pd.DataFrame(subs)
            fig_hist = px.histogram(
                df, x="overall", nbins=10,
                color_discrete_sequence=["#3b82f6"],
                labels={"overall": "Overall Score", "count": "Submissions"},
            )
            fig_hist.update_layout(
                paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                font={"color": "#94a3b8", "family": "Inter"},
                xaxis=dict(gridcolor="#334155", color="#64748b"),
                yaxis=dict(gridcolor="#334155", color="#64748b"),
                height=240, margin=dict(l=0, r=0, t=12, b=0),
                bargap=0.1,
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        with col_chart2:
            st.markdown('<div class="section-title">Status Breakdown</div>', unsafe_allow_html=True)
            statuses = pd.DataFrame(subs)["status"].value_counts().reset_index()
            statuses.columns = ["Status", "Count"]
            fig_pie = px.pie(
                statuses, names="Status", values="Count",
                color_discrete_sequence=["#3b82f6","#4ade80","#fbbf24","#c084fc","#f87171"],
                hole=0.55,
            )
            fig_pie.update_layout(
                paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
                font={"color": "#94a3b8", "family": "Inter"},
                height=240, margin=dict(l=0, r=0, t=12, b=0),
                legend=dict(font=dict(color="#94a3b8"), bgcolor="#1e293b"),
                showlegend=True,
            )
            fig_pie.update_traces(textfont_color="#e2e8f0")
            st.plotly_chart(fig_pie, use_container_width=True)

        # ── Recent submissions ─────────────────────────────────────────────
        st.markdown('<div class="section-title">Recent Submissions</div>', unsafe_allow_html=True)
        recent = sorted(subs, key=lambda x: x["submitted_at"], reverse=True)[:5]
        for sub in recent:
            col_id, col_name, col_score, col_status, col_stage = st.columns([1.2, 3, 1.5, 1.5, 2])
            with col_id:
                st.markdown(f'<span class="info-chip">{sub["id"]}</span>', unsafe_allow_html=True)
            with col_name:
                st.markdown(f'<span style="color:#e2e8f0; font-size:0.88rem; font-weight:500;">{sub["name"]}</span>', unsafe_allow_html=True)
            with col_score:
                css = score_color(sub["overall"])
                st.markdown(f'<span class="{css}">{sub["overall"]}</span>', unsafe_allow_html=True)
            with col_status:
                sc = status_class(sub["status"])
                st.markdown(f'<span class="status-pill {sc}">{sub["status"]}</span>', unsafe_allow_html=True)
            with col_stage:
                st.markdown(f'<span style="color:#64748b; font-size:0.8rem;">{sub["stage"]}</span>', unsafe_allow_html=True)

    else:
        st.markdown("""
        <div style="text-align:center; padding: 60px 0; color: #475569;">
            <div style="font-size:3rem; margin-bottom:16px;">⚙️</div>
            <div style="font-size:1.1rem; font-weight:600; color:#64748b; margin-bottom:8px;">No submissions yet</div>
            <div style="font-size:0.88rem;">Head to <strong>Submissions</strong> to upload your first innovation idea,
            or click <strong>Load Demo Data</strong> in the sidebar.</div>
        </div>""", unsafe_allow_html=True)

    # ── Pipeline snapshot ─────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Innovation Pipeline Snapshot</div>', unsafe_allow_html=True)
    stage_counts = {s["name"]: 0 for s in STAGES}
    for sub in subs:
        if sub["stage"] in stage_counts:
            stage_counts[sub["stage"]] += 1

    cols = st.columns(len(STAGES))
    for i, (stage, col) in enumerate(zip(STAGES, cols)):
        count = stage_counts.get(stage["name"], 0)
        with col:
            st.markdown(f"""
            <div class="stage-card">
                <div class="stage-number" style="background:{stage['color']}22; color:{stage['color']};">
                    {i+1}
                </div>
                <div class="stage-count" style="color:{stage['color']};">{count}</div>
                <div class="stage-name">{stage['name']}</div>
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: SUBMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📂  Submissions":

    st.markdown("""
    <div class="forge-header">
        <h1>Submissions</h1>
        <p>Upload innovation ideas, score them with AI, and manage their lifecycle through your pipeline.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Upload panel ──────────────────────────────────────────────────────────
    with st.expander("➕  Upload New Submission", expanded=len(st.session_state.submissions) == 0):
        col_form1, col_form2 = st.columns([2, 1])
        with col_form1:
            idea_name = st.text_input(
                "Idea / Concept Name",
                placeholder="e.g., Self-Healing Polymer Coating",
            )
            uploaded_files = st.file_uploader(
                "Upload supporting files",
                type=["pdf", "png", "jpg", "jpeg", "mp4", "mov", "txt", "docx"],
                accept_multiple_files=True,
                help="Accepted: PDF, images (PNG/JPG), videos (MP4/MOV), or text documents",
            )
        with col_form2:
            initial_stage = st.selectbox("Initial Stage", STAGE_NAMES, index=0)
            notes = st.text_area("Notes (optional)", height=100, placeholder="Brief description or context…")

        btn_col1, btn_col2 = st.columns([1, 4])
        with btn_col1:
            submit_btn = st.button("Submit Idea", use_container_width=True)

        if submit_btn:
            if not idea_name.strip():
                st.error("Please enter an idea name.")
            else:
                file_types = list({
                    f.type.split("/")[-1].upper()
                    for f in (uploaded_files or [])
                }) or ["Text"]
                sid = f"FOS-{st.session_state.next_id}"
                st.session_state.next_id += 1
                st.session_state.submissions.append({
                    "id":          sid,
                    "name":        idea_name.strip(),
                    "file_type":   ", ".join(file_types),
                    "status":      "New",
                    "stage":       initial_stage,
                    "overall":     0.0,
                    "innovation":  0.0,
                    "feasibility": 0.0,
                    "categories":  {},
                    "submitted_at": datetime.now().strftime("%Y-%m-%d"),
                    "notes":       notes,
                })
                st.success(f"Submission **{sid}** added successfully!")
                st.rerun()

    # ── Filter bar ────────────────────────────────────────────────────────────
    if st.session_state.submissions:
        st.markdown('<div class="section-title">All Submissions</div>', unsafe_allow_html=True)

        f1, f2, f3, f4 = st.columns([2, 1.5, 1.5, 1])
        with f1:
            search_q = st.text_input("Search", placeholder="Filter by name or ID…", label_visibility="collapsed")
        with f2:
            filter_status = st.selectbox("Status", ["All Statuses", "New", "Scored", "In Review", "Approved", "Rejected"], label_visibility="collapsed")
        with f3:
            filter_stage = st.selectbox("Stage", ["All Stages"] + STAGE_NAMES, label_visibility="collapsed")
        with f4:
            sort_by = st.selectbox("Sort", ["Submitted", "Score ↓", "Score ↑", "Name"], label_visibility="collapsed")

        subs = st.session_state.submissions
        if search_q:
            subs = [s for s in subs if search_q.lower() in s["name"].lower() or search_q.lower() in s["id"].lower()]
        if filter_status != "All Statuses":
            subs = [s for s in subs if s["status"] == filter_status]
        if filter_stage != "All Stages":
            subs = [s for s in subs if s["stage"] == filter_stage]
        if sort_by == "Score ↓":
            subs = sorted(subs, key=lambda x: x["overall"], reverse=True)
        elif sort_by == "Score ↑":
            subs = sorted(subs, key=lambda x: x["overall"])
        elif sort_by == "Name":
            subs = sorted(subs, key=lambda x: x["name"])
        else:
            subs = sorted(subs, key=lambda x: x["submitted_at"], reverse=True)

        # ── Header row ────────────────────────────────────────────────────────
        h = st.columns([1.2, 3, 1.2, 1.2, 1.2, 1.5, 1.8, 2.5])
        headers = ["ID", "Idea Name", "Overall", "Innovation", "Feasibility", "Status", "Stage", "Actions"]
        for col, label in zip(h, headers):
            col.markdown(f'<span style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;color:#475569;font-weight:600;">{label}</span>', unsafe_allow_html=True)

        st.markdown("<hr style='margin:6px 0 4px 0;'>", unsafe_allow_html=True)

        for sub in subs:
            row = st.columns([1.2, 3, 1.2, 1.2, 1.2, 1.5, 1.8, 2.5])
            with row[0]:
                st.markdown(f'<span class="info-chip">{sub["id"]}</span>', unsafe_allow_html=True)
            with row[1]:
                st.markdown(f'<span style="color:#e2e8f0;font-size:0.88rem;font-weight:500;">{sub["name"]}</span><br><span style="color:#475569;font-size:0.72rem;">{sub["file_type"]} · {sub["submitted_at"]}</span>', unsafe_allow_html=True)
            with row[2]:
                if sub["overall"] > 0:
                    css = score_color(sub["overall"])
                    st.markdown(f'<span class="{css}" style="font-size:0.95rem;">{sub["overall"]}</span>', unsafe_allow_html=True)
                    st.progress(int(sub["overall"]) / 100)
                else:
                    st.markdown('<span style="color:#334155;">—</span>', unsafe_allow_html=True)
            with row[3]:
                if sub["innovation"] > 0:
                    css = score_color(sub["innovation"])
                    st.markdown(f'<span class="{css}">{sub["innovation"]}</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span style="color:#334155;">—</span>', unsafe_allow_html=True)
            with row[4]:
                if sub["feasibility"] > 0:
                    css = score_color(sub["feasibility"])
                    st.markdown(f'<span class="{css}">{sub["feasibility"]}</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span style="color:#334155;">—</span>', unsafe_allow_html=True)
            with row[5]:
                sc = status_class(sub["status"])
                st.markdown(f'<span class="status-pill {sc}">{sub["status"]}</span>', unsafe_allow_html=True)
            with row[6]:
                st.markdown(f'<span style="color:#64748b;font-size:0.82rem;">{sub["stage"]}</span>', unsafe_allow_html=True)
            with row[7]:
                act1, act2, act3 = st.columns(3)
                with act1:
                    if st.button("AI Score", key=f"score_{sub['id']}"):
                        with st.spinner("Scoring…"):
                            time.sleep(1.2)
                            scores = ai_score_submission(sub, rubric)
                            idx = next(i for i, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                            st.session_state.submissions[idx].update({
                                "overall":     scores["overall"],
                                "innovation":  scores["innovation"],
                                "feasibility": scores["feasibility"],
                                "categories":  scores["categories"],
                                "status":      "Scored",
                            })
                            st.rerun()
                with act2:
                    if st.button("Advance", key=f"adv_{sub['id']}"):
                        idx = next(i for i, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                        cur = STAGE_NAMES.index(st.session_state.submissions[idx]["stage"])
                        if cur < len(STAGE_NAMES) - 1:
                            st.session_state.submissions[idx]["stage"] = STAGE_NAMES[cur + 1]
                            st.rerun()
                with act3:
                    if st.button("Delete", key=f"del_{sub['id']}"):
                        st.session_state.submissions = [
                            s for s in st.session_state.submissions if s["id"] != sub["id"]
                        ]
                        st.rerun()

            # ── Score detail expander ──────────────────────────────────────
            if sub["categories"]:
                with st.expander(f"View Score Detail — {sub['name']}"):
                    gauge_cols = st.columns(3)
                    key_cats = list(sub["categories"].items())
                    for i, (cat_id, cat_data) in enumerate(key_cats[:3]):
                        with gauge_cols[i % 3]:
                            st.plotly_chart(
                                make_gauge(cat_data["score"], cat_data["name"]),
                                use_container_width=True, key=f"gauge_{sub['id']}_{cat_id}"
                            )
                    for cat_id, cat_data in key_cats:
                        pct = cat_data["score"] / 100
                        bar_color = score_color_hex(cat_data["score"])
                        st.markdown(f"""
                        <div style="margin-bottom:10px;">
                            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                                <span style="font-size:0.82rem;color:#94a3b8;">{cat_data['name']}</span>
                                <span style="font-size:0.82rem;font-weight:600;color:{bar_color};">{cat_data['score']}</span>
                            </div>
                        </div>""", unsafe_allow_html=True)
                        st.progress(int(cat_data["score"]) / 100)

            st.markdown("<hr style='margin:4px 0;border-color:#1e293b;'>", unsafe_allow_html=True)

        # ── Bulk action ───────────────────────────────────────────────────────
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        bulk_col1, bulk_col2 = st.columns([1, 5])
        with bulk_col1:
            if st.button("🤖  Process All with AI", use_container_width=True):
                unscored = [s for s in st.session_state.submissions if s["status"] == "New"]
                if unscored:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    for i, sub in enumerate(unscored):
                        status_text.markdown(f'<span style="color:#94a3b8;font-size:0.82rem;">Scoring {sub["name"]}…</span>', unsafe_allow_html=True)
                        time.sleep(0.6)
                        scores = ai_score_submission(sub, rubric)
                        idx = next(j for j, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                        st.session_state.submissions[idx].update({
                            "overall":     scores["overall"],
                            "innovation":  scores["innovation"],
                            "feasibility": scores["feasibility"],
                            "categories":  scores["categories"],
                            "status":      "Scored",
                        })
                        progress_bar.progress((i + 1) / len(unscored))
                    status_text.empty()
                    st.success(f"Scored {len(unscored)} submission(s)!")
                    st.rerun()
                else:
                    st.info("No unscored submissions found.")

    else:
        st.markdown("""
        <div style="text-align:center; padding: 60px 0; color: #475569;">
            <div style="font-size:3rem; margin-bottom:16px;">📂</div>
            <div style="font-size:1.1rem; font-weight:600; color:#64748b; margin-bottom:8px;">No submissions yet</div>
            <div style="font-size:0.88rem;">Use the upload panel above to add your first innovation idea.</div>
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔀  Pipeline":

    st.markdown("""
    <div class="forge-header">
        <h1>Innovation Pipeline</h1>
        <p>Track your submissions across all 7 stages of the innovation lifecycle — from initial intake to live market monitoring.</p>
    </div>
    """, unsafe_allow_html=True)

    subs = st.session_state.submissions
    stage_map = {s["name"]: [] for s in STAGES}
    for sub in subs:
        if sub["stage"] in stage_map:
            stage_map[sub["stage"]].append(sub)

    # ── Flow diagram ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Pipeline Flow</div>', unsafe_allow_html=True)

    cols = st.columns(len(STAGES))
    for i, (stage, col) in enumerate(zip(STAGES, cols)):
        items = stage_map.get(stage["name"], [])
        count = len(items)
        avg = round(sum(s["overall"] for s in items) / max(count, 1), 1) if items else 0
        avg_color = score_color_hex(avg)
        avg_html = (
            f'<div style="margin-top:8px;font-size:0.72rem;color:#64748b;">'
            f'Avg Score: <span style="color:{avg_color};font-weight:600;">{avg}</span></div>'
            if count else ""
        )
        with col:
            st.markdown(f"""
            <div class="stage-card" style="border-top: 3px solid {stage['color']};">
                <div class="stage-number" style="background:{stage['color']}22; color:{stage['color']};">
                    {i+1}
                </div>
                <div class="stage-name">{stage['name']}</div>
                <div class="stage-count" style="color:{stage['color']};">{count}</div>
                <div class="stage-desc">{stage.get('description', '')}</div>
                {avg_html}
            </div>""", unsafe_allow_html=True)

    # ── Sankey flow ───────────────────────────────────────────────────────────
    if subs:
        st.markdown('<div class="section-title">Stage Distribution</div>', unsafe_allow_html=True)
        counts = [len(stage_map.get(s["name"], [])) for s in STAGES]
        names = [s["name"] for s in STAGES]
        colors = [s["color"] for s in STAGES]
        fig_bar = go.Figure(go.Bar(
            x=names, y=counts,
            marker_color=colors,
            text=counts, textposition="auto",
            textfont=dict(color="#e2e8f0", size=11),
        ))
        fig_bar.update_layout(
            paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
            font={"color": "#94a3b8", "family": "Inter"},
            xaxis=dict(gridcolor="#334155", color="#64748b"),
            yaxis=dict(gridcolor="#334155", color="#64748b", title="Submissions"),
            height=280, margin=dict(l=0, r=0, t=12, b=0),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── Per-stage detail ──────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Submissions by Stage</div>', unsafe_allow_html=True)
    for stage in STAGES:
        items = stage_map.get(stage["name"], [])
        with st.expander(f"{stage['name']}  ·  {len(items)} submission{'s' if len(items)!=1 else ''}"):
            if items:
                for sub in items:
                    c1, c2, c3, c4 = st.columns([1.2, 3.5, 1.5, 1.5])
                    c1.markdown(f'<span class="info-chip">{sub["id"]}</span>', unsafe_allow_html=True)
                    c2.markdown(f'<span style="color:#e2e8f0;font-size:0.88rem;">{sub["name"]}</span>', unsafe_allow_html=True)
                    if sub["overall"] > 0:
                        css = score_color(sub["overall"])
                        c3.markdown(f'<span class="{css}">Score: {sub["overall"]}</span>', unsafe_allow_html=True)
                    else:
                        c3.markdown('<span style="color:#475569;">Not scored</span>', unsafe_allow_html=True)
                    sc = status_class(sub["status"])
                    c4.markdown(f'<span class="status-pill {sc}">{sub["status"]}</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span style="color:#475569;font-size:0.85rem;">No submissions in this stage.</span>', unsafe_allow_html=True)

    # ── Conversion funnel ─────────────────────────────────────────────────────
    if subs:
        st.markdown('<div class="section-title">Conversion Funnel</div>', unsafe_allow_html=True)
        for i, stage in enumerate(STAGES):
            count = len(stage_map.get(stage["name"], []))
            pct = count / max(len(subs), 1)
            bar_w = max(pct, 0.02)
            st.markdown(f"""
            <div style="display:flex; align-items:center; margin-bottom:10px; gap:12px;">
                <span style="width:110px; font-size:0.8rem; color:#94a3b8; text-align:right;">{stage['name']}</span>
                <div style="flex:1; background:#0f172a; border-radius:4px; height:22px; overflow:hidden;">
                    <div style="width:{int(bar_w*100)}%; background:{stage['color']}; height:100%; border-radius:4px;
                                display:flex; align-items:center; padding-left:8px;">
                        <span style="font-size:0.72rem; color:white; font-weight:600;">{count}</span>
                    </div>
                </div>
                <span style="width:48px; font-size:0.78rem; color:#64748b;">{int(pct*100)}%</span>
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: RUBRIC SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️  Rubric Settings":

    st.markdown("""
    <div class="forge-header">
        <h1>Rubric Settings</h1>
        <p>Configure scoring categories, weights, and thresholds that drive the AI evaluation engine.</p>
    </div>
    """, unsafe_allow_html=True)

    if not rubric:
        st.error("No rubric.json found. Please create a rubric.json file in the project root.")
    else:
        criteria_list = rubric.get("criteria", [])
        total_w = sum(c.get("weight", 0) for c in criteria_list)
        crit_count = len(criteria_list)

        # ── Header info ────────────────────────────────────────────────────────
        col_info1, col_info2 = st.columns([3, 1])
        with col_info1:
            st.markdown(f"""
            <div class="rubric-category">
                <div class="rubric-category-name">{rubric.get('rubric_name', 'Innovation Rubric')}</div>
                <div class="rubric-category-desc">{rubric.get('description', '')}</div>
                <div style="margin-top:8px;">
                    <span class="info-chip">{crit_count} criteria</span>
                    <span class="info-chip">Scores 1–10 per criterion</span>
                    <span class="info-chip">Weighted avg out of 100</span>
                </div>
            </div>""", unsafe_allow_html=True)
        with col_info2:
            w_ok = abs(total_w - 100) < 1
            w_color = "#4ade80" if w_ok else "#f87171"
            w_label = "Balanced" if w_ok else "Should sum to 100"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Weight</div>
                <div class="metric-value" style="color:{w_color};">{total_w}%</div>
                <div class="metric-sub">{w_label}</div>
            </div>""", unsafe_allow_html=True)

        # ── Scoring thresholds ─────────────────────────────────────────────────
        st.markdown('<div class="section-title">Scoring Thresholds</div>', unsafe_allow_html=True)
        t1, t2, t3 = st.columns(3)
        with t1:
            st.markdown(f"""
            <div class="metric-card" style="border-color:#4ade8044;">
                <div class="metric-label">Green Zone</div>
                <div class="metric-value" style="color:#4ade80;">≥ {THRESHOLDS['green']}</div>
                <div class="metric-sub">High potential, fast-track</div>
            </div>""", unsafe_allow_html=True)
        with t2:
            st.markdown(f"""
            <div class="metric-card" style="border-color:#fbbf2444;">
                <div class="metric-label">Yellow Zone</div>
                <div class="metric-value" style="color:#fbbf24;">{THRESHOLDS['yellow']}–{THRESHOLDS['green']-1}</div>
                <div class="metric-sub">Needs review, conditional</div>
            </div>""", unsafe_allow_html=True)
        with t3:
            st.markdown(f"""
            <div class="metric-card" style="border-color:#f8717144;">
                <div class="metric-label">Red Zone</div>
                <div class="metric-value" style="color:#f87171;">< {THRESHOLDS['yellow']}</div>
                <div class="metric-sub">Low priority, de-prioritize</div>
            </div>""", unsafe_allow_html=True)

        # ── Gating Rules ──────────────────────────────────────────────────────
        gating = rubric.get("gating_rules", [])
        if gating:
            st.markdown('<div class="section-title">Gating Rules (Auto-Reject / Flag)</div>', unsafe_allow_html=True)
            gate_html = "".join(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
                f'<span style="color:#f87171;font-size:1rem;">⛔</span>'
                f'<span style="font-size:0.85rem;color:#e2e8f0;">{rule}</span></div>'
                for rule in gating
            )
            st.markdown(f'<div style="background:#0f172a;border:1px solid #334155;border-radius:10px;padding:16px 20px;">{gate_html}</div>', unsafe_allow_html=True)

        # ── Criteria weight chart ──────────────────────────────────────────────
        st.markdown('<div class="section-title">Criteria Weights</div>', unsafe_allow_html=True)

        cat_colors = ["#3b82f6","#10b981","#f59e0b","#8b5cf6","#f97316","#06b6d4","#ec4899","#84cc16"]
        cat_names   = [c["criterion"]      for c in criteria_list]
        cat_weights = [c.get("weight", 0)  for c in criteria_list]

        fig_weights = go.Figure(go.Bar(
            x=cat_names, y=cat_weights,
            marker_color=[cat_colors[i % len(cat_colors)] for i in range(len(cat_names))],
            text=[f"{w}%" for w in cat_weights],
            textposition="auto",
            textfont=dict(color="#e2e8f0", size=11),
        ))
        fig_weights.update_layout(
            paper_bgcolor="#1e293b", plot_bgcolor="#1e293b",
            font={"color": "#94a3b8", "family": "Inter"},
            xaxis=dict(gridcolor="#334155", color="#64748b", tickangle=-25),
            yaxis=dict(gridcolor="#334155", color="#64748b", title="Weight (%)"),
            height=260, margin=dict(l=0, r=0, t=8, b=60),
        )
        st.plotly_chart(fig_weights, use_container_width=True)

        # ── Criterion detail cards ─────────────────────────────────────────────
        st.markdown('<div class="section-title">Criterion Detail</div>', unsafe_allow_html=True)
        for i, crit in enumerate(criteria_list):
            color = cat_colors[i % len(cat_colors)]
            anchors = crit.get("scoring_anchors", {})
            sub_factors = crit.get("sub_factors", [])
            red_flags = crit.get("red_flags", [])
            evidence = crit.get("evidence_required", "")

            with st.expander(f"{crit['criterion']}  ·  Weight: {crit.get('weight', 0)}%"):
                st.markdown(f'<span style="color:#94a3b8;font-size:0.85rem;">{crit.get("description","")}</span>', unsafe_allow_html=True)
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

                col_left, col_right = st.columns([3, 2])

                with col_left:
                    # Scoring anchors
                    if anchors:
                        st.markdown('<span style="font-size:0.78rem;text-transform:uppercase;letter-spacing:0.06em;color:#475569;font-weight:600;">Scoring Anchors</span>', unsafe_allow_html=True)
                        anchor_colors = {"1-3": "#f87171", "4-6": "#fbbf24", "7-10": "#4ade80"}
                        for band, desc in anchors.items():
                            ac = anchor_colors.get(band, "#94a3b8")
                            st.markdown(f"""
                            <div style="background:#0f172a;border-left:3px solid {ac};border-radius:6px;
                                        padding:8px 12px;margin:6px 0;">
                                <span style="color:{ac};font-weight:700;font-size:0.8rem;">{band}</span>
                                <span style="color:#94a3b8;font-size:0.8rem;margin-left:8px;">{desc}</span>
                            </div>""", unsafe_allow_html=True)

                    # Evidence required
                    if evidence:
                        st.markdown(f"""
                        <div style="margin-top:10px;background:#0f172a;border:1px solid #334155;
                                    border-radius:6px;padding:8px 12px;">
                            <span style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;
                                         color:#475569;font-weight:600;">Evidence Required</span><br>
                            <span style="color:#94a3b8;font-size:0.8rem;">{evidence}</span>
                        </div>""", unsafe_allow_html=True)

                with col_right:
                    # Sub-factors
                    if sub_factors:
                        st.markdown('<span style="font-size:0.78rem;text-transform:uppercase;letter-spacing:0.06em;color:#475569;font-weight:600;">Sub-Factors</span>', unsafe_allow_html=True)
                        sf_html = "".join(
                            f'<div style="display:flex;align-items:center;gap:8px;margin:5px 0;">'
                            f'<span style="color:{color};font-size:0.7rem;">▸</span>'
                            f'<span style="color:#e2e8f0;font-size:0.82rem;">{sf}</span></div>'
                            for sf in sub_factors
                        )
                        st.markdown(f'<div style="background:#0f172a;border:1px solid #334155;border-radius:6px;padding:10px 14px;">{sf_html}</div>', unsafe_allow_html=True)

                    # Red flags
                    if red_flags:
                        st.markdown('<span style="font-size:0.78rem;text-transform:uppercase;letter-spacing:0.06em;color:#475569;font-weight:600;margin-top:10px;display:block;">Red Flags</span>', unsafe_allow_html=True)
                        rf_html = "".join(
                            f'<div style="display:flex;align-items:center;gap:8px;margin:5px 0;">'
                            f'<span style="color:#f87171;font-size:0.75rem;">⚑</span>'
                            f'<span style="color:#f87171;font-size:0.82rem;">{rf}</span></div>'
                            for rf in red_flags
                        )
                        st.markdown(f'<div style="background:#2a0a0a;border:1px solid #7f1d1d44;border-radius:6px;padding:10px 14px;margin-top:6px;">{rf_html}</div>', unsafe_allow_html=True)

        # ── Rubric JSON view ────────────────────────────────────────────────
        st.markdown('<div class="section-title">Raw Rubric (rubric.json)</div>', unsafe_allow_html=True)
        st.json(rubric, expanded=False)

        st.info(
            "To modify the rubric, edit **rubric.json** in the project root and restart the app. "
            "Changes to criteria, weights, and thresholds will take effect immediately.",
            icon="ℹ️"
        )
