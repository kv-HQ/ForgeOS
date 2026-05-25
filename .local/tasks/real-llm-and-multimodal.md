# Real LLM Scoring + Multimodal Upload

## What & Why
Replace the simulated AI scoring engine with a real LLM (xAI Grok or OpenAI-compatible API), and improve the file uploader to extract text from PDFs and images so uploaded content actually informs the score. A toggle in Rubric Settings lets users switch between Simulated and Real LLM mode without restarting the app.

## Done looks like
- A "Scoring Mode" selector (Simulated / Real LLM) appears in Rubric Settings and persists in session state.
- When Real LLM mode is active, "AI Score" and "Process All with AI" send the idea name, notes, and any extracted file text to the configured LLM API endpoint with the full rubric as context.
- The model returns structured JSON with: 8 criterion scores (1–10), justifications, red flags, gating rule outcomes, and a weighted total — matching Extensive Rubric v2 exactly. The app parses and stores this just like the simulated result.
- If the API key is missing or the call fails, the app falls back to simulated scoring and shows a clear warning banner.
- The file uploader extracts plain text from PDFs (via `pdfminer.six` or `pypdf`) and passes it as additional context to the scorer. Images show a placeholder note ("Image uploaded — manual review recommended"). Video files show a similar placeholder.
- The `FORGE_LLM_API_KEY` and optionally `FORGE_LLM_BASE_URL` / `FORGE_LLM_MODEL` environment variables control the LLM connection. No keys are hard-coded.
- `requirements.txt` is updated with any new dependencies.
- The app remains stable: all existing simulated-mode behaviour is unchanged.

## Out of scope
- Persistent storage of scores across sessions (still in-memory).
- OCR for images (placeholder message only).
- Video transcription.
- UI redesign or changes outside Rubric Settings and the scoring flow.

## Steps
1. **Environment variable wiring** — Read `FORGE_LLM_API_KEY`, `FORGE_LLM_BASE_URL` (default to xAI endpoint), and `FORGE_LLM_MODEL` (default `grok-3`) at app startup; store availability flag in session/module scope.

2. **Scoring mode toggle** — Add a "Scoring Mode" radio/selectbox to the Rubric Settings page. Store choice in `st.session_state`. When Real LLM is chosen but no API key is found, show an inline warning and disable the option.

3. **LLM scoring function** — Write `ai_score_submission_llm(submission, rubric_data)` that: builds a structured system prompt embedding the full rubric JSON; sends the idea text (name + notes + extracted file text) as the user message; instructs the model to respond with a strict JSON schema (8 criteria, score, justification, red_flags, gating_pass, weighted_total); parses and validates the response; falls back to the existing simulated function on any error.

4. **Route scoring calls** — In the "AI Score" button handler and the "Process All with AI" loop, check `st.session_state.scoring_mode` and call either `ai_score_submission_llm` or the existing `ai_score_submission` accordingly.

5. **PDF text extraction** — On file upload, attempt to extract text from PDFs using `pypdf` (lightweight). Store extracted text on the submission object (`submission["extracted_text"]`). Pass this to the scorer as additional context.

6. **Image and video placeholders** — For image files, append a note to `extracted_text` saying content requires manual visual review. For video files, append a similar placeholder. This ensures the LLM prompt always has a consistent context field.

7. **Dependency update** — Add `pypdf` (and `httpx` or use stdlib `urllib` for the LLM call if not already present) to `requirements.txt`.

## Relevant files
- `app.py`
- `rubric.json`
- `requirements.txt`
