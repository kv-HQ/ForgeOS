---
title: Score multiple ideas at the same time — parallel processing for large batches
---
# Score multiple ideas at the same time — parallel processing for large batches

  ## What & Why
  The "Process All with AI" button scores submissions one at a time. In Real LLM mode with many submissions, this can take minutes. Concurrent API calls would dramatically reduce wait time for teams with large pipelines.

  ## Done looks like
  - "Process All with AI" fires LLM calls concurrently (e.g. up to 5 at once) using threading or asyncio
  - A live progress display shows which ideas are being scored simultaneously
  - Results are committed to session state as each call completes
  - Falls back to sequential if concurrent mode hits API rate limits

  ## Relevant files
  - `app.py` — run_bulk handler (~line 1867)
  - `app.py` — route_scoring() and ai_score_submission_llm() functions