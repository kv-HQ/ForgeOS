"""
Unit tests for bulk submission upload helpers.

Run: python -m unittest tests.test_bulk_upload -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent.parent
APP_PATH = ROOT / "app.py"


def _load_app_namespace():
    source = APP_PATH.read_text(encoding="utf-8")

    class SessionState(dict):
        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError as exc:
                raise AttributeError(name) from exc

        def __setattr__(self, name, value):
            self[name] = value

    mock_st = MagicMock()
    mock_st.session_state = SessionState(
        {
            "submissions": [],
            "next_id": 1001,
            "bulk_upload_row_ids": [0],
            "bulk_upload_next_row_id": 1,
            "scoring_mode": "Simulated AI",
            "session_llm_key": "",
        }
    )
    mock_st.set_page_config = lambda **kwargs: None
    mock_st.markdown = lambda *args, **kwargs: None
    mock_st.sidebar = MagicMock()
    mock_st.sidebar.__enter__ = lambda self: self
    mock_st.sidebar.__exit__ = lambda *args: None
    mock_st.radio = lambda *args, **kwargs: "Home"
    mock_st.query_params = MagicMock()
    mock_st.query_params.get = lambda key, default=None: default
    mock_st.button = lambda *args, **kwargs: False
    mock_st.columns = lambda spec: [MagicMock() for _ in (range(spec) if isinstance(spec, int) else spec)]
    mock_st.expander = MagicMock()
    mock_st.expander.return_value.__enter__ = lambda self: self
    mock_st.expander.return_value.__exit__ = lambda *args: None
    mock_st.plotly_chart = lambda *args, **kwargs: None
    mock_st.cache_data = lambda fn: fn
    mock_st.dialog = lambda *args, **kwargs: (lambda fn: fn)
    mock_st.rerun = lambda: None

    sys.modules["streamlit"] = mock_st
    ns = {"__name__": "forge_app_test", "__file__": str(APP_PATH), "st": mock_st}
    exec(compile(source, str(APP_PATH), "exec"), ns)
    return ns, mock_st


class BulkUploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns, cls.mock_st = _load_app_namespace()

    def setUp(self):
        self.mock_st.session_state.clear()
        self.mock_st.session_state.update(
            {
                "submissions": [],
                "next_id": 1001,
                "bulk_upload_row_ids": [0, 1],
                "bulk_upload_next_row_id": 2,
                "scoring_mode": "Simulated AI",
                "session_llm_key": "",
            }
        )
        self.mock_st.session_state["bulk_name_0"] = "Idea Alpha"
        self.mock_st.session_state["bulk_name_1"] = "Idea Beta"
        self.mock_st.session_state["bulk_notes_0"] = "Notes A"
        self.mock_st.session_state["bulk_notes_1"] = "Notes B"

    def test_append_submission_creates_record(self):
        sid, fc, chars = self.ns["_append_submission_from_upload"](
            "Smart Bottle Cap",
            "Pilot notes",
            "Intake",
            None,
            False,
        )
        self.assertEqual(sid, "FOS-1001")
        self.assertEqual(fc, 0)
        self.assertEqual(chars, 0)
        self.assertEqual(len(self.mock_st.session_state["submissions"]), 1)
        sub = self.mock_st.session_state["submissions"][0]
        self.assertEqual(sub["name"], "Smart Bottle Cap")
        self.assertEqual(sub["notes"], "Pilot notes")
        self.assertEqual(sub["stage"], "Intake")

    def test_reset_bulk_upload_form_clears_row_keys(self):
        self.ns["_reset_bulk_upload_form"]()
        self.assertEqual(self.mock_st.session_state["bulk_upload_row_ids"], [0])
        self.assertIsNone(self.mock_st.session_state.get("bulk_name_1"))
        self.assertIsNone(self.mock_st.session_state.get("bulk_notes_1"))


if __name__ == "__main__":
    unittest.main()
