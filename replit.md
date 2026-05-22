# ForgeOS

AI Agentic Innovation OS for Physical Goods Companies — score, track, and manage product innovation ideas through a 7-stage pipeline using an AI-powered rubric.

## Run & Operate

- `streamlit run app.py` — run ForgeOS (port 5000, configured in `.streamlit/config.toml`)
- The **ForgeOS** workflow in Replit handles this automatically.

## Stack

- Python 3.11 + Streamlit 1.45
- Plotly for gauges and charts
- Pandas for data handling
- No database — session state (in-memory); persistence can be added later

## Where things live

- `app.py` — entire app (sidebar nav, Dashboard, Submissions, Pipeline, Rubric Settings)
- `rubric.json` — scoring rubric: categories, weights, criteria, thresholds, pipeline stages
- `.streamlit/config.toml` — Streamlit server config (port 5000, dark theme)
- `requirements.txt` — Python dependencies

## Product

ForgeOS has four sections:

1. **Dashboard** — KPI cards (total submissions, avg score, high-potential count, approved count), score distribution histogram, status pie chart, recent submissions list, pipeline snapshot.
2. **Submissions** — File uploader (PDF, image, video, text), idea submission form, sortable/filterable table with inline progress bars, per-submission score gauges, AI Score / Advance Stage / Delete actions, bulk "Process All with AI" button.
3. **Pipeline** — 7-stage flow (Intake → Concept → Validation → Prototyping → Market Test → Scaling → Monitoring) with counts, avg scores, bar chart, per-stage submission list, and a conversion funnel.
4. **Rubric Settings** — Category weight chart, per-criterion detail cards, raw JSON view, threshold bands (green/yellow/red).

## Architecture decisions

- All scoring is simulated AI (random within plausible range weighted by rubric); swap `ai_score_submission()` in `app.py` for a real LLM call when ready.
- Rubric is loaded from `rubric.json` at startup (cached); editing the file + restarting the app applies changes immediately.
- Session state stores submissions in memory — add a database (SQLite or Postgres) for persistence.
- All CSS is injected via `st.markdown(unsafe_allow_html=True)` using a single `<style>` block at the top of `app.py`.

## Gotchas

- Never use backslash escapes inside nested f-strings in Python 3.11 — extract to a variable first.
- The `.streamlit/config.toml` is managed by Replit's Streamlit module; do not change `port` or `address`.
- `pnpm-workspace` tooling (api-server, mockup-sandbox) is separate infrastructure — ForgeOS does not use it.

## User preferences

- Premium dark UI: blues/greens/neutrals, Mobbin-style admin dashboard.
- Score color bands: green ≥ 70, yellow 50–69, red < 50.
- Run with `streamlit run app.py`.
