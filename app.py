import streamlit as st
import json
import os
import uuid
import random
import time
import hashlib
import urllib.request
import urllib.error
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ─── LLM Config ──────────────────────────────────────────────────────────────
_FORGE_LLM_API_KEY  = os.environ.get("FORGE_LLM_API_KEY", "")
_FORGE_LLM_BASE_URL = os.environ.get("FORGE_LLM_BASE_URL", "https://api.x.ai/v1").rstrip("/")
_FORGE_LLM_MODEL    = os.environ.get("FORGE_LLM_MODEL", "grok-3")
_LLM_AVAILABLE      = bool(_FORGE_LLM_API_KEY)   # True only when env var is set

# ─── Persistent key file (never committed — listed in .gitignore) ─────────────
_KEY_FILE = os.path.join(os.path.dirname(__file__), ".forge_api_key")


def _load_saved_key() -> str:
    """Read the persisted API key from disk. Returns '' if absent or unreadable."""
    try:
        with open(_KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except (OSError, IOError):
        return ""


def _save_key_to_disk(key: str) -> None:
    """Write the API key to disk so it survives page refreshes."""
    try:
        with open(_KEY_FILE, "w", encoding="utf-8") as f:
            f.write(key.strip())
    except (OSError, IOError):
        pass   # silently ignore (e.g. read-only FS)


def _clear_saved_key() -> None:
    """Delete the persisted key file from disk."""
    try:
        os.remove(_KEY_FILE)
    except (OSError, FileNotFoundError):
        pass


def _effective_llm_key() -> str:
    """Return the API key to use: env var takes priority, then session-entered key."""
    if _FORGE_LLM_API_KEY:
        return _FORGE_LLM_API_KEY
    return st.session_state.get("session_llm_key", "").strip()


def _llm_ready() -> bool:
    """True when a usable API key is available (env var or session entry)."""
    return bool(_effective_llm_key())

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
if "flash_msg" not in st.session_state:
    st.session_state.flash_msg = None
if "scoring_mode" not in st.session_state:
    st.session_state.scoring_mode = "Simulated"
if "session_llm_key" not in st.session_state:
    # Load from disk on first run so key survives page refreshes
    st.session_state.session_llm_key = _load_saved_key()

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

def forge_badge(sub):
    """
    Return (label, text_color, bg_color) for the ForgeOS AI quality badge.
    Derived from gating flags and overall score.
    Returns (None, None, None) when the submission is unscored.
    """
    if sub.get("auto_reject"):
        return "Auto-Reject", "#f85149", "#2b0f0f"
    if sub.get("high_risk"):
        return "High Risk",   "#d29922", "#2b1f05"
    score = sub.get("overall", 0)
    if score >= THRESHOLDS["green"]:
        return "Strong",      "#3fb950", "#0d2b1a"
    if score >= THRESHOLDS["yellow"]:
        return "Promising",   "#58a6ff", "#0c1e35"
    if score > 0:
        return "Needs Work",  "#8b949e", "#1c2128"
    return None, None, None

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


def extract_file_text(uploaded_files):
    """
    Extract plain text from uploaded files for use as LLM context.
    - PDF: text extracted via pypdf
    - Image: placeholder note
    - Video: placeholder note
    - Text/other: decoded as UTF-8 where possible
    Returns a combined string.
    """
    if not uploaded_files:
        return ""
    parts = []
    for f in uploaded_files:
        fname = f.name.lower()
        ftype = f.type or ""
        try:
            if fname.endswith(".pdf") or "pdf" in ftype:
                try:
                    import pypdf
                    reader = pypdf.PdfReader(f)
                    pages  = []
                    for page in reader.pages:
                        txt = page.extract_text()
                        if txt:
                            pages.append(txt.strip())
                    if pages:
                        combined = "\n".join(pages)
                        parts.append(f"[PDF: {f.name}]\n{combined}")
                    else:
                        parts.append(f"[PDF: {f.name}] (no extractable text — may be scanned image)")
                except Exception as pdf_err:
                    parts.append(f"[PDF: {f.name}] (extraction failed: {pdf_err})")
            elif any(fname.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
                parts.append(f"[Image: {f.name}] — Image uploaded; manual visual review recommended.")
            elif any(fname.endswith(ext) for ext in (".mp4", ".mov", ".avi", ".webm", ".mkv")):
                parts.append(f"[Video: {f.name}] — Video uploaded; manual review recommended (transcription not available).")
            elif any(fname.endswith(ext) for ext in (".txt", ".md", ".csv")):
                raw = f.read()
                try:
                    parts.append(f"[Text: {f.name}]\n{raw.decode('utf-8', errors='replace')[:4000]}")
                except Exception:
                    parts.append(f"[Text: {f.name}] (could not decode)")
            else:
                raw = f.read()
                try:
                    decoded = raw.decode("utf-8", errors="replace")[:2000]
                    parts.append(f"[File: {f.name}]\n{decoded}")
                except Exception:
                    parts.append(f"[File: {f.name}] (binary — cannot extract text)")
        except Exception as outer_err:
            parts.append(f"[File: {f.name}] (read error: {outer_err})")
        finally:
            try:
                f.seek(0)
            except Exception:
                pass
    return "\n\n".join(parts)


def _ai_score_llm_pure(submission, rubric_data, api_key: str, base_url: str, model: str):
    """
    Pure LLM scoring — no st.session_state or module-level globals accessed.
    All config is passed in explicitly so this is safe to call from worker threads.
    Raises RuntimeError on API/parse failure (caller handles fallback).
    """
    criteria    = rubric_data.get("criteria", [])
    rubric_json = json.dumps(rubric_data, indent=2)

    system_prompt = f"""You are ForgeOS, an expert innovation scoring engine for physical goods companies.
You will score a product idea submission against the ForgeOS Extensive Rubric v2.

RUBRIC JSON:
{rubric_json}

INSTRUCTIONS:
- Score each criterion on a scale of 1.0–10.0 (one decimal place).
- Return ONLY a valid JSON object — no markdown, no extra text.
- The JSON must have this exact schema:
{{
  "criteria": {{
    "<criterion_name>": {{
      "score_10": <float 1.0-10.0>,
      "justification": "<2-3 sentence rubric-anchored justification>",
      "red_flags": [<list of triggered red flag strings, may be empty>],
      "gating_pass": <true if score meets the gating threshold for this criterion, else false>
    }}
  }},
  "weighted_total": <float 0-100>
}}
- Use the exact criterion names from the rubric.
- Weight the overall score as a weighted average using the weights in the rubric.
- Be discerning and critical — physical goods innovation is hard. Do not inflate scores.
- Base your scores on the idea name, notes, and any uploaded file content provided."""

    name           = submission.get("name", "")
    notes          = submission.get("notes", "")
    extracted_text = submission.get("extracted_text", "")

    user_parts = [f"IDEA NAME: {name}"]
    if notes.strip():
        user_parts.append(f"NOTES: {notes}")
    if extracted_text.strip():
        user_parts.append(f"UPLOADED FILE CONTENT:\n{extracted_text[:6000]}")
    user_message = "\n\n".join(user_parts)

    payload = json.dumps({
        "model":           model,
        "messages":        [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        "response_format": {"type": "json_object"},
        "temperature":     0.2,
    }).encode("utf-8")

    req = urllib.request.Request(
        url     = f"{base_url}/chat/completions",
        data    = payload,
        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method  = "POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw_body   = resp.read().decode("utf-8")
            api_result = json.loads(raw_body)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM API HTTP {e.code}: {err_body[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"LLM API connection error: {e.reason}") from e

    content  = api_result["choices"][0]["message"]["content"]
    llm_json = json.loads(content)

    llm_criteria    = llm_json.get("criteria", {})
    scored_criteria = {}

    GATE_MAP = {
        "Innovation & Novelty":                  (6.0, "auto-reject"),
        "Technical & Manufacturing Feasibility": (6.0, "auto-reject"),
        "Sustainability & Circularity":          (5.0, "high-risk"),
        "Evidence Quality & Realism":            (4.0, "auto-reject"),
    }

    for crit in criteria:
        key          = crit["criterion"]
        weight       = crit.get("weight", 10)
        llm_crit     = llm_criteria.get(key, {})
        score_10     = float(llm_crit.get("score_10", 5.0))
        score_10     = max(1.0, min(10.0, round(score_10, 1)))
        justification = llm_crit.get("justification", "")
        red_flags    = llm_crit.get("red_flags", [])

        if score_10 <= 3:
            band      = "1-3"
            anchor_txt = crit.get("scoring_anchors", {}).get("1-3", "Below threshold")
        elif score_10 <= 6:
            band      = "4-6"
            anchor_txt = crit.get("scoring_anchors", {}).get("4-6", "Moderate")
        else:
            band      = "7-10"
            anchor_txt = crit.get("scoring_anchors", {}).get("7-10", "Strong")

        evidence_level = "Sufficient" if score_10 >= 6 else ("Partial" if score_10 >= 4 else "Insufficient")

        scored_criteria[key] = {
            "name":          key,
            "score_10":      score_10,
            "score":         round(score_10 * 10),
            "weight":        weight,
            "weight_frac":   weight / 100.0,
            "anchor_band":   band,
            "anchor_text":   anchor_txt,
            "justification": justification,
            "evidence":      evidence_level,
            "evidence_req":  crit.get("evidence_required", ""),
            "red_flags":     red_flags,
            "sub_factors":   crit.get("sub_factors", []),
        }

    total_w = sum(v["weight_frac"] for v in scored_criteria.values())
    overall = round(
        sum(v["score"] * v["weight_frac"] for v in scored_criteria.values()) / max(total_w, 0.01),
        1,
    )
    overall = min(overall, 100.0)

    auto_reject_flags, high_risk_flags = [], []
    for crit_name, (threshold, action) in GATE_MAP.items():
        if crit_name in scored_criteria:
            s = scored_criteria[crit_name]["score_10"]
            if s < threshold:
                msg_g = f"{crit_name}: {s:.1f}/10 — below gate threshold of {threshold}/10"
                (auto_reject_flags if action == "auto-reject" else high_risk_flags).append(msg_g)

    return {
        "overall":     overall,
        "innovation":  scored_criteria.get("Innovation & Novelty", {}).get("score", 0),
        "feasibility": scored_criteria.get("Technical & Manufacturing Feasibility", {}).get("score", 0),
        "categories":  scored_criteria,
        "auto_reject": auto_reject_flags,
        "high_risk":   high_risk_flags,
        "scored_at":   datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def ai_score_submission_llm(submission, rubric_data):
    """
    Real LLM scoring using an OpenAI-compatible API (default: xAI Grok).
    Sends the full rubric as system context and the submission details as user message.
    Parses the structured JSON response and maps it to the same dict shape as
    ai_score_submission(). Falls back to ai_score_submission() on any error and
    returns a (result, warning_message) tuple.
    """
    criteria    = rubric_data.get("criteria", [])
    rubric_json = json.dumps(rubric_data, indent=2)

    system_prompt = f"""You are ForgeOS, an expert innovation scoring engine for physical goods companies.
You will score a product idea submission against the ForgeOS Extensive Rubric v2.

RUBRIC JSON:
{rubric_json}

INSTRUCTIONS:
- Score each criterion on a scale of 1.0–10.0 (one decimal place).
- Return ONLY a valid JSON object — no markdown, no extra text.
- The JSON must have this exact schema:
{{
  "criteria": {{
    "<criterion_name>": {{
      "score_10": <float 1.0-10.0>,
      "justification": "<2-3 sentence rubric-anchored justification>",
      "red_flags": [<list of triggered red flag strings, may be empty>],
      "gating_pass": <true if score meets the gating threshold for this criterion, else false>
    }}
  }},
  "weighted_total": <float 0-100>
}}
- Use the exact criterion names from the rubric.
- Weight the overall score as a weighted average using the weights in the rubric.
- Be discerning and critical — physical goods innovation is hard. Do not inflate scores.
- Base your scores on the idea name, notes, and any uploaded file content provided."""

    name           = submission.get("name", "")
    notes          = submission.get("notes", "")
    extracted_text = submission.get("extracted_text", "")

    user_parts = [f"IDEA NAME: {name}"]
    if notes.strip():
        user_parts.append(f"NOTES: {notes}")
    if extracted_text.strip():
        user_parts.append(f"UPLOADED FILE CONTENT:\n{extracted_text[:6000]}")
    user_message = "\n\n".join(user_parts)

    payload = json.dumps({
        "model":           _FORGE_LLM_MODEL,
        "messages":        [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        "response_format": {"type": "json_object"},
        "temperature":     0.2,
    }).encode("utf-8")

    req = urllib.request.Request(
        url     = f"{_FORGE_LLM_BASE_URL}/chat/completions",
        data    = payload,
        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {_effective_llm_key()}",
        },
        method  = "POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw_body   = resp.read().decode("utf-8")
            api_result = json.loads(raw_body)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM API HTTP {e.code}: {err_body[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"LLM API connection error: {e.reason}") from e

    content = api_result["choices"][0]["message"]["content"]
    llm_json = json.loads(content)

    llm_criteria  = llm_json.get("criteria", {})
    scored_criteria = {}

    GATE_MAP = {
        "Innovation & Novelty":                  (6.0, "auto-reject"),
        "Technical & Manufacturing Feasibility": (6.0, "auto-reject"),
        "Sustainability & Circularity":          (5.0, "high-risk"),
        "Evidence Quality & Realism":            (4.0, "auto-reject"),
    }

    for crit in criteria:
        key          = crit["criterion"]
        weight       = crit.get("weight", 10)
        llm_crit     = llm_criteria.get(key, {})
        score_10     = float(llm_crit.get("score_10", 5.0))
        score_10     = max(1.0, min(10.0, round(score_10, 1)))
        justification = llm_crit.get("justification", "")
        red_flags    = llm_crit.get("red_flags", [])

        if score_10 <= 3:
            band = "1-3"
            anchor_txt = crit.get("scoring_anchors", {}).get("1-3", "Below threshold")
        elif score_10 <= 6:
            band = "4-6"
            anchor_txt = crit.get("scoring_anchors", {}).get("4-6", "Moderate")
        else:
            band = "7-10"
            anchor_txt = crit.get("scoring_anchors", {}).get("7-10", "Strong")

        evidence_level = "Sufficient" if score_10 >= 6 else ("Partial" if score_10 >= 4 else "Insufficient")

        scored_criteria[key] = {
            "name":          key,
            "score_10":      score_10,
            "score":         round(score_10 * 10),
            "weight":        weight,
            "weight_frac":   weight / 100.0,
            "anchor_band":   band,
            "anchor_text":   anchor_txt,
            "justification": justification,
            "evidence":      evidence_level,
            "evidence_req":  crit.get("evidence_required", ""),
            "red_flags":     red_flags,
            "sub_factors":   crit.get("sub_factors", []),
        }

    total_w = sum(v["weight_frac"] for v in scored_criteria.values())
    overall = round(
        sum(v["score"] * v["weight_frac"] for v in scored_criteria.values()) / max(total_w, 0.01),
        1,
    )
    overall = min(overall, 100.0)

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


def route_scoring(submission, rubric_data):
    """
    Route scoring to either the real LLM or the simulated engine based on
    st.session_state.scoring_mode. Returns (score_dict, warning_str_or_None).
    warning_str is non-None when Real LLM was requested but fell back to Simulated.
    """
    mode = st.session_state.get("scoring_mode", "Simulated")
    if mode == "Real LLM":
        if not _llm_ready():
            return ai_score_submission(submission, rubric_data), "No API key available — fell back to Simulated scoring."
        try:
            result = ai_score_submission_llm(submission, rubric_data)
            return result, None
        except Exception as e:
            return ai_score_submission(submission, rubric_data), f"LLM error ({e}) — fell back to Simulated scoring."
    return ai_score_submission(submission, rubric_data), None


def generate_stage_summary(submission, new_stage):
    """
    Generate a rich, physical-goods-specific HTML stage summary.
    Product type is inferred from the submission name; all content is
    pre-computed so no backslash escapes appear inside f-string expressions.
    """
    name  = submission.get("name", "this idea")
    nl    = name.lower()

    # ── Product-type detection ─────────────────────────────────────────────────
    is_bio     = any(w in nl for w in ["bio", "mycelium", "compost", "organic", "plant", "hemp"])
    is_carbon  = any(w in nl for w in ["carbon", "fibre", "fiber", "graphene"])
    is_polymer = any(w in nl for w in ["polymer", "coating", "composite", "resin", "foam", "panel"])
    is_mech    = any(w in nl for w in ["motor", "drive", "exoskeleton", "frame", "actuator", "gear"])
    is_thermal = any(w in nl for w in ["thermal", "insulation", "heat", "cooling", "regulator"])
    is_pack    = any(w in nl for w in ["packaging", "pack", "wrap", "container", "pouch"])
    is_wear    = any(w in nl for w in ["sleeve", "compression", "garment", "textile", "wearable"])
    is_smart   = any(w in nl for w in ["smart", "sensor", "iot", "connected", "digital", "electronic"])

    # ── Material / commercial context ─────────────────────────────────────────
    if is_bio:
        mat1     = "Mycelium composite (Ecovative-spec substrate)"
        mat2     = "Recycled PLA structural reinforcement"
        mfg      = "Compression moulding with biodegradable release agents"
        bom      = "$4–$9 per unit at 5K MOQ"
        retail   = "$18–$35 DTC / $10–$18 wholesale"
        r_tech   = "Medium"
        r_reg    = "Low (food-contact cert. if applicable)"
        r_mkt    = "Medium — consumer education required on novel materials"
        kpis     = ["Biodegradation rate (days)", "Compressive strength (kPa)", "Customer NPS"]
        sup_list = ["Ecovative Design", "Mogu S.r.l.", "BioFab"]
    elif is_carbon or is_polymer:
        mat1     = "High-performance polymer alloy (PEEK/PA66 blend)"
        mat2     = "UD carbon-fibre prepreg (T300 grade)"
        mfg      = "Autoclave cure + CNC post-processing for tight tolerances"
        bom      = "$18–$38 per unit at 2K MOQ"
        retail   = "$75–$180 B2B / OEM channel"
        r_tech   = "High — thermal cycling and UV degradation testing required"
        r_reg    = "Medium — REACH compliance, RoHS if electronic"
        r_mkt    = "Low — industrial buyers are specification-driven"
        kpis     = ["Tensile strength vs spec", "Surface defect rate (%)", "B2B reorder rate"]
        sup_list = ["Toray Industries", "Solvay", "Hexcel"]
    elif is_mech:
        mat1     = "Aerospace-grade Al 6061-T6 billet"
        mat2     = "Carbon-fibre composite structural panels"
        mfg      = "CNC machining + die-casting; anodised finish"
        bom      = "$25–$55 per unit at 1K MOQ"
        retail   = "$120–$280 direct + distributor"
        r_tech   = "High — dynamic load, fatigue, and drop-test certification required"
        r_reg    = "Medium — CE marking / UL for mechatronic variants"
        r_mkt    = "Medium — OEM partnerships accelerate channel velocity"
        kpis     = ["Mean cycles to failure", "Assembly defect rate (%)", "On-time delivery %"]
        sup_list = ["Protocase", "Xometry", "Fictiv"]
    elif is_thermal:
        mat1     = "Aerogel-reinforced silica blanket (10mm)"
        mat2     = "Vacuum-insulated panel (VIP) core option"
        mfg      = "Lamination + die-cutting with sealed edge processing"
        bom      = "$9–$22 per unit at 3K MOQ"
        retail   = "$40–$95 DTC; $22–$50 wholesale"
        r_tech   = "Medium — moisture ingress and thermal cycling required"
        r_reg    = "Low — confirm UL 94 flammability rating"
        r_mkt    = "Medium — technical sell requires performance data sheets"
        kpis     = ["Thermal resistance (R-value)", "Moisture ingress rate", "Field failure rate"]
        sup_list = ["Cabot Corporation", "Evonik", "Kingspan Group"]
    elif is_pack:
        mat1     = "Cellulose-based moulded fibre (recycled content)"
        mat2     = "PHA bioplastic barrier coating"
        mfg      = "Wet-press moulded fibre + inline PHA spray coating"
        bom      = "$0.45–$1.40 per unit at 50K MOQ"
        retail   = "$2.20–$4.80 wholesale to brand customers"
        r_tech   = "Low — key risk is moisture-barrier performance spec"
        r_reg    = "Low — confirm EN 13432 / ASTM D6400 compostability"
        r_mkt    = "Low — strong regulatory tailwinds (SUP Directive, plastic bans)"
        kpis     = ["WVTR (g/m²/day)", "Unit cost vs virgin plastic", "Brand customer LTV"]
        sup_list = ["Huhtamaki", "Sealed Air", "Smurfit Kappa"]
    elif is_wear:
        mat1     = "Medical-grade 70D nylon/elastane knit (CE Class I)"
        mat2     = "Silicone grip bead strips"
        mfg      = "Cut-and-sew flatlock seaming; ultrasonic bonding option"
        bom      = "$6–$14 per unit at 5K MOQ"
        retail   = "$39–$89 DTC; $22–$45 wholesale"
        r_tech   = "Low — main risk is sizing accuracy across segments"
        r_reg    = "Medium — CE Class I MDR 2017/745 if medical claims made"
        r_mkt    = "Medium — DTC channel requires clinical claims or influencer evidence"
        kpis     = ["Return rate by size band", "NPS", "Reorder rate at 90 days"]
        sup_list = ["Sanfori", "Amann Group", "Coats plc"]
    elif is_smart:
        mat1     = "PCB assembly (4-layer, 35μm copper, FR4 substrate)"
        mat2     = "Polycarbonate IP65 enclosure"
        mfg      = "SMT PCBA + injection-moulded housing + firmware flash and test"
        bom      = "$20–$48 per unit at 2K MOQ"
        retail   = "$89–$199 DTC; $45–$95 OEM"
        r_tech   = "High — EMC (CE/FCC), battery safety (UN38.3) required"
        r_reg    = "High — CE mandatory; FCC ID for US; UKCA post-Brexit"
        r_mkt    = "Medium — SaaS/platform revenue model improves LTV significantly"
        kpis     = ["Device uptime (%)", "MTBF (hours)", "MRR growth"]
        sup_list = ["JLCPCB", "PCBWay", "Foxconn"]
    else:
        mat1     = "Primary material TBD — pending Validation review"
        mat2     = "Secondary reinforcement TBD"
        mfg      = "Manufacturing process to be determined post feasibility review"
        bom      = "TBD — cost modelling scheduled for Validation"
        retail   = "TBD"
        r_tech   = "TBD"
        r_reg    = "TBD"
        r_mkt    = "TBD"
        kpis     = ["Core product KPI", "Quality metric", "Commercial metric"]
        sup_list = ["Suppliers to be sourced at Validation"]

    sup1 = sup_list[0]
    sup2 = sup_list[1] if len(sup_list) > 1 else "TBD"
    kpi1 = kpis[0]
    kpi2 = kpis[1] if len(kpis) > 1 else "Quality metric"
    kpi3 = kpis[2] if len(kpis) > 2 else "Commercial metric"
    mat1_short = mat1.split("(")[0].strip()
    mat2_short = mat2.split("(")[0].strip()

    seed = int(hashlib.md5((name + new_stage).encode()).hexdigest()[:8], 16)
    rng  = random.Random(seed)

    # ── HTML building helpers (inline styles only) ────────────────────────────
    def bul(items, color="#58a6ff"):
        parts = []
        for item in items:
            parts.append(
                f'<div style="font-size:11px;color:#b0b8c4;line-height:1.75;">'
                f'<span style="color:{color};">▸</span> {item}</div>'
            )
        return "".join(parts)

    def sec(title, body):
        return (
            f'<div style="margin-bottom:10px;">'
            f'<div style="font-size:9px;text-transform:uppercase;letter-spacing:0.1em;'
            f'color:#8b949e;font-weight:700;margin-bottom:5px;">{title}</div>'
            f'{body}'
            f'</div>'
        )

    def kv(label, val):
        return (
            f'<div style="font-size:11px;color:#b0b8c4;margin-bottom:3px;">'
            f'<span style="color:#8b949e;">{label}:</span> <b style="color:#e6edf3;">{val}</b></div>'
        )

    footer_style = (
        'style="font-size:10px;color:#6e7681;border-top:1px solid #21262d44;'
        'padding-top:6px;margin-top:6px;"'
    )

    # ── Per-stage templates (2 variants, seeded pick) ─────────────────────────
    CONCEPT = [
        sec("Refined Product Specification v0.1",
            kv("Concept", name)
            + kv("Primary material", mat1)
            + kv("Secondary", mat2)
            + kv("Manufacturing process", mfg)
            + kv("Unit cost target", bom))
        + sec("Key Design Decisions", bul([
            "Lock in differentiated feature set before IP filing window closes",
            "Confirm material supply chain depth with 2+ qualified vendors",
            f"Commission DFM review from {sup1} or equivalent contract manufacturer",
            "Benchmark vs top 3 competitors: pricing, performance, sustainability",
        ]))
        + f'<div {footer_style}>Next gate: Concept review + rubric re-score in 14 days</div>',

        sec("Material & Process Rationale",
            kv("Primary", mat1)
            + kv("Secondary", mat2)
            + kv("Process", mfg)
            + kv("BOM target", bom))
        + sec("Initial Design Direction", bul([
            f"Form factor: compact, production-ready, optimised for {mfg.split('+')[0].strip().lower()}",
            "Finish: premium industrial aesthetic — anodised / matte / textured",
            "Key interaction: single-touch / tool-free / zero-waste assembly principle",
            "IP note: provisional patent application recommended within 30 days",
        ], color="#3fb950"))
        + f'<div {footer_style}>Next gate: Concept review + rubric re-score in 14 days</div>',
    ]

    VALIDATION = [
        sec("Risk Analysis",
            kv("Technical risk", r_tech)
            + kv("Regulatory risk", r_reg)
            + kv("Market risk", r_mkt))
        + sec("Feasibility Summary", bul([
            f"Manufacturing process: {mfg}",
            f"Indicative BOM: {bom}",
            f"Target retail: {retail}",
            "First-article lead time: 8–12 weeks from tooling sign-off",
            f"Primary supplier candidate: {sup1}",
        ]))
        + sec("Validation Sprint — 4 Weeks", bul([
            f"Week 1–2: BOM costing with {sup1} and {sup2} (RFQs issued)",
            "Week 2–3: Customer discovery — 10 B2B decision-maker interviews",
            "Week 3–4: Regulatory pathway mapping + compliance counsel brief",
        ], color="#d29922"))
        + f'<div {footer_style}>Gate criteria: BOM within 15% of model · 8+ positive customer interviews</div>',

        sec("Technical Feasibility Report", bul([
            f"Core material: {mat1}",
            f"Process: {mfg}",
            f"Technical risk: {r_tech}",
            f"First-article cost estimate commissioned from {sup1}",
        ]))
        + sec("Market Validation Plan", bul([
            "Target: 10 structured interviews with procurement / R&D decision-makers",
            f"Pricing hypothesis: {retail}",
            "Key probe: willingness to pay vs incumbent solution price point",
            f"Regulatory path: {r_reg}",
        ]))
        + f'<div {footer_style}>Gate criteria: BOM within 15% of model · 8+ positive customer interviews</div>',
    ]

    PROTOTYPING = [
        sec("Bill of Materials — Draft v0.1", bul([
            f"[01] {mat1_short} — bulk pricing from {sup1}",
            f"[02] {mat2_short} — RFQ issued to {sup2}",
            "[03] Tooling and fixturing — amortised over 5K+ units",
            "[04] Assembly labour — CMO rate TBD (target: below 20% of BOM)",
            f"[05] Packaging — included in BOM target of {bom}",
            "[06] QC testing per unit — est. $0.50–$1.50",
        ]))
        + sec("Prototype Milestones", bul([
            "Week 1–2: CAD finalisation + DFM sign-off with CMO",
            "Week 3–4: Tooling order placed; first-article by Week 6",
            "Week 5–6: Functional prototype build + internal performance test",
            "Week 7–8: User testing cohort (n=12) + design iteration",
            "Week 9: Go/no-go gate review with updated rubric score",
        ], color="#3fb950"))
        + f'<div {footer_style}>Manufacturing partner shortlisted: {sup1}</div>',

        sec("Prototyping Plan", bul([
            f"Process: {mfg}",
            f"CMO shortlist: {sup1} (primary), {sup2} (backup)",
            "Target: 3 functional prototypes + 5 for user testing cohort",
            f"BOM target: {bom}",
            "Critical path: tooling lead time typically 6–10 weeks",
        ]))
        + sec("Testing Protocol", bul([
            "Performance: validate vs rubric scoring anchor specifications",
            "Durability: 500-cycle accelerated life test (IEC 60068 reference)",
            f"Regulatory pre-screen: {r_reg}",
            "User sessions: structured 45-min tests with 12 target customers",
        ], color="#d29922"))
        + f'<div {footer_style}>Gate criteria: prototype meets spec · user NPS at or above 45</div>',
    ]

    MARKET_TEST = [
        sec("Go-to-Market Outline", bul([
            "Channel 1: DTC e-commerce (Shopify) — hero SKU only for focus",
            "Channel 2: 1 regional distributor for B2B / trade pilot",
            "Launch geography: UK + DACH (EU regulatory alignment)",
            "Launch cohort: 50 beta customers from validated discovery pool",
        ]))
        + sec("Pricing Strategy", bul([
            f"Anchor price: {retail}",
            "Approach: value-based — benchmark vs incumbent at 1.3x premium",
            "A/B test: premium vs value positioning in paid acquisition",
            f"Gross margin at {bom}: target 55–65% DTC / 40–50% wholesale",
        ], color="#d29922"))
        + sec("Target Customer Profile", bul([
            "Primary: procurement leads at mid-market manufacturers (50–500 employees)",
            "Secondary: DTC early adopters in sustainability / performance segment",
            "Core pain point: current solutions fail on performance, cost, or sustainability",
        ]))
        + f'<div {footer_style}>Gate: 8-week sell-through at or above 60% · NPS at or above 45 · CAC within model</div>',

        sec("Launch Playbook", bul([
            f"Hero SKU: {name} — single variant for market focus",
            f"Price point: {retail} — tested and validated with beta cohort",
            "Acquisition: paid search + LinkedIn (B2B) + partner referral programme",
            "Week 1–2: soft launch to beta list; Week 3+: paid channels fully live",
        ]))
        + sec("Commercial Assumptions", bul([
            f"BOM at launch: {bom}",
            "Gross margin target: 55–65% DTC / 40–50% wholesale",
            "CAC budget: 15–20% of first-year estimated LTV",
            "Payback period target: 9 months or less",
        ], color="#3fb950"))
        + f'<div {footer_style}>Gate: 8-week sell-through at or above 60% · NPS at or above 45 · CAC within model</div>',
    ]

    SCALING = [
        sec("Supply Chain Plan", bul([
            f"Tier 1 CMO: {sup1} — primary, 70% of volume commitment",
            f"Tier 2 backup: {sup2} — 30% or overflow (dual-source strategy active)",
            "Safety stock: 8 weeks forward cover at rolling forecast volume",
            "Incoterms: DAP — landed cost fully included in margin model",
            "Sea freight lead time: 10–14 weeks farm-to-warehouse",
        ]))
        + sec("Volume Cost Model", bul([
            f"Unit BOM at 10K MOQ: {bom}",
            f"Target retail: {retail}",
            "Logistics and duty: estimated 8–12% of landed cost",
            "Gross margin at scale: 58–68% DTC / 42–52% wholesale",
            "Breakeven volume: modelled at 3.5K units per month",
        ], color="#3fb950"))
        + f'<div {footer_style}>QMS: ISO 9001 scope extension filed; 3 inline QC checkpoints active</div>',

        sec("Manufacturing Scale-Up", bul([
            f"Primary CMO: {sup1} — NDA and quality agreement signed",
            f"Process: {mfg}",
            "Production ramp: 1K to 5K to 15K units over 3 quarters",
            "Tooling investment amortised over 12 months at forecast volume",
        ]))
        + sec("Operational Priorities", bul([
            "QMS: 8 inline inspection points defined and staffed",
            "Compliance: all certifications confirmed before channel expansion",
            "Inventory: demand-driven replenishment model activated",
            "Channel: 3 new distributors contracted for Q2 rollout",
        ], color="#58a6ff"))
        + f'<div {footer_style}>QMS: ISO 9001 scope extension filed; 3 inline QC checkpoints active</div>',
    ]

    MONITORING = [
        sec("KPI Dashboard — Live Tracking", bul([
            f"Product: {kpi1} — weekly vs baseline target",
            f"Quality: {kpi2} — automated alert if threshold breached",
            f"Commercial: {kpi3} — cohort analysis run monthly",
            "Return rate: target below 2.5%; triggers engineering review above 4%",
            "NPS: monthly pulse survey; target score at or above 50",
            "Gross margin: weekly P&L reviewed vs model",
        ]))
        + sec("90-Day Review Framework", bul([
            "Day 30: first commercial report — sell-through, returns, NPS baseline",
            "Day 60: product council review — improvement backlog prioritised",
            "Day 90: full P&L vs model; go/no-go for next-gen variant scoping",
        ], color="#3fb950"))
        + f'<div {footer_style}>V2 concept exploration scoped for month 4; innovation team briefed</div>',

        sec("Post-Launch Improvement Roadmap", bul([
            "Sprint 1 (month 1): resolve top 3 issues from beta customer feedback",
            "Sprint 2 (month 2): packaging cost optimisation — target 8% reduction",
            f"Sprint 3 (month 3): premium variant scoping for {name} V2",
            "Month 4: innovation brief to pipeline team for next-gen concept",
        ]))
        + sec("Live Metrics", bul([
            f"Tracking: {kpi1}, {kpi2}, {kpi3}",
            "Alert thresholds set in ops dashboard",
            "Weekly ops standup: return rate, NPS, gross margin reviewed",
            "Customer feedback loop: support tickets + quarterly user panel",
        ], color="#58a6ff"))
        + f'<div {footer_style}>V2 concept exploration scoped for month 4; innovation team briefed</div>',
    ]

    INTAKE_FALLBACK = [
        f'<div style="font-size:11px;color:#b0b8c4;">'
        f'{name} returned to Intake for re-assessment. '
        f'Assign a stage owner and complete the rubric scoring checklist before re-advancing.</div>'
    ]

    template_map = {
        "Concept":     CONCEPT,
        "Validation":  VALIDATION,
        "Prototyping": PROTOTYPING,
        "Market Test": MARKET_TEST,
        "Scaling":     SCALING,
        "Monitoring":  MONITORING,
    }

    options = template_map.get(new_stage, INTAKE_FALLBACK)
    return rng.choice(options)

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
        base_dt  = datetime.now() - timedelta(days=days_ago)
        # Build stage history: one entry per stage up to the current one
        history = []
        for sn in STAGE_NAMES:
            entry_dt = base_dt + timedelta(days=STAGE_NAMES.index(sn) * 3)
            history.append({"stage": sn, "moved_at": entry_dt.strftime("%Y-%m-%d")})
            if sn == stage:
                break
        st.session_state.submissions.append({
            "id":             sid,
            "name":           name,
            "file_type":      ftype,
            "status":         status,
            "stage":          stage,
            "overall":        scores["overall"],
            "innovation":     scores["innovation"],
            "feasibility":    scores["feasibility"],
            "categories":     scores["categories"],
            "auto_reject":    scores.get("auto_reject", []),
            "high_risk":      scores.get("high_risk", []),
            "scored_at":      scores.get("scored_at", ""),
            "stage_summary":  generate_stage_summary({"name": name, "overall": scores["overall"]}, stage) if stage != "Intake" else "",
            "stage_history":  history,
            "extracted_text": "",
            "submitted_at":  base_dt.strftime("%Y-%m-%d"),
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
        <div style="font-size:11px;font-weight:600;color:#8b949e;">ForgeOS v0.2</div>
        <div style="font-size:10px;color:#6e7681;margin-top:2px;">Day 2 Polish · AI Scoring Engine</div>
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

    # ── Flash message ─────────────────────────────────────────────────────────
    if st.session_state.flash_msg:
        ftype, fmsg = st.session_state.flash_msg
        st.session_state.flash_msg = None
        if ftype == "success":
            st.success(fmsg)
        elif ftype == "info":
            st.info(fmsg)
        elif ftype == "warning":
            st.warning(fmsg)
        else:
            st.error(fmsg)

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
                extracted = ""
                if uploaded:
                    with st.spinner("Extracting file content…"):
                        extracted = extract_file_text(uploaded)
                sid = f"FOS-{st.session_state.next_id}"
                st.session_state.next_id += 1
                st.session_state.submissions.append({
                    "id":             sid,
                    "name":           idea_name.strip(),
                    "file_type":      ", ".join(ftypes),
                    "status":         "New",
                    "stage":          init_stage,
                    "overall":        0.0,
                    "innovation":     0.0,
                    "feasibility":    0.0,
                    "categories":     {},
                    "auto_reject":    [],
                    "high_risk":      [],
                    "scored_at":      "",
                    "stage_summary":  "",
                    "stage_history":  [{"stage": init_stage, "moved_at": datetime.now().strftime("%Y-%m-%d")}],
                    "submitted_at":   datetime.now().strftime("%Y-%m-%d"),
                    "notes":          notes_txt,
                    "extracted_text": extracted,
                })
                file_note = f" ({len(uploaded)} file(s) processed)" if uploaded else ""
                st.success(f"Submission {sid} added{file_note}.")
                st.rerun()

    # ── Toolbar ───────────────────────────────────────────────────────────────
    if st.session_state.submissions:
        tb1, tb2, tb3, tb4, tb5, tb6 = st.columns([3, 1.5, 1.5, 1.2, 1.1, 1.8])
        with tb1:
            search_q = st.text_input("search", placeholder="Search by name or ID…", label_visibility="collapsed")
        with tb2:
            f_status = st.selectbox("st", ["All Statuses","New","Scored","In Review","Approved","Rejected"], label_visibility="collapsed")
        with tb3:
            f_stage  = st.selectbox("sg", ["All Stages"] + STAGE_NAMES, label_visibility="collapsed")
        with tb4:
            f_sort   = st.selectbox("sort", ["Newest","Score ↓","Score ↑","Name"], label_visibility="collapsed")
        with tb5:
            bulk_concurrency = st.number_input(
                "concurrency",
                min_value=1,
                max_value=10,
                value=st.session_state.get("bulk_concurrency", 5),
                step=1,
                label_visibility="collapsed",
                help="Number of submissions scored simultaneously. Higher = faster, but raises rate-limit risk with Real LLM mode.",
                key="bulk_concurrency",
            )
        with tb6:
            run_bulk = st.button("🤖  Process All with AI", use_container_width=True)

        if run_bulk:
            unscored = [s for s in st.session_state.submissions if s["status"] == "New"]
            if unscored:
                # ── Snapshot ALL config before spawning threads ─────────────────
                # Workers must never read st.session_state — pass everything in.
                mode_label = st.session_state.get("scoring_mode", "Simulated")
                is_llm     = mode_label == "Real LLM"
                snap_key   = _effective_llm_key() if is_llm else ""
                snap_url   = _FORGE_LLM_BASE_URL
                snap_model = _FORGE_LLM_MODEL
                rubric_snap = rubric   # plain dict — safe to read across threads

                # Use user-selected concurrency limit, capped at the number of unscored items
                user_concurrency = int(st.session_state.get("bulk_concurrency", 5))
                max_workers = min(user_concurrency, len(unscored))
                n           = len(unscored)

                # ── Live display slots ──────────────────────────────────────────
                prog_bar    = st.progress(0.0)
                status_slot = st.empty()

                # ── Thread-safe in-flight tracking ──────────────────────────────
                # active_ids: IDs whose worker is currently executing (not queued)
                active_ids  = set()
                active_lock = threading.Lock()

                # stop_event: set by the first worker that hits a 429/rate-limit;
                # subsequent workers check this before making their LLM call and
                # fall back to Simulated instead, preserving score quality semantics.
                stop_event  = threading.Event()

                def _score_worker_pure(sub, rubric_data, mode, api_key, base_url, model):
                    """
                    Pure worker: all config passed in — no st.session_state access.
                    Returns (sub_id, score_dict, warning_str_or_None, is_rate_limit).
                    """
                    sub_id = sub["id"]
                    with active_lock:
                        active_ids.add(sub_id)
                    try:
                        if mode == "Real LLM":
                            # Rate-limit gate: if another worker already hit 429,
                            # use Simulated immediately rather than hammering the API.
                            if stop_event.is_set():
                                sc = ai_score_submission(sub, rubric_data)
                                return sub_id, sc, None, False
                            if not api_key:
                                sc = ai_score_submission(sub, rubric_data)
                                return sub_id, sc, "No API key — used Simulated fallback.", False
                            try:
                                sc = _ai_score_llm_pure(sub, rubric_data, api_key, base_url, model)
                                return sub_id, sc, None, False
                            except RuntimeError as exc:
                                warn = str(exc)
                                is_rate = ("429" in warn or "rate" in warn.lower())
                                if is_rate:
                                    stop_event.set()   # signal all other workers
                                sc = ai_score_submission(sub, rubric_data)
                                return sub_id, sc, warn, is_rate
                        else:
                            time.sleep(0.3)   # brief stagger for Simulated visual effect
                            sc = ai_score_submission(sub, rubric_data)
                            return sub_id, sc, None, False
                    finally:
                        with active_lock:
                            active_ids.discard(sub_id)

                id_to_name       = {sub["id"]: sub["name"] for sub in unscored}
                llm_warns        = []
                completed        = 0
                rate_limit_hits  = 0

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_id = {
                        executor.submit(
                            _score_worker_pure,
                            sub, rubric_snap, mode_label, snap_key, snap_url, snap_model,
                        ): sub["id"]
                        for sub in unscored
                    }

                    for future in as_completed(future_to_id):
                        # Cancelled futures (from stop_event path) raise CancelledError
                        try:
                            sub_id, sc, warn, is_rate = future.result()
                        except Exception:
                            # Will be picked up in the sequential fallback below
                            continue

                        if is_rate:
                            rate_limit_hits += 1
                            # Cancel any futures still queued (not yet started)
                            for f in future_to_id:
                                if not f.running() and not f.done():
                                    f.cancel()

                        # ── Session state update — main thread only ────────────
                        idx = next(
                            j for j, s in enumerate(st.session_state.submissions)
                            if s["id"] == sub_id
                        )
                        st.session_state.submissions[idx].update({
                            "overall":     sc["overall"],
                            "innovation":  sc["innovation"],
                            "feasibility": sc["feasibility"],
                            "categories":  sc["categories"],
                            "auto_reject": sc["auto_reject"],
                            "high_risk":   sc["high_risk"],
                            "scored_at":   sc["scored_at"],
                            "status":      "Scored",
                        })
                        if warn:
                            llm_warns.append(warn)

                        completed += 1
                        prog_bar.progress(completed / n)

                        # ── Live status: accurately read in-flight IDs ─────────
                        done_name = id_to_name[sub_id]
                        with active_lock:
                            currently_active = set(active_ids)
                        in_flight = [id_to_name[i] for i in currently_active if i in id_to_name]
                        flight_html = ""
                        if in_flight:
                            names_str   = ", ".join(f"<em>{nm}</em>" for nm in in_flight[:4])
                            more        = f" +{len(in_flight)-4} more" if len(in_flight) > 4 else ""
                            flight_html = f'<span style="color:#6e7681;"> · in-flight: {names_str}{more}</span>'
                        status_slot.markdown(
                            f'<div style="font-size:12px;color:#3fb950;padding:4px 0;">'
                            f'✓ <strong style="color:#e6edf3">{done_name}</strong> scored '
                            f'<span style="color:#8b949e;">({completed}/{n})</span>'
                            f'{flight_html}</div>',
                            unsafe_allow_html=True,
                        )

                # ── Sequential fallback for any still-New after rate-limit ──────
                still_new = [s for s in st.session_state.submissions if s["status"] == "New"]
                if still_new:
                    status_slot.markdown(
                        f'<div style="font-size:12px;color:#d29922;padding:4px 0;">'
                        f'⚠ Rate limit hit — finishing {len(still_new)} remaining idea(s) sequentially '
                        f'with Simulated scoring…</div>',
                        unsafe_allow_html=True,
                    )
                    for sub in still_new:
                        sc = ai_score_submission(sub, rubric_snap)
                        idx = next(
                            j for j, s in enumerate(st.session_state.submissions)
                            if s["id"] == sub["id"]
                        )
                        st.session_state.submissions[idx].update({
                            "overall":     sc["overall"],
                            "innovation":  sc["innovation"],
                            "feasibility": sc["feasibility"],
                            "categories":  sc["categories"],
                            "auto_reject": sc["auto_reject"],
                            "high_risk":   sc["high_risk"],
                            "scored_at":   sc["scored_at"],
                            "status":      "Scored",
                        })
                        completed += 1
                        prog_bar.progress(completed / n)

                # ── Summary ────────────────────────────────────────────────────
                status_slot.empty()
                prog_bar.progress(1.0)
                if rate_limit_hits:
                    st.warning(
                        f"{rate_limit_hits} API call(s) hit rate limits — those ideas were scored "
                        "with Simulated fallback. Remaining ideas were processed sequentially. "
                        "Try a smaller batch or wait before re-running.",
                        icon="⚠️",
                    )
                elif llm_warns:
                    st.warning(llm_warns[0], icon="⚠️")
                n_reject       = sum(1 for s in st.session_state.submissions if s.get("auto_reject"))
                parallel_note  = f" ({max_workers} concurrent)" if max_workers > 1 else ""
                st.success(
                    f"Scored {n} submission(s){parallel_note}. "
                    f"{n_reject} triggered auto-reject gates."
                )
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

        hd = st.columns([1.1, 3.2, 1.0, 1.0, 1.0, 1.4, 1.5, 1.5, 2.8])
        for col, label in zip(hd, ["ID","Idea Name","Overall","Innov.","Feas.","Status","AI Badge","Stage","Actions"]):
            col.markdown(f'<span style="font-size:11px;text-transform:uppercase;letter-spacing:0.06em;color:#8b949e;font-weight:600;">{label}</span>', unsafe_allow_html=True)

        st.markdown("<hr style='margin:6px 0 0 0'>", unsafe_allow_html=True)

        for sub in visible:
            row = st.columns([1.1, 3.2, 1.0, 1.0, 1.0, 1.4, 1.5, 1.5, 2.8])

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
                blabel, bcolor, bbg = forge_badge(sub)
                if blabel:
                    st.markdown(
                        f'<span style="font-size:10px;font-weight:700;color:{bcolor};'
                        f'background:{bbg};border:1px solid {bcolor}44;'
                        f'border-radius:4px;padding:2px 7px;white-space:nowrap;">'
                        f'{blabel}</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown('<span style="color:#6e7681;font-size:12px;">—</span>', unsafe_allow_html=True)

            with row[7]:
                sc = next((s["color"] for s in STAGES if s["name"] == sub["stage"]), "#8b949e")
                st.markdown(f'<span style="font-size:11px;font-weight:600;color:{sc};">● {sub["stage"]}</span>', unsafe_allow_html=True)

            with row[8]:
                a1, a2, a3 = st.columns(3)
                with a1:
                    if st.button("Score", key=f"sc_{sub['id']}"):
                        mode_label = st.session_state.get("scoring_mode", "Simulated")
                        spinner_txt = f"Scoring using ForgeOS Extensive Rubric v2 ({mode_label})…"
                        with st.spinner(spinner_txt):
                            if mode_label == "Simulated":
                                time.sleep(0.8)
                            sc2, warn2 = route_scoring(sub, rubric)
                            idx = next(i for i, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                            st.session_state.submissions[idx].update({
                                "overall":     sc2["overall"],
                                "innovation":  sc2["innovation"],
                                "feasibility": sc2["feasibility"],
                                "categories":  sc2["categories"],
                                "auto_reject": sc2["auto_reject"],
                                "high_risk":   sc2["high_risk"],
                                "scored_at":   sc2["scored_at"],
                                "status":      "Scored",
                            })
                            gate_note = " · Auto-Reject gate triggered" if sc2["auto_reject"] else (" · High-Risk flag raised" if sc2["high_risk"] else "")
                            fallback_note = f" · ⚠ {warn2}" if warn2 else ""
                            st.session_state.flash_msg = ("success", f"Scored '{sub['name']}' — Overall: {sc2['overall']}/100{gate_note}{fallback_note}")
                            st.rerun()
                with a2:
                    cur_stage_idx = STAGE_NAMES.index(sub["stage"]) if sub["stage"] in STAGE_NAMES else -1
                    at_last = cur_stage_idx >= len(STAGE_NAMES) - 1
                    if st.button("Advance", key=f"adv_{sub['id']}", disabled=at_last):
                        new_stage = STAGE_NAMES[cur_stage_idx + 1]
                        with st.spinner(f"Advancing '{sub['name']}' to {new_stage}…"):
                            time.sleep(0.5)
                            idx     = next(i for i, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                            summary = generate_stage_summary(st.session_state.submissions[idx], new_stage)
                            hist    = st.session_state.submissions[idx].get("stage_history", [])
                            hist.append({"stage": new_stage, "moved_at": datetime.now().strftime("%Y-%m-%d")})
                            st.session_state.submissions[idx]["stage"]         = new_stage
                            st.session_state.submissions[idx]["stage_summary"] = summary
                            st.session_state.submissions[idx]["stage_history"] = hist
                            st.session_state.flash_msg = ("info", f"'{sub['name']}' advanced to {new_stage} — AI stage brief generated")
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

                    # ── Stage history timeline ────────────────────────────────
                    hist = sub.get("stage_history", [])
                    if hist:
                        dots = ""
                        for i, entry in enumerate(hist):
                            is_current = (entry["stage"] == sub["stage"])
                            sc_clr = next((s["color"] for s in STAGES if s["name"] == entry["stage"]), "#8b949e")
                            dot_clr = sc_clr if is_current else "#30363d"
                            txt_clr = sc_clr if is_current else "#6e7681"
                            fw  = "700" if is_current else "500"
                            connector = '<span style="color:#30363d;margin:0 4px;">→</span>' if i < len(hist) - 1 else ""
                            dots += (
                                f'<span style="font-size:11px;font-weight:{fw};color:{txt_clr};">'
                                f'<span style="color:{dot_clr};">●</span> {entry["stage"]}'
                                f'<span style="font-size:9px;color:#6e7681;margin-left:4px;">{entry["moved_at"]}</span>'
                                f'</span>{connector}'
                            )
                        st.markdown(f"""
                        <div style="background:#0d1117;border:1px solid #21262d;border-radius:8px;
                                    padding:10px 16px;margin-bottom:12px;overflow-x:auto;white-space:nowrap;">
                          <div style="font-size:10px;font-weight:700;color:#8b949e;
                                      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">
                            Stage History</div>
                          <div>{dots}</div>
                        </div>""", unsafe_allow_html=True)

                    # ── Stage summary ────────────────────────────────────────
                    summ = sub.get("stage_summary", "")
                    if summ:
                        st.markdown(f"""
                        <div style="background:#0c1e35;border:1px solid #1f6feb44;border-radius:8px;
                                    padding:12px 16px;margin-bottom:16px;">
                          <div style="font-size:10px;font-weight:700;color:#58a6ff;
                                      text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">
                            AI Stage Note — {sub['stage']}</div>
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

    # ── Flash message ─────────────────────────────────────────────────────────
    if st.session_state.flash_msg:
        ftype, fmsg = st.session_state.flash_msg
        st.session_state.flash_msg = None
        if ftype == "success":
            st.success(fmsg)
        elif ftype == "info":
            st.info(fmsg)
        elif ftype == "warning":
            st.warning(fmsg)
        else:
            st.error(fmsg)

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
                    score_badge_html = ""
                    if sub["overall"] > 0:
                        bc = score_badge_class(sub["overall"])
                        score_badge_html = f'<span class="badge-score {bc}" style="font-size:10px;">{sub["overall"]}</span>'
                    pc = pill_class(sub["status"])
                    blabel, bcolor, bbg = forge_badge(sub)
                    fb_html = ""
                    if blabel:
                        fb_html = (
                            f'<span style="font-size:9px;font-weight:700;color:{bcolor};'
                            f'background:{bbg};border:1px solid {bcolor}44;'
                            f'border-radius:3px;padding:1px 5px;margin-left:4px;">'
                            f'{blabel}</span>'
                        )

                    st.markdown(f"""
                    <div class="kanban-card">
                        <div class="kanban-card-title">{sub['name']}</div>
                        <div class="kanban-card-meta" style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;">
                            <span class="forge-id" style="font-size:10px;">{sub['id']}</span>
                            {score_badge_html}{fb_html}
                        </div>
                        <div style="margin-top:6px;">
                            <span class="pill {pc}" style="font-size:10px;">{sub['status']}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)

                    # ── Inline action buttons ───────────────────────────────
                    cur_idx = STAGE_NAMES.index(sub["stage"]) if sub["stage"] in STAGE_NAMES else -1
                    at_last = cur_idx >= len(STAGE_NAMES) - 1
                    btn_score, btn_adv = st.columns(2)
                    with btn_score:
                        if st.button("Score", key=f"pipe_sc_{sub['id']}"):
                            mode_label = st.session_state.get("scoring_mode", "Simulated")
                            with st.spinner(f"Scoring using ForgeOS Extensive Rubric v2 ({mode_label})…"):
                                if mode_label == "Simulated":
                                    time.sleep(0.8)
                                sc2, warn2 = route_scoring(sub, rubric)
                                idx = next(i for i, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                                st.session_state.submissions[idx].update({
                                    "overall":     sc2["overall"],
                                    "innovation":  sc2["innovation"],
                                    "feasibility": sc2["feasibility"],
                                    "categories":  sc2["categories"],
                                    "auto_reject": sc2["auto_reject"],
                                    "high_risk":   sc2["high_risk"],
                                    "scored_at":   sc2["scored_at"],
                                    "status":      "Scored",
                                })
                                gate_note  = " · Auto-Reject gate triggered" if sc2["auto_reject"] else (" · High-Risk flag raised" if sc2["high_risk"] else "")
                                fallback_note = f" · ⚠ {warn2}" if warn2 else ""
                                st.session_state.flash_msg = ("success", f"Scored '{sub['name']}' — Overall: {sc2['overall']}/100{gate_note}{fallback_note}")
                                st.rerun()
                    with btn_adv:
                        if st.button("Advance →", key=f"pipe_adv_{sub['id']}", disabled=at_last):
                            new_stage = STAGE_NAMES[cur_idx + 1]
                            with st.spinner(f"Advancing '{sub['name']}' to {new_stage}…"):
                                time.sleep(0.5)
                                idx     = next(i for i, s in enumerate(st.session_state.submissions) if s["id"] == sub["id"])
                                summary = generate_stage_summary(st.session_state.submissions[idx], new_stage)
                                hist    = st.session_state.submissions[idx].get("stage_history", [])
                                hist.append({"stage": new_stage, "moved_at": datetime.now().strftime("%Y-%m-%d")})
                                st.session_state.submissions[idx]["stage"]         = new_stage
                                st.session_state.submissions[idx]["stage_summary"] = summary
                                st.session_state.submissions[idx]["stage_history"] = hist
                                st.session_state.flash_msg = ("info", f"'{sub['name']}' advanced to {new_stage} — AI stage brief generated")
                            st.rerun()
            else:
                st.markdown('<div class="kanban-empty">No ideas</div>', unsafe_allow_html=True)

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

        # ── Scoring Mode ──────────────────────────────────────────────────────
        st.markdown('<div class="section-hd">Scoring Mode</div>', unsafe_allow_html=True)

        # Determine key source so UI can react without rerunning
        _key_from_env     = bool(_FORGE_LLM_API_KEY)
        _key_from_session = bool(st.session_state.get("session_llm_key", "").strip())
        _key_available    = _key_from_env or _key_from_session

        # ── In-app API key entry (shown only when env var is absent) ───────────
        if not _key_from_env:
            _key_on_disk = bool(_load_saved_key())

            st.markdown("""
            <div style="background:#161b22;border:1px solid #21262d;border-radius:8px;
                        padding:14px 16px;margin-bottom:14px;">
              <div style="font-size:11px;font-weight:700;color:#8b949e;text-transform:uppercase;
                          letter-spacing:0.06em;margin-bottom:6px;">API Key</div>
              <div style="font-size:12px;color:#8b949e;margin-bottom:10px;">
                Paste an OpenAI-compatible API key to enable Real LLM scoring.
                Use <strong style="color:#e6edf3;">Save key</strong> to remember it across refreshes —
                it is stored in a local file on this server and never committed to version control.
                It is only sent to the configured LLM endpoint
                (<code style="color:#58a6ff;">api.x.ai/v1</code> by default).
              </div>
            </div>""", unsafe_allow_html=True)

            ki1, ki2 = st.columns([5, 1])
            with ki1:
                entered_key = st.text_input(
                    "API Key",
                    value=st.session_state.session_llm_key,
                    type="password",
                    placeholder="sk-… or xai-…",
                    label_visibility="collapsed",
                    help="OpenAI-compatible API key. Click 'Save key' to persist across refreshes.",
                )
            with ki2:
                save_clicked = st.button(
                    "Save key",
                    use_container_width=True,
                    disabled=not entered_key.strip(),
                    help="Write key to disk so it survives page refreshes.",
                )

            # Update session state when input changes
            if entered_key != st.session_state.session_llm_key:
                st.session_state.session_llm_key = entered_key.strip()
                _key_from_session = bool(st.session_state.session_llm_key)
                _key_available    = _key_from_session

            # Save to disk when button clicked
            if save_clicked and entered_key.strip():
                _save_key_to_disk(entered_key.strip())
                st.session_state.session_llm_key = entered_key.strip()
                _key_from_session = True
                _key_available    = True
                _key_on_disk      = True
                st.session_state.flash_msg = ("success", "API key saved — it will be remembered after page refresh.")
                st.rerun()

            # Status line + clear button
            if _key_from_session:
                key_preview = st.session_state.session_llm_key[:6] + "••••••••"
                persist_note = (
                    "saved to disk · survives refresh"
                    if _key_on_disk
                    else "session only · click Save key to persist"
                )
                st_row1, st_row2 = st.columns([4, 1])
                with st_row1:
                    st.markdown(
                        f'<div style="font-size:11px;color:#3fb950;margin-top:6px;">'
                        f'✓ Key active ({key_preview}) · {persist_note}</div>',
                        unsafe_allow_html=True,
                    )
                with st_row2:
                    if st.button("Clear", help="Remove key from memory and disk.", use_container_width=True):
                        _clear_saved_key()
                        st.session_state.session_llm_key = ""
                        st.session_state.scoring_mode    = "Simulated"
                        st.session_state.flash_msg = ("info", "API key cleared from memory and disk.")
                        st.rerun()
            else:
                st.markdown(
                    '<div style="font-size:11px;color:#6e7681;margin-top:4px;">'
                    'No key entered — Real LLM mode unavailable.</div>',
                    unsafe_allow_html=True,
                )

        llm_option_label = "Real LLM" if _key_available else "Real LLM (no key)"
        mode_options = ["Simulated", llm_option_label]
        current_mode = st.session_state.get("scoring_mode", "Simulated")
        current_idx  = 1 if current_mode == "Real LLM" else 0

        scol1, scol2 = st.columns([2, 3])
        with scol1:
            chosen = st.radio(
                "scoring_mode_radio",
                options=mode_options,
                index=current_idx,
                label_visibility="collapsed",
                help="Simulated uses keyword-weighted heuristics. Real LLM sends data to the configured AI endpoint.",
                disabled=not _key_available and current_mode != "Real LLM",
            )
            new_mode = "Real LLM" if chosen.startswith("Real LLM") and _key_available else "Simulated"
            if new_mode != current_mode:
                st.session_state.scoring_mode = new_mode
                st.rerun()
        with scol2:
            if new_mode == "Real LLM":
                key_note = "API key from environment variable." if _key_from_env else "API key entered for this session — not persisted."
                st.markdown(f"""
                <div style="background:#0d2b1a;border:1px solid #238636;border-radius:8px;padding:10px 14px;">
                  <div style="font-size:11px;font-weight:700;color:#3fb950;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Real LLM Active</div>
                  <div style="font-size:12px;color:#b0b8c4;">Model: <code style="color:#58a6ff;">{_FORGE_LLM_MODEL}</code></div>
                  <div style="font-size:12px;color:#b0b8c4;">Endpoint: <code style="color:#58a6ff;">{_FORGE_LLM_BASE_URL}</code></div>
                  <div style="font-size:11px;color:#8b949e;margin-top:4px;">{key_note} Uploaded PDFs are extracted and sent as context.</div>
                </div>""", unsafe_allow_html=True)
            else:
                if not _key_available and not _key_from_env:
                    st.markdown("""
                    <div style="background:#1c1207;border:1px solid #9e6a03;border-radius:8px;padding:10px 14px;">
                      <div style="font-size:11px;font-weight:700;color:#d29922;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Real LLM Unavailable</div>
                      <div style="font-size:12px;color:#8b949e;">Paste an API key above to unlock Real LLM scoring, or set the <code style="color:#58a6ff;">FORGE_LLM_API_KEY</code> environment variable for a persistent connection.</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:10px 14px;">
                      <div style="font-size:11px;font-weight:700;color:#8b949e;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Simulated Mode</div>
                      <div style="font-size:12px;color:#8b949e;">Uses keyword signals and rubric-anchored heuristics. Reproducible — same idea always scores the same. No API key required.</div>
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
