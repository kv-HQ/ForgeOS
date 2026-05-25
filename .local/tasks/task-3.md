---
title: Let users type in or paste a real API key without touching environment variables
---
# Let users type in or paste a real API key without touching environment variables

  ## What & Why
  Currently users must set FORGE_LLM_API_KEY as an environment variable, which requires platform knowledge. An in-app key entry form in Rubric Settings would let non-technical users unlock Real LLM mode instantly.

  ## Done looks like
  - A secure text input (password type) appears in Rubric Settings when no env key is detected
  - The entered key is stored in session state and used for LLM calls in that session
  - A clear note explains the key is not persisted to disk
  - The Real LLM option becomes selectable after a valid key is entered

  ## Relevant files
  - `app.py` — Rubric Settings page section (around the Scoring Mode toggle, ~line 2386)
  - `app.py` — _LLM_AVAILABLE flag and _FORGE_LLM_API_KEY constant (~line 15)