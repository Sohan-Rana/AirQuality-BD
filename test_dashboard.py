from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app" / "dashboard.py")


def test_dashboard_runs_without_errors():
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
    assert any("SYNTHETIC" in w.value for w in at.warning)
    assert len(at.tabs) == 6
