from unittest.mock import MagicMock

import pytest
from mcp_core.engine.quality_gate import QualityGate


@pytest.fixture
def gate():
    return QualityGate()


def test_check_score_only_all_pass(gate):
    # Mock processor to pass
    gate.processor.lint = MagicMock(return_value=(True, []))
    gate.processor.format_check = MagicMock(return_value=(True, "OK"))

    report = gate.check_score_only("test_func", "def hello(): pass", "desc")
    assert report["final_score"] == 100
    assert report["reliability"] == "high"
    assert report["linter"]["passed"] is True
    assert report["formatter"]["passed"] is True


def test_check_score_only_lint_fail(gate):
    # Mock processor to fail with 2 errors (10 pts each, max 70 penalty)
    gate.processor.lint = MagicMock(return_value=(False, ["Error 1", "Error 2"]))
    gate.processor.format_check = MagicMock(return_value=(True, "OK"))

    report = gate.check_score_only("test_func", "def hello(): pass", "desc")
    # Score: 100 - penalty(70) = 30 (since 2 errors in 1 line exceeds max penalty)
    assert report["final_score"] == 30
    assert report["linter"]["passed"] is False


def test_check_score_only_formatter_fail(gate):
    gate.processor.lint = MagicMock(return_value=(True, []))
    gate.processor.format_check = MagicMock(return_value=(False, "Need formatting"))

    report = gate.check_score_only("test_func", "def hello(): pass", "desc")
    # Score: 100 - 30 = 70
    assert report["final_score"] == 70
    assert report["reliability"] == "medium"
    assert report["formatter"]["passed"] is False
