"""
Unit tests for criterion deep-dive expand state and content generation.

Run: python -m unittest tests.test_criterion_expand -v
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent.parent
APP_PATH = ROOT / "app.py"


def _load_app_namespace():
    """Import app.py with Streamlit mocked so page code does not require a server."""
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
            "nav_page": "Home",
            "shortlist": {},
            "investment_memos": {},
            "criterion_detail_cache": {},
            "criterion_detail_force": False,
            "criterion_deep_dive_active": None,
            "criterion_deep_dive_sub_id": None,
            "criterion_deep_dive_criterion": None,
            "next_id": 1,
            "scoring_mode": "Simulated AI",
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
    mock_st.success = lambda *args, **kwargs: None
    mock_st.info = lambda *args, **kwargs: None
    mock_st.warning = lambda *args, **kwargs: None
    mock_st.error = lambda *args, **kwargs: None
    mock_st.spinner = MagicMock()
    mock_st.spinner.return_value.__enter__ = lambda self: self
    mock_st.spinner.return_value.__exit__ = lambda *args: None
    def _cache_data(*args, **kwargs):
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        return lambda fn: fn

    mock_st.cache_data = _cache_data
    mock_st.dialog = lambda *args, **kwargs: (lambda fn: fn)
    mock_st.rerun = lambda: None
    mock_st.container = MagicMock()
    mock_st.container.return_value.__enter__ = lambda self: self
    mock_st.container.return_value.__exit__ = lambda *args: None

    sys.modules["streamlit"] = mock_st

    ns = {
        "__name__": "forge_app_test",
        "__file__": str(APP_PATH),
        "st": mock_st,
    }
    exec(compile(source, str(APP_PATH), "exec"), ns)
    return ns, mock_st


class CriterionExpandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns, cls.mock_st = _load_app_namespace()

    def setUp(self):
        self.mock_st.session_state.clear()
        self.mock_st.session_state.update(
            {
                "submissions": [],
                "nav_page": "Submissions",
                "memo_sub_id": "FOS-1",
                "memo_needs_generate": True,
                "investment_memos": {},
                "criterion_detail_cache": {},
                "criterion_detail_force": False,
                "criterion_deep_dive_active": None,
                "criterion_deep_dive_sub_id": None,
                "criterion_deep_dive_criterion": None,
            }
        )

    def test_panel_key_format(self):
        key = self.ns["_criterion_panel_key"]("FOS-9", "Market Opportunity")
        self.assertEqual(key, "deep_dive_FOS-9_market_opportunity")
        other = self.ns["_criterion_panel_key"]("FOS-9", "Technical Feasibility")
        self.assertNotEqual(key, other)

    def test_open_sets_unique_session_key(self):
        self.ns["_open_criterion_deep_dive"]("FOS-2", "Innovation")
        key = self.ns["_criterion_panel_key"]("FOS-2", "Innovation")
        self.assertEqual(self.mock_st.session_state["criterion_deep_dive_active"], key)
        self.assertEqual(self.mock_st.session_state["criterion_deep_dive_sub_id"], "FOS-2")
        self.assertEqual(self.mock_st.session_state["criterion_deep_dive_criterion"], "Innovation")
        self.assertTrue(self.mock_st.session_state["criterion_detail_force"])

    def test_open_clears_memo_but_not_other_criterion(self):
        self.ns["_open_criterion_deep_dive"]("FOS-3", "Innovation")
        key_a = self.ns["_criterion_panel_key"]("FOS-3", "Innovation")
        self.ns["_open_criterion_deep_dive"]("FOS-3", "Feasibility")
        key_b = self.ns["_criterion_panel_key"]("FOS-3", "Feasibility")
        self.assertEqual(self.mock_st.session_state["criterion_deep_dive_active"], key_b)
        self.assertNotEqual(key_a, key_b)
        self.assertIsNone(self.mock_st.session_state.get("memo_sub_id"))
        self.assertFalse(self.mock_st.session_state.get("memo_needs_generate"))

    def test_upload_panel_does_not_auto_close_deep_dive(self):
        """Regression: typing in New Submission must not clear an open deep dive."""
        self.ns["_open_criterion_deep_dive"]("FOS-4", "Traction")
        idea_name = "New coating idea"
        uploaded = ["fake-file.pdf"]
        self.assertTrue(idea_name.strip() or uploaded)
        self.assertIsNotNone(self.mock_st.session_state.get("criterion_deep_dive_active"))

    def test_is_open_matches_submission_and_criterion(self):
        self.ns["_open_criterion_deep_dive"]("FOS-5", "Innovation")
        self.assertTrue(self.ns["_is_criterion_deep_dive_open"]("FOS-5", "Innovation"))
        self.assertFalse(self.ns["_is_criterion_deep_dive_open"]("FOS-5", "Feasibility"))

    def test_close_submission_only_closes_matching_keys(self):
        self.ns["_open_criterion_deep_dive"]("FOS-6", "Innovation")
        self.assertEqual(self.mock_st.session_state["criterion_deep_dive_sub_id"], "FOS-6")
        self.ns["_close_criterion_deep_dives_for_submission"]("FOS-6")
        self.assertIsNone(self.mock_st.session_state.get("criterion_deep_dive_active"))

        self.ns["_open_criterion_deep_dive"]("FOS-7", "Innovation")
        self.ns["_close_criterion_deep_dives_for_submission"]("FOS-6")
        self.assertEqual(self.mock_st.session_state["criterion_deep_dive_sub_id"], "FOS-7")

    def test_local_deep_dive_contains_required_sections(self):
        rubric = json.loads((ROOT / "rubric.json").read_text(encoding="utf-8"))
        crit_name = rubric["criteria"][0]["criterion"]
        submission = {
            "id": "FOS-10",
            "name": "Test Widget",
            "notes": (
                "Our widget uses recycled aluminum and ships through direct-to-consumer channels. "
                "Early customers report strong repeat purchase intent."
            ),
            "extracted_text": "",
            "categories": {
                crit_name: {
                    "score": 72,
                    "score_10": 7.2,
                    "weight": 15,
                    "evidence": "Partial",
                    "justification": "Solid concept with partial supporting evidence.",
                    "red_flags": [],
                }
            },
        }
        md = self.ns["_generate_criterion_detail_local"](submission, crit_name, rubric)
        for heading in (
            "## Summary",
            "## Score Rationale",
            "## Rubric Anchor Analysis",
            "## Evidence from Submission",
            "## Flags & Highlights",
        ):
            self.assertIn(heading, md)
        self.assertIn("After reviewing", md)
        self.assertIn("1-3", md)
        self.assertIn("7-10", md)
        self.assertIn("Test Widget", md)
        self.assertIn(crit_name, md)

    def test_generate_criterion_detail_fallback_without_api_key(self):
        rubric = json.loads((ROOT / "rubric.json").read_text(encoding="utf-8"))
        crit_name = rubric["criteria"][1]["criterion"]
        submission = {
            "id": "FOS-11",
            "name": "Packaging Prototype",
            "notes": "Compostable mailers validated in pilot shipments across three regions.",
            "extracted_text": "",
            "categories": {
                crit_name: {
                    "score": 55,
                    "score_10": 5.5,
                    "weight": 12,
                    "evidence": "Partial",
                    "justification": "Moderate score pending stronger proof points.",
                    "red_flags": [],
                }
            },
        }
        self.mock_st.session_state["session_llm_key"] = ""
        self.assertFalse(self.ns["_llm_ready"]())
        md, source, warning = self.ns["generate_criterion_detail"](submission, crit_name, rubric)
        self.assertEqual(source, "structured")
        self.assertIn("## Summary", md)
        self.assertIsNotNone(warning)


if __name__ == "__main__":
    unittest.main()
