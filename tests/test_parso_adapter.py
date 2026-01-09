import pytest

from src.extensions.parso import run_stage3_demo, run_stage4_demo


def test_run_stage3_demo_in_process():
    stats = run_stage3_demo(demo=True)
    assert isinstance(stats, dict)
    assert "processed_events" in stats or "active_users" in stats


def test_run_stage4_demo_in_process():
    out = run_stage4_demo(demo=True)
    assert isinstance(out, dict)
    assert "results" in out and "stats" in out
    assert isinstance(out["results"], list)
    assert isinstance(out["stats"], dict)
