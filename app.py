import streamlit as st
import json
import os
import uuid
import random
import time
import hashlib
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
.forge-card:hover { border-color: #6e7681; }

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
    color: #8b949e;
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
    border: 1px solid #6e7681;
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
    border: 1px solid #6e7681;
    border-radius: 9999px;
    padding: 1px 7px;
}
.kanban-card {
    background: #161b22;
    border: 1px solid #6e7681;
    border-radius: 6px;
    padding: 10px 12px;
    margin-bottom: 8px;
    transition: border-color 0.15s, box-shadow 0.15s;
    cursor: default;
}
.kanban-card:hover {
    border-color: #8b949e;
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
    color: #8b949e;
    text-align: center;
    padding: 20px 8px;
    border: 1px dashed #6e7681;
    border-radius: 6px;
}

/* ══ Upload zone ════════════════════════════════════════════ */
[data-testid="stFileUploader"] {
    background: #161b22 !important;
    border: 1px dashed #6e7681 !important;
    border-radius: 8px !important;
    transition: border-color 0.15s !important;
}
[data-testid="stFileUploader"]:hover { border-color: #58a6ff !important; }
[data-testid="stFileUploader"] label { color: #8d96a3 !important; }

/* ══ Buttons ════════════════════════════════════════════════ */
.stButton > button {
    background: #21262d !important;
    color: #c9d1d9 !important;
    border: 1px solid #6e7681 !important;
    border-radius: 6px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    padding: 5px 14px !important;
    transition: background 0.15s, border-color 0.15s !important;
    white-space: nowrap !important;
}
.stButton > button:hover {
    background: #6e7681 !important;
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
    border: 1px solid #6e7681 !important;
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
.crit-card:hover { border-color: #6e7681; }
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
    color: #6e7681;
    margin-top: 2px;
}
.sb-section-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6e7681;
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
.empty-sub   { font-size: 13px; color: #8b949e; }

/* ══ Overrides ══════════════════════════════════════════════ */
hr { border-color: #6e7681 !important; margin: 12px 0 !important; }
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
        title={"text": title, "font": {"size": 10, "color": "#8b949e", "family": "Inter"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#21262d",
                     "tickfont": {"color": "#6e7681", "size": 8}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "#0d1117",
            "bordercolor": "#21262d",
            "borderwidth": 1,
            "steps": [
                {"range": [0,  40],  "color": "#3d1515"},
                {"range": [40, 70],  "color": "#3d2e08"},
                {"range": [70, 100], "color": "#0d2b1a"},
            ],
        }
    ))
    fig.update_layout(
        paper_bgcolor="#161b22", plot_bgcolor="#161b22",
        height=height, margin=dict(l=10, r=10, t=24, b=4),
        font={"family": "Inter"},
    )
    return fig

def _criterion_justification(key, band, display_name, score_10, anchor_txt, rng):
    """
    Return a criterion-specific, idea-aware justification that references the
    rubric anchor wording and the submission name. Two variants per (criterion,
    band) so the seeded RNG creates variety across ideas.
    """
    n = display_name  # already title-cased by caller
    s = score_10
    a = anchor_txt

    CRIT_JUST = {
        "Innovation & Novelty": {
            "1-3": [
                f"'{n}' scores {s}/10 on innovation. Rubric anchor: \"{a}\". No novel material, process, or IP pathway is evident — the concept mirrors existing market solutions without a defensible differentiation vector. Prior-art analysis is absent.",
                f"Innovation claim for '{n}' is unsupported ({s}/10). Anchor: \"{a}\". The submission describes incremental improvements at best; no breakthrough in materials, design IP, or manufacturing process could be identified against the rubric sub-factors.",
            ],
            "4-6": [
                f"'{n}' achieves moderate innovation ({s}/10). Anchor: \"{a}\". Some unique elements are present, but IP defensibility is thin and head-to-head competitors are not clearly outpaced. A stronger prior-art map and IP landscape review would materially lift this score.",
                f"Innovation for '{n}' is promising but incomplete ({s}/10). Anchor: \"{a}\". Differentiation is real but could erode quickly without clearer IP strategy or a harder-to-replicate manufacturing process advantage.",
            ],
            "7-10": [
                f"'{n}' demonstrates strong innovation ({s}/10). Anchor: \"{a}\". Breakthrough positioning across material, design, or process is identifiable, and an IP moat is credible. This submission outperforms peer ideas on novelty and competitive defensibility.",
                f"Exceptional innovation trajectory for '{n}' ({s}/10). Anchor: \"{a}\". The concept exhibits genuine differentiation — whether in novel materials, proprietary manufacturing steps, or design IP — that creates a meaningful barrier to fast-follow competition.",
            ],
        },
        "Market Potential & Saturation": {
            "1-3": [
                f"Market case for '{n}' is weak ({s}/10). Anchor: \"{a}\". Market data is absent or implausible; the saturation level is not addressed and no validated demand signal is present. TAM/SAM/SOM claims are either missing or wildly optimistic.",
                f"'{n}' fails to establish a compelling market thesis ({s}/10). Anchor: \"{a}\". The target segment is either too small, too saturated, or the submission conflates total market size with reachable opportunity.",
            ],
            "4-6": [
                f"'{n}' targets a viable but competitive market ({s}/10). Anchor: \"{a}\". Demand signals exist but TAM/SAM/SOM projections need substantiation, and competitive positioning — especially against incumbents — requires much sharper articulation.",
                f"Market potential for '{n}' is moderate ({s}/10). Anchor: \"{a}\". Growth trends are broadly supportive, but the submission does not convincingly show how the product carves out sustainable share in a crowded field.",
            ],
            "7-10": [
                f"'{n}' addresses a large and validated market ({s}/10). Anchor: \"{a}\". Market sizing is credible, the unmet need is clearly articulated with customer evidence, and growth trends strongly support the timing of entry.",
                f"Strong market case for '{n}' ({s}/10). Anchor: \"{a}\". The submission identifies a sizeable, growing segment with documented demand gaps, and positions the product to capture meaningful share without relying on overly optimistic projections.",
            ],
        },
        "Technical & Manufacturing Feasibility": {
            "1-3": [
                f"'{n}' is a pure concept at this stage ({s}/10). Anchor: \"{a}\". No manufacturing path, BOM estimate, or supplier context is provided. Scalability from prototype to production is entirely unaddressed — a critical gap at any pipeline stage.",
                f"Manufacturing feasibility for '{n}' is critically under-evidenced ({s}/10). Anchor: \"{a}\". The submission does not engage with cost structure, supply chain complexity, or process constraints that would allow a feasibility judgement.",
            ],
            "4-6": [
                f"'{n}' shows basic technical viability but scaling is unclear ({s}/10). Anchor: \"{a}\". A prototype pathway exists, but the BOM, supplier network, and cost-at-volume picture are incomplete. Significant engineering and supply chain work remains before production is realistic.",
                f"Technical feasibility for '{n}' is partially established ({s}/10). Anchor: \"{a}\". Core mechanics are plausible, but the submission lacks detail on manufacturing process, tooling costs, and supply chain resilience that would de-risk a production commitment.",
            ],
            "7-10": [
                f"'{n}' demonstrates a clear path to production ({s}/10). Anchor: \"{a}\". BOM realism, supplier references, and scalable process design are all credibly addressed. Cost structure at volume is defensible and the supply chain risk profile is manageable.",
                f"Excellent manufacturing feasibility for '{n}' ({s}/10). Anchor: \"{a}\". The submission provides a convincing factory-floor-to-shelf narrative with realistic cost models, identified supply partners, and a scalable process that survives scrutiny.",
            ],
        },
        "Sustainability & Circularity": {
            "1-3": [
                f"'{n}' shows negligible sustainability thinking ({s}/10). Anchor: \"{a}\". No lifecycle consideration, material certification, or circular design element is present. The submission risks greenwashing exposure without measurable environmental metrics.",
                f"Sustainability score for '{n}' is critically low ({s}/10). Anchor: \"{a}\". Material choices and end-of-life pathways are not addressed. Without LCA evidence or recyclability data, the product cannot credibly claim environmental positioning.",
            ],
            "4-6": [
                f"'{n}' makes basic sustainability efforts but gaps remain ({s}/10). Anchor: \"{a}\". Some eco-conscious language is present, but measurable metrics, certifications, and a genuine circular design strategy are missing. Greenwashing risk is moderate.",
                f"Sustainability approach for '{n}' is partial ({s}/10). Anchor: \"{a}\". Intentions are visible but the submission does not quantify carbon footprint, recyclability, or ethical sourcing in a way that stands up to third-party scrutiny.",
            ],
            "7-10": [
                f"'{n}' demonstrates strong circular design thinking ({s}/10). Anchor: \"{a}\". Material choices, end-of-life pathways, and measurable impact reduction are all credibly addressed. Certifications or LCA references make environmental claims verifiable.",
                f"Sustainability profile for '{n}' is compelling ({s}/10). Anchor: \"{a}\". The submission embeds circularity into the product architecture — not as a marketing overlay but as a structural design principle — with quantifiable environmental commitments.",
            ],
        },
        "Regulatory Compliance & Risk": {
            "1-3": [
                f"'{n}' does not address regulatory requirements ({s}/10). Anchor: \"{a}\". Key standards, certifications, and compliance pathways are absent. This is a critical blocker — without a regulatory roadmap the product cannot reach market in most jurisdictions.",
                f"Regulatory risk for '{n}' is high ({s}/10). Anchor: \"{a}\". No evidence of awareness of relevant directives, safety testing requirements, or certification timelines. This gap could significantly delay or prevent market entry.",
            ],
            "4-6": [
                f"'{n}' has basic regulatory awareness but an incomplete compliance plan ({s}/10). Anchor: \"{a}\". Relevant regulations are acknowledged, but the roadmap to certification — including timelines, costs, and responsible parties — is underdeveloped.",
                f"Compliance approach for '{n}' is nascent ({s}/10). Anchor: \"{a}\". The submission identifies the regulatory landscape at a surface level but does not demonstrate a structured path through testing, approval, and ongoing compliance management.",
            ],
            "7-10": [
                f"'{n}' presents a clear regulatory roadmap ({s}/10). Anchor: \"{a}\". Relevant standards are identified, certification pathways are mapped, and risk mitigation measures are credible. Compliance is treated as a strategic asset, not an afterthought.",
                f"Strong compliance posture for '{n}' ({s}/10). Anchor: \"{a}\". The submission demonstrates proactive regulatory engagement — standards are named, testing protocols are outlined, and the timeline to market approval is realistic and risk-adjusted.",
            ],
        },
        "Team & Execution Capability": {
            "1-3": [
                f"Team behind '{n}' lacks the credentials to execute ({s}/10). Anchor: \"{a}\". No relevant physical-goods experience, manufacturing expertise, or supply chain relationships are demonstrated. Key functional roles appear unfilled with no hiring plan.",
                f"Execution capability for '{n}' is critically under-evidenced ({s}/10). Anchor: \"{a}\". The submission does not establish credibility in the domain — no track record in bringing comparable physical products to market is presented.",
            ],
            "4-6": [
                f"'{n}' has a partially capable team ({s}/10). Anchor: \"{a}\". Some relevant expertise is present, but critical capability gaps exist — particularly in manufacturing operations, regulatory affairs, or commercial channels. An explicit hiring roadmap would strengthen confidence.",
                f"Team for '{n}' shows promise with identified gaps ({s}/10). Anchor: \"{a}\". Founding competencies are present in some domains but the submission acknowledges — or ignores — functional holes that will create execution risk at scale.",
            ],
            "7-10": [
                f"'{n}' is backed by a strong, balanced execution team ({s}/10). Anchor: \"{a}\". Demonstrated track record in physical goods, manufacturing partnerships, and commercial channels is clearly evidenced. The team has credibly done this before.",
                f"Excellent team capability for '{n}' ({s}/10). Anchor: \"{a}\". The founders bring domain-specific depth — engineering, operations, and commercial roles are all credibly covered, with a track record that validates their ability to navigate production and go-to-market.",
            ],
        },
        "Business Model & Commercial Viability": {
            "1-3": [
                f"Commercial case for '{n}' is underdeveloped ({s}/10). Anchor: \"{a}\". No clear revenue model, pricing rationale, or unit economics are presented. The path from concept to profitable operation is entirely hypothetical.",
                f"'{n}' lacks a viable business model ({s}/10). Anchor: \"{a}\". Revenue streams are vague, margin structure is absent, and the go-to-market plan does not establish how the product reaches paying customers at commercially viable volumes.",
            ],
            "4-6": [
                f"'{n}' has a basic but unproven commercial model ({s}/10). Anchor: \"{a}\". Revenue logic is present, but unit economics are not fully worked through and the go-to-market approach lacks channel specificity. Early traction or letters of intent would materially strengthen this.",
                f"Business model for '{n}' is directionally sound but thin ({s}/10). Anchor: \"{a}\". Pricing assumptions are broadly reasonable, but margin analysis at target volumes and channel cost structure are not sufficiently evidenced to build high commercial confidence.",
            ],
            "7-10": [
                f"'{n}' presents a clear path to profitable scaling ({s}/10). Anchor: \"{a}\". Unit economics are realistic, pricing is validated against customer willingness to pay, and the go-to-market plan is specific enough to be credible with well-defined channel partners.",
                f"Strong commercial viability for '{n}' ({s}/10). Anchor: \"{a}\". The revenue model is coherent, margins are defensible at target volumes, and early market signals — through pilots, LOIs, or channel relationships — reduce execution risk significantly.",
            ],
        },
        "Evidence Quality & Realism": {
            "1-3": [
                f"'{n}' is heavy on aspiration, light on evidence ({s}/10). Anchor: \"{a}\". Claims throughout the submission are unsupported by data, references, or validated tests. The overall picture is optimistic but not credible against rigorous rubric scrutiny.",
                f"Evidence quality for '{n}' is critically low ({s}/10). Anchor: \"{a}\". Contradictory statements and unsubstantiated projections undermine confidence across all other criteria. The submission reads as a pitch narrative rather than a grounded innovation case.",
            ],
            "4-6": [
                f"'{n}' provides partial evidence with notable gaps ({s}/10). Anchor: \"{a}\". Some claims are substantiated, but key assertions — particularly around market size, manufacturing costs, and technical performance — rest on assumptions rather than data.",
                f"Realism for '{n}' is moderate ({s}/10). Anchor: \"{a}\". The submission is internally consistent in places but uneven — well-evidenced sections sit alongside claims that are speculative or that rely on best-case scenario projections.",
            ],
            "7-10": [
                f"'{n}' is well-supported, consistent, and realistic ({s}/10). Anchor: \"{a}\". Evidence is cited throughout — market data, technical references, team credentials, and financial assumptions are all grounded and internally consistent. Confidence in this submission is high.",
                f"Excellent evidence quality for '{n}' ({s}/10). Anchor: \"{a}\". The submission demonstrates disciplined realism — projections are conservative, assumptions are made explicit, and supporting data sources are traceable. This is the standard against which peer submissions should be benchmarked.",
            ],
        },
    }

    # Fall back to generic if criterion name not found (future rubric additions)
    generic = {
        "1-3": [f"'{n}' scores {s}/10 — below threshold. Rubric anchor: \"{a}\". Critical gaps identified; immediate remediation required before advancing."],
        "4-6": [f"'{n}' scores {s}/10 — moderate. Rubric anchor: \"{a}\". Partial evidence present; deeper validation recommended across key sub-factors."],
        "7-10": [f"'{n}' scores {s}/10 — strong. Rubric anchor: \"{a}\". Submission exceeds sector benchmarks; clear validation pathway demonstrated."],
    }
    options = CRIT_JUST.get(key, generic).get(band, generic[band])
    return rng.choice(options)


def ai_score_submission(submission, rubric_data):
    """
    Chain-of-thought AI scoring engine.

    Reads all 8 criteria from rubric.json, derives context signals from the
    submission name/notes using keyword matching, then produces per-criterion
    scores (1-10) with idea-specific, rubric-anchored justifications.
    Applies gating rules and returns a fully structured breakdown.

    → Swap the RNG internals for a real LLM call when the API is connected.
    """
    name         = submission.get("name",  "").lower()
    notes        = submission.get("notes", "").lower()
    text         = name + " " + notes
    display_name = submission.get("name", "This submission").title()

    # Seed RNG on submission name → reproducible scores for the same idea
    seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
    rng  = random.Random(seed)

    criteria = rubric_data.get("criteria", [])

    # ── Keyword signals per criterion (positive boost / negative penalty) ─────
    SIGNALS = {
        "Innovation & Novelty": (
            ["breakthrough", "novel", "patent", "unique", "first", "bio", "mycelium",
             "self-heal", "nano", "smart", "micro", "carbon", "polymer", "proprietary",
             "advanced", "new material", "new process"],
            ["me-too", "copy", "basic", "simple", "existing", "commodity", "standard"],
        ),
        "Market Potential & Saturation": (
            ["market", "demand", "customer", "growth", "billion", "segment",
             "untapped", "commercial", "b2b", "validated", "gap", "underserved"],
            ["saturated", "small market", "niche only", "declining", "crowded"],
        ),
        "Technical & Manufacturing Feasibility": (
            ["prototype", "manufacturing", "supply chain", "bom", "scalable",
             "production", "material", "motor", "thermal", "compression",
             "insulation", "packaging", "exoskeleton", "foam", "coating", "tooling"],
            ["concept only", "theoretical", "unproven at scale", "unclear process"],
        ),
        "Sustainability & Circularity": (
            ["biodegradable", "sustainable", "circular", "recyclable", "eco",
             "mycelium", "bio", "carbon", "lca", "ethical", "renewable", "compostable"],
            ["virgin plastic", "toxic", "greenwash", "no certification", "landfill"],
        ),
        "Regulatory Compliance & Risk": (
            ["compliance", "certified", "fda", "ce", "regulatory", "standard",
             "iso", "approval", "testing", "safety", "directive", "reach"],
            ["unregulated", "no compliance plan", "unapproved"],
        ),
        "Team & Execution Capability": (
            ["team", "experience", "expert", "founder", "engineer",
             "track record", "proven", "background", "led", "built", "shipped"],
            ["no team", "inexperienced", "first time", "no relevant experience"],
        ),
        "Business Model & Commercial Viability": (
            ["revenue", "profit", "margin", "pricing", "unit economics",
             "commercial", "traction", "contract", "letters of intent", "b2b", "channel"],
            ["no revenue model", "unclear model", "free only", "donated"],
        ),
        "Evidence Quality & Realism": (
            ["data", "research", "study", "validated", "tested", "evidence",
             "pilot", "prototype", "results", "measured", "demonstrated", "cited"],
            ["vague", "hype", "we believe", "speculative", "unsubstantiated"],
        ),
    }

    scored_criteria = {}

    for crit in criteria:
        key          = crit["criterion"]
        weight       = crit.get("weight", 10)
        anchors      = crit.get("scoring_anchors", {})
        rf_list      = crit.get("red_flags", [])
        sub_facs     = crit.get("sub_factors", [])
        evidence_req = crit.get("evidence_required", "")

        # Base score biased toward mid-range; seeded for reproducibility
        base = rng.randint(48, 76)

        # Keyword signal adjustment
        pos_words, neg_words = SIGNALS.get(key, ([], []))
        boost   = min(sum(3 for w in pos_words if w in text), 21)
        penalty = min(sum(5 for w in neg_words if w in text), 24)
        raw     = max(10, min(95, base + boost - penalty))

        # 1-10 scale
        score_10 = round(raw / 10.0, 1)
        score_10 = max(1.0, min(10.0, score_10))

        # Anchor band
        if score_10 <= 3:
            band       = "1-3"
            anchor_txt = anchors.get("1-3", "Below threshold")
        elif score_10 <= 6:
            band       = "4-6"
            anchor_txt = anchors.get("4-6", "Moderate")
        else:
            band       = "7-10"
            anchor_txt = anchors.get("7-10", "Strong")

        justification  = _criterion_justification(key, band, display_name, score_10, anchor_txt, rng)
        evidence_level = "Sufficient" if score_10 >= 6 else ("Partial" if score_10 >= 4 else "Insufficient")

        # Detect red flags triggered by submission text
        triggered_flags = [
            rf for rf in rf_list
            if any(w in text for w in rf.lower().split() if len(w) > 4)
        ]

        scored_criteria[key] = {
            "name":          key,
            "score_10":      score_10,
            "score":         round(score_10 * 10),  # 0-100 for gauges/progress bars
            "weight":        weight,
            "weight_frac":   weight / 100.0,
            "anchor_band":   band,
            "anchor_text":   anchor_txt,
            "justification": justification,
            "evidence":      evidence_level,
            "evidence_req":  evidence_req,
            "red_flags":     triggered_flags,
            "sub_factors":   sub_facs,
        }

    # ── Weighted overall score (0-100) ────────────────────────────────────────
    total_w = sum(v["weight_frac"] for v in scored_criteria.values())
    overall = round(
        sum(v["score"] * v["weight_frac"] for v in scored_criteria.values()) / max(total_w, 0.01),
        1,
    )
    overall = min(overall, 100.0)

    # ── Gating rules (parsed from rubric) ────────────────────────────────────
    GATE_MAP = {
        "Innovation & Novelty":                  (6.0, "auto-reject"),
        "Technical & Manufacturing Feasibility": (6.0, "auto-reject"),
        "Sustainability & Circularity":          (5.0, "high-risk"),
        "Evidence Quality & Realism":            (4.0, "auto-reject"),
    }
    auto_reject_flags, high_risk_flags = [], []
    for crit_name, (threshold, action) in GATE_MAP.items():
        if crit_name in scored_criteria:
            s = scored_criteria[crit_name]["score_10"]
            if s < threshold:
                msg = f"{crit_name}: {s:.1f}/10 — below gate threshold of {threshold}/10"
                (auto_reject_flags if action == "auto-reject" else high_risk_flags).append(msg)

    return {
        "overall":     overall,
        "innovation":  scored_criteria.get("Innovation & Novelty", {}).get("score", 0),
        "feasibility": scored_criteria.get("Technical & Manufacturing Feasibility", {}).get("score", 0),
        "categories":  scored_criteria,
        "auto_reject": auto_reject_flags,
        "high_risk":   high_risk_flags,
        "scored_at":   datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def generate_stage_summary(submission, new_stage):
    """
    Simulate an AI-generated advancement note when a submission moves to the
    next pipeline stage. Returns a realistic, idea-specific operational summary.
    """
    name  = submission.get("name", "this idea")
    score = submission.get("overall", 0)
    sc    = f" — ForgeOS score: {score}/100" if score > 0 else ""

    TEMPLATES = {
        "Concept": [
            f"Concept review opened for '{name}'{sc}. The innovation profile shows early differentiation; the next critical actions are a structured prior-art review, TAM/SAM/SOM validation, and a first-pass IP landscape assessment. Assign a concept owner and set a 2-week gate review.",
            f"'{name}' enters Concept stage{sc}. Initial rubric signals are promising — recommend a 5-day deep-dive sprint covering: (1) competitive positioning map, (2) material/process novelty assessment, and (3) a first-cut BOM to anchor feasibility assumptions.",
            f"Concept stage activated for '{name}'{sc}. Evidence package flagged for peer review. Priority gap: strengthen the market validation narrative with at least 3 customer interviews before the next stage gate. IP filing timeline to be confirmed with counsel.",
        ],
        "Validation": [
            f"Technical and market validation commenced for '{name}'{sc}. Critical path items: BOM review with 2 qualified suppliers, customer discovery interviews (target: 10 B2B decision-makers), and initial regulatory pathway mapping. Stage gate: 4 weeks.",
            f"'{name}' advances to Validation{sc}. Engineering deep-dive and LCA review are the priority workstreams. Sustainability claims require third-party data validation — greenwashing risk flag raised during concept review. Compliance counsel engaged.",
            f"Validation stage active for '{name}'{sc}. Manufacturing feasibility is the key unknown: commission a first-article cost estimate and identify 3 potential contract manufacturers. Market validation to run in parallel with a structured demand-testing experiment.",
        ],
        "Prototyping": [
            f"Prototype development initiated for '{name}'{sc}. Manufacturing partner shortlisted from Validation stage. First-article testing targets set: dimensional accuracy ±0.5mm, material spec confirmed, cost-at-volume within 15% of model. 8-week sprint cadence with weekly build-test-learn cycles.",
            f"'{name}' enters Rapid Prototyping{sc}. Tooling cost review approved; materials sourcing order placed with primary supplier. Prototype spec sheet attached to this record. Key risk: lead time on proprietary components — mitigation: dual-source strategy activated.",
            f"Prototyping sprint live for '{name}'{sc}. Cross-functional team assembled: product engineering, industrial design, and supply chain. Milestone 1 (functional prototype): Week 4. Milestone 2 (user testing prototype): Week 8. Go/no-go decision at Week 9 gate.",
        ],
        "Market Test": [
            f"Market test phase launched for '{name}'{sc}. Beta cohort of 50 early adopters identified across 2 target segments. NPS baseline set; return rate and unit sell-through tracked weekly. Pricing model A/B tested: premium vs value anchor in pilot region. Results review at 6-week mark.",
            f"'{name}' enters limited market release{sc}. Channel partnership finalised with regional distributor. SKU count limited to 1 hero variant for test — learnings will inform range extension decisions. Real-world performance data will be the primary input for the full production go/no-go.",
            f"Market test initiated for '{name}'{sc}. E-commerce pilot live with a controlled ad spend of $5K/month. Target metrics: CAC < $40, conversion rate > 2.5%, repeat purchase within 60 days. Qualitative feedback loop via post-purchase survey activated. Stage review at 8 weeks.",
        ],
        "Scaling": [
            f"Scaling phase activated for '{name}'{sc}. Minimum order quantities confirmed with primary manufacturer; volume pricing locked at target margin. Supply chain hardening in progress: safety stock model built, 2nd-tier supplier qualified. QMS documentation initiated.",
            f"'{name}' approved for full production ramp{sc}. Inventory build plan: 3-month rolling forecast with 4-week safety buffer. Channel expansion into 3 new territories approved — logistics and customs compliance review completed. Marketing asset library handed to growth team.",
            f"Scaling stage live for '{name}'{sc}. Commercial ops handover complete. Demand planning model updated with real market test sell-through data. Key focus: maintaining quality at volume — inline QC checkpoints inserted at 3 production milestones. Weekly operations review commenced.",
        ],
        "Monitoring": [
            f"Post-launch monitoring active for '{name}'{sc}. KPI dashboard live: units sold, return rate, NPS, gross margin, and CAC tracked weekly. 90-day performance review scheduled. Alert thresholds set: return rate > 3% triggers engineering review; NPS < 40 triggers product council.",
            f"'{name}' enters live monitoring{sc}. Return rate, NPS, and unit economics tracked against targets set at Market Test gate. First monthly business review scheduled. Customer feedback loops formalised: support ticket analysis, review mining, and quarterly user interviews.",
            f"Monitoring phase commenced for '{name}'{sc}. Continuous improvement backlog created from beta feedback. Product council review quarterly. Innovation pipeline team notified: insights from '{name}' to feed into next-generation concept exploration within 6 months.",
        ],
    }

    options = TEMPLATES.get(new_stage, [f"'{name}' advanced to {new_stage}{sc}. Assign a stage owner, review the checklist, and set the next gate date."])
    seed = int(hashlib.md5((name + new_stage).encode()).hexdigest()[:8], 16)
    return random.Random(seed).choice(options)

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
        sub_stub = {"name": name, "notes": ""}
        if status != "New":
            scores = ai_score_submission(sub_stub, rubric)
        else:
            scores = {
                "overall": 0.0, "innovation": 0.0, "feasibility": 0.0,
                "categories": {}, "auto_reject": [], "high_risk": [], "scored_at": "",
            }
        days_ago = random.randint(1, 45)
        st.session_state.submissions.append({
            "id":            sid,
            "name":          name,
            "file_type":     ftype,
            "status":        status,
            "stage":         stage,
            "overall":       scores["overall"],
            "innovation":    scores["innovation"],
            "feasibility":   scores["feasibility"],
            "categories":    scores["categories"],
            "auto_reject":   scores.get("auto_reject", []),
            "high_risk":     scores.get("high_risk", []),
            "scored_at":     scores.get("scored_at", ""),
            "stage_summary": generate_stage_summary({"name": name, "overall": scores["overall"]}, stage) if stage != "Intake" else "",
            "submitted_at":  (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
            "notes":         "",
        })

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-logo">
        <div class="sb-wordmark">⚙ ForgeOS</div>
        <div class="sb-tag">Innovation Pipeline</div>
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
    <div class="sb-stat-row"><span class="sb-stat-label">Avg Score</span><span class="sb-stat-val" style="color:{score_hex(avg_score) if total else '#8b949e'}">{avg_score if total else '—'}</span></div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

    if st.button("Load Demo Data", use_container_width=True):
        if not st.session_state.submissions:
            add_demo_submissions()
            st.rerun()
        else:
            st.warning("Submissions already loaded.")

    st.markdown("""
    <div style="padding: 20px 16px 8px 16px;border-top:1px solid #21262d;margin-top:12px;">
        <div style="font-size:11px;font-weight:600;color:#8b949e;">ForgeOS v0.1</div>
        <div style="font-size:10px;color:#6e7681;margin-top:2px;">Built in 1 day · AI Scoring Engine</div>
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
        <div class="stat-value" style="color:{score_hex(avg_score) if total else '#8b949e'}">{avg_score if total else '—'}</div>
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
        <div class="stat-value" style="color:{score_hex(avg_innov) if avg_innov else '#8b949e'}">{avg_innov if avg_innov else '—'}</div>
        <div class="stat-sub">Innovation criterion</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Avg Feasibility</div>
        <div class="stat-value" style="color:{score_hex(avg_feas) if avg_feas else '#8b949e'}">{avg_feas if avg_feas else '—'}</div>
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
                    xaxis=dict(gridcolor="#21262d", color="#8b949e", title="Overall Score"),
                    yaxis=dict(gridcolor="#21262d", color="#8b949e", title="Count"),
                    height=220, margin=dict(l=0, r=0, t=8, b=0),
                    bargap=0.08,
                )
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.markdown('<div style="height:220px;display:flex;align-items:center;justify-content:center;color:#6e7681;font-size:13px;">No scored submissions yet</div>', unsafe_allow_html=True)

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
                badge = '<span style="color:#6e7681;font-size:12px;">—</span>'
            pc = pill_class(sub["status"])
            stage_color = next((s["color"] for s in STAGES if s["name"] == sub["stage"]), "#8b949e")
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
                    "id":            sid,
                    "name":          idea_name.strip(),
                    "file_type":     ", ".join(ftypes),
                    "status":        "New",
                    "stage":         init_stage,
                    "overall":       0.0,
                    "innovation":    0.0,
                    "feasibility":   0.0,
                    "categories":    {},
                    "auto_reject":   [],
                    "high_risk":     [],
                    "scored_at":     "",
                    "stage_summary": "",
                    "submitted_at":  datetime.now().strftime("%Y-%m-%d"),
                    "notes":         notes_txt,
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
                    msg.markdown(
                        f'<div style="font-size:12px;color:#8b949e;padding:4px 0;">'
                        f'🤖 Scoring <strong style="color:#e6edf3">{sub["name"]}</strong> '
                        f'({i+1}/{len(unscored)})…</div>',
                        unsafe_allow_html=True,
                    )
                    time.sleep(0.6)
                    sc  = ai_score_submission(sub, rubric)
                    idx = next(j for j, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                    st.session_state.submissions[idx].update({
                        "overall":   sc["overall"],
                        "innovation":  sc["innovation"],
                        "feasibility": sc["feasibility"],
                        "categories":  sc["categories"],
                        "auto_reject": sc["auto_reject"],
                        "high_risk":   sc["high_risk"],
                        "scored_at":   sc["scored_at"],
                        "status":      "Scored",
                    })
                    prog.progress((i + 1) / len(unscored))
                msg.empty()
                n_reject = sum(1 for s in st.session_state.submissions if s.get("auto_reject"))
                st.success(f"Scored {len(unscored)} submission(s). {n_reject} triggered auto-reject gates.")
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
            col.markdown(f'<span style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;color:#8b949e;font-weight:600;">{label}</span>', unsafe_allow_html=True)

        st.markdown("<hr style='margin:6px 0 0 0'>", unsafe_allow_html=True)

        for sub in visible:
            row = st.columns([1.2, 3.5, 1.1, 1.1, 1.1, 1.5, 1.5, 2.8])

            with row[0]:
                st.markdown(f'<span class="forge-id">{sub["id"]}</span>', unsafe_allow_html=True)

            with row[1]:
                st.markdown(f'<span style="font-size:13px;color:#e6edf3;font-weight:500;">{sub["name"]}</span>'
                            f'<br><span style="font-size:11px;color:#8b949e;">{sub["file_type"]} · {sub["submitted_at"]}</span>',
                            unsafe_allow_html=True)

            for col, field in zip(row[2:5], ["overall","innovation","feasibility"]):
                val = sub[field]
                if val > 0:
                    bc = score_badge_class(val)
                    col.markdown(f'<span class="badge-score {bc}">{val}</span>', unsafe_allow_html=True)
                else:
                    col.markdown('<span style="color:#6e7681;font-size:13px;">—</span>', unsafe_allow_html=True)

            with row[5]:
                pc = pill_class(sub["status"])
                st.markdown(f'<span class="pill {pc}">{sub["status"]}</span>', unsafe_allow_html=True)

            with row[6]:
                sc = next((s["color"] for s in STAGES if s["name"] == sub["stage"]), "#8b949e")
                st.markdown(f'<span style="font-size:11px;font-weight:600;color:{sc};">● {sub["stage"]}</span>', unsafe_allow_html=True)

            with row[7]:
                a1, a2, a3 = st.columns(3)
                with a1:
                    if st.button("Score", key=f"sc_{sub['id']}"):
                        with st.spinner(f"Scoring {sub['name']}…"):
                            time.sleep(0.8)
                            sc2 = ai_score_submission(sub, rubric)
                            idx = next(i for i, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                            st.session_state.submissions[idx].update({
                                "overall":    sc2["overall"],
                                "innovation":  sc2["innovation"],
                                "feasibility": sc2["feasibility"],
                                "categories":  sc2["categories"],
                                "auto_reject": sc2["auto_reject"],
                                "high_risk":   sc2["high_risk"],
                                "scored_at":   sc2["scored_at"],
                                "status":      "Scored",
                            })
                            st.rerun()
                with a2:
                    cur_stage_idx = STAGE_NAMES.index(sub["stage"]) if sub["stage"] in STAGE_NAMES else -1
                    at_last = cur_stage_idx >= len(STAGE_NAMES) - 1
                    if st.button("Advance", key=f"adv_{sub['id']}", disabled=at_last):
                        idx          = next(i for i, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                        new_stage    = STAGE_NAMES[cur_stage_idx + 1]
                        summary      = generate_stage_summary(st.session_state.submissions[idx], new_stage)
                        st.session_state.submissions[idx]["stage"]         = new_stage
                        st.session_state.submissions[idx]["stage_summary"] = summary
                        st.rerun()
                with a3:
                    if st.button("Delete", key=f"del_{sub['id']}"):
                        st.session_state.submissions = [s for s in st.session_state.submissions if s["id"] != sub["id"]]
                        st.rerun()

            # ── Score detail expander ──────────────────────────────────────────
            if sub["categories"]:
                with st.expander(f"AI Score Breakdown — {sub['name']}", expanded=False):

                    # ── Gating warnings ──────────────────────────────────────
                    ar = sub.get("auto_reject", [])
                    hr = sub.get("high_risk",   [])
                    if ar:
                        ar_items = "".join(f"<li>{r}</li>" for r in ar)
                        st.markdown(f"""
                        <div style="background:#2b0f0f;border:1px solid #6e1818;border-radius:8px;
                                    padding:12px 16px;margin-bottom:12px;">
                          <div style="font-size:11px;font-weight:700;color:#f85149;
                                      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">
                            ⛔ Auto-Reject Gate Triggered</div>
                          <ul style="margin:0;padding-left:16px;font-size:12px;color:#f85149;">{ar_items}</ul>
                        </div>""", unsafe_allow_html=True)
                    if hr:
                        hr_items = "".join(f"<li>{r}</li>" for r in hr)
                        st.markdown(f"""
                        <div style="background:#2b1f05;border:1px solid #9e6a03;border-radius:8px;
                                    padding:12px 16px;margin-bottom:12px;">
                          <div style="font-size:11px;font-weight:700;color:#d29922;
                                      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">
                            ⚠ High-Risk Flag</div>
                          <ul style="margin:0;padding-left:16px;font-size:12px;color:#d29922;">{hr_items}</ul>
                        </div>""", unsafe_allow_html=True)

                    # ── Stage summary ────────────────────────────────────────
                    summ = sub.get("stage_summary", "")
                    if summ:
                        st.markdown(f"""
                        <div style="background:#0c1e35;border:1px solid #1f6feb44;border-radius:8px;
                                    padding:12px 16px;margin-bottom:16px;">
                          <div style="font-size:10px;font-weight:700;color:#58a6ff;
                                      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">
                            Stage Note</div>
                          <div style="font-size:12px;color:#b0b8c4;line-height:1.6;">{summ}</div>
                        </div>""", unsafe_allow_html=True)

                    # ── Top-4 gauges ─────────────────────────────────────────
                    top4 = list(sub["categories"].items())[:4]
                    gauge_cols = st.columns(len(top4))
                    for i, (cid, cd) in enumerate(top4):
                        with gauge_cols[i]:
                            st.plotly_chart(
                                make_gauge(cd["score"], cd["name"]),
                                use_container_width=True,
                                key=f"g_{sub['id']}_{i}",
                            )

                    # ── Per-criterion detail rows ────────────────────────────
                    st.markdown('<div class="section-hd" style="margin-top:12px;">All Criteria</div>', unsafe_allow_html=True)

                    anchor_colors = {"1-3": "#f85149", "4-6": "#d29922", "7-10": "#3fb950"}
                    ev_colors     = {"Sufficient": "#3fb950", "Partial": "#d29922", "Insufficient": "#f85149"}

                    for cid, cd in sub["categories"].items():
                        c        = score_hex(cd["score"])
                        band_c   = anchor_colors.get(cd.get("anchor_band", "4-6"), "#8b949e")
                        ev_c     = ev_colors.get(cd.get("evidence", "Partial"), "#8b949e")
                        s10      = cd.get("score_10", round(cd["score"] / 10, 1))
                        just_txt = cd.get("justification", "")
                        ev_lbl   = cd.get("evidence", "Partial")
                        rf_hits  = cd.get("red_flags", [])
                        wt       = cd.get("weight", "—")

                        rf_html = ""
                        if rf_hits:
                            rf_html = "".join(f'<span style="font-size:10px;color:#f85149;margin-right:8px;">⚑ {rf}</span>' for rf in rf_hits)
                            rf_html = f'<div style="margin-top:4px;">{rf_html}</div>'

                        st.markdown(f"""
                        <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;
                                    padding:12px 16px;margin-bottom:8px;">
                          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                            <span style="font-size:13px;font-weight:600;color:#e6edf3;">{cid}</span>
                            <div style="display:flex;align-items:center;gap:8px;">
                              <span style="font-size:11px;color:#8b949e;">Weight: {wt}%</span>
                              <span style="font-size:14px;font-weight:800;color:{c};">{s10}/10</span>
                              <span style="font-size:10px;font-weight:600;color:{ev_c};
                                           background:{ev_c}18;border:1px solid {ev_c}44;
                                           border-radius:4px;padding:1px 6px;">
                                {ev_lbl}</span>
                            </div>
                          </div>
                          <div style="background:#21262d;border-radius:2px;height:4px;margin-bottom:8px;">
                            <div style="width:{cd['score']}%;background:{c};height:100%;border-radius:2px;"></div>
                          </div>
                          <div style="font-size:12px;color:#8b949e;line-height:1.5;">{just_txt}</div>
                          {rf_html}
                        </div>""", unsafe_allow_html=True)

                    scored_at = sub.get("scored_at", "")
                    if scored_at:
                        st.markdown(f'<div style="font-size:11px;color:#8b949e;margin-top:8px;text-align:right;">Scored at {scored_at}</div>', unsafe_allow_html=True)

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
            xaxis=dict(gridcolor="#21262d", color="#8b949e"),
            yaxis=dict(gridcolor="#21262d", color="#8b949e", title="Submissions"),
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
              <span style="width:36px;font-size:11px;color:#8b949e;">{int(pct*100)}%</span>
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
              <div style="font-size:11px;color:#8b949e;">{len(criteria_list)} criteria</div>
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
                            st.markdown('<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#8b949e;font-weight:700;margin-bottom:8px;">Scoring Anchors</div>', unsafe_allow_html=True)
                            anchor_map = {"1-3": ("anchor-low","#f85149"), "4-6": ("anchor-mid","#d29922"), "7-10": ("anchor-high","#3fb950")}
                            for band, desc in anchors.items():
                                cls_n, clr = anchor_map.get(band, ("", "#8b949e"))
                                st.markdown(f"""
                                <div class="anchor-band {cls_n}">
                                  <span style="color:{clr};font-weight:700;font-size:11px;">{band}</span>
                                  <span style="color:#8d96a3;font-size:11px;margin-left:8px;">{desc}</span>
                                </div>""", unsafe_allow_html=True)

                        if evidence:
                            st.markdown(f"""
                            <div style="margin-top:12px;padding:8px 12px;background:#0d1117;border:1px solid #21262d;border-radius:6px;">
                              <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#8b949e;font-weight:700;margin-bottom:4px;">Evidence Required</div>
                              <div style="font-size:12px;color:#8d96a3;">{evidence}</div>
                            </div>""", unsafe_allow_html=True)

                    with cr:
                        if subs_f:
                            st.markdown('<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#8b949e;font-weight:700;margin-bottom:8px;">Sub-Factors</div>', unsafe_allow_html=True)
                            tags = "".join(f'<span class="subfactor-tag">▸ {sf}</span>' for sf in subs_f)
                            st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:4px;">{tags}</div>', unsafe_allow_html=True)

                        if redflags:
                            st.markdown('<div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#8b949e;font-weight:700;margin:12px 0 8px;">Red Flags</div>', unsafe_allow_html=True)
                            flags_html = "".join(f'<div class="redflag-item">⚑ {rf}</div>' for rf in redflags)
                            st.markdown(f'<div style="background:#2b0f0f18;border:1px solid #6e181822;border-radius:6px;padding:10px 12px;">{flags_html}</div>', unsafe_allow_html=True)

        with tab_gate:
            if gating:
                st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
                for rule in gating:
                    st.markdown(f'<div class="gate-rule"><span style="color:#f85149;font-size:14px;">⛔</span> {rule}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<p style="color:#8b949e;font-size:13px;">No gating rules defined.</p>', unsafe_allow_html=True)

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
                xaxis=dict(gridcolor="#21262d", color="#8b949e", tickangle=-30),
                yaxis=dict(gridcolor="#21262d", color="#8b949e", title="Weight (%)"),
                height=300, margin=dict(l=0, r=0, t=8, b=80),
            )
            st.plotly_chart(fig_w, use_container_width=True)

        with tab_json:
            st.json(rubric, expanded=False)
            st.info("Edit rubric.json and restart the app to apply changes.", icon="ℹ️")

    st.markdown('</div>', unsafe_allow_html=True)
