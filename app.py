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

# ─── Design System v2 — Premium Redesign ─────────────────────────────────────
st.markdown("""
<style>
/* ══ Design Tokens ══════════════════════════════════════════════ */
:root {
  --bg:            #07101f;
  --surface:       #0b1626;
  --card:          #0f1e30;
  --card-hover:    #132438;
  --border:        #1a2f49;
  --border-soft:   #111e2f;
  --text-1:        #ddeaf8;
  --text-2:        #8aa4c0;
  --text-3:        #4e6680;
  --accent:        #3b82f6;
  --accent-dim:    rgba(59,130,246,0.10);
  --accent-glow:   rgba(59,130,246,0.20);
  --green:         #22c55e;
  --green-bg:      rgba(34,197,94,0.09);
  --green-border:  rgba(34,197,94,0.24);
  --amber:         #f59e0b;
  --amber-bg:      rgba(245,158,11,0.09);
  --amber-border:  rgba(245,158,11,0.24);
  --red:           #f43f5e;
  --red-bg:        rgba(244,63,94,0.09);
  --red-border:    rgba(244,63,94,0.24);
  --purple:        #a78bfa;
  --purple-bg:     rgba(167,139,250,0.09);
  --purple-border: rgba(167,139,250,0.24);
  --shadow-sm: 0 1px 5px rgba(0,0,16,0.55), 0 0 0 1px rgba(255,255,255,0.025);
  --shadow-md: 0 4px 20px rgba(0,0,16,0.60), 0 0 0 1px rgba(255,255,255,0.038);
  --shadow-lg: 0 10px 40px rgba(0,0,16,0.70), 0 0 0 1px rgba(255,255,255,0.05);
  --r-sm: 6px; --r-md: 10px; --r-lg: 14px;
  --ease: cubic-bezier(0.4,0,0.2,1); --dur: 140ms;
}

/* ══ Base overrides ═════════════════════════════════════════════ */
*, html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, sans-serif !important;
  -webkit-font-smoothing: antialiased !important;
}
.stApp { background: var(--bg) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-3); }

/* ══ Sidebar ════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #060f1e 0%, #050c18 100%) !important;
  border-right: 1px solid var(--border) !important;
  min-width: 220px !important; max-width: 220px !important;
}
[data-testid="stSidebar"] > div { padding: 0 !important; }
[data-testid="stSidebarContent"] { padding: 0 !important; }
[data-testid="stSidebar"] .stRadio > label { display: none !important; }
[data-testid="stSidebar"] .stRadio > div {
  display: flex !important; flex-direction: column !important;
  gap: 1px !important; padding: 0 8px !important;
}
[data-testid="stSidebar"] .stRadio > div > label {
  display: flex !important; align-items: center !important;
  padding: 7px 10px 7px 12px !important; border-radius: var(--r-sm) !important;
  margin: 1px 0 !important; cursor: pointer !important;
  font-size: 13px !important; font-weight: 500 !important;
  color: var(--text-2) !important;
  transition: all var(--dur) var(--ease) !important;
  border: none !important; border-left: 2px solid transparent !important;
}
[data-testid="stSidebar"] .stRadio > div > label:hover {
  background: rgba(59,130,246,0.08) !important;
  color: var(--text-1) !important;
  border-left-color: rgba(59,130,246,0.4) !important;
}
[data-testid="stSidebar"] .stRadio > div > label > div:first-child { display: none !important; }
[data-testid="stSidebar"] .stRadio > div > label > div:last-child > p {
  font-size: 13px !important; font-weight: 500 !important;
  color: inherit !important; margin: 0 !important;
}

/* ══ Top bar ════════════════════════════════════════════════════ */
.forge-topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px; height: 50px;
  border-bottom: 1px solid var(--border);
  background: rgba(7,16,31,0.93);
  backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
  position: sticky; top: 0; z-index: 100;
}
.forge-topbar-left { display: flex; align-items: center; gap: 12px; }
.forge-breadcrumb {
  font-size: 12px; color: var(--text-3); font-weight: 500;
  display: flex; align-items: center; gap: 7px;
}
.forge-breadcrumb span { color: var(--text-1); font-weight: 600; font-size: 14px; }
.forge-sep { color: var(--border); }
.forge-page-tag {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.09em; color: var(--accent);
  background: var(--accent-dim); border: 1px solid rgba(59,130,246,0.22);
  padding: 2px 9px; border-radius: 99px;
}
.forge-topbar-status {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; color: var(--text-3); font-weight: 500;
}
.forge-status-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--green); box-shadow: 0 0 7px var(--green);
  animation: pulse-dot 2.5s ease-in-out infinite;
}
@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:0.35} }

/* ══ Page content ═══════════════════════════════════════════════ */
.page-content { padding: 24px 28px 48px !important; }

/* ══ KPI card grid ══════════════════════════════════════════════ */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(152px, 1fr));
  gap: 12px; margin-bottom: 28px;
}
.kpi-card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: 18px 18px 16px;
  box-shadow: var(--shadow-sm); transition: all var(--dur) var(--ease);
  position: relative; overflow: hidden; cursor: default;
}
.kpi-card::after {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(59,130,246,0.55), transparent);
  opacity: 0; transition: opacity var(--dur) var(--ease);
}
.kpi-card:hover {
  border-color: rgba(59,130,246,0.3); transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
.kpi-card:hover::after { opacity: 1; }
.kpi-icon { font-size: 18px; margin-bottom: 10px; display: block; }
.kpi-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.09em; color: var(--text-3); margin-bottom: 8px;
}
.kpi-value {
  font-size: 30px; font-weight: 800; color: var(--text-1); line-height: 1;
  margin-bottom: 6px; font-variant-numeric: tabular-nums; letter-spacing: -0.03em;
}
.kpi-sub { font-size: 11px; color: var(--text-3); line-height: 1.4; }

/* ══ Stat strip (legacy fallback) ═══════════════════════════════ */
.stat-strip {
  border: 1px solid var(--border) !important; border-radius: var(--r-md) !important;
  background: var(--card) !important; box-shadow: var(--shadow-sm) !important;
  overflow: hidden !important;
}
.stat-item {
  padding: 18px 20px !important; border-right: 1px solid var(--border) !important;
  transition: background var(--dur) var(--ease) !important;
}
.stat-item:hover { background: var(--card-hover) !important; }
.stat-label {
  font-size: 10px !important; font-weight: 700 !important;
  text-transform: uppercase !important; letter-spacing: 0.09em !important;
  color: var(--text-3) !important; margin-bottom: 8px !important;
}
.stat-value {
  font-size: 26px !important; font-weight: 800 !important;
  color: var(--text-1) !important; letter-spacing: -0.025em !important;
  line-height: 1 !important; margin-bottom: 4px !important;
}
.stat-sub { font-size: 11px !important; color: var(--text-3) !important; }

/* ══ Section header ═════════════════════════════════════════════ */
.section-hd {
  font-size: 10px !important; font-weight: 700 !important;
  text-transform: uppercase !important; letter-spacing: 0.10em !important;
  color: var(--text-3) !important;
  margin: 28px 0 14px !important; padding-bottom: 10px !important;
  border-bottom: 1px solid var(--border-soft) !important;
  display: flex !important; align-items: center !important; gap: 10px !important;
}
.section-hd::before {
  content: ''; display: block; width: 3px; height: 12px;
  background: linear-gradient(180deg, var(--accent) 0%, #6366f1 100%);
  border-radius: 2px; flex-shrink: 0;
}

/* ══ Forge card ═════════════════════════════════════════════════ */
.forge-card {
  background: var(--card) !important; border: 1px solid var(--border) !important;
  border-radius: var(--r-md) !important; box-shadow: var(--shadow-sm) !important;
  transition: all var(--dur) var(--ease) !important;
}
.forge-card:hover {
  border-color: rgba(59,130,246,0.3) !important; box-shadow: var(--shadow-md) !important;
}

/* ══ Score badge ════════════════════════════════════════════════ */
.badge-score {
  display: inline-flex !important; align-items: center !important; gap: 4px !important;
  padding: 3px 9px !important; border-radius: var(--r-sm) !important;
  font-size: 12px !important; font-weight: 700 !important;
  font-variant-numeric: tabular-nums !important; letter-spacing: -0.01em !important;
}
.badge-green  { background: var(--green-bg)  !important; color: var(--green)  !important; border: 1px solid var(--green-border)  !important; }
.badge-yellow { background: var(--amber-bg)  !important; color: var(--amber)  !important; border: 1px solid var(--amber-border)  !important; }
.badge-red    { background: var(--red-bg)    !important; color: var(--red)    !important; border: 1px solid var(--red-border)    !important; }

/* ══ Status pill ════════════════════════════════════════════════ */
.pill {
  display: inline-block !important; padding: 3px 9px !important;
  border-radius: 99px !important; font-size: 11px !important;
  font-weight: 600 !important; letter-spacing: 0.02em !important;
}
.pill-new      { background: var(--accent-dim)  !important; color: #60a5fa     !important; border: 1px solid rgba(59,130,246,0.25)  !important; }
.pill-scored   { background: var(--green-bg)    !important; color: var(--green) !important; border: 1px solid var(--green-border)    !important; }
.pill-review   { background: var(--amber-bg)    !important; color: var(--amber) !important; border: 1px solid var(--amber-border)    !important; }
.pill-approved { background: var(--purple-bg)   !important; color: var(--purple)!important; border: 1px solid var(--purple-border)   !important; }
.pill-rejected { background: var(--red-bg)      !important; color: var(--red)   !important; border: 1px solid var(--red-border)      !important; }

/* ══ Table ══════════════════════════════════════════════════════ */
.forge-table { width: 100%; border-collapse: collapse; }
.forge-th {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.09em; color: var(--text-3); padding: 10px 14px;
  text-align: left; border-bottom: 1px solid var(--border);
  white-space: nowrap; background: rgba(7,16,31,0.55);
}
.forge-tr { border-bottom: 1px solid var(--border-soft); transition: background var(--dur) var(--ease); }
.forge-tr:last-child { border-bottom: none; }
.forge-tr:hover { background: rgba(59,130,246,0.05) !important; }
.forge-tr:nth-child(even) { background: rgba(255,255,255,0.012); }
.forge-td { padding: 11px 14px; font-size: 13px; color: var(--text-2); vertical-align: middle; }
.forge-td-primary { color: var(--text-1); font-weight: 500; }
.forge-id {
  font-size: 10px; font-weight: 700; color: var(--text-3);
  font-family: 'SF Mono','Fira Code','Consolas',monospace !important;
  background: var(--surface); padding: 3px 7px; border-radius: 4px;
  border: 1px solid var(--border); letter-spacing: 0.04em;
}

/* ══ Kanban ═════════════════════════════════════════════════════ */
.kanban-col-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 0 11px; margin-bottom: 12px; border-bottom: 1px solid var(--border-soft);
}
.kanban-col-name {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.10em; color: var(--text-2); display: flex; align-items: center; gap: 6px;
}
.kanban-count {
  font-size: 10px; font-weight: 700; color: var(--text-3);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 99px; padding: 1px 8px; min-width: 22px; text-align: center;
  font-variant-numeric: tabular-nums;
}
.kanban-card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--r-sm); padding: 11px 13px; margin-bottom: 7px;
  box-shadow: var(--shadow-sm); transition: all var(--dur) var(--ease);
  cursor: default; border-left-width: 3px;
}
.kanban-card:hover {
  border-color: rgba(59,130,246,0.32); box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
.kanban-card-title {
  font-size: 12px; font-weight: 500; color: var(--text-1);
  margin-bottom: 8px; line-height: 1.45;
}
.kanban-card-meta {
  font-size: 11px; color: var(--text-3);
  display: flex; align-items: center; flex-wrap: wrap; gap: 4px;
}
.kanban-empty {
  font-size: 12px; color: var(--text-3); text-align: center;
  padding: 22px 8px; border: 1px dashed var(--border);
  border-radius: var(--r-sm); background: rgba(255,255,255,0.01);
}

/* ══ Stage flow card (dashboard pipeline) ═══════════════════════ */
.stage-flow-card {
  background: var(--card); border: 1px solid var(--border);
  border-top-width: 2px; border-radius: var(--r-md);
  padding: 14px 10px 13px; text-align: center;
  box-shadow: var(--shadow-sm); transition: all var(--dur) var(--ease);
}
.stage-flow-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.stage-flow-icon { font-size: 20px; margin-bottom: 6px; display: block; }
.stage-flow-num {
  font-size: 28px; font-weight: 900; line-height: 1;
  margin-bottom: 5px; letter-spacing: -0.04em;
  font-variant-numeric: tabular-nums;
}
.stage-flow-name {
  font-size: 9px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.09em; color: var(--text-3);
}

/* ══ Upload zone ════════════════════════════════════════════════ */
[data-testid="stFileUploader"] {
  background: var(--card) !important;
  border: 1.5px dashed var(--border) !important;
  border-radius: var(--r-md) !important;
  transition: all var(--dur) var(--ease) !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: var(--accent) !important;
  background: rgba(59,130,246,0.03) !important;
}

/* ══ Buttons ════════════════════════════════════════════════════ */
.stButton > button {
  background: var(--surface) !important; color: var(--text-2) !important;
  border: 1px solid var(--border) !important; border-radius: var(--r-sm) !important;
  font-size: 12px !important; font-weight: 600 !important; padding: 6px 14px !important;
  transition: all var(--dur) var(--ease) !important; letter-spacing: 0.01em !important;
}
.stButton > button:hover {
  background: var(--card-hover) !important; border-color: rgba(59,130,246,0.38) !important;
  color: var(--text-1) !important; transform: translateY(-1px) !important;
  box-shadow: 0 2px 10px rgba(0,0,0,0.35) !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg,#3b82f6 0%,#2563eb 100%) !important;
  border-color: rgba(59,130,246,0.55) !important; color: #fff !important;
  box-shadow: 0 2px 10px rgba(59,130,246,0.30) !important;
}
.stButton > button[kind="primary"]:hover {
  box-shadow: 0 4px 22px rgba(59,130,246,0.48) !important;
  transform: translateY(-1px) !important;
}

/* ══ Inputs ═════════════════════════════════════════════════════ */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] input {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  border-radius: var(--r-sm) !important; color: var(--text-1) !important;
  font-size: 13px !important; transition: all var(--dur) var(--ease) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important; outline: none !important;
}

/* ══ Expander ═══════════════════════════════════════════════════ */
[data-testid="stExpander"] {
  background: var(--card) !important; border: 1px solid var(--border) !important;
  border-radius: var(--r-md) !important; box-shadow: var(--shadow-sm) !important;
  transition: border-color var(--dur) var(--ease) !important;
}
[data-testid="stExpander"]:hover { border-color: rgba(59,130,246,0.28) !important; }
[data-testid="stExpander"] summary {
  color: var(--text-2) !important; padding: 13px 18px !important;
}

/* ══ Progress & alerts ══════════════════════════════════════════ */
[data-testid="stProgress"] > div > div { border-radius: 99px !important; }
[data-testid="stAlert"] {
  background: var(--card) !important; border: 1px solid var(--border) !important;
  border-radius: var(--r-md) !important;
}

/* ══ Rubric criterion card ══════════════════════════════════════ */
.crit-card {
  background: var(--card) !important; border: 1px solid var(--border) !important;
  border-radius: var(--r-md) !important; box-shadow: var(--shadow-sm) !important;
  transition: all var(--dur) var(--ease) !important;
}
.crit-card:hover { border-color: rgba(59,130,246,0.30) !important; box-shadow: var(--shadow-md) !important; }
.crit-name { font-size: 13px !important; font-weight: 600 !important; color: var(--text-1) !important; }
.crit-desc { font-size: 12px !important; color: var(--text-3) !important; line-height: 1.55 !important; }
.crit-weight {
  background: var(--accent-dim) !important; color: var(--accent) !important;
  border: 1px solid rgba(59,130,246,0.25) !important;
}
.anchor-band {
  background: var(--surface) !important; border-radius: var(--r-sm) !important;
  padding: 8px 12px !important; color: var(--text-2) !important; font-size: 12px !important;
}
.anchor-low  { border-left: 3px solid var(--red)   !important; }
.anchor-mid  { border-left: 3px solid var(--amber) !important; }
.anchor-high { border-left: 3px solid var(--green) !important; }
.subfactor-tag {
  background: var(--surface) !important; border: 1px solid var(--border) !important;
  color: var(--text-3) !important;
}
.gate-rule {
  background: var(--red-bg) !important; border: 1px solid var(--red-border) !important;
  border-radius: var(--r-sm) !important;
}

/* ══ Sidebar custom HTML ════════════════════════════════════════ */
.sb-logo { padding: 16px 14px 14px; border-bottom: 1px solid var(--border); margin-bottom: 4px; }
.sb-wordmark {
  font-size: 15px; font-weight: 800; color: var(--text-1);
  letter-spacing: -0.04em; display: flex; align-items: center; gap: 9px;
}
.sb-logo-icon {
  width: 28px; height: 28px; flex-shrink: 0;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-size: 15px; box-shadow: 0 2px 14px rgba(59,130,246,0.40);
}
.sb-tag { font-size: 9px; letter-spacing: 0.07em; color: var(--text-3); margin-top: 2px; font-weight: 500; text-transform: uppercase; }
.sb-section-label {
  font-size: 9px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.13em; color: var(--text-3); padding: 14px 14px 5px;
}
.sb-divider { border-top: 1px solid var(--border); margin: 8px 0; }
.sb-stat-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 14px; font-size: 12px; }
.sb-stat-label { color: var(--text-3); }
.sb-stat-val   { color: var(--text-2); font-weight: 600; font-variant-numeric: tabular-nums; }

/* ══ Empty state ════════════════════════════════════════════════ */
.empty-state { text-align: center; padding: 72px 24px; }
.empty-icon  { font-size: 40px; margin-bottom: 16px; opacity: 0.13; display: block; }
.empty-title { font-size: 16px; font-weight: 600; color: var(--text-2); margin-bottom: 8px; }
.empty-sub   { font-size: 13px; color: var(--text-3); line-height: 1.65; }

/* ══ Misc overrides ═════════════════════════════════════════════ */
hr { border-color: var(--border) !important; margin: 14px 0 !important; }
[data-testid="stMarkdownContainer"] p { font-size: 13px; color: var(--text-2); line-height: 1.6; }
[data-testid="stCheckbox"] span { color: var(--text-2) !important; font-size: 13px !important; }
[data-testid="stFileUploader"] label { color: var(--text-3) !important; }
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
        paper_bgcolor="#0f1e30", plot_bgcolor="#0f1e30",
        height=height, margin=dict(l=10, r=10, t=24, b=4),
        font={"family": "Inter", "color": "#4e6680"},
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


def _vision_describe_image(img_bytes: bytes, filename: str, api_key: str, base_url: str, model: str) -> str:
    """
    Send an image to a vision-capable LLM and return a structured description.
    Raises RuntimeError on failure — caller handles fallback.
    """
    import base64 as _b64
    ext  = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp"}.get(ext, "image/jpeg")
    data_url = f"data:{mime};base64,{_b64.b64encode(img_bytes).decode()}"

    prompt = (
        "You are analyzing an uploaded file for a physical goods product innovation platform. "
        "Describe what you see in structured form covering: "
        "(1) Product or concept shown, "
        "(2) Key design or technical features visible, "
        "(3) Apparent materials or manufacturing process, "
        "(4) Market positioning signals. "
        "Be specific and technical. Max 200 words."
    )
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
        ]}],
        "max_tokens": 400,
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(
        url=f"{base_url}/chat/completions", data=payload, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise RuntimeError(f"Vision API: {exc}") from exc


def extract_file_text(
    uploaded_files,
    status_slot=None,
    use_llm_vision: bool = False,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
):
    """
    Rich multimodal content extraction.
    Returns (combined_text: str, summaries: list[dict]).

    Each summary dict keys:
      name, file_type, extraction_method, chars, pages (PDF),
      dimensions (image), thumbnail_b64 (image/video), preview, file_size_kb
    """
    import io as _io
    if not uploaded_files:
        return "", []

    parts: list = []
    summaries: list = []

    for f in uploaded_files:
        fname      = f.name
        flower     = fname.lower()
        ftype_mime = f.type or ""
        file_bytes = f.read()
        file_size_kb = round(len(file_bytes) / 1024, 1)

        summary: dict = {
            "name": fname, "file_type": "other", "extraction_method": "none",
            "chars": 0, "pages": None, "dimensions": None,
            "thumbnail_b64": None, "preview": "", "file_size_kb": file_size_kb,
        }

        if status_slot:
            status_slot.markdown(
                f'<div style="font-size:12px;color:#8b949e;padding:2px 0;">'
                f'⚙ Parsing <strong style="color:#e6edf3;">{fname}</strong> '
                f'<span style="color:#6e7681;">({file_size_kb} KB)</span></div>',
                unsafe_allow_html=True,
            )

        try:
            # ── PDF ──────────────────────────────────────────────────────────
            if flower.endswith(".pdf") or "pdf" in ftype_mime:
                summary["file_type"] = "pdf"
                text_pages: list = []
                page_count = 0
                method = "none"

                # Try PyMuPDF (layout-aware, handles columns/tables better)
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    page_count = doc.page_count
                    for pg in doc:
                        blocks = pg.get_text("blocks")
                        pg_text = "\n".join(
                            b[4].strip()
                            for b in sorted(blocks, key=lambda b: (b[1], b[0]))
                            if len(b) > 4 and b[4].strip()
                        )
                        if pg_text:
                            text_pages.append(f"[Page {pg.number + 1}]\n{pg_text}")
                    doc.close()
                    method = "PyMuPDF"
                except ImportError:
                    pass  # fall through to pypdf
                except Exception:
                    pass

                if not text_pages:
                    try:
                        import pypdf
                        reader = pypdf.PdfReader(_io.BytesIO(file_bytes))
                        page_count = len(reader.pages)
                        for pg in reader.pages:
                            t = pg.extract_text()
                            if t:
                                text_pages.append(t.strip())
                        method = "pypdf"
                    except Exception as pdf_err:
                        text_pages = [f"(Extraction failed: {pdf_err})"]
                        method = "error"

                combined_pdf = "\n\n".join(text_pages)
                label = f"[PDF: {fname} · {page_count} page(s) · via {method}]"
                parts.append(f"{label}\n{combined_pdf}")
                summary.update({
                    "extraction_method": method,
                    "chars": len(combined_pdf),
                    "pages": page_count,
                    "preview": combined_pdf[:400].replace("\n", " "),
                })

            # ── Image ─────────────────────────────────────────────────────────
            elif any(flower.endswith(x) for x in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
                summary["file_type"] = "image"
                from PIL import Image as _PILImage
                import base64 as _b64

                img = _PILImage.open(_io.BytesIO(file_bytes))
                w, h = img.size
                fmt  = img.format or flower.rsplit(".", 1)[-1].upper()

                # EXIF
                exif_lines: list = []
                try:
                    raw_exif = img._getexif()
                    if raw_exif:
                        from PIL.ExifTags import TAGS as _TAGS
                        wanted = {"Make", "Model", "DateTime", "Software"}
                        for tid, val in raw_exif.items():
                            tname = _TAGS.get(tid, "")
                            if tname in wanted:
                                exif_lines.append(f"{tname}: {str(val)[:80]}")
                except Exception:
                    pass

                # Thumbnail (for UI display)
                thumb = img.copy()
                thumb.thumbnail((240, 180), _PILImage.LANCZOS)
                if thumb.mode not in ("RGB", "L"):
                    thumb = thumb.convert("RGB")
                buf = _io.BytesIO()
                thumb.save(buf, format="JPEG", quality=75)
                thumb_b64 = _b64.b64encode(buf.getvalue()).decode()

                exif_str   = "; ".join(exif_lines) if exif_lines else "none"
                meta_text  = (
                    f"Image: {fname}\n"
                    f"Dimensions: {w}×{h} px  Format: {fmt}\n"
                    f"File size: {file_size_kb} KB\n"
                    f"EXIF: {exif_str}"
                )

                # LLM vision analysis
                vision_text = ""
                if use_llm_vision and api_key:
                    try:
                        vision_text = _vision_describe_image(file_bytes, fname, api_key, base_url, model)
                        method = "vision_llm+pillow"
                    except Exception as ve:
                        vision_text = f"(Vision analysis unavailable: {ve})"
                        method = "pillow_metadata"
                else:
                    method = "pillow_metadata"

                full_img_text = meta_text + (f"\n\nAI Visual Analysis:\n{vision_text}" if vision_text else "")
                parts.append(f"[Image: {fname}]\n{full_img_text}")
                summary.update({
                    "extraction_method": method,
                    "chars": len(full_img_text),
                    "dimensions": f"{w}×{h}",
                    "thumbnail_b64": thumb_b64,
                    "preview": (vision_text[:300] if vision_text and "unavailable" not in vision_text
                                else meta_text[:200]),
                })

            # ── Video ─────────────────────────────────────────────────────────
            elif any(flower.endswith(x) for x in (".mp4", ".mov", ".avi", ".webm", ".mkv")):
                summary["file_type"] = "video"
                ext_label = flower.rsplit(".", 1)[-1].upper()
                meta_text = (
                    f"Video file: {fname}\n"
                    f"Format: {ext_label}  File size: {file_size_kb} KB\n"
                    "Note: Full transcription not available. Score this submission based on "
                    "the idea name, notes, and any accompanying documents."
                )
                frame_note = ""
                thumb_b64  = None

                # Try cv2 for first-frame extraction (optional dependency)
                try:
                    import cv2 as _cv2
                    import tempfile, os as _os, base64 as _b64
                    from PIL import Image as _PILImage
                    with tempfile.NamedTemporaryFile(
                        suffix=f".{flower.rsplit('.', 1)[-1]}", delete=False
                    ) as tmp:
                        tmp.write(file_bytes)
                        tmp_path = tmp.name
                    cap = _cv2.VideoCapture(tmp_path)
                    fps         = cap.get(_cv2.CAP_PROP_FPS) or 25
                    total_fr    = int(cap.get(_cv2.CAP_PROP_FRAME_COUNT))
                    duration_s  = round(total_fr / fps, 1) if total_fr else 0
                    vid_w       = int(cap.get(_cv2.CAP_PROP_FRAME_WIDTH))
                    vid_h       = int(cap.get(_cv2.CAP_PROP_FRAME_HEIGHT))
                    ret, frame  = cap.read()
                    cap.release()
                    _os.unlink(tmp_path)
                    meta_text += f"\nResolution: {vid_w}×{vid_h}  Duration: {duration_s}s  FPS: {round(fps,1)}"
                    if ret:
                        rgb   = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)
                        pil_f = _PILImage.fromarray(rgb)
                        pil_f.thumbnail((240, 180), _PILImage.LANCZOS)
                        buf_f = _io.BytesIO()
                        pil_f.save(buf_f, format="JPEG", quality=75)
                        thumb_b64 = _b64.b64encode(buf_f.getvalue()).decode()
                        if use_llm_vision and api_key:
                            try:
                                buf_vis = _io.BytesIO()
                                pil_f.save(buf_vis, format="JPEG", quality=85)
                                frame_note = "\n\nFirst-frame visual analysis:\n" + _vision_describe_image(
                                    buf_vis.getvalue(), f"{fname}_frame.jpg", api_key, base_url, model
                                )
                            except Exception:
                                frame_note = "\n(First-frame vision analysis unavailable)"
                except ImportError:
                    pass
                except Exception:
                    pass

                full_vid_text = meta_text + frame_note
                parts.append(f"[Video: {fname}]\n{full_vid_text}")
                summary.update({
                    "extraction_method": "cv2+vision" if frame_note else ("cv2" if thumb_b64 else "metadata"),
                    "chars": len(full_vid_text),
                    "thumbnail_b64": thumb_b64,
                    "preview": full_vid_text[:200],
                })

            # ── Text / document ──────────────────────────────────────────────
            elif any(flower.endswith(x) for x in (".txt", ".md", ".csv", ".docx", ".doc")):
                summary["file_type"] = "text"
                if flower.endswith(".docx"):
                    try:
                        import docx as _docx
                        doc  = _docx.Document(_io.BytesIO(file_bytes))
                        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                        parts.append(f"[Document: {fname}]\n{text[:6000]}")
                        summary.update({
                            "extraction_method": "python-docx",
                            "chars": len(text),
                            "preview": text[:300],
                        })
                    except ImportError:
                        decoded = file_bytes.decode("utf-8", errors="replace")[:4000]
                        parts.append(f"[Document: {fname}]\n{decoded}")
                        summary.update({"extraction_method": "utf8", "chars": len(decoded), "preview": decoded[:300]})
                else:
                    decoded = file_bytes.decode("utf-8", errors="replace")[:6000]
                    parts.append(f"[Text: {fname}]\n{decoded}")
                    summary.update({"extraction_method": "utf8", "chars": len(decoded), "preview": decoded[:300]})

            # ── Fallback ─────────────────────────────────────────────────────
            else:
                try:
                    decoded = file_bytes.decode("utf-8", errors="replace")[:2000]
                    parts.append(f"[File: {fname}]\n{decoded}")
                    summary.update({"extraction_method": "utf8", "chars": len(decoded), "preview": decoded[:200]})
                except Exception:
                    parts.append(f"[File: {fname}] (binary — cannot extract text)")

        except Exception as outer_err:
            parts.append(f"[File: {fname}] (error: {outer_err})")
            summary["preview"] = f"Extraction error: {outer_err}"

        summaries.append(summary)

    return "\n\n".join(parts), summaries


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
            "file_summaries": [],
            "submitted_at":  base_dt.strftime("%Y-%m-%d"),
            "notes":         "",
        })

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sb-logo">
        <div class="sb-wordmark">
            <div class="sb-logo-icon">⚙</div>
            ForgeOS
        </div>
        <div class="sb-tag">Innovation OS · Physical Goods</div>
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

    st.markdown(f"""
    <div style="padding:16px 14px 12px;border-top:1px solid var(--border);margin-top:12px;">
        <div style="font-size:10px;font-weight:700;color:var(--text-3);text-transform:uppercase;letter-spacing:0.09em;">ForgeOS v0.2</div>
        <div style="font-size:10px;color:var(--text-3);margin-top:3px;">AI Scoring · Extensive Rubric v2</div>
        <div style="margin-top:10px;display:flex;align-items:center;gap:6px;">
          <div style="width:5px;height:5px;border-radius:50%;background:var(--green);box-shadow:0 0 6px var(--green);"></div>
          <span style="font-size:10px;color:var(--text-3);">Engine ready</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":

    st.markdown(f"""
    <div class="forge-topbar">
      <div class="forge-topbar-left">
        <div class="forge-breadcrumb">ForgeOS <span class="forge-sep">/</span> <span>Dashboard</span></div>
        <div class="forge-page-tag">Analytics</div>
      </div>
      <div class="forge-topbar-status">
        <div class="forge-status-dot"></div>
        {total} idea{"s" if total != 1 else ""} tracked
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-content">', unsafe_allow_html=True)

    # ── Apollo-style stat strip ───────────────────────────────────────────────
    avg_innov = round(sum(s["innovation"] for s in subs if s["innovation"] > 0) / max(sum(1 for s in subs if s["innovation"] > 0), 1), 1)
    avg_feas  = round(sum(s["feasibility"] for s in subs if s["feasibility"] > 0) / max(sum(1 for s in subs if s["feasibility"] > 0), 1), 1)

    _kpi_cols = st.columns(6)
    _kpi_items = [
        (_kpi_cols[0], "📋", "Total Ideas",      str(total),                                                                  "All ideas tracked",              "#ddeaf8"),
        (_kpi_cols[1], "📊", "Avg Score",         str(avg_score) if total else "—",                                           "Out of 100 points",              score_hex(avg_score) if total else "#4e6680"),
        (_kpi_cols[2], "🚀", "High Potential",    str(high_pot),                                                               f"Score ≥ {THRESHOLDS['green']}",  "#22c55e"),
        (_kpi_cols[3], "✅", "Approved",           str(approved),                                                               "Moving to production",           "#a78bfa"),
        (_kpi_cols[4], "💡", "Avg Innovation",    str(avg_innov) if avg_innov else "—",                                        "Innovation criterion",           score_hex(avg_innov) if avg_innov else "#4e6680"),
        (_kpi_cols[5], "🔧", "Avg Feasibility",   str(avg_feas) if avg_feas else "—",                                         "Manufacturing score",            score_hex(avg_feas) if avg_feas else "#4e6680"),
    ]
    for _col, _icon, _label, _val, _sub, _color in _kpi_items:
        with _col:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-icon">{_icon}</div>
                <div class="kpi-label">{_label}</div>
                <div class="kpi-value" style="color:{_color};">{_val}</div>
                <div class="kpi-sub">{_sub}</div>
            </div>""", unsafe_allow_html=True)

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
                    color_discrete_sequence=["#3b82f6"],
                )
                fig_hist.update_traces(marker_line_width=0)
                fig_hist.update_layout(
                    paper_bgcolor="#0f1e30", plot_bgcolor="#0f1e30",
                    font={"color": "#4e6680", "family": "Inter", "size": 11},
                    xaxis=dict(gridcolor="#1a2f49", color="#4e6680", title="Overall Score", showgrid=True),
                    yaxis=dict(gridcolor="#1a2f49", color="#4e6680", title="Count", showgrid=True),
                    height=230, margin=dict(l=0, r=0, t=8, b=0),
                    bargap=0.10,
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
                color_discrete_sequence=["#3b82f6","#22c55e","#f59e0b","#a78bfa","#f43f5e","#38bdf8","#fb923c"],
                hole=0.6,
            )
            fig_pie.update_layout(
                paper_bgcolor="#0f1e30", plot_bgcolor="#0f1e30",
                font={"color": "#4e6680", "family": "Inter", "size": 11},
                height=230, margin=dict(l=0, r=0, t=8, b=0),
                legend=dict(font=dict(color="#8aa4c0", size=11), bgcolor="#0f1e30", bordercolor="#1a2f49", borderwidth=1),
                showlegend=True,
            )
            fig_pie.update_traces(textfont_color="#ddeaf8", textfont_size=11)
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

        _STAGE_ICONS = {
            "Intake": "📥", "Concept": "💡", "Validation": "🔬",
            "Prototyping": "🛠", "Market Test": "📈", "Scaling": "⚡", "Monitoring": "📡",
        }
        cols = st.columns(len(STAGES))
        for stage, col in zip(STAGES, cols):
            cnt = stage_counts_map.get(stage["name"], 0)
            _ico = _STAGE_ICONS.get(stage["name"], "●")
            with col:
                st.markdown(f"""
                <div class="stage-flow-card" style="border-top-color:{stage['color']};">
                    <div class="stage-flow-icon">{_ico}</div>
                    <div class="stage-flow-num" style="color:{stage['color']};">{cnt}</div>
                    <div class="stage-flow-name">{stage['name']}</div>
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

    _sub_scored_ct = sum(1 for s in st.session_state.submissions if s["status"] not in ("New",))
    st.markdown(f"""
    <div class="forge-topbar">
      <div class="forge-topbar-left">
        <div class="forge-breadcrumb">ForgeOS <span class="forge-sep">/</span> <span>Submissions</span></div>
        <div class="forge-page-tag">Idea Intake</div>
      </div>
      <div class="forge-topbar-status">
        <div class="forge-status-dot"></div>
        {_sub_scored_ct} scored
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
                type=["pdf","png","jpg","jpeg","gif","webp","bmp","mp4","mov","avi","webm","txt","md","csv","docx"],
                accept_multiple_files=True,
                help="PDF (layout-aware extraction) · PNG/JPG/WebP (vision analysis) · MP4/MOV (metadata + first-frame) · TXT/CSV/DOCX",
            )
            # ── Instant file previews (before submit) ────────────────────
            if uploaded:
                import io as _preview_io
                from PIL import Image as _PreviewImage
                n_prev = min(len(uploaded), 5)
                prev_cols = st.columns(n_prev)
                _type_icons = {
                    "pdf": "📄", "mp4": "🎬", "mov": "🎬", "avi": "🎬",
                    "webm": "🎬", "txt": "📝", "md": "📝", "csv": "📊", "docx": "📝",
                }
                for pi, pf in enumerate(uploaded[:n_prev]):
                    with prev_cols[pi]:
                        pn = pf.name.lower()
                        pf.seek(0)
                        if any(pn.endswith(x) for x in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
                            try:
                                raw = pf.read()
                                img_prev = _PreviewImage.open(_preview_io.BytesIO(raw))
                                st.image(img_prev, caption=pf.name[:22], use_container_width=True)
                            except Exception:
                                st.markdown(f"🖼 `{pf.name[:20]}`")
                        else:
                            ext_p = pn.rsplit(".", 1)[-1] if "." in pn else "file"
                            icon_p = _type_icons.get(ext_p, "📎")
                            sz_p = round(pf.size / 1024, 1) if hasattr(pf, "size") else "?"
                            st.markdown(
                                f'<div style="border:1px solid #21262d;border-radius:6px;'
                                f'padding:8px 10px;text-align:center;font-size:12px;color:#8b949e;">'
                                f'<div style="font-size:22px;margin-bottom:4px;">{icon_p}</div>'
                                f'<div style="color:#e6edf3;font-weight:600;word-break:break-all;">{pf.name[:20]}</div>'
                                f'<div style="font-size:10px;margin-top:2px;">{ext_p.upper()} · {sz_p} KB</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                        pf.seek(0)
                if len(uploaded) > n_prev:
                    st.caption(f"+ {len(uploaded) - n_prev} more file(s)")

        with col_f2:
            init_stage = st.selectbox("Initial Stage", STAGE_NAMES)
            notes_txt  = st.text_area("Notes", height=96, placeholder="Brief context…")
            if uploaded and _llm_ready():
                use_vis = st.checkbox(
                    "🔍 Vision analysis for images",
                    value=True,
                    help="Uses LLM vision to describe image content. Requires Real LLM mode & API key.",
                )
            else:
                use_vis = False

        if st.button("Submit Idea"):
            if not idea_name.strip():
                st.error("Idea name is required.")
            else:
                ftypes = list({f.type.split("/")[-1].upper() for f in (uploaded or [])}) or ["—"]
                extracted    = ""
                file_summaries: list = []
                if uploaded:
                    with st.status("Parsing uploaded files…", expanded=True) as parse_status:
                        _slot = st.empty()
                        _is_llm_mode = st.session_state.get("scoring_mode", "Simulated AI") == "Real LLM"
                        extracted, file_summaries = extract_file_text(
                            uploaded,
                            status_slot=_slot,
                            use_llm_vision=(use_vis and _llm_ready() and _is_llm_mode),
                            api_key=_effective_llm_key(),
                            base_url=_FORGE_LLM_BASE_URL,
                            model=_FORGE_LLM_MODEL,
                        )
                        _slot.empty()
                        total_chars = sum(s["chars"] for s in file_summaries)
                        parse_status.update(
                            label=f"✅ {len(file_summaries)} file(s) parsed — {total_chars:,} chars extracted",
                            state="complete",
                        )
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
                    "file_summaries": file_summaries,
                })
                file_note = f" ({len(uploaded)} file(s) parsed)" if uploaded else ""
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
                bulk_start_time     = time.time()
                _completion_times_: list[float] = []
                completed_ids_:     set[str] = set()

                # Per-card state: id → {"name", "state": Pending/Scoring/Done, "score"}
                card_states_: dict = {
                    sub["id"]: {"name": sub["name"], "state": "Pending", "score": 0}
                    for sub in unscored
                }

                prog_bar    = st.progress(0.0)
                dash_header = st.empty()
                dash_grid   = st.empty()
                log_slot    = st.empty()

                # Accumulates plain-data log rows; each entry is a dict
                log_entries_: list[dict] = []

                # ── Thread-safe in-flight tracking ──────────────────────────────
                # active_ids: IDs whose worker is currently executing (not queued)
                active_ids  = set()
                active_lock = threading.Lock()

                def _render_bulk_dashboard_():
                    """Re-render the full card grid and ETA header."""
                    elapsed = time.time() - bulk_start_time
                    n_done  = len(completed_ids_)
                    n_left  = n - n_done
                    if n_done > 0:
                        avg_t   = elapsed / n_done
                        eta_sec = int(avg_t * n_left)
                        if eta_sec < 60:
                            eta_str = f"{eta_sec}s remaining"
                        else:
                            m_part  = eta_sec // 60
                            s_part  = eta_sec % 60
                            eta_str = f"{m_part}m {s_part}s remaining"
                    else:
                        eta_str = "calculating…"

                    dash_header.markdown(
                        f'<div style="display:flex;align-items:center;gap:16px;padding:8px 0 2px;">'
                        f'<span style="font-size:12px;color:#8b949e;">'
                        f'<strong style="color:#e6edf3">{n_done}</strong> / {n} scored'
                        f'</span>'
                        f'<span style="font-size:12px;color:#30363d;">|</span>'
                        f'<span style="font-size:12px;color:#8b949e;">&#9201; {eta_str}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    with active_lock:
                        scoring_ids = set(active_ids)

                    cards_html = ""
                    for cid, cs in card_states_.items():
                        raw_name  = cs["name"]
                        name_disp = (raw_name[:20] + "…") if len(raw_name) > 20 else raw_name
                        state     = "Scoring" if cid in scoring_ids else cs["state"]

                        if state == "Done":
                            sc_val = cs["score"]
                            color  = score_hex(sc_val)
                            badge  = (
                                f'<span style="font-size:10px;font-weight:600;color:{color};'
                                f'background:rgba(63,185,80,0.1);padding:2px 7px;border-radius:20px;">Done</span>'
                            )
                            score_disp = (
                                f'<div style="font-size:24px;font-weight:700;color:{color};'
                                f'line-height:1.1;margin-top:4px;">{sc_val}</div>'
                            )
                            card_bg = "rgba(63,185,80,0.04)"
                            border  = color
                        elif state == "Scoring":
                            badge  = (
                                '<span style="font-size:10px;font-weight:600;color:#58a6ff;'
                                'background:rgba(31,111,235,0.15);padding:2px 7px;border-radius:20px;">Scoring…</span>'
                            )
                            score_disp = '<div style="font-size:11px;color:#6e7681;margin-top:4px;">in progress</div>'
                            card_bg    = "rgba(31,111,235,0.05)"
                            border     = "#1f6feb"
                        else:
                            badge  = (
                                '<span style="font-size:10px;font-weight:600;color:#6e7681;'
                                'background:#21262d;padding:2px 7px;border-radius:20px;">Pending</span>'
                            )
                            score_disp = '<div style="font-size:11px;color:#484f58;margin-top:4px;">—</div>'
                            card_bg    = "#0d1117"
                            border     = "#30363d"

                        cards_html += (
                            f'<div style="background:{card_bg};border:1px solid {border};border-radius:8px;'
                            f'padding:10px 12px;min-height:80px;display:flex;flex-direction:column;'
                            f'justify-content:space-between;">'
                            f'<div style="font-size:12px;color:#e6edf3;font-weight:500;'
                            f'line-height:1.3;word-break:break-word;">{name_disp}</div>'
                            f'<div style="margin-top:6px;">{badge}{score_disp}</div>'
                            f'</div>'
                        )

                    dash_grid.markdown(
                        f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));'
                        f'gap:8px;padding:4px 0 10px;">{cards_html}</div>',
                        unsafe_allow_html=True,
                    )

                def _render_log_():
                    """Re-render the scrollable progress log panel."""
                    if not log_entries_:
                        log_slot.empty()
                        return
                    rows_html = ""
                    for entry in reversed(log_entries_):
                        name_disp = (entry["name"][:28] + "…") if len(entry["name"]) > 28 else entry["name"]
                        sc_val    = entry["score"]
                        sc_color  = score_hex(sc_val)
                        status    = entry["status"]
                        if status == "rate-limited":
                            badge_color = "#f85149"
                            badge_bg    = "rgba(248,81,73,0.12)"
                            badge_label = "Rate-limited"
                        elif status == "fallback":
                            badge_color = "#d29922"
                            badge_bg    = "rgba(210,153,34,0.12)"
                            badge_label = "Fallback"
                        else:
                            badge_color = "#3fb950"
                            badge_bg    = "rgba(63,185,80,0.12)"
                            badge_label = "Scored"
                        rows_html += (
                            f'<div style="display:flex;align-items:center;gap:10px;'
                            f'padding:5px 10px;border-bottom:1px solid #21262d;font-size:12px;">'
                            f'<span style="color:#484f58;min-width:50px;">{entry["ts"]}</span>'
                            f'<span style="color:#e6edf3;flex:1;white-space:nowrap;overflow:hidden;'
                            f'text-overflow:ellipsis;">{name_disp}</span>'
                            f'<span style="color:{sc_color};font-weight:700;min-width:32px;'
                            f'text-align:right;">{sc_val}</span>'
                            f'<span style="font-size:10px;font-weight:600;color:{badge_color};'
                            f'background:{badge_bg};padding:1px 7px;border-radius:20px;'
                            f'min-width:76px;text-align:center;">{badge_label}</span>'
                            f'</div>'
                        )
                    n_done = len(log_entries_)
                    panel_html = (
                        f'<details open style="margin-top:8px;">'
                        f'<summary style="cursor:pointer;font-size:12px;font-weight:600;'
                        f'color:#8b949e;padding:4px 2px;user-select:none;">'
                        f'Progress Log &nbsp;<span style="color:#58a6ff">{n_done}</span> / {n} completed'
                        f'</summary>'
                        f'<div style="max-height:180px;overflow-y:auto;background:#0d1117;'
                        f'border:1px solid #21262d;border-radius:6px;margin-top:4px;">'
                        f'{rows_html}'
                        f'</div>'
                        f'</details>'
                    )
                    log_slot.markdown(panel_html, unsafe_allow_html=True)

                # Initial render — all Pending
                _render_bulk_dashboard_()

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
                        completed_ids_.add(sub_id)
                        card_states_[sub_id]["state"] = "Done"
                        card_states_[sub_id]["score"] = sc["overall"]
                        log_status = "rate-limited" if is_rate else ("fallback" if warn else "scored")
                        log_entries_.append({
                            "ts":     datetime.now().strftime("%H:%M:%S"),
                            "name":   id_to_name.get(sub_id, sub_id),
                            "score":  sc["overall"],
                            "status": log_status,
                        })
                        _render_bulk_dashboard_()
                        _render_log_()

                # ── Sequential fallback for any still-New after rate-limit ──────
                still_new = [s for s in st.session_state.submissions if s["status"] == "New"]
                if still_new:
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
                        completed_ids_.add(sub["id"])
                        card_states_[sub["id"]]["state"] = "Done"
                        card_states_[sub["id"]]["score"] = sc["overall"]
                        log_entries_.append({
                            "ts":     datetime.now().strftime("%H:%M:%S"),
                            "name":   sub["name"],
                            "score":  sc["overall"],
                            "status": "fallback",
                        })
                        _render_bulk_dashboard_()
                        _render_log_()

                # ── Summary ────────────────────────────────────────────────────
                dash_header.empty()
                dash_grid.empty()
                log_slot.empty()
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

                    # ── Uploaded file summaries ──────────────────────────────
                    file_sums = sub.get("file_summaries", [])
                    if file_sums:
                        _ftype_icons = {
                            "pdf": "📄", "image": "🖼", "video": "🎬",
                            "text": "📝", "other": "📎",
                        }
                        _method_labels = {
                            "PyMuPDF": "PyMuPDF", "pypdf": "pypdf",
                            "vision_llm+pillow": "LLM Vision", "pillow_metadata": "Pillow",
                            "cv2+vision": "cv2 + Vision", "cv2": "cv2",
                            "metadata": "metadata", "utf8": "text", "python-docx": "docx",
                        }
                        st.markdown(
                            '<div style="font-size:10px;font-weight:700;color:#8b949e;'
                            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">'
                            '📎 Uploaded Files</div>',
                            unsafe_allow_html=True,
                        )
                        fs_cols = st.columns(min(len(file_sums), 3))
                        for fi, fs in enumerate(file_sums):
                            with fs_cols[fi % 3]:
                                ftype_ic = _ftype_icons.get(fs.get("file_type", "other"), "📎")
                                method_lbl = _method_labels.get(fs.get("extraction_method", ""), fs.get("extraction_method", "—"))
                                extra = ""
                                if fs.get("pages"):
                                    extra = f'{fs["pages"]} pages · '
                                if fs.get("dimensions"):
                                    extra = f'{fs["dimensions"]} · '
                                chars_lbl = f'{fs["chars"]:,} chars' if fs.get("chars") else "—"
                                size_lbl  = f'{fs["file_size_kb"]} KB' if fs.get("file_size_kb") else ""

                                if fs.get("thumbnail_b64"):
                                    st.markdown(
                                        f'<img src="data:image/jpeg;base64,{fs["thumbnail_b64"]}" '
                                        f'style="width:100%;border-radius:4px;margin-bottom:4px;">',
                                        unsafe_allow_html=True,
                                    )
                                st.markdown(
                                    f'<div style="background:#0d1117;border:1px solid #21262d;'
                                    f'border-radius:6px;padding:8px 10px;margin-bottom:8px;font-size:11px;">'
                                    f'<div style="font-weight:600;color:#e6edf3;margin-bottom:3px;">'
                                    f'{ftype_ic} {fs["name"][:30]}</div>'
                                    f'<div style="color:#8b949e;">{extra}{chars_lbl} · {size_lbl}</div>'
                                    f'<div style="color:#6e7681;font-size:10px;margin-top:2px;">'
                                    f'via {method_lbl}</div>'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )

                        # Extracted text preview (collapsible)
                        raw_text = sub.get("extracted_text", "")
                        if raw_text.strip():
                            with st.expander("📄 Extracted Content Preview", expanded=False):
                                st.code(raw_text[:3000] + ("…" if len(raw_text) > 3000 else ""), language=None)

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

    _pipe_total = len(st.session_state.submissions)
    st.markdown(f"""
    <div class="forge-topbar">
      <div class="forge-topbar-left">
        <div class="forge-breadcrumb">ForgeOS <span class="forge-sep">/</span> <span>Pipeline</span></div>
        <div class="forge-page-tag">7-Stage Flow</div>
      </div>
      <div class="forge-topbar-status">
        <div class="forge-status-dot"></div>
        {_pipe_total} in pipeline
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

    _KBOARD_ICONS = {
        "Intake": "📥", "Concept": "💡", "Validation": "🔬",
        "Prototyping": "🛠", "Market Test": "📈", "Scaling": "⚡", "Monitoring": "📡",
    }
    cols = st.columns(len(STAGES))
    for stage, col in zip(STAGES, cols):
        items = stage_map.get(stage["name"], [])
        with col:
            _kb_icon = _KBOARD_ICONS.get(stage["name"], "●")
            st.markdown(f"""
            <div class="kanban-col-header">
                <span class="kanban-col-name" style="color:{stage['color']}">{_kb_icon} {stage['name']}</span>
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
            paper_bgcolor="#0f1e30", plot_bgcolor="#0f1e30",
            font={"color": "#4e6680", "family": "Inter", "size": 11},
            xaxis=dict(gridcolor="#1a2f49", color="#4e6680", showgrid=False),
            yaxis=dict(gridcolor="#1a2f49", color="#4e6680", title="Submissions", showgrid=True),
            height=240, margin=dict(l=0, r=0, t=8, b=0),
            showlegend=False, bargap=0.25,
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
              <span style="width:108px;font-size:11px;color:var(--text-3);text-align:right;flex-shrink:0;font-weight:500;">{stage['name']}</span>
              <div style="flex:1;background:var(--surface);border-radius:99px;height:16px;overflow:hidden;border:1px solid var(--border);">
                <div style="width:{bar_w}%;background:{stage['color']};height:100%;border-radius:99px;
                            display:flex;align-items:center;padding-left:8px;min-width:22px;
                            box-shadow:0 0 8px {stage['color']}55;transition:width 0.4s ease;">
                  <span style="font-size:9px;color:rgba(0,0,0,0.75);font-weight:800;">{cnt if cnt else ''}</span>
                </div>
              </div>
              <span style="width:36px;font-size:11px;color:var(--text-3);font-weight:600;font-variant-numeric:tabular-nums;">{int(pct*100)}%</span>
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
        <div class="forge-breadcrumb">ForgeOS <span class="forge-sep">/</span> <span>Rubric Settings</span></div>
        <div class="forge-page-tag">Scoring Config</div>
      </div>
      <div class="forge-topbar-status">
        <div class="forge-status-dot"></div>
        Extensive Rubric v2
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
                paper_bgcolor="#0f1e30", plot_bgcolor="#0f1e30",
                font={"color": "#4e6680", "family": "Inter", "size": 11},
                xaxis=dict(gridcolor="#1a2f49", color="#4e6680", tickangle=-30, showgrid=False),
                yaxis=dict(gridcolor="#1a2f49", color="#4e6680", title="Weight (%)", showgrid=True),
                height=300, margin=dict(l=0, r=0, t=8, b=80),
            )
            st.plotly_chart(fig_w, use_container_width=True)

        with tab_json:
            st.json(rubric, expanded=False)
            st.info("Edit rubric.json and restart the app to apply changes.", icon="ℹ️")

    st.markdown('</div>', unsafe_allow_html=True)
